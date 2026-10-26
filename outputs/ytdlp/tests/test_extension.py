import json
import unittest
from pathlib import Path


EXTENSION = Path(__file__).resolve().parents[2] / "ClipFlow Chrome"


class ChromeExtensionTests(unittest.TestCase):
    def test_manifest_adds_scoped_tf1_network_access(self):
        manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "2.8.7")
        self.assertEqual(manifest["name"], "ClipFlow")
        self.assertEqual(
            set(manifest["permissions"]),
            {"nativeMessaging", "storage", "activeTab", "scripting", "webRequest"},
        )
        self.assertEqual(manifest["host_permissions"], ["https://*.tf1.fr/*"])
        self.assertNotIn("content_scripts", manifest)

    def test_popup_scans_loaded_streams_and_embedded_frames(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_EXTENSION_VERSION = "2.8.7"', source)
        self.assertIn("chrome.runtime.reload()", source)
        self.assertIn('performance.getEntriesByType("resource")', source)
        self.assertIn('return "HLS"', source)
        self.assertIn('return "DASH"', source)
        self.assertIn("allFrames: true", source)

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
        self.assertIn("function monitorActiveJob(tabId, jobId)", background)
        self.assertIn("resumeActiveJobMonitors()", background)
        self.assertIn("progress: response.progress", background)
        self.assertIn("updateJobBadge(tabId, response)", background)
        self.assertIn("width: 300px", styles)

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
        self.assertIn("Audio uniquement", markup)
        self.assertIn("MP3 sans vidéo", markup)
        self.assertNotIn('id="choose-folder"', markup)
        self.assertNotIn('id="folder-status"', markup)
        self.assertNotIn('id="scan-hint"', markup)
        self.assertNotIn("<footer>", markup)
        self.assertIn('destination.value === "choose"', source)

    def test_popup_uses_soft_shadows_without_card_outlines(self):
        styles = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn("--shadow-card", styles)
        self.assertIn("--shadow-control", styles)
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
        self.assertIn('button.textContent = "Protégée"', source)
        self.assertIn("selectedVideos.some((video) => video.drmProtected)", source)

    def test_direct_webm_requires_confirmation_before_conversion_download(self):
        source = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("function requiresWebmConversion(video)", source)
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


if __name__ == "__main__":
    unittest.main()
