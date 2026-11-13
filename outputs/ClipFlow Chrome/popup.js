const SETTINGS_VERSION = 7;
const EXPECTED_EXTENSION_VERSION = "2.12.1";
const UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000;
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
  language: "auto",
};

const UI_TEXT = {
  fr: {
    openSettings: "Ouvrir les réglages", closeSettings: "Fermer les réglages", settings: "Réglages",
    webMedia: "Médias web", settingsHint: "Personnalisez ClipFlow",
    downloadSettings: "Réglages du téléchargement", language: "Langue de l’extension", languageAuto: "Automatique",
    extensionVersion: "Extension {version}",
    saveTo: "Enregistrer dans", destinationFolder: "Dossier de destination", downloads: "Téléchargements",
    otherFolder: "Autre dossier…", chosenFolder: "Dossier choisi",
    completionSoundTitle: "Jouer un son à la fin du téléchargement", completionSound: "Son de fin",
    whenReady: "Quand le fichier est prêt", checkUpdate: "Chercher une mise à jour",
    updateHint: "ClipFlow vérifie les releases GitHub sécurisées.", fileOption: "Option du fichier",
    audioOnly: "Audio uniquement", mp3NoVideo: "MP3 sans vidéo", download: "Téléchargement",
    preparing: "Préparation…", analyzingPage: "Analyse de la page…", rescan: "Relancer l’analyse",
    searchingPlayers: "Recherche des lecteurs vidéo…", engineUnavailable: "Le moteur ClipFlow est indisponible.",
    updateFailed: "La demande de mise à jour a échoué.", installVersion: "Installer ClipFlow v{version}",
    updateAvailable: "Nouvelle version disponible · application, extension et module Premiere Pro.",
    upToDate: "ClipFlow v{version} est à jour.", checking: "Vérification…",
    secureGithub: "Connexion sécurisée à GitHub…", retry: "Réessayer", installing: "Installation…",
    installingDetail: "Téléchargement, vérification et installation en cours…", updateInstalled: "Mise à jour installée.",
    updateComplete: "Mise à jour terminée", retryInstall: "Réessayer l’installation", toFolder: "Vers {folder}",
    stateUnavailable: "État momentanément indisponible.", downloading: "Téléchargement en cours…",
    downloadComplete: "Téléchargement terminé", complete: "Terminé", fileReady: "Fichier prêt.",
    downloadCancelled: "Téléchargement annulé", downloadError: "Échec du téléchargement",
    downloadFailed: "Le téléchargement a échoué.", protected: "Protégée",
    drmManifest: "Le manifeste de cette source est chiffré par DRM.", downloadConvert: "Télécharger et convertir en MP4",
    send: "Envoi…", unavailable: "ClipFlow est indisponible.", tf1Preparing: "Préparation automatique du flux TF1…",
    startedBackground: "Téléchargement démarré en arrière-plan.", inProgress: "En cours",
    chromePageUnsupported: "Cette page Chrome ne peut pas être analysée.", pageNoResponse: "La page n’a pas répondu à l’analyse.",
    hlsUnavailable: "Le flux HLS TF1 est indisponible.", drmPlayer: "Un lecteur protégé par DRM a été détecté. Son flux chiffré ne peut pas être téléchargé.",
    noVideo: "Aucune vidéo visible. Lancez la lecture quelques secondes puis relancez l’analyse.",
    scanFailed: "Impossible d’analyser cette page.", webmConfirm: "Cette vidéo est au format WebM. ClipFlow doit la convertir en MP4 pour la rendre compatible avec macOS et Premiere Pro. Voulez-vous continuer ?",
    detectedOne: "1 vidéo détectée{extras}.", detectedMany: "{count} vidéos détectées{extras}.",
    drmIgnored: "lecteur DRM ignoré", hiddenVariantOne: "1 variante technique masquée", hiddenVariantMany: "{count} variantes techniques masquées",
    bestSource: "meilleure source détectée", video: "Vidéo", integratedPlayer: "Lecteur intégré",
    integratedVideoPlayer: "Lecteur vidéo dans un cadre intégré", kindVideo: "VIDÉO",
  },
  en: {
    openSettings: "Open settings", closeSettings: "Close settings", settings: "Settings",
    webMedia: "Web media", settingsHint: "Customize ClipFlow",
    downloadSettings: "Download settings", language: "Extension language", languageAuto: "Automatic",
    extensionVersion: "Extension {version}",
    saveTo: "Save to", destinationFolder: "Destination folder", downloads: "Downloads",
    otherFolder: "Other folder…", chosenFolder: "Selected folder",
    completionSoundTitle: "Play a sound when the download finishes", completionSound: "Completion sound",
    whenReady: "When the file is ready", checkUpdate: "Check for updates",
    updateHint: "ClipFlow checks secure GitHub releases.", fileOption: "File option",
    audioOnly: "Audio only", mp3NoVideo: "MP3 without video", download: "Download",
    preparing: "Preparing…", analyzingPage: "Analyzing page…", rescan: "Scan again",
    searchingPlayers: "Looking for video players…", engineUnavailable: "The ClipFlow engine is unavailable.",
    updateFailed: "The update request failed.", installVersion: "Install ClipFlow v{version}",
    updateAvailable: "New version available · app, extension and Premiere Pro panel.",
    upToDate: "ClipFlow v{version} is up to date.", checking: "Checking…",
    secureGithub: "Securely connecting to GitHub…", retry: "Try again", installing: "Installing…",
    installingDetail: "Downloading, verifying and installing…", updateInstalled: "Update installed.",
    updateComplete: "Update complete", retryInstall: "Retry installation", toFolder: "To {folder}",
    stateUnavailable: "Status temporarily unavailable.", downloading: "Downloading…",
    downloadComplete: "Download complete", complete: "Done", fileReady: "File ready.",
    downloadCancelled: "Download cancelled", downloadError: "Download failed",
    downloadFailed: "The download failed.", protected: "Protected",
    drmManifest: "This source manifest is DRM-encrypted.", downloadConvert: "Download and convert to MP4",
    send: "Sending…", unavailable: "ClipFlow is unavailable.", tf1Preparing: "Automatically preparing the TF1 stream…",
    startedBackground: "Download started in the background.", inProgress: "In progress",
    chromePageUnsupported: "This Chrome page cannot be analyzed.", pageNoResponse: "The page did not respond to analysis.",
    hlsUnavailable: "The TF1 HLS stream is unavailable.", drmPlayer: "A DRM-protected player was detected. Its encrypted stream cannot be downloaded.",
    noVideo: "No visible video. Start playback for a few seconds, then scan again.",
    scanFailed: "Unable to analyze this page.", webmConfirm: "This video uses WebM. ClipFlow must convert it to MP4 for macOS and Premiere Pro compatibility. Continue?",
    detectedOne: "1 video detected{extras}.", detectedMany: "{count} videos detected{extras}.",
    drmIgnored: "DRM player ignored", hiddenVariantOne: "1 technical variant hidden", hiddenVariantMany: "{count} technical variants hidden",
    bestSource: "best source detected", video: "Video", integratedPlayer: "Embedded player",
    integratedVideoPlayer: "Video player in an embedded frame", kindVideo: "VIDEO",
  },
};

let settings = { ...DEFAULT_SETTINGS };
let activePage = null;

const audioOnly = document.getElementById("audio-only");
const completionSound = document.getElementById("completion-sound");
const language = document.getElementById("language");
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
const progressFill = document.getElementById("progress-fill");
const checkUpdate = document.getElementById("check-update");
const updateStatus = document.getElementById("update-status");
const extensionVersion = document.getElementById("extension-version");
let displayedProgress = 0;
let progressAnimation = null;
let progressPoll = null;
let availableUpdate = null;
let lastUpdateResponse = null;

function activeLanguage() {
  if (settings.language === "fr" || settings.language === "en") return settings.language;
  return String(chrome.i18n.getUILanguage?.() || navigator.language || "en").toLowerCase().startsWith("fr") ? "fr" : "en";
}

function t(key, values = {}) {
  const text = UI_TEXT[activeLanguage()]?.[key] || UI_TEXT.fr[key] || key;
  return Object.entries(values).reduce((result, [name, value]) => result.replaceAll(`{${name}}`, String(value)), text);
}

function applyLanguage() {
  document.documentElement.lang = activeLanguage();
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.title = t(element.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAria));
  });
  extensionVersion.textContent = t("extensionVersion", { version: chrome.runtime.getManifest().version });
  if (lastUpdateResponse) displayUpdate(lastUpdateResponse);
}

function runtimeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(t("engineUnavailable")));
      } else if (!response?.ok) {
        reject(new Error(response?.error || t("updateFailed")));
      } else {
        resolve(response);
      }
    });
  });
}

function displayUpdate(response) {
  lastUpdateResponse = response;
  availableUpdate = response.available ? response : null;
  settingsToggle.classList.toggle("update-ready", Boolean(availableUpdate));
  if (availableUpdate) {
    checkUpdate.textContent = t("installVersion", { version: response.latestVersion || response.latestRelease });
    updateStatus.textContent = t("updateAvailable");
  } else {
    checkUpdate.textContent = t("checkUpdate");
    updateStatus.textContent = t("upToDate", { version: response.currentVersion || response.currentRelease });
  }
}

async function findUpdate(manual = false) {
  if (!manual) {
    const stored = await chrome.storage.local.get("clipFlowUpdateCheck");
    const cached = stored.clipFlowUpdateCheck;
    const installedVersion = chrome.runtime.getManifest().version;
    if (
      cached
      && String(cached.currentVersion || "") === installedVersion
      && Date.now() - Number(cached.checkedAt || 0) < UPDATE_CHECK_INTERVAL
    ) {
      displayUpdate(cached);
      return;
    }
  }
  checkUpdate.disabled = true;
  checkUpdate.textContent = t("checking");
  updateStatus.textContent = t("secureGithub");
  try {
    const response = await runtimeMessage({ type: "check_update", language: activeLanguage() });
    const cached = { ...response, checkedAt: Date.now() };
    await chrome.storage.local.set({ clipFlowUpdateCheck: cached });
    displayUpdate(cached);
  } catch (error) {
    updateStatus.textContent = error.message;
    checkUpdate.textContent = t("retry");
  } finally {
    checkUpdate.disabled = false;
  }
}

async function installAvailableUpdate() {
  if (!availableUpdate) {
    await findUpdate(true);
    return;
  }
  checkUpdate.disabled = true;
  checkUpdate.textContent = t("installing");
  updateStatus.textContent = t("installingDetail");
  try {
    const response = await runtimeMessage({
      type: "install_update",
      release: availableUpdate.latestRelease,
      releaseTag: availableUpdate.releaseTag,
      archiveAssetId: availableUpdate.archiveAssetId,
      checksumAssetId: availableUpdate.checksumAssetId,
      language: activeLanguage(),
    });
    await chrome.storage.local.remove("clipFlowUpdateCheck");
    updateStatus.textContent = activeLanguage() === "en"
      ? "ClipFlow was updated. Restart Premiere Pro if it was open."
      : (response.message || t("updateInstalled"));
    checkUpdate.textContent = t("updateComplete");
    setTimeout(() => chrome.runtime.reload(), 900);
  } catch (error) {
    updateStatus.textContent = error.message;
    checkUpdate.textContent = t("retryInstall");
    checkUpdate.disabled = false;
  }
}

function setSettingsOpen(open) {
  settingsPanel.hidden = !open;
  settingsToggle.setAttribute("aria-expanded", String(open));
  settingsToggle.setAttribute("aria-label", open ? t("closeSettings") : t("openSettings"));
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
  if (!["downloads", "premiere", "custom"].includes(settings.destination)) {
    settings.destination = "downloads";
    settings.destinationPath = "";
  }
  audioOnly.checked = settings.audioOnly;
  completionSound.checked = settings.completionSound;
  language.value = ["auto", "fr", "en"].includes(settings.language) ? settings.language : "auto";
  settings.language = language.value;
  applyLanguage();
  if (settings.destination !== "custom") {
    const labels = { downloads: "downloads" };
    settings.destinationLabel = labels[settings.destination]
      ? t(labels[settings.destination])
      : "Premiere Pro";
  }
  if (settings.destination === "custom" && settings.destinationPath) {
    const option = document.createElement("option");
    option.value = "custom";
    option.textContent = settings.destinationLabel || t("chosenFolder");
    destination.insertBefore(option, destination.querySelector('option[value="choose"]'));
  }
  destination.value = settings.destination;
  await saveSettings();
}

function detectVideosOnPage(uiLanguage = "fr") {
  const copy = uiLanguage === "en" ? {
    detectedVideo: "Detected video", youtubePlayer: "YouTube player", bestQuality: "best quality via yt-dlp",
    dailymotionPlayer: "Dailymotion player", htmlPlayer: "HTML5 player", video: "Video",
    substackSource: "Substack MP4 source", fromPage: "extracted from page", declaredStream: "Stream declared by page",
    linkedMedia: "Linked media", mediaLink: "Media link found on page", declaredMedia: "Media declared in page data",
    embeddedPlayer: "Embedded player", embeddedPlayerPage: "Embedded video player page", originalPage: "Extracted from original page",
    mediaStream: "Media stream", detectedStream: "Detected {kind} stream", network: "network", networkActivity: "network activity",
  } : {
    detectedVideo: "Vidéo détectée", youtubePlayer: "lecteur YouTube", bestQuality: "meilleure qualité via yt-dlp",
    dailymotionPlayer: "lecteur Dailymotion", htmlPlayer: "lecteur HTML5", video: "Vidéo",
    substackSource: "source MP4 Substack", fromPage: "extraction depuis la page", declaredStream: "Flux déclaré par la page",
    linkedMedia: "Média lié", mediaLink: "Lien média présent dans la page", declaredMedia: "Média déclaré dans les données de la page",
    embeddedPlayer: "Lecteur intégré", embeddedPlayerPage: "Page du lecteur vidéo intégré", originalPage: "Extraction depuis la page d’origine",
    mediaStream: "Flux média", detectedStream: "Flux {kind} détecté", network: "réseau", networkActivity: "activité réseau",
  };
  const detectorText = (key, values = {}) => Object.entries(values).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)), copy[key],
  );
  const pageUrl = location.href;
  const title = document.title || location.hostname;
  const pageThumbnailSource = document.querySelector(
    'meta[property="og:image"], meta[property="og:image:secure_url"], meta[name="twitter:image"], meta[name="twitter:image:src"]',
  )?.content || "";
  let pageThumbnail = "";
  try {
    const resolvedThumbnail = new URL(pageThumbnailSource, pageUrl);
    if (["http:", "https:"].includes(resolvedThumbnail.protocol)) pageThumbnail = resolvedThumbnail.href;
  } catch (_error) { /* aucune miniature de page exploitable */ }
  const pageThumbnailLooksGeneric = /(?:^|[\/_-])(?:logo|brand|icon|favicon|avatar)(?:[\/_\-.]|$)/i.test(pageThumbnail);
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

  function youtubeVideoId(rawUrl) {
    try {
      const parsed = new URL(rawUrl);
      if (parsed.hostname === "youtu.be") return parsed.pathname.split("/").filter(Boolean)[0] || "";
      if (parsed.pathname === "/watch") return parsed.searchParams.get("v") || "";
      const match = parsed.pathname.match(/^\/(?:shorts|live|embed)\/([^/?#]+)/);
      return match?.[1] || "";
    } catch (_error) {
      return "";
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
    if (/\.mp4(?:$|[?#&])/i.test(decoded) || /(?:format|type)=mp4/i.test(decoded)) return "MP4";
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

  function visibleRect(element) {
    const rect = element?.getBoundingClientRect?.();
    if (!rect || rect.width < 80 || rect.height < 45) return null;
    if (rect.right <= 0 || rect.bottom <= 0 || rect.left >= innerWidth || rect.top >= innerHeight) return null;
    return {
      x: Math.max(0, rect.left),
      y: Math.max(0, rect.top),
      width: Math.min(rect.width, innerWidth - Math.max(0, rect.left)),
      height: Math.min(rect.height, innerHeight - Math.max(0, rect.top)),
      viewportWidth: innerWidth,
      viewportHeight: innerHeight,
    };
  }

  function captureVideoFrame(video) {
    try {
      if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) return "";
      const width = Math.min(240, video.videoWidth);
      const height = Math.max(1, Math.round(width * video.videoHeight / video.videoWidth));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = Math.min(160, height);
      const context = canvas.getContext("2d", { alpha: false });
      if (!context) return "";
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const data = canvas.toDataURL("image/jpeg", 0.74);
      return data.length <= 180_000 ? data : "";
    } catch (_error) {
      return "";
    }
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
      label: label || title || copy.detectedVideo,
      detail: detail || resolved.hostname,
      kind,
      pageFallback: Boolean(options.pageFallback),
      priority: Number(options.priority) || 0,
      playerKey: options.playerKey || "",
      source: options.source || "page",
      mediaRole,
      thumbnail: "",
      thumbnailScore: 0,
      thumbnailRect: options.thumbnailRect || null,
    };
    const capturedThumbnail = typeof options.capturedThumbnail === "string"
      && /^data:image\/(?:jpeg|png|webp);base64,/i.test(options.capturedThumbnail)
      && options.capturedThumbnail.length <= 180_000
      ? options.capturedThumbnail
      : "";
    if (capturedThumbnail) {
      candidate.thumbnail = capturedThumbnail;
      candidate.thumbnailScore = 100;
    } else {
      const thumbnailSource = options.thumbnail || pageThumbnail;
      try {
        const thumbnail = new URL(thumbnailSource, pageUrl);
        if (["http:", "https:"].includes(thumbnail.protocol)) {
          candidate.thumbnail = thumbnail.href;
          candidate.thumbnailScore = options.thumbnailScore
            || (thumbnail.href === pageThumbnail && pageThumbnailLooksGeneric ? 5 : 40);
        }
      } catch (_error) { /* la carte restera sans miniature */ }
    }
    const identity = options.playerKey ? `${url}|${options.playerKey}` : url;
    const previousIndex = seen.get(identity);
    if (previousIndex !== undefined) {
      const previous = found[previousIndex];
      if (previous.priority < candidate.priority) {
        if (candidate.thumbnailScore < previous.thumbnailScore) {
          candidate.thumbnail = previous.thumbnail;
          candidate.thumbnailScore = previous.thumbnailScore;
          candidate.thumbnailRect ||= previous.thumbnailRect;
        }
        found[previousIndex] = candidate;
      } else if (candidate.thumbnailScore > previous.thumbnailScore) {
        previous.thumbnail = candidate.thumbnail;
        previous.thumbnailScore = candidate.thumbnailScore;
        previous.thumbnailRect ||= candidate.thumbnailRect;
      }
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
    const dimensions = width && height ? `${width}×${height}` : copy.youtubePlayer;
    if (isYouTubeVideoPage(pageUrl)) {
      const videoId = youtubeVideoId(pageUrl);
      add(pageUrl, title, `${dimensions} · ${copy.bestQuality}`, {
        kind: "PAGE",
        pageFallback: true,
        priority: 120,
        thumbnail: videoId ? `https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/hqdefault.jpg` : pageThumbnail,
        thumbnailScore: videoId ? 90 : 40,
      });
    }
    return { pageUrl, pageTitle: title, drmDetected, videos: found };
  }

  const dailymotion = /(^|\.)dailymotion\.[a-z]{2,3}$/i.test(location.hostname);
  if (dailymotion) {
    const player = videoElements[0];
    const width = player?.videoWidth || player?.clientWidth || 0;
    const height = player?.videoHeight || player?.clientHeight || 0;
    const dimensions = width && height ? `${width}×${height}` : copy.dailymotionPlayer;
    if (isDailymotionVideoPage(pageUrl)) {
      add(pageUrl, title, `${dimensions} · ${copy.bestQuality}`, {
        kind: "PAGE",
        pageFallback: true,
        priority: 125,
        playerKey: "dailymotion-player",
        source: "page",
        mediaRole: "audio-video",
        thumbnail: pageThumbnail,
      });
    }
    return { pageUrl, pageTitle: title, drmDetected, durationSeconds, videos: found };
  }

  videoElements.forEach((video, index) => {
    const width = video.videoWidth || video.clientWidth || 0;
    const height = video.videoHeight || video.clientHeight || 0;
    const dimensions = width && height ? `${width}×${height}` : copy.htmlPlayer;
    const substackPlayer = /(^|\.)substack\.com$/i.test(location.hostname)
      ? video.closest("[data-media-upload-id]")
      : null;
    const substackMediaId = substackPlayer
      ? video.dataset.videoId || substackPlayer.dataset.mediaUploadId || ""
      : "";
    let nearbyLabel = "";
    let previous = substackPlayer?.previousElementSibling || null;
    for (let distance = 0; previous && distance < 5; distance += 1) {
      const emphasized = previous.querySelector?.("strong")?.textContent?.trim();
      if (emphasized) {
        nearbyLabel = emphasized;
        break;
      }
      previous = previous.previousElementSibling;
    }
    const label = nearbyLabel
      || video.getAttribute("aria-label")
      || video.getAttribute("title")
      || `${copy.video} ${index + 1}`;
    const rect = video.getBoundingClientRect();
    const capturedThumbnail = captureVideoFrame(video);
    const thumbnailRect = visibleRect(video);
    const playerKey = visibleVideoElements.length
      ? `visual-${Math.round(rect.left / 40)}-${Math.round(rect.top / 40)}-${Math.round(rect.width / 40)}-${Math.round(rect.height / 40)}`
      : `player-${index}`;
    const sources = [
      substackMediaId
        ? `${location.origin}/api/v1/video/upload/${encodeURIComponent(substackMediaId)}/src?type=mp4`
        : "",
      video.currentSrc,
      video.src,
      ...Array.from(video.querySelectorAll("source[src]"), (source) => source.src),
    ].filter(Boolean);
    const directSources = sources.filter((source) => /^https?:/i.test(source));
    directSources.forEach((source) => {
      const isSubstackMp4 = Boolean(substackMediaId) && source.includes(`/video/upload/${substackMediaId}/`);
      add(source, label, isSubstackMp4 ? `${dimensions} · ${copy.substackSource}` : `${dimensions} · ${copy.htmlPlayer}`, {
        priority: isSubstackMp4 ? 130 : 100,
        playerKey,
        source: isSubstackMp4 ? "substack" : "player",
        // A URL carried by a real <video> element is a complete source for
        // progressive players such as SeeArtTV. Without this hint, the filter
        // could prefer the unsupported HTML page over the MP4 being played.
        mediaRole: "audio-video",
        thumbnail: video.poster || pageThumbnail,
        thumbnailScore: video.poster ? 70 : 40,
        capturedThumbnail,
        thumbnailRect,
      });
    });
    add(pageUrl, label, `${dimensions} · ${copy.fromPage}`, {
      kind: "PAGE",
      pageFallback: true,
      priority: directSources.length ? 55 : 75,
      playerKey,
      source: "page",
      mediaRole: "audio-video",
      thumbnail: video.poster || pageThumbnail,
      thumbnailScore: video.poster ? 70 : 40,
      capturedThumbnail,
      thumbnailRect,
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
      add(meta.content, title, copy.declaredStream, { priority: 90, source: "metadata" });
    });
  }

  const mediaPattern = /\.(?:mp4|m4v|mov|webm|m3u8|mpd|mp3|m4a|aac|ogg|ogv)(?:$|[?#&])/i;
  const linkedMedia = Array.from(document.querySelectorAll("a[href], source[src], embed[src]"), (element) => (
    element.href || element.src
  )).filter(Boolean);
  linkedMedia.filter((href) => mediaPattern.test(href)).slice(0, 30).forEach((href, index) => {
    add(href, `${copy.linkedMedia} ${index + 1}`, copy.mediaLink, { priority: 70, source: "link" });
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
        const thumbnail = Array.isArray(value.thumbnailUrl)
          ? value.thumbnailUrl.find((item) => typeof item === "string")
          : (typeof value.thumbnailUrl === "string" ? value.thumbnailUrl : "");
        for (const property of ["contentUrl", "embedUrl", "url"]) {
          if (!audioOnlyObject && typeof value[property] === "string") {
            add(value[property], value.name || `${copy.video} ${structuredVideoIndex}`, copy.declaredMedia, {
              priority: 85,
              source: "structured",
              playerKey: structuredKey,
              mediaRole: /VideoObject/i.test(typeText) ? "audio-video" : "unknown",
              thumbnail,
              thumbnailScore: thumbnail ? 65 : 0,
            });
          }
        }
      }
      pending.push(...Object.values(value).filter((item) => item && typeof item === "object").slice(0, 50));
    }
  });

  embeddedPlayers.forEach((frame, index) => {
    const thumbnailRect = visibleRect(frame);
    add(frame.src, `${copy.embeddedPlayer} ${index + 1}`, copy.embeddedPlayerPage, {
      kind: "PLAYER",
      pageFallback: true,
      priority: 65,
      source: "embed",
      playerKey: `embed-${index}`,
      thumbnailRect,
    });
  });

  if (!videoElements.length && embeddedPlayers.length === 1) {
    add(pageUrl, title, copy.originalPage, {
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
    add(entry.name, kind === "FLUX" ? copy.mediaStream : detectorText("detectedStream", { kind }), `${entry.name.split("/")[2] || copy.network} · ${copy.networkActivity}`, {
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
    progressFill.style.width = `${displayedProgress}%`;
    return;
  }
  if (progressAnimation) clearInterval(progressAnimation);
  progressAnimation = setInterval(() => {
    displayedProgress = Math.min(safeTarget, displayedProgress + 1);
    progressPercent.textContent = `${displayedProgress} %`;
    progressFill.style.width = `${displayedProgress}%`;
    if (displayedProgress >= safeTarget) {
      clearInterval(progressAnimation);
      progressAnimation = null;
    }
  }, 24);
}

function showProgress(jobId, tabId, destinationLabel = t("downloads"), button = null, feedback = null) {
  if (!jobId || !Number.isInteger(Number(tabId))) return;
  progressSection.hidden = false;
  progressLabel.textContent = t("toFolder", { folder: destinationLabel });
  progressDetail.textContent = t("preparing");
  displayedProgress = Math.max(1, displayedProgress);
  progressPercent.textContent = `${displayedProgress} %`;
  progressFill.style.width = `${displayedProgress}%`;
  animateProgress(displayedProgress);
  if (progressPoll) clearTimeout(progressPoll);

  const poll = () => {
    chrome.runtime.sendMessage({ type: "download_status", jobId, tabId: Number(tabId), language: activeLanguage() }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        progressDetail.textContent = response?.error || t("stateUnavailable");
        progressPoll = setTimeout(poll, 1200);
        return;
      }
      animateProgress(response.progress);
      progressDetail.textContent = response.message || t("downloading");
      if (response.state === "complete") {
        animateProgress(100);
        progressLabel.textContent = t("downloadComplete");
        if (button) button.textContent = t("complete");
        if (feedback) {
          feedback.dataset.kind = "success";
          feedback.textContent = t("fileReady");
        }
        return;
      }
      if (response.state === "error" || response.state === "cancelled") {
        progressLabel.textContent = response.state === "cancelled" ? t("downloadCancelled") : t("downloadError");
        if (button) {
          button.disabled = false;
          button.textContent = t("retry");
        }
        if (feedback) {
          feedback.dataset.kind = "error";
          feedback.textContent = response.message || t("downloadFailed");
        }
        return;
      }
      progressPoll = setTimeout(poll, 700);
    });
  };
  poll();
}

function restoreActiveProgress(tabId) {
    chrome.runtime.sendMessage({ type: "get_active_job", tabId, language: activeLanguage() }, (response) => {
    const job = response?.job;
    if (chrome.runtime.lastError || !response?.ok || !job?.jobId) return;
    if (Date.now() - Number(job.updatedAt || 0) > 24 * 60 * 60 * 1000) return;
    showProgress(job.jobId, tabId, job.destinationLabel);
    animateProgress(job.progress || 1);
    if (job.message) progressDetail.textContent = job.message;
  });
}

function requiresWebmConversion(video) {
  if (video.kind === "WEBM") return true;
  try {
    return new URL(video.url).pathname.toLowerCase().endsWith(".webm");
  } catch (_error) {
    return false;
  }
}

function capturedTabImage(windowId) {
  return new Promise((resolve) => {
    chrome.tabs.captureVisibleTab(windowId, { format: "jpeg", quality: 72 }, (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) resolve("");
      else resolve(dataUrl);
    });
  });
}

function croppedVisibleThumbnail(screenshotUrl, rect) {
  return new Promise((resolve) => {
    if (!screenshotUrl || !rect?.width || !rect?.height || !rect.viewportWidth || !rect.viewportHeight) {
      resolve("");
      return;
    }
    const image = new Image();
    image.onload = () => {
      try {
        const scaleX = image.naturalWidth / rect.viewportWidth;
        const scaleY = image.naturalHeight / rect.viewportHeight;
        const sourceX = Math.max(0, Math.round(rect.x * scaleX));
        const sourceY = Math.max(0, Math.round(rect.y * scaleY));
        const sourceWidth = Math.min(image.naturalWidth - sourceX, Math.round(rect.width * scaleX));
        const sourceHeight = Math.min(image.naturalHeight - sourceY, Math.round(rect.height * scaleY));
        if (sourceWidth < 40 || sourceHeight < 24) {
          resolve("");
          return;
        }
        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = Math.max(90, Math.min(150, Math.round(240 * sourceHeight / sourceWidth)));
        const context = canvas.getContext("2d", { alpha: false });
        if (!context) {
          resolve("");
          return;
        }
        context.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.76));
      } catch (_error) {
        resolve("");
      }
    };
    image.onerror = () => resolve("");
    image.src = screenshotUrl;
  });
}

async function enrichWeakThumbnails(tab, selectedVideos) {
  const targets = selectedVideos.filter((video) => video.thumbnailRect && Number(video.thumbnailScore || 0) < 70);
  if (!targets.length) return;
  const screenshot = await capturedTabImage(tab.windowId);
  if (!screenshot) return;
  await Promise.all(targets.map(async (video) => {
    const thumbnail = await croppedVisibleThumbnail(screenshot, video.thumbnailRect);
    if (thumbnail) {
      video.thumbnail = thumbnail;
      video.thumbnailScore = 95;
    }
  }));
}

function createVideoCard(video, index) {
  const card = document.createElement("article");
  card.className = "video-card";
  let thumbnail = null;
  if (video.thumbnail) {
    thumbnail = document.createElement("img");
    thumbnail.className = "video-thumbnail";
    thumbnail.src = video.thumbnail;
    thumbnail.alt = "";
    thumbnail.loading = "eager";
    thumbnail.referrerPolicy = "no-referrer";
    thumbnail.addEventListener("error", () => {
      thumbnail.remove();
      card.classList.add("without-thumbnail");
    });
  } else {
    card.classList.add("without-thumbnail");
  }
  const heading = document.createElement("div");
  heading.className = "video-heading";
  const kind = document.createElement("span");
  kind.className = "video-kind";
  kind.textContent = video.kind === "VIDÉO" ? t("kindVideo") : (video.kind || t("kindVideo"));
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
  const defaultButtonLabel = requiresWebmConversion(video)
    ? t("downloadConvert")
    : t("download");
  button.textContent = defaultButtonLabel;
  const feedback = document.createElement("div");
  feedback.className = "video-feedback";

  if (video.drmProtected) {
    button.disabled = true;
    button.textContent = t("protected");
    feedback.dataset.kind = "error";
    feedback.textContent = t("drmManifest");
    card.dataset.index = String(index);
    card.append(...(thumbnail ? [thumbnail] : []), heading, detail, button, feedback);
    return card;
  }

  button.addEventListener("click", () => {
    if (requiresWebmConversion(video)) {
      const accepted = window.confirm(
        t("webmConfirm"),
      );
      if (!accepted) return;
    }
    button.disabled = true;
    button.textContent = t("send");
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
      language: activeLanguage(),
    }, (response) => {
      button.disabled = false;
      button.textContent = defaultButtonLabel;
      if (chrome.runtime.lastError || !response?.ok) {
        feedback.dataset.kind = "error";
        feedback.textContent = response?.error || t("unavailable");
        return;
      }
      feedback.dataset.kind = "success";
      feedback.textContent = response.preparing
        ? t("tf1Preparing")
        : t("startedBackground");
      if (response.jobId) {
        button.textContent = t("inProgress");
        showProgress(response.jobId, activePage.tabId, response.destinationLabel, button, feedback);
      } else {
        button.disabled = false;
        button.textContent = defaultButtonLabel;
      }
    });
  });

  card.dataset.index = String(index);
  card.append(...(thumbnail ? [thumbnail] : []), heading, detail, button, feedback);
  return card;
}

async function scan() {
  videos.replaceChildren();
  pageTitle.textContent = t("analyzingPage");
  setStatus(t("searchingPlayers"));
  rescan.disabled = true;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https?:/i.test(tab.url || "")) {
      throw new Error(t("chromePageUnsupported"));
    }
    restoreActiveProgress(tab.id);
    let results;
    try {
      results = await chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: detectVideosOnPage,
        args: [activeLanguage()],
      });
    } catch (_frameError) {
      results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: detectVideosOnPage,
        args: [activeLanguage()],
      });
    }
    const mainResult = results.find((result) => result.frameId === 0)?.result;
    if (!mainResult) throw new Error(t("pageNoResponse"));
    const topPlayerKeys = new Set(mainResult.videos.map((video) => video.playerKey).filter(Boolean));
    const singleEmbeddedPlayer = topPlayerKeys.has("embed-0")
      && !Array.from(topPlayerKeys).some((key) => /^embed-[1-9]\d*$/.test(key));
    const merged = new Map();
    const topFrameRects = new Map();
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
          if (injection.frameId === 0 && video.thumbnailRect) topFrameRects.set(video.playerKey, video.thumbnailRect);
          if (injection.frameId !== 0) video.thumbnailRect = null;
        }
        if (injection.frameId !== 0 && video.pageFallback && video.kind === "PAGE") {
          video.kind = "PLAYER";
          video.label = frame.pageTitle || t("integratedPlayer");
          video.detail = t("integratedVideoPlayer");
          video.priority = Math.max(65, video.priority || 0);
        }
        const identity = `${video.url}|${video.playerKey || ""}`;
        const previous = merged.get(identity);
        if (!previous || (previous.priority || 0) < (video.priority || 0)) merged.set(identity, video);
      });
    });
    merged.forEach((video) => {
      if (!video.thumbnailRect && video.playerKey && topFrameRects.has(video.playerKey)) {
        video.thumbnailRect = topFrameRects.get(video.playerKey);
      }
    });
    let monitoredMedia = [];
    let tf1Status = null;
    try {
      const monitored = await chrome.runtime.sendMessage({ type: "get_network_media", tabId: tab.id, language: activeLanguage() });
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
      setStatus(tf1Status.message || t("hlsUnavailable"), "error");
      return;
    }
    const filtered = selectRealVideos(allCandidates);
    const multipleVideos = filtered.videos.length > 1;
    const selectedVideos = filtered.videos.map((video, index) => ({
      ...video,
      label: multipleVideos
        ? (video.label || `${t("video")} ${index + 1}`)
        : (tab.title || mainResult.pageTitle || video.label),
      detail: `${video.kind === "VIDÉO" ? t("kindVideo") : video.kind} · ${t("bestSource")}`,
    }));
    await enrichWeakThumbnails(tab, selectedVideos);
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
        setStatus(t("drmPlayer"), "warning");
      } else {
        setStatus(t("noVideo"));
      }
      return;
    }
    const count = activePage.videos.length;
    const drmNote = activePage.drmDetected ? t("drmIgnored") : "";
    const notes = [];
    if (activePage.hiddenSourceCount) notes.push(t(activePage.hiddenSourceCount > 1 ? "hiddenVariantMany" : "hiddenVariantOne", { count: activePage.hiddenSourceCount }));
    if (drmNote) notes.push(drmNote);
    const extras = notes.length ? ` · ${notes.join(" · ")}` : "";
    setStatus(t(count > 1 ? "detectedMany" : "detectedOne", { count, extras }), activePage.drmDetected ? "warning" : "normal");
    activePage.videos.forEach((video, index) => videos.append(createVideoCard(video, index)));
  } catch (error) {
    setStatus(error.message || t("scanFailed"), "error");
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

language.addEventListener("change", async () => {
  settings.language = language.value;
  if (settings.destination !== "custom") {
    const labels = { downloads: "downloads" };
    settings.destinationLabel = labels[settings.destination]
      ? t(labels[settings.destination])
      : "Premiere Pro";
  }
  applyLanguage();
  setSettingsOpen(true);
  await saveSettings();
  await scan();
});

destination.addEventListener("change", async () => {
  if (destination.value === "choose") {
    destination.disabled = true;
    chrome.runtime.sendMessage({ type: "choose_folder", language: activeLanguage() }, async (response) => {
      destination.disabled = false;
      if (chrome.runtime.lastError || !response?.ok) {
        destination.value = settings.destination;
        if (response?.error) setStatus(response.error, "error");
        return;
      }
      settings.destination = "custom";
      settings.destinationPath = response.path;
      settings.destinationLabel = response.label || t("chosenFolder");
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

checkUpdate.addEventListener("click", installAvailableUpdate);

rescan.addEventListener("click", scan);

loadSettings()
  .then(() => Promise.all([scan(), findUpdate(false)]))
  .catch((error) => setStatus(error.message, "error"));
