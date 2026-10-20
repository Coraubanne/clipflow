const SETTINGS_VERSION = 6;
const EXPECTED_EXTENSION_VERSION = "2.8.6";
if (chrome.runtime.getManifest().version !== EXPECTED_EXTENSION_VERSION) {
  // Une extension non empaquetée ne recharge pas toujours son service worker
  // quand ses fichiers changent. L’ouverture du popup applique la mise à jour.
  chrome.runtime.reload();
}
const DEFAULT_SETTINGS = {
  settingsVersion: SETTINGS_VERSION,
  audioOnly: false,
  completionSound: true,
  destination: "downloads",
  destinationPath: "",
  destinationLabel: "Téléchargements",
};

let settings = { ...DEFAULT_SETTINGS };
let activePage = null;

const audioOnly = document.getElementById("audio-only");
const completionSound = document.getElementById("completion-sound");
const destination = document.getElementById("destination");
const settingsToggle = document.getElementById("settings-toggle");
const settingsPanel = document.getElementById("settings-panel");
const pageTitle = document.getElementById("page-title");
const status = document.getElementById("status");
const videos = document.getElementById("videos");
const rescan = document.getElementById("rescan");
const progressSection = document.getElementById("download-progress");
const progressLabel = document.getElementById("progress-label");
const progressDetail = document.getElementById("progress-detail");
const progressPercent = document.getElementById("progress-percent");
let displayedProgress = 0;
let progressAnimation = null;
let progressPoll = null;

function setSettingsOpen(open) {
  settingsPanel.hidden = !open;
  settingsToggle.setAttribute("aria-expanded", String(open));
  settingsToggle.setAttribute("aria-label", open ? "Fermer les réglages" : "Ouvrir les réglages");
}

async function saveSettings() {
  settings.settingsVersion = SETTINGS_VERSION;
  await chrome.storage.local.set({ tubeSaveSettings: settings });
}

async function loadSettings() {
  const stored = await chrome.storage.local.get("tubeSaveSettings");
  const previous = stored.tubeSaveSettings || {};
  settings = {
    ...DEFAULT_SETTINGS,
    ...previous,
    settingsVersion: SETTINGS_VERSION,
    audioOnly: typeof previous.audioOnly === "boolean"
      ? previous.audioOnly
      : previous.quality === "audio",
    completionSound: previous.completionSound !== false,
  };
  delete settings.quality;
  audioOnly.checked = settings.audioOnly;
  completionSound.checked = settings.completionSound;
  if (settings.destination === "custom" && settings.destinationPath) {
    const option = document.createElement("option");
    option.value = "custom";
    option.textContent = settings.destinationLabel || "Dossier choisi";
    destination.insertBefore(option, destination.querySelector('option[value="choose"]'));
  }
  destination.value = settings.destination;
  await saveSettings();
}

function detectVideosOnPage() {
  const pageUrl = location.href;
  const title = document.title || location.hostname;
  const found = [];
  const seen = new Map();
  const allVideoElements = Array.from(document.querySelectorAll("video"));
  const visibleVideoElements = allVideoElements.filter((video) => {
    const rect = video.getBoundingClientRect();
    const style = getComputedStyle(video);
    return rect.width >= 80 && rect.height >= 45
      && style.display !== "none"
      && style.visibility !== "hidden"
      && Number(style.opacity || 1) > 0;
  });
  const videoElements = visibleVideoElements.length ? visibleVideoElements : allVideoElements;
  const embeddedPlayers = Array.from(document.querySelectorAll("iframe[src]"))
    .filter((frame) => /youtube|youtu\.be|vimeo|dailymotion|player|video/i.test(frame.src));
  const segmentPattern = /\.(?:m4s|cmfv|cmfa|ts)(?:$|[?#])/i;
  const drmPattern = /(?:widevine|playready|fairplay|license|licence|clearkey|media.?keys)/i;
  let drmDetected = false;
  let durationSeconds = 0;

  function isYouTubeVideoPage(rawUrl) {
    try {
      const parsed = new URL(rawUrl);
      const host = parsed.hostname.toLowerCase();
      if (host === "youtu.be") return parsed.pathname.length > 1;
      if (host !== "youtube.com" && !host.endsWith(".youtube.com")) return true;
      if (parsed.pathname === "/watch") return Boolean(parsed.searchParams.get("v"));
      return ["/shorts/", "/live/", "/embed/", "/clip/"].some((prefix) => parsed.pathname.startsWith(prefix));
    } catch (_error) {
      return false;
    }
  }

  function isDailymotionVideoPage(rawUrl) {
    try {
      const parsed = new URL(rawUrl);
      const host = parsed.hostname.toLowerCase();
      if (!/(^|\.)dailymotion\.[a-z]{2,3}$/i.test(host)) return false;
      if (/\/(?:video|embed\/video|crawler\/video)\/[a-z0-9]+/i.test(parsed.pathname)) return true;
      return parsed.pathname.includes("/player") && Boolean(parsed.searchParams.get("video"));
    } catch (_error) {
      return false;
    }
  }

  try {
    drmDetected = allVideoElements.some((video) => Boolean(video.mediaKeys));
    durationSeconds = Math.max(
      0,
      ...allVideoElements.map((video) => Number.isFinite(video.duration) ? video.duration : 0),
    );
  } catch (_error) {
    drmDetected = false;
  }

  function classify(url) {
    let decoded = url;
    try { decoded = decodeURIComponent(url); } catch (_error) { /* URL signée */ }
    if (/\.m3u8(?:$|[?#&])/i.test(decoded) || /(?:format|type)=m3u8/i.test(decoded)) return "HLS";
    if (/\.mpd(?:$|[?#&])/i.test(decoded) || /(?:format|type)=mpd/i.test(decoded)) return "DASH";
    if (/\.mp4(?:$|[?#&])/i.test(decoded)) return "MP4";
    if (/\.webm(?:$|[?#&])/i.test(decoded)) return "WEBM";
    if (/\.(?:m4v|mov|ogv)(?:$|[?#&])/i.test(decoded)) return "VIDÉO";
    if (/\.(?:m4a|mp3|aac|ogg|opus)(?:$|[?#&])/i.test(decoded)) return "AUDIO";
    return "FLUX";
  }

  function parsedDuration(rawValue) {
    if (typeof rawValue === "number" && Number.isFinite(rawValue)) return rawValue;
    if (typeof rawValue !== "string") return 0;
    if (/^\d+(?:\.\d+)?$/.test(rawValue.trim())) return Number(rawValue);
    const match = rawValue.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/i);
    if (!match) return 0;
    return (Number(match[1]) || 0) * 3600 + (Number(match[2]) || 0) * 60 + (Number(match[3]) || 0);
  }

  function add(rawUrl, label, detail, options = {}) {
    let resolved;
    try {
      resolved = new URL(rawUrl, pageUrl);
    } catch (_error) {
      return;
    }
    if (!["http:", "https:"].includes(resolved.protocol)) return;
    resolved.hash = "";
    const url = resolved.href;
    if (options.fromNetwork && segmentPattern.test(resolved.pathname)) return;
    if (!/no[-_]?drm/i.test(url) && drmPattern.test(url)) {
      drmDetected = true;
      return;
    }
    const kind = options.kind || classify(url);
    const descriptor = `${label || ""} ${detail || ""} ${url}`.toLowerCase();
    let mediaRole = options.mediaRole || "unknown";
    if (kind === "AUDIO" || /(?:audio[\s_-]*(?:only|seul)|sound[\s_-]*only|bestaudio)/i.test(descriptor)) {
      mediaRole = "audio-only";
    } else if (/(?:video[\s_-]*only|sans[\s_-]*audio|no[\s_-]*audio|bestvideo)/i.test(descriptor)) {
      mediaRole = "video-only";
    } else if (/(?:audio\s*(?:\+|&|and|et|\/)\s*vid[eé]o|vid[eé]o\s*(?:\+|&|and|et|\/)\s*audio|muxed|progressive)/i.test(descriptor)) {
      mediaRole = "audio-video";
    } else if (["HLS", "DASH", "PAGE", "PLAYER"].includes(kind)) {
      mediaRole = "audio-video";
    }
    const candidate = {
      url,
      label: label || title || "Vidéo détectée",
      detail: detail || resolved.hostname,
      kind,
      pageFallback: Boolean(options.pageFallback),
      priority: Number(options.priority) || 0,
      playerKey: options.playerKey || "",
      source: options.source || "page",
      mediaRole,
    };
    const identity = options.playerKey ? `${url}|${options.playerKey}` : url;
    const previousIndex = seen.get(identity);
    if (previousIndex !== undefined) {
      if (found[previousIndex].priority < candidate.priority) found[previousIndex] = candidate;
      return;
    }
    seen.set(identity, found.length);
    found.push(candidate);
  }

  const youtube = /(^|\.)youtube\.com$/i.test(location.hostname) || location.hostname === "youtu.be";
  if (youtube) {
    const player = videoElements[0];
    const width = player?.videoWidth || player?.clientWidth || 0;
    const height = player?.videoHeight || player?.clientHeight || 0;
    const dimensions = width && height ? `${width}×${height}` : "lecteur YouTube";
    if (isYouTubeVideoPage(pageUrl)) {
      add(pageUrl, title, `${dimensions} · meilleure qualité via yt-dlp`, {
        kind: "PAGE",
        pageFallback: true,
        priority: 120,
      });
    }
    return { pageUrl, pageTitle: title, drmDetected, videos: found };
  }

  const dailymotion = /(^|\.)dailymotion\.[a-z]{2,3}$/i.test(location.hostname);
  if (dailymotion) {
    const player = videoElements[0];
    const width = player?.videoWidth || player?.clientWidth || 0;
    const height = player?.videoHeight || player?.clientHeight || 0;
    const dimensions = width && height ? `${width}×${height}` : "lecteur Dailymotion";
    if (isDailymotionVideoPage(pageUrl)) {
      add(pageUrl, title, `${dimensions} · meilleure qualité via yt-dlp`, {
        kind: "PAGE",
        pageFallback: true,
        priority: 125,
        playerKey: "dailymotion-player",
        source: "page",
        mediaRole: "audio-video",
      });
    }
    return { pageUrl, pageTitle: title, drmDetected, durationSeconds, videos: found };
  }

  videoElements.forEach((video, index) => {
    const width = video.videoWidth || video.clientWidth || 0;
    const height = video.videoHeight || video.clientHeight || 0;
    const dimensions = width && height ? `${width}×${height}` : "lecteur HTML5";
    const label = video.getAttribute("aria-label") || video.getAttribute("title") || `Vidéo ${index + 1}`;
    const rect = video.getBoundingClientRect();
    const playerKey = visibleVideoElements.length
      ? `visual-${Math.round(rect.left / 40)}-${Math.round(rect.top / 40)}-${Math.round(rect.width / 40)}-${Math.round(rect.height / 40)}`
      : `player-${index}`;
    const sources = [
      video.currentSrc,
      video.src,
      ...Array.from(video.querySelectorAll("source[src]"), (source) => source.src),
    ].filter(Boolean);
    const directSources = sources.filter((source) => /^https?:/i.test(source));
    directSources.forEach((source) => add(source, label, `${dimensions} · lecteur HTML5`, {
      priority: 100,
      playerKey,
      source: "player",
      // A URL carried by a real <video> element is a complete source for
      // progressive players such as SeeArtTV. Without this hint, the filter
      // could prefer the unsupported HTML page over the MP4 being played.
      mediaRole: "audio-video",
    }));
    add(pageUrl, label, `${dimensions} · extraction depuis la page`, {
      kind: "PAGE",
      pageFallback: true,
      priority: directSources.length ? 55 : 75,
      playerKey,
      source: "page",
      mediaRole: "audio-video",
    });
  });

  for (const selector of [
    'meta[property="og:video"]',
    'meta[property="og:video:url"]',
    'meta[property="og:video:secure_url"]',
    'meta[property="og:video:stream"]',
    'meta[name="twitter:player:stream"]',
  ]) {
    document.querySelectorAll(selector).forEach((meta) => {
      add(meta.content, title, "Flux déclaré par la page", { priority: 90, source: "metadata" });
    });
  }

  const mediaPattern = /\.(?:mp4|m4v|mov|webm|m3u8|mpd|mp3|m4a|aac|ogg|ogv)(?:$|[?#&])/i;
  const linkedMedia = Array.from(document.querySelectorAll("a[href], source[src], embed[src]"), (element) => (
    element.href || element.src
  )).filter(Boolean);
  linkedMedia.filter((href) => mediaPattern.test(href)).slice(0, 30).forEach((href, index) => {
    add(href, `Média lié ${index + 1}`, "Lien média présent dans la page", { priority: 70, source: "link" });
  });

  let structuredVideoIndex = 0;
  document.querySelectorAll("script[type='application/ld+json']").forEach((script) => {
    let root;
    try { root = JSON.parse(script.textContent || "null"); } catch (_error) { return; }
    const pending = [root];
    let inspected = 0;
    while (pending.length && inspected < 250) {
      const value = pending.pop();
      inspected += 1;
      if (!value || typeof value !== "object") continue;
      if (Array.isArray(value)) {
        pending.push(...value.slice(0, 50));
        continue;
      }
      const type = Array.isArray(value["@type"]) ? value["@type"].join(" ") : value["@type"];
      if (/VideoObject|AudioObject|MediaObject/i.test(String(type || ""))) {
        durationSeconds = Math.max(durationSeconds, parsedDuration(value.duration));
        const typeText = String(type || "");
        const audioOnlyObject = /AudioObject/i.test(typeText) && !/VideoObject/i.test(typeText);
        const structuredKey = !videoElements.length && structuredVideoIndex < embeddedPlayers.length
          ? `embed-${structuredVideoIndex}`
          : `structured-${structuredVideoIndex}`;
        structuredVideoIndex += 1;
        for (const property of ["contentUrl", "embedUrl", "url"]) {
          if (!audioOnlyObject && typeof value[property] === "string") {
            add(value[property], value.name || `Vidéo ${structuredVideoIndex}`, "Média déclaré dans les données de la page", {
              priority: 85,
              source: "structured",
              playerKey: structuredKey,
              mediaRole: /VideoObject/i.test(typeText) ? "audio-video" : "unknown",
            });
          }
        }
      }
      pending.push(...Object.values(value).filter((item) => item && typeof item === "object").slice(0, 50));
    }
  });

  embeddedPlayers.forEach((frame, index) => {
    add(frame.src, `Lecteur intégré ${index + 1}`, "Page du lecteur vidéo intégré", {
      kind: "PLAYER",
      pageFallback: true,
      priority: 65,
      source: "embed",
      playerKey: `embed-${index}`,
    });
  });

  if (!videoElements.length && embeddedPlayers.length === 1) {
    add(pageUrl, title, "Extraction depuis la page d’origine", {
      kind: "PAGE",
      pageFallback: true,
      priority: 80,
      source: "page",
      playerKey: "embed-0",
      mediaRole: "audio-video",
    });
  }

  const resources = performance.getEntriesByType("resource").slice(-1500);
  resources.forEach((entry) => {
    if (!entry?.name || typeof entry.name !== "string") return;
    if (!/no[-_]?drm/i.test(entry.name) && drmPattern.test(entry.name)) {
      drmDetected = true;
      return;
    }
    const kind = classify(entry.name);
    const initiator = String(entry.initiatorType || "").toLowerCase();
    const parsedResource = new URL(entry.name);
    const hiddenDelivery = parsedResource.hostname === "delivery.tf1.fr";
    const isStream = kind === "HLS" || kind === "DASH" || hiddenDelivery;
    const isDirectMedia = ["MP4", "WEBM", "VIDÉO", "AUDIO"].includes(kind);
    const wasLoadedByMedia = ["video", "audio", "media"].includes(initiator);
    if (!isStream && !isDirectMedia && !wasLoadedByMedia) return;
    add(entry.name, `${kind === "FLUX" ? "Flux média" : `Flux ${kind}`} détecté`, `${entry.name.split("/")[2] || "réseau"} · activité réseau`, {
      kind: hiddenDelivery ? "VIDÉO" : (kind === "FLUX" ? "RÉSEAU" : kind),
      priority: isStream ? 115 : (wasLoadedByMedia ? 105 : 95),
      fromNetwork: true,
      source: "network",
    });
  });

  found.sort((left, right) => right.priority - left.priority || left.label.localeCompare(right.label));
  return { pageUrl, pageTitle: title, drmDetected, durationSeconds, videos: found.slice(0, 30) };
}

function selectRealVideos(candidates) {
  if (!candidates.length) return { videos: [], hiddenCount: 0 };

  const kindRank = {
    HLS: 60,
    DASH: 55,
    MP4: 45,
    WEBM: 40,
    "VIDÉO": 35,
    PAGE: 25,
    PLAYER: 20,
    FLUX: 10,
    "RÉSEAU": 5,
    AUDIO: 0,
  };
  const roleRank = {
    "audio-video": 200,
    unknown: 0,
    "video-only": -200,
    "audio-only": -400,
  };
  const extractorBonus = (video) => /(^|\.)dailymotion\.[a-z]{2,3}$/i.test((() => {
    try { return new URL(video.url).hostname; } catch (_error) { return ""; }
  })()) ? 100 : 0;
  const score = (video) => (roleRank[video.mediaRole] ?? 0)
    + (kindRank[video.kind] ?? 10)
    + extractorBonus(video)
    + ((video.priority || 0) / 100);
  const best = (items) => [...items].sort((left, right) => score(right) - score(left))[0];
  const possibleVideos = candidates.filter((video) => video.kind !== "AUDIO"
    && video.kind !== "RÉSEAU"
    && video.mediaRole !== "audio-only");
  const combinedVideos = possibleVideos.filter((video) => video.mediaRole === "audio-video");
  const usable = combinedVideos.length
    ? combinedVideos
    : possibleVideos.filter((video) => video.mediaRole !== "video-only");
  const playerGroups = new Map();

  usable.forEach((video) => {
    if (!video.playerKey) return;
    if (!playerGroups.has(video.playerKey)) playerGroups.set(video.playerKey, []);
    playerGroups.get(video.playerKey).push(video);
  });

  const htmlPlayerGroups = new Map(
    Array.from(playerGroups).filter(([key]) => /(?:^|:)(?:player-\d+|visual-)/.test(key)),
  );
  const preferredGroups = htmlPlayerGroups.size ? htmlPlayerGroups : playerGroups;

  let selected = [];
  if (preferredGroups.size === 1) {
    // Un seul lecteur : les manifests et fichiers vus sur le réseau sont ses variantes,
    // pas des vidéos supplémentaires. On n'affiche que la meilleure source complète.
    const onlyGroup = Array.from(preferredGroups.values())[0];
    const ungroupedStreams = usable.filter((video) => !video.playerKey && ["HLS", "DASH", "MP4", "WEBM", "VIDÉO"].includes(video.kind));
    selected = [best([...onlyGroup, ...ungroupedStreams])];
  } else if (preferredGroups.size > 1) {
    // Plusieurs vrais éléments <video> : une carte par lecteur, sans ses variantes.
    selected = Array.from(preferredGroups.values(), (group) => best(group));
  } else if (usable.length) {
    // Lecteur personnalisé sans élément <video> accessible : manifeste, fichier direct,
    // puis page du lecteur, dans cet ordre.
    selected = [best(usable)];
  } else {
    // Dernier recours pour certains lecteurs opaques : une seule requête média générique.
    const fallback = best(candidates.filter((video) => video.kind !== "AUDIO"
      && video.mediaRole !== "audio-only"
      && video.mediaRole !== "video-only"));
    if (fallback) selected = [fallback];
  }

  const unique = [];
  const seen = new Set();
  selected.filter(Boolean).forEach((video) => {
    const key = `${video.url}|${video.playerKey || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    unique.push(video);
  });
  return { videos: unique, hiddenCount: Math.max(0, candidates.length - unique.length) };
}

function setStatus(text, kind = "normal") {
  status.textContent = text;
  status.dataset.kind = kind;
}

function animateProgress(target) {
  const safeTarget = Math.max(1, Math.min(100, Math.round(Number(target) || 1)));
  if (safeTarget <= displayedProgress) {
    progressPercent.textContent = `${displayedProgress} %`;
    return;
  }
  if (progressAnimation) clearInterval(progressAnimation);
  progressAnimation = setInterval(() => {
    displayedProgress = Math.min(safeTarget, displayedProgress + 1);
    progressPercent.textContent = `${displayedProgress} %`;
    if (displayedProgress >= safeTarget) {
      clearInterval(progressAnimation);
      progressAnimation = null;
    }
  }, 24);
}

function showProgress(jobId, tabId, destinationLabel = "Téléchargements", button = null, feedback = null) {
  if (!jobId || !Number.isInteger(Number(tabId))) return;
  progressSection.hidden = false;
  progressLabel.textContent = `Vers ${destinationLabel}`;
  progressDetail.textContent = "Préparation…";
  displayedProgress = Math.max(1, displayedProgress);
  progressPercent.textContent = `${displayedProgress} %`;
  animateProgress(displayedProgress);
  if (progressPoll) clearTimeout(progressPoll);

  const poll = () => {
    chrome.runtime.sendMessage({ type: "download_status", jobId, tabId: Number(tabId) }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        progressDetail.textContent = response?.error || "État momentanément indisponible.";
        progressPoll = setTimeout(poll, 1200);
        return;
      }
      animateProgress(response.progress);
      progressDetail.textContent = response.message || "Téléchargement en cours…";
      if (response.state === "complete") {
        animateProgress(100);
        progressLabel.textContent = "Téléchargement terminé";
        if (button) button.textContent = "Terminé";
        if (feedback) {
          feedback.dataset.kind = "success";
          feedback.textContent = "Fichier prêt.";
        }
        return;
      }
      if (response.state === "error" || response.state === "cancelled") {
        progressLabel.textContent = response.state === "cancelled" ? "Téléchargement annulé" : "Échec du téléchargement";
        if (button) {
          button.disabled = false;
          button.textContent = "Réessayer";
        }
        if (feedback) {
          feedback.dataset.kind = "error";
          feedback.textContent = response.message || "Le téléchargement a échoué.";
        }
        return;
      }
      progressPoll = setTimeout(poll, 700);
    });
  };
  poll();
}

function restoreActiveProgress(tabId) {
  chrome.runtime.sendMessage({ type: "get_active_job", tabId }, (response) => {
    const job = response?.job;
    if (chrome.runtime.lastError || !response?.ok || !job?.jobId) return;
    if (Date.now() - Number(job.updatedAt || 0) > 24 * 60 * 60 * 1000) return;
    showProgress(job.jobId, tabId, job.destinationLabel);
    animateProgress(job.progress || 1);
    if (job.message) progressDetail.textContent = job.message;
  });
}

function createVideoCard(video, index) {
  const card = document.createElement("article");
  card.className = "video-card";
  const heading = document.createElement("div");
  heading.className = "video-heading";
  const kind = document.createElement("span");
  kind.className = "video-kind";
  kind.textContent = video.kind || "VIDÉO";
  const title = document.createElement("div");
  title.className = "video-title";
  title.textContent = video.label;
  heading.append(kind, title);
  const detail = document.createElement("div");
  detail.className = "video-detail";
  detail.textContent = video.detail;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "download";
  button.textContent = "Télécharger";
  const feedback = document.createElement("div");
  feedback.className = "video-feedback";

  if (video.drmProtected) {
    button.disabled = true;
    button.textContent = "Protégée";
    feedback.dataset.kind = "error";
    feedback.textContent = "Le manifeste de cette source est chiffré par DRM.";
    card.dataset.index = String(index);
    card.append(heading, detail, button, feedback);
    return card;
  }

  button.addEventListener("click", () => {
    button.disabled = true;
    button.textContent = "Envoi…";
    feedback.textContent = "";
    chrome.runtime.sendMessage({
      type: "download",
      tabId: activePage.tabId,
      url: video.url,
      referer: video.url === activePage.pageUrl ? "" : activePage.pageUrl,
      sourceTitle: video.label || activePage.pageTitle || "",
      quality: settings.audioOnly ? "audio" : "best",
      completionSound: settings.completionSound,
      destination: settings.destination,
      destinationPath: settings.destinationPath,
      settingsVersion: SETTINGS_VERSION,
    }, (response) => {
      button.disabled = false;
      button.textContent = "Télécharger";
      if (chrome.runtime.lastError || !response?.ok) {
        feedback.dataset.kind = "error";
        feedback.textContent = response?.error || "ClipFlow est indisponible.";
        return;
      }
      feedback.dataset.kind = "success";
      feedback.textContent = response.preparing
        ? "Préparation automatique du flux TF1…"
        : "Téléchargement démarré en arrière-plan.";
      if (response.jobId) {
        button.textContent = "En cours";
        showProgress(response.jobId, activePage.tabId, response.destinationLabel, button, feedback);
      } else {
        button.disabled = false;
        button.textContent = "Télécharger";
      }
    });
  });

  card.dataset.index = String(index);
  card.append(heading, detail, button, feedback);
  return card;
}

async function scan() {
  videos.replaceChildren();
  pageTitle.textContent = "Analyse de la page…";
  setStatus("Recherche des lecteurs vidéo…");
  rescan.disabled = true;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https?:/i.test(tab.url || "")) {
      throw new Error("Cette page Chrome ne peut pas être analysée.");
    }
    restoreActiveProgress(tab.id);
    let results;
    try {
      results = await chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: detectVideosOnPage,
      });
    } catch (_frameError) {
      results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: detectVideosOnPage,
      });
    }
    const mainResult = results.find((result) => result.frameId === 0)?.result;
    if (!mainResult) throw new Error("La page n’a pas répondu à l’analyse.");
    const topPlayerKeys = new Set(mainResult.videos.map((video) => video.playerKey).filter(Boolean));
    const singleEmbeddedPlayer = topPlayerKeys.has("embed-0")
      && !Array.from(topPlayerKeys).some((key) => /^embed-[1-9]\d*$/.test(key));
    const merged = new Map();
    let drmDetected = false;
    let durationSeconds = 0;
    results.forEach((injection) => {
      const frame = injection.result;
      if (!frame) return;
      drmDetected ||= Boolean(frame.drmDetected);
      durationSeconds = Math.max(durationSeconds, Number(frame.durationSeconds) || 0);
      frame.videos.forEach((original) => {
        const video = { ...original };
        if (video.playerKey) {
          video.playerKey = injection.frameId !== 0 && singleEmbeddedPlayer
            ? "0:embed-0"
            : `${injection.frameId}:${video.playerKey}`;
        }
        if (injection.frameId !== 0 && video.pageFallback && video.kind === "PAGE") {
          video.kind = "PLAYER";
          video.label = frame.pageTitle || "Lecteur intégré";
          video.detail = "Lecteur vidéo dans un cadre intégré";
          video.priority = Math.max(65, video.priority || 0);
        }
        const identity = `${video.url}|${video.playerKey || ""}`;
        const previous = merged.get(identity);
        if (!previous || (previous.priority || 0) < (video.priority || 0)) merged.set(identity, video);
      });
    });
    let monitoredMedia = [];
    let tf1Status = null;
    try {
      const monitored = await chrome.runtime.sendMessage({ type: "get_network_media", tabId: tab.id });
      if (monitored?.ok) {
        if (Array.isArray(monitored.media)) monitoredMedia = monitored.media;
        tf1Status = monitored.tf1Status || null;
      }
    } catch (_networkError) {
      // La détection dans la page reste disponible si le moniteur réseau est indisponible.
    }
    monitoredMedia.forEach((video) => {
      const identity = `${video.url}|${video.playerKey || ""}`;
      const previous = merged.get(identity);
      if (!previous || (previous.priority || 0) < (video.priority || 0)) merged.set(identity, video);
    });
    const allCandidates = Array.from(merged.values())
      .sort((left, right) => (right.priority || 0) - (left.priority || 0) || left.label.localeCompare(right.label));
    const recentTf1Error = tf1Status?.state === "error"
      && Date.now() - Number(tf1Status.updatedAt || 0) < 30 * 1000
      && !allCandidates.some((video) => video.source === "tf1-hls");
    if (recentTf1Error) {
      pageTitle.textContent = tab.title || mainResult.pageTitle;
      setStatus(tf1Status.message || "Le flux HLS TF1 est indisponible.", "error");
      return;
    }
    const filtered = selectRealVideos(allCandidates);
    const multipleVideos = filtered.videos.length > 1;
    const selectedVideos = filtered.videos.map((video, index) => ({
      ...video,
      label: multipleVideos
        ? (video.label || `Vidéo ${index + 1}`)
        : (tab.title || mainResult.pageTitle || video.label),
      detail: `${video.kind} · meilleure source détectée`,
    }));
    activePage = {
      tabId: tab.id,
      pageUrl: tab.url,
      pageTitle: tab.title || mainResult.pageTitle,
      drmDetected: drmDetected || selectedVideos.some((video) => video.drmProtected),
      durationSeconds,
      videos: selectedVideos.slice(0, 12),
      hiddenSourceCount: filtered.hiddenCount,
    };
    pageTitle.textContent = activePage.pageTitle;
    if (!activePage.videos.length) {
      if (activePage.drmDetected) {
        setStatus("Un lecteur protégé par DRM a été détecté. Son flux chiffré ne peut pas être téléchargé.", "warning");
      } else {
        setStatus("Aucune vidéo visible. Lancez la lecture quelques secondes puis relancez l’analyse.");
      }
      return;
    }
    const count = activePage.videos.length;
    const drmNote = activePage.drmDetected ? " · lecteur DRM ignoré" : "";
    const filteredNote = activePage.hiddenSourceCount
      ? ` · ${activePage.hiddenSourceCount} variante${activePage.hiddenSourceCount > 1 ? "s" : ""} technique${activePage.hiddenSourceCount > 1 ? "s" : ""} masquée${activePage.hiddenSourceCount > 1 ? "s" : ""}`
      : "";
    setStatus(`${count} vidéo${count > 1 ? "s" : ""} détectée${count > 1 ? "s" : ""}${filteredNote}${drmNote}.`, activePage.drmDetected ? "warning" : "normal");
    activePage.videos.forEach((video, index) => videos.append(createVideoCard(video, index)));
  } catch (error) {
    setStatus(error.message || "Impossible d’analyser cette page.", "error");
  } finally {
    rescan.disabled = false;
  }
}

audioOnly.addEventListener("change", async () => {
  settings.audioOnly = audioOnly.checked;
  await saveSettings();
});

completionSound.addEventListener("change", async () => {
  settings.completionSound = completionSound.checked;
  await saveSettings();
});

destination.addEventListener("change", async () => {
  if (destination.value === "choose") {
    destination.disabled = true;
    chrome.runtime.sendMessage({ type: "choose_folder" }, async (response) => {
      destination.disabled = false;
      if (chrome.runtime.lastError || !response?.ok) {
        destination.value = settings.destination;
        if (response?.error) setStatus(response.error, "error");
        return;
      }
      settings.destination = "custom";
      settings.destinationPath = response.path;
      settings.destinationLabel = response.label || "Dossier choisi";
      let custom = destination.querySelector('option[value="custom"]');
      if (!custom) {
        custom = document.createElement("option");
        custom.value = "custom";
        destination.insertBefore(custom, destination.querySelector('option[value="choose"]'));
      }
      custom.textContent = settings.destinationLabel;
      destination.value = "custom";
      await saveSettings();
    });
    return;
  }
  settings.destination = destination.value;
  if (settings.destination !== "custom") {
    settings.destinationPath = "";
    settings.destinationLabel = destination.options[destination.selectedIndex].text;
  }
  await saveSettings();
});

settingsToggle.addEventListener("click", () => {
  setSettingsOpen(settingsPanel.hidden);
});

rescan.addEventListener("click", scan);

loadSettings().then(scan).catch((error) => setStatus(error.message, "error"));
