const NATIVE_HOST = "fr.tubesave.chrome";
const SETTINGS_VERSION = 6;
const QUALITY_KEYS = new Set(["best", "audio", "1080", "720", "480"]);
const DESTINATION_KEYS = new Set(["downloads", "movies", "desktop", "custom", "premiere"]);
const NETWORK_MEDIA_PREFIX = "tubeSaveNetworkMedia:";
const NETWORK_MEDIA_TTL = 30 * 60 * 1000;
const TF1_PENDING_PREFIX = "tubeSaveTf1Pending:";
const TF1_STATUS_PREFIX = "tubeSaveTf1Status:";
const ACTIVE_JOB_PREFIX = "clipFlowActiveJob:";
const TF1_PENDING_TTL = 2 * 60 * 1000;
const JOB_POLL_INTERVAL = 700;
let networkMediaWrites = Promise.resolve();
const tf1HlsRequests = new Set();
const activeJobPollers = new Map();

function networkMediaKey(tabId) {
  return `${NETWORK_MEDIA_PREFIX}${tabId}`;
}

function tf1PendingKey(tabId) {
  return `${TF1_PENDING_PREFIX}${tabId}`;
}

function tf1StatusKey(tabId) {
  return `${TF1_STATUS_PREFIX}${tabId}`;
}

function activeJobKey(tabId) {
  return `${ACTIVE_JOB_PREFIX}${tabId}`;
}

async function rememberActiveJob(tabId, response) {
  if (!Number.isInteger(tabId) || tabId < 0 || typeof response?.jobId !== "string") return;
  await chrome.storage.session.set({
    [activeJobKey(tabId)]: {
      jobId: response.jobId,
      destinationLabel: response.destinationLabel || "Téléchargements",
      state: "queued",
      progress: 1,
      message: "Préparation…",
      updatedAt: Date.now(),
    },
  });
  monitorActiveJob(tabId, response.jobId);
}

async function updateJobBadge(tabId, response) {
  const badgeText = response.state === "complete"
    ? "✓"
    : response.state === "error" || response.state === "cancelled"
      ? "!"
      : `${Math.max(1, Math.min(99, Number(response.progress) || 1))}%`;
  await chrome.action.setBadgeText({ tabId, text: badgeText });
  await chrome.action.setBadgeBackgroundColor({
    tabId,
    color: response.state === "complete" ? "#248a3d" : response.state === "error" ? "#d70015" : "#0a84ff",
  });
}

function stopActiveJobMonitor(tabId) {
  const current = activeJobPollers.get(tabId);
  if (current?.timer) clearTimeout(current.timer);
  activeJobPollers.delete(tabId);
}

function monitorActiveJob(tabId, jobId) {
  if (!Number.isInteger(tabId) || tabId < 0 || typeof jobId !== "string" || !jobId) return;
  stopActiveJobMonitor(tabId);
  const token = { jobId, timer: null };
  activeJobPollers.set(tabId, token);

  const poll = async () => {
    if (activeJobPollers.get(tabId) !== token) return;
    try {
      const response = await sendNativeMessage({ action: "status", jobId });
      const key = activeJobKey(tabId);
      const stored = await chrome.storage.session.get(key);
      if (stored[key]?.jobId === jobId) {
        await chrome.storage.session.set({
          [key]: {
            ...stored[key],
            state: response.state,
            progress: response.progress,
            message: response.message,
            updatedAt: Date.now(),
          },
        });
      }
      await updateJobBadge(tabId, response);
      if (["complete", "error", "cancelled"].includes(response.state)) {
        stopActiveJobMonitor(tabId);
        return;
      }
    } catch (_error) {
      // Le prochain passage reprend automatiquement après un redémarrage bref
      // du moteur local ou du service worker Manifest V3.
    }
    if (activeJobPollers.get(tabId) === token) {
      token.timer = setTimeout(poll, JOB_POLL_INTERVAL);
    }
  };
  poll();
}

async function resumeActiveJobMonitors() {
  const stored = await chrome.storage.session.get(null);
  Object.entries(stored).forEach(([key, job]) => {
    if (!key.startsWith(ACTIVE_JOB_PREFIX) || typeof job?.jobId !== "string") return;
    if (["complete", "error", "cancelled"].includes(job.state)) return;
    const tabId = Number(key.slice(ACTIVE_JOB_PREFIX.length));
    if (Number.isInteger(tabId) && tabId >= 0) monitorActiveJob(tabId, job.jobId);
  });
}

function setTf1Status(tabId, state, message) {
  return chrome.storage.session.set({
    [tf1StatusKey(tabId)]: { state, message, updatedAt: Date.now() },
  });
}

function responseHeader(headers, name) {
  return (headers || []).find((header) => header.name?.toLowerCase() === name)?.value || "";
}

function requestHeader(headers, name) {
  return (headers || []).find((header) => header.name?.toLowerCase() === name)?.value || "";
}

function hlsManifestHasDrm(manifest) {
  return String(manifest || "").split(/\r?\n/).some((line) => {
    if (!/^#EXT-X-(?:SESSION-)?KEY:/i.test(line)) return false;
    return /URI=["']?skd:\/\//i.test(line)
      || /KEYFORMAT=["']?(?:com\.apple\.streamingkeydelivery|com\.microsoft\.playready)/i.test(line)
      || /KEYFORMAT=["']?urn:uuid:(?:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed|9a04f079-9840-4286-ab92-e65be0885f95)/i.test(line);
  });
}

async function inspectHlsDrm(streamUrl) {
  const pending = [streamUrl];
  const visited = new Set();
  let checked = false;
  while (pending.length && visited.size < 4) {
    const currentUrl = pending.shift();
    if (!currentUrl || visited.has(currentUrl)) continue;
    visited.add(currentUrl);
    try {
      const response = await fetch(currentUrl, { cache: "no-store", credentials: "omit" });
      if (!response.ok) continue;
      const manifest = await response.text();
      checked = true;
      if (hlsManifestHasDrm(manifest)) return true;
      for (const rawLine of manifest.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#") || !/\.m3u8(?:$|[?#])/i.test(line)) continue;
        try { pending.push(new URL(line, currentUrl).href); } catch (_error) { /* manifeste invalide */ }
      }
    } catch (_error) {
      // yt-dlp effectuera la vérification si Chrome ne peut pas lire le manifeste.
    }
  }
  return checked ? false : null;
}

function dashManifestHasDrm(manifest) {
  const text = String(manifest || "");
  if (!/<(?:[\w.-]+:)?ContentProtection\b/i.test(text)) return false;
  return /schemeIdUri\s*=\s*["']urn:mpeg:dash:mp4protection:2011["']/i.test(text)
    || /schemeIdUri\s*=\s*["']urn:uuid:(?:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed|9a04f079-9840-4286-ab92-e65be0885f95|94ce86fb-07ff-4f43-adb8-93d2fa968ca2|e2719d58-a985-b3c9-781a-b030af78d30e)["']/i.test(text)
    || /<(?:[\w.-]+:)?pssh\b/i.test(text)
    || /<mspr:pro\b/i.test(text);
}

async function inspectDashDrm(streamUrl) {
  try {
    const response = await fetch(streamUrl, { cache: "no-store", credentials: "omit" });
    if (!response.ok) return null;
    return dashManifestHasDrm(await response.text());
  } catch (_error) {
    // yt-dlp effectuera la vérification si Chrome ne peut pas lire le manifeste.
    return null;
  }
}

function networkMediaKind(url, contentType) {
  let parsed;
  try { parsed = new URL(url); } catch (_error) { return ""; }
  const path = parsed.pathname.toLowerCase();
  const mime = String(contentType || "").toLowerCase();
  if (/\.(?:m4s|cmfv|cmfa|ts)(?:$|[?#])/i.test(url)
      || /(?:^|[/_.-])(?:segment|fragment|chunk|init)(?:[/_.-]|$)/i.test(path)) return "";
  if (/no[-_]?drm/i.test(url)) {
    // "nodrm" décrit justement un flux non chiffré ; ne pas le confondre avec un DRM.
  } else if (/(?:widevine|playready|fairplay|clearkey|license|licence)/i.test(url)) {
    return "";
  }
  if (/\.m3u8(?:$|[?#])/i.test(url) || /mpegurl/i.test(mime)) return "HLS";
  if (/\.mpd(?:$|[?#])/i.test(url) || /dash\+xml/i.test(mime)) return "DASH";
  if (/\.mp4(?:$|[?#])/i.test(url) || /^video\/mp4/i.test(mime)) return "MP4";
  if (/\.webm(?:$|[?#])/i.test(url) || /^video\/webm/i.test(mime)) return "WEBM";
  if (/^video\//i.test(mime)) return "VIDÉO";
  // TF1 masque parfois le manifeste derrière une URL sans extension. Cette URL
  // reste directement exploitable par yt-dlp et redirige vers le flux signé.
  if (parsed.hostname === "delivery.tf1.fr") return "VIDÉO";
  return "";
}

function storeNetworkMedia(tabId, item) {
  const key = networkMediaKey(tabId);
  const storedItem = { ...item, detectedAt: Date.now() };
  networkMediaWrites = networkMediaWrites.then(async () => {
    const stored = await chrome.storage.session.get(key);
    const current = Array.isArray(stored[key]) ? stored[key] : [];
    const recent = current.filter((entry) => Date.now() - Number(entry.detectedAt || 0) < NETWORK_MEDIA_TTL);
    const withoutDuplicate = recent.filter((entry) => entry.url !== storedItem.url);
    await chrome.storage.session.set({ [key]: [...withoutDuplicate, storedItem].slice(-20) });
  }).catch(() => {});
  return networkMediaWrites;
}

async function rememberNetworkMedia(details) {
  if (details.tabId < 0 || details.method !== "GET") return;
  const contentType = responseHeader(details.responseHeaders, "content-type");
  const kind = networkMediaKind(details.url, contentType);
  if (!kind) return;
  const manifestDrm = kind === "HLS"
    ? await inspectHlsDrm(details.url)
    : kind === "DASH"
      ? await inspectDashDrm(details.url)
      : null;
  await storeNetworkMedia(details.tabId, {
    url: details.url,
    label: "Vidéo détectée pendant la lecture",
    detail: manifestDrm === true
      ? `${new URL(details.url).hostname} · manifeste protégé par DRM`
      : `${new URL(details.url).hostname} · flux observé par ClipFlow`,
    kind,
    drmProtected: manifestDrm === true,
    pageFallback: false,
    priority: 125,
    playerKey: "",
    source: "network-monitor",
    mediaRole: "audio-video",
  });
}

async function requestTf1HlsVariant(details) {
  if (details.tabId < 0 || details.method !== "GET") return;
  const authorization = requestHeader(details.requestHeaders, "authorization");
  if (!authorization) {
    const pendingKey = tf1PendingKey(details.tabId);
    const stored = await chrome.storage.session.get(pendingKey);
    if (stored[pendingKey]) {
      await setTf1Status(details.tabId, "error", "La session TF1 n’a pas fourni l’autorisation du flux HLS.");
    }
    return;
  }
  let url;
  try { url = new URL(details.url); } catch (_error) { return; }
  const mediaId = url.pathname.split("/").filter(Boolean).at(-1);
  if (!mediaId) return;
  const requestKey = `${details.tabId}:${mediaId}`;
  if (tf1HlsRequests.has(requestKey)) return;
  tf1HlsRequests.add(requestKey);
  url.searchParams.set("format", "hls");
  const headers = { Authorization: authorization };
  const requestId = requestHeader(details.requestHeaders, "x-request-id");
  if (requestId) headers["x-request-id"] = requestId;
  await setTf1Status(details.tabId, "requesting", "Recherche du flux HLS officiel TF1…");

  try {
    const response = await fetch(url.href, { headers, cache: "no-store", credentials: "omit" });
    if (!response.ok) throw new Error(`Réponse TF1 ${response.status}`);
    const payload = await response.json();
    const delivery = payload?.delivery || {};
    const rawUrl = delivery.url;
    const streamDescription = [
      rawUrl,
      delivery.streamId,
      delivery["stream-id"],
      payload?.media?.streamId,
      payload?.media?.["stream-id"],
    ].filter((value) => typeof value === "string").join(" ");
    const explicitlyClear = /no[-_]?drm/i.test(streamDescription);
    const drmFlag = (value) => value === true
      || (typeof value === "string" && /(?:widevine|playready|fairplay|drm)/i.test(value));
    const apiMarksDrm = !explicitlyClear && (
      drmFlag(payload?.media?.drm)
      || drmFlag(delivery.drm)
      || (Array.isArray(delivery.drms) && delivery.drms.length > 0)
    );
    if (typeof rawUrl !== "string") throw new Error("TF1 n’a pas fourni de flux HLS");
    const streamUrl = normalizedWebUrl(rawUrl);
    const manifestDrm = await inspectHlsDrm(streamUrl);
    await storeNetworkMedia(details.tabId, {
      url: streamUrl,
      label: payload?.media?.title || "Vidéo TF1",
      detail: manifestDrm === true
        ? "HLS officiel TF1 · protégé par DRM"
        : apiMarksDrm
          ? "HLS officiel TF1 · vérification du manifeste par yt-dlp"
          : "HLS officiel TF1 · audio et vidéo",
      kind: "HLS",
      drmProtected: manifestDrm === true,
      pageFallback: false,
      priority: 145,
      playerKey: "",
      source: "tf1-hls",
      mediaRole: "audio-video",
    });
    await setTf1Status(
      details.tabId,
      manifestDrm === true ? "protected" : "ready",
      manifestDrm === true
        ? "TF1 fournit uniquement un flux chiffré pour cette vidéo."
        : "Flux HLS officiel TF1 prêt.",
    );

    const pendingKey = tf1PendingKey(details.tabId);
    const stored = await chrome.storage.session.get(pendingKey);
    const pending = stored[pendingKey];
    if (pending && Number(pending.expiresAt) > Date.now() && pending.nativeRequest) {
      await chrome.storage.session.remove(pendingKey);
      if (manifestDrm === true) {
        await chrome.action.setBadgeText({ tabId: details.tabId, text: "DRM" });
        await chrome.action.setBadgeBackgroundColor({ tabId: details.tabId, color: "#7a2e0b" });
        return;
      }
      const response = await sendNativeMessage({
        ...pending.nativeRequest,
        url: streamUrl,
        referer: pending.pageUrl || pending.nativeRequest.referer || "",
      });
      await rememberActiveJob(details.tabId, response);
      await setTf1Status(details.tabId, "sent", "Téléchargement envoyé à ClipFlow.");
      await chrome.action.setBadgeText({ tabId: details.tabId, text: "✓" });
      await chrome.action.setBadgeBackgroundColor({ tabId: details.tabId, color: "#16803a" });
    }
  } catch (error) {
    await setTf1Status(details.tabId, "error", error.message || "Flux HLS TF1 indisponible.");
    await chrome.action.setBadgeText({ tabId: details.tabId, text: "!" });
    await chrome.action.setBadgeBackgroundColor({ tabId: details.tabId, color: "#b42318" });
  } finally {
    tf1HlsRequests.delete(requestKey);
  }
}

chrome.webRequest.onBeforeSendHeaders.addListener(
  requestTf1HlsVariant,
  { urls: ["https://mediainfo.tf1.fr/mediainfocombo/*"], types: ["xmlhttprequest"] },
  ["requestHeaders", "extraHeaders"],
);

chrome.webRequest.onHeadersReceived.addListener(
  rememberNetworkMedia,
  { urls: ["https://*.tf1.fr/*"], types: ["media", "xmlhttprequest", "other"] },
  ["responseHeaders"],
);

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading") chrome.storage.session.remove(networkMediaKey(tabId));
});

chrome.tabs.onRemoved.addListener((tabId) => {
  stopActiveJobMonitor(tabId);
  chrome.storage.session.remove([networkMediaKey(tabId), tf1PendingKey(tabId), tf1StatusKey(tabId), activeJobKey(tabId)]);
});

function normalizedWebUrl(rawUrl, errorMessage = "Adresse de vidéo invalide.") {
  let url;
  try {
    url = new URL(rawUrl);
  } catch (_error) {
    throw new Error(errorMessage);
  }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
    throw new Error(errorMessage);
  }
  const hostname = url.hostname.replace(/^\[|\]$/g, "").replace(/\.$/, "").toLowerCase();
  if (!hostname || hostname === "localhost" || hostname.endsWith(".localhost")) {
    throw new Error(errorMessage);
  }
  const ipv4 = hostname.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (ipv4) {
    const octets = ipv4.slice(1).map(Number);
    const [a, b] = octets;
    const invalid = octets.some((part) => part > 255)
      || a === 0 || a === 10 || a === 127 || a >= 224
      || (a === 100 && b >= 64 && b <= 127)
      || (a === 169 && b === 254)
      || (a === 172 && b >= 16 && b <= 31)
      || (a === 192 && b === 168);
    if (invalid) throw new Error(errorMessage);
  } else if (hostname.includes(":")) {
    const compact = hostname.toLowerCase();
    if (compact === "::" || compact === "::1" || /^f[cd]/.test(compact) || /^fe[89ab]/.test(compact)) {
      throw new Error(errorMessage);
    }
  }
  url.hash = "";
  return url.href;
}

function sendNativeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST, message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error("Le moteur ClipFlow est indisponible. Réinstallez l’application puis réessayez."));
        return;
      }
      if (!response || response.ok !== true) {
        reject(new Error(response?.error || "ClipFlow n’a pas accepté la demande."));
        return;
      }
      resolve(response);
    });
  });
}

async function handleMessage(message, sender) {
  if (sender.id !== chrome.runtime.id || !message || typeof message !== "object") {
    throw new Error("Demande refusée.");
  }

  if (message.type === "get_network_media") {
    const tabId = Number(message.tabId);
    if (!Number.isInteger(tabId) || tabId < 0) throw new Error("Onglet invalide.");
    await networkMediaWrites;
    const key = networkMediaKey(tabId);
    const statusKey = tf1StatusKey(tabId);
    const stored = await chrome.storage.session.get([key, statusKey]);
    const media = (Array.isArray(stored[key]) ? stored[key] : [])
      .filter((entry) => Date.now() - Number(entry.detectedAt || 0) < NETWORK_MEDIA_TTL);
    return { ok: true, media, tf1Status: stored[statusKey] || null };
  }
  if (message.type === "choose_folder") {
    return sendNativeMessage({ action: "choose_folder" });
  }
  if (message.type === "get_active_job") {
    const tabId = Number(message.tabId);
    if (!Number.isInteger(tabId) || tabId < 0) throw new Error("Onglet invalide.");
    const key = activeJobKey(tabId);
    const stored = await chrome.storage.session.get(key);
    const job = stored[key] || null;
    if (job && Number(job.updatedAt || 0) < Date.now() - 24 * 60 * 60 * 1000) {
      await chrome.storage.session.remove(key);
      return { ok: true, job: null };
    }
    return { ok: true, job };
  }
  if (message.type === "download_status") {
    const tabId = Number(message.tabId);
    if (!Number.isInteger(tabId) || tabId < 0) throw new Error("Onglet invalide.");
    const response = await sendNativeMessage({ action: "status", jobId: message.jobId });
    const key = activeJobKey(tabId);
    const stored = await chrome.storage.session.get(key);
    if (stored[key]) {
      await chrome.storage.session.set({
        [key]: {
          ...stored[key],
          state: response.state,
          progress: response.progress,
          message: response.message,
          updatedAt: Date.now(),
        },
      });
    }
    await updateJobBadge(tabId, response);
    return response;
  }
  if (message.type !== "download") {
    throw new Error("Action inconnue.");
  }

  const url = normalizedWebUrl(message.url);
  const referer = message.referer
    ? normalizedWebUrl(message.referer, "Adresse de page d’origine invalide.")
    : "";
  const requestedQuality = QUALITY_KEYS.has(message.quality) ? message.quality : "best";
  const quality = requestedQuality === "audio" ? "audio" : "best";
  const destination = DESTINATION_KEYS.has(message.destination)
    ? message.destination
    : "downloads";
  const destinationPath = destination === "custom" && typeof message.destinationPath === "string"
    ? message.destinationPath.slice(0, 4096)
    : "";
  const sourceTitle = typeof message.sourceTitle === "string"
    ? message.sourceTitle.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, 300)
    : "";
  if (destination === "custom" && !destinationPath) {
    throw new Error("Choisissez d’abord un dossier de destination.");
  }

  const nativeRequest = {
    action: "download",
    url,
    quality,
    completionSound: message.completionSound !== false,
    destination,
    destinationPath,
    settingsVersion: message.settingsVersion === SETTINGS_VERSION ? SETTINGS_VERSION : 0,
  };
  if (referer) nativeRequest.referer = referer;
  if (sourceTitle) nativeRequest.sourceTitle = sourceTitle;

  const tabId = Number(message.tabId);
  let refererUrl;
  try { refererUrl = referer ? new URL(referer) : null; } catch (_error) { refererUrl = null; }
  const isTf1Page = refererUrl && /(^|\.)tf1\.fr$/i.test(refererUrl.hostname);
  const isTf1Dash = isTf1Page && /(?:\.mpd(?:$|[?#])|vod-das\.|\.ism\/)/i.test(url);
  if (isTf1Dash && Number.isInteger(tabId) && tabId >= 0) {
    await chrome.storage.session.set({
      [tf1PendingKey(tabId)]: {
        nativeRequest,
        pageUrl: referer,
        expiresAt: Date.now() + TF1_PENDING_TTL,
      },
    });
    await setTf1Status(tabId, "reloading", "Recharge automatique pour obtenir le flux HLS TF1…");
    await chrome.action.setBadgeText({ tabId, text: "…" });
    await chrome.action.setBadgeBackgroundColor({ tabId, color: "#1367d1" });
    await chrome.tabs.reload(tabId);
    return { ok: true, preparing: true, destinationLabel: "ClipFlow après la préparation TF1" };
  }
  const response = await sendNativeMessage(nativeRequest);
  await rememberActiveJob(tabId, response);
  return response;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then((response) => sendResponse(response))
    .catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

resumeActiveJobMonitors();
