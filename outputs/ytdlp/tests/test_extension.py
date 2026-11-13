import json
import unittest
from pathlib import Path


EXTENSION = Path(__file__).resolve().parents[2] / "ClipFlow Chrome"


class ChromeExtensionTests(unittest.TestCase):
    def test_manifest_adds_scoped_tf1_network_access(self):
        manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "2.13.1")
        self.assertEqual(manifest["name"], "__MSG_extensionName__")
        self.assertEqual(manifest["default_locale"], "en")
        self.assertEqual(
            set(manifest["permissions"]),
            {"nativeMessaging", "storage", "activeTab", "scripting", "webRequest"},
        )
        self.assertEqual(manifest["host_permissions"], ["https://*.tf1.fr/*"])
        self.assertNotIn("content_scripts", manifest)
        for locale in ("en", "fr"):
            messages = json.loads(
                (EXTENSION / "_locales" / locale / "messages.json").read_text(encoding="utf-8")
            )
            self.assertIn("extensionName", messages)
            self.assertIn("extensionDescription", messages)

    def test_popup_scans_loaded_streams_and_embedded_frames(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_EXTENSION_VERSION = "2.13.1"', source)
        self.assertIn("chrome.runtime.reload()", source)
        self.assertIn('performance.getEntriesByType("resource")', source)
        self.assertIn('return "HLS"', source)
        self.assertIn('return "DASH"', source)
        self.assertIn("allFrames: true", source)

    def test_update_cache_is_invalidated_after_an_extension_upgrade(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("const installedVersion = chrome.runtime.getManifest().version", source)
        self.assertIn('String(cached.currentVersion || "") === installedVersion', source)

    def test_video_cards_show_available_thumbnails(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        styles = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn('meta[property="og:image"]', source)
        self.assertIn("video.poster || pageThumbnail", source)
        self.assertIn("value.thumbnailUrl", source)
        self.assertIn("https://i.ytimg.com/vi/", source)
        self.assertIn("function captureVideoFrame(video)", source)
        self.assertIn("chrome.tabs.captureVisibleTab", source)
        self.assertIn("function croppedVisibleThumbnail", source)
        self.assertIn("await enrichWeakThumbnails(tab, selectedVideos)", source)
        self.assertIn('thumbnail.className = "video-thumbnail"', source)
        self.assertIn("thumbnail.addEventListener(\"error\"", source)
        self.assertIn(".video-thumbnail", styles)
        self.assertIn("object-fit: cover", styles)
        self.assertIn("width: 108px", styles)
        self.assertIn("max-height: 360px", styles)

    def test_popup_sends_page_title_for_generic_stream_filenames(self):
        popup = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn("sourceTitle: video.label || activePage.pageTitle", popup)
        self.assertIn("nativeRequest.sourceTitle = sourceTitle", background)

    def test_youtube_navigation_pages_are_not_offered_as_videos(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("function isYouTubeVideoPage(rawUrl)", source)
        self.assertIn('parsed.pathname === "/watch"', source)
        self.assertIn("if (isYouTubeVideoPage(pageUrl))", source)

    def test_dailymotion_uses_the_supported_page_extractor_not_a_raw_manifest(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        requirements = (EXTENSION.parent / "ytdlp" / "requirements.txt").read_text(encoding="utf-8")
        spec = (EXTENSION.parent / "ytdlp" / "TubeSave.spec").read_text(encoding="utf-8")
        self.assertIn("function isDailymotionVideoPage(rawUrl)", source)
        self.assertIn("if (dailymotion)", source)
        self.assertIn('playerKey: "dailymotion-player"', source)
        self.assertIn("extractorBonus", source)
        self.assertIn("yt-dlp[default,curl-cffi]", requirements)
        self.assertIn('"curl_cffi"', spec)

    def test_popup_shows_compact_numeric_background_progress(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        styles = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn('id="progress-percent"', markup)
        self.assertIn("function animateProgress(target)", source)
        self.assertIn('type: "download_status"', source)
        self.assertIn('action: "status"', background)
        self.assertIn("function monitorActiveJob(tabId, jobId, language", background)
        self.assertIn("resumeActiveJobMonitors()", background)
        self.assertIn("progress: response.progress", background)
        self.assertIn("updateJobBadge(tabId, response)", background)
        self.assertIn('id="progress-fill"', markup)
        self.assertIn("progressFill.style.width", source)
        self.assertIn("width: 356px", styles)

    def test_popup_uses_best_quality_automatically_with_audio_only_checkbox(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn('id="audio-only"', markup)
        self.assertNotIn('id="quality"', markup)
        self.assertIn('settings.audioOnly ? "audio" : "best"', source)
        self.assertIn('requestedQuality === "audio" ? "audio" : "best"', background)

    def test_completion_sound_can_be_disabled_and_is_remembered(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn('id="completion-sound"', markup)
        self.assertIn("completionSound: true", source)
        self.assertIn("settings.completionSound = completionSound.checked", source)
        self.assertIn("completionSound: settings.completionSound", source)
        self.assertIn("completionSound: message.completionSound !== false", background)
        self.assertIn('id="settings-toggle"', markup)
        self.assertIn('id="settings-panel"', markup)
        self.assertIn("function setSettingsOpen(open)", source)
        self.assertIn("setSettingsOpen(settingsPanel.hidden)", source)
        self.assertIn("Son de fin", markup)
        self.assertIn("Quand le fichier est prêt", markup)

    def test_secure_github_update_is_available_from_settings(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn('id="check-update"', markup)
        self.assertIn("Chercher une mise à jour", markup)
        self.assertIn('type: "check_update"', source)
        self.assertIn('type: "install_update"', source)
        self.assertIn('action: "check_update"', background)
        self.assertIn('action: "install_update"', background)
        self.assertIn("UPDATE_CHECK_INTERVAL", source)

    def test_popup_ignores_segments_and_reports_drm(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("segmentPattern", source)
        self.assertIn("drmDetected", source)
        self.assertIn("drmProtected", source)

    def test_popup_keeps_only_compact_essential_controls(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        self.assertIn('value="downloads"', markup)
        self.assertIn('value="premiere"', markup)
        self.assertIn('value="choose"', markup)
        self.assertNotIn('value="movies"', markup)
        self.assertNotIn('value="desktop"', markup)
        self.assertIn('["downloads", "premiere", "custom"]', source)
        self.assertIn("Audio uniquement", markup)
        self.assertIn("MP3 sans vidéo", markup)
        self.assertNotIn('id="choose-folder"', markup)
        self.assertNotIn('id="folder-status"', markup)
        self.assertNotIn('id="scan-hint"', markup)
        self.assertNotIn("<footer>", markup)
        self.assertIn('destination.value === "choose"', source)

    def test_popup_uses_soft_shadows_without_card_outlines(self):
        styles = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn("--shadow-panel", styles)
        self.assertIn("--shadow-control", styles)
        self.assertIn("backdrop-filter: blur(22px)", styles)
        self.assertNotIn("border: 1px", styles)
        self.assertNotIn("border-color:", styles)

    def test_popup_groups_technical_variants_into_real_videos(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("function selectRealVideos(candidates)", source)
        self.assertIn('video.kind !== "AUDIO"', source)
        self.assertIn('video.kind !== "RÉSEAU"', source)
        self.assertIn("hiddenSourceCount", source)
        self.assertIn("meilleure source détectée", source)
        self.assertIn("htmlPlayerGroups", source)
        self.assertIn("structuredVideoIndex", source)
        self.assertIn('`${video.url}|${video.playerKey || ""}`', source)

    def test_popup_prefers_combined_audio_video_and_visible_players(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn('"audio-video": 200', source)
        self.assertIn('video.mediaRole !== "audio-only"', source)
        self.assertIn("const combinedVideos", source)
        self.assertIn("? combinedVideos", source)
        self.assertIn("visibleVideoElements", source)
        self.assertIn("audioOnlyObject", source)
        self.assertIn("progressive players such as SeeArtTV", source)
        self.assertIn('mediaRole: "audio-video",', source)

    def test_popup_groups_embedded_player_without_guessing_tf1_drm(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("embeddedPlayers.length === 1", source)
        self.assertIn('playerKey: "embed-0"', source)
        self.assertNotIn("tf1LongFormProtected", source)
        self.assertNotIn("programme complet TF1+ est protégé par DRM", source)
        self.assertIn("get_network_media", source)
        self.assertIn("delivery.tf1.fr", source)
        self.assertIn("singleEmbeddedPlayer", source)
        self.assertIn('? "0:embed-0"', source)
        self.assertIn('id="destination"', (EXTENSION / "popup.html").read_text(encoding="utf-8"))

    def test_background_captures_tf1_manifests_without_treating_nodrm_as_drm(self):
        source = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn("chrome.webRequest.onHeadersReceived", source)
        self.assertIn("application/dash+xml", source.replace(r"dash\+xml", "application/dash+xml"))
        self.assertIn("no[-_]?drm", source)
        self.assertIn('parsed.hostname === "delivery.tf1.fr"', source)
        self.assertIn("chrome.webRequest.onBeforeSendHeaders", source)
        self.assertIn('url.searchParams.set("format", "hls")', source)
        self.assertIn('source: "tf1-hls"', source)
        self.assertIn("apiMarksDrm", source)
        self.assertNotIn("if (hasDrm)", source)
        self.assertIn('headers = { Authorization: authorization }', source)
        self.assertIn('await chrome.tabs.reload(tabId)', source)
        self.assertIn('url: streamUrl', source)
        self.assertIn('TF1_PENDING_TTL', source)
        self.assertIn('explicitlyClear', source)
        self.assertNotIn("authorization,", source)
        self.assertIn("function hlsManifestHasDrm(manifest)", source)
        self.assertIn("async function inspectHlsDrm(streamUrl)", source)
        self.assertIn("function dashManifestHasDrm(manifest)", source)
        self.assertIn("async function inspectDashDrm(streamUrl)", source)
        self.assertIn('kind === "DASH"', source)
        self.assertIn('drmProtected: manifestDrm === true', source)
        self.assertIn('text: "DRM"', source)

    def test_popup_disables_confirmed_drm_sources(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("if (video.drmProtected)", source)
        self.assertIn('button.textContent = t("protected")', source)
        self.assertIn("selectedVideos.some((video) => video.drmProtected)", source)

    def test_interface_language_can_be_automatic_french_or_english(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        markup = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        background = (EXTENSION / "background.js").read_text(encoding="utf-8")
        self.assertIn('id="language"', markup)
        self.assertIn('value="auto"', markup)
        self.assertIn('value="fr"', markup)
        self.assertIn('value="en"', markup)
        self.assertIn('language: "auto"', source)
        self.assertIn("function activeLanguage()", source)
        self.assertIn("function applyLanguage()", source)
        self.assertIn("language: activeLanguage()", source)
        self.assertIn("const language = interfaceLanguage(message?.language)", background)
        self.assertIn("Langue de l’extension", markup)
        self.assertNotIn("N’affecte pas la langue audio des vidéos", markup)
        self.assertNotIn("languageHint", source)
        self.assertIn('id="extension-version"', markup)
        self.assertIn('t("extensionVersion"', source)

    def test_open_settings_are_visually_blue(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        styles = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn('.settings-toggle[aria-expanded="true"]', styles)
        self.assertIn("linear-gradient(145deg, #2996ff", styles)
        self.assertIn("rgba(24, 132, 255, .16)", styles)
        self.assertIn('document.body.classList.toggle("settings-open", open)', source)
        self.assertIn("body.settings-open .quick-options", styles)
        self.assertIn("body.settings-open .download-progress", styles)
        self.assertIn("body.settings-open .results", styles)

    def test_amazon_video_posters_are_inlined_for_reliable_thumbnails(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("async function inlineAmazonThumbnails(candidates)", source)
        self.assertIn("media-amazon", source)
        self.assertIn('cache: "force-cache"', source)
        self.assertIn("candidate.thumbnail = encoded", source)
        self.assertIn("await inlineAmazonThumbnails(found)", source)

    def test_notification_count_is_removed_from_media_titles(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("function cleanMediaTitle(value)", source)
        self.assertIn('.replace(/^\\s*[\\[(]\\d+[\\])]\\s*/, "")', source)
        self.assertIn("const mediaTitle = cleanMediaTitle(tab.title || mainResult.pageTitle)", source)
        self.assertIn("label: cleanMediaTitle(multipleVideos", source)

    def test_direct_webm_requires_confirmation_before_conversion_download(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("function requiresWebmConversion(video)", source)
        self.assertIn('if (video.kind === "WEBM") return true;', source)
        self.assertIn('.endsWith(".webm")', source)
        self.assertIn("if (requiresWebmConversion(video))", source)
        self.assertIn("const accepted = window.confirm(", source)
        self.assertIn("convertir en MP4", source)
        self.assertIn('"Télécharger et convertir en MP4"', source)
        self.assertIn("if (!accepted) return;", source)
        click_handler = source.index('button.addEventListener("click", () => {')
        confirmation = source.index("window.confirm(", click_handler)
        send_download = source.index("chrome.runtime.sendMessage({", confirmation)
        self.assertLess(confirmation, send_download)

    def test_substack_native_players_use_their_public_mp4_sources(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn('video.closest("[data-media-upload-id]")', source)
        self.assertIn("video.dataset.videoId", source)
        self.assertIn("/api/v1/video/upload/", source)
        self.assertIn("/src?type=mp4", source)
        self.assertIn('source: isSubstackMp4 ? "substack" : "player"', source)
        self.assertIn("priority: isSubstackMp4 ? 130 : 100", source)
        self.assertIn('/(?:format|type)=mp4/i', source)


if __name__ == "__main__":
    unittest.main()
