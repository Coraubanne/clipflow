import json
import queue
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import (
    PROFILES,
    DownloadWorker,
    already_downloaded_path,
    automatic_browser_session_enabled,
    authentication_required_output,
    browser_cookie_source,
    build_download_command,
    child_environment,
    consume_extension_requests,
    drm_protected_output,
    ensure_chrome_native_host,
    extension_request_values,
    hide_visible_partials,
    is_web_url,
    is_youtube_url,
    is_retryable_output,
    last_used_browser_profile,
    queue_premiere_import,
    wait_for_premiere_import,
    play_completion_sound,
    resume_legacy_partials,
    validation_timed_out,
    with_browser_cookies,
    write_extension_status,
)


class TubeSaveTests(unittest.TestCase):
    def test_distribution_is_a_background_only_user_agent(self):
        project = Path(__file__).resolve().parents[1]
        source = (project / "app.py").read_text(encoding="utf-8")
        spec = (project / "TubeSave.spec").read_text(encoding="utf-8")
        app_class = source.index("class TubeSaveApp(tk.Tk):")
        constructor_start = source.index("    def __init__(self) -> None:", app_class)
        constructor = source[constructor_start:source.index("    def _environment_status", constructor_start)]
        reopen = source[source.index("    def _show_window"):source.index("    def _build_ui", source.index("    def _show_window"))]
        extension_poll = source[source.index("    def _poll_extension_requests"):source.index("    def _cancel", source.index("    def _poll_extension_requests"))]
        self.assertIn('"LSUIElement": True', spec)
        self.assertIn("super().__init__(useTk=False)", constructor)
        self.assertNotIn("self._build_ui()", constructor)
        self.assertIn("TubeSaveApp().run_forever()", source)
        self.assertNotIn("deiconify", reopen)
        self.assertNotIn("deiconify", extension_poll)

    def test_completion_sound_uses_native_afplay_without_a_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            player = root / "afplay"
            sound = root / "Pop.aiff"
            player.touch()
            sound.touch()
            with patch("app.subprocess.Popen") as popen:
                self.assertTrue(play_completion_sound(player, (sound,)))
        popen.assert_called_once_with(
            [str(player), str(sound)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def test_extension_progress_status_is_atomic_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            write_extension_status("job-42", "running", 140, "Téléchargement", home)
            status = home / "Library/Application Support/TubeSave/Status/job-42.json"
            payload = json.loads(status.read_text(encoding="utf-8"))
        self.assertEqual(payload["state"], "running")
        self.assertEqual(payload["progress"], 100)
        self.assertEqual(payload["message"], "Téléchargement")

    def test_youtube_url(self):
        self.assertTrue(is_youtube_url("https://youtu.be/abc"))
        self.assertFalse(is_youtube_url("https://example.com/abc"))

    def test_public_web_url_accepts_video_sites_and_refuses_local_targets(self):
        self.assertTrue(is_web_url("https://example.com/videos/watch?id=42"))
        self.assertTrue(is_web_url("http://media.example.org/movie.mp4"))
        self.assertFalse(is_web_url("http://localhost/video.mp4"))
        self.assertFalse(is_web_url("http://127.0.0.1/video.mp4"))
        self.assertFalse(is_web_url("http://192.168.1.20/video.mp4"))
        self.assertFalse(is_web_url("file:///tmp/video.mp4"))
        self.assertFalse(is_web_url("https://user:secret@example.com/video"))

    def test_compatible_profile_requires_h264_mp4_without_resolution_limit(self):
        profile = PROFILES[0]
        with tempfile.TemporaryDirectory() as directory:
            command = build_download_command(
                ["python", "-m", "yt_dlp"],
                "https://youtu.be/abc",
                Path(directory),
                profile,
                Path("/tmp/ffmpeg"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            )
        self.assertIn("res,lang,br,fps", command)
        self.assertFalse(any("res:" in item for item in command))
        self.assertEqual(command[command.index("--merge-output-format") + 1], "mp4")
        self.assertNotIn("--remux-video", command)
        selector = command[command.index("--format") + 1]
        self.assertIn("[ext=mp4]", selector)
        self.assertIn("[vcodec^=avc1]", selector)
        self.assertTrue(selector.startswith("bv[ext=mp4][vcodec^=avc1][protocol^=http]"))

    def test_default_is_unlimited_compatible_mp4(self):
        self.assertEqual(PROFILES[0].mode, "compatible")
        self.assertIsNone(PROFILES[0].max_height)

    def test_default_prioritizes_max_h264_resolution_and_original_audio(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        )
        self.assertIn("res,lang,br,fps", command)
        self.assertFalse(any("res:1080" in item for item in command))
        self.assertFalse(any("vcodec:h264" in item for item in command))
        self.assertFalse(any("hevc" in item.lower() for item in command))
        self.assertNotIn("--extractor-args", command)
        self.assertEqual(command[command.index("--concurrent-fragments") + 1], "4")
        selector = command[command.index("--format") + 1]
        self.assertEqual(
            selector,
            "bv[ext=mp4][vcodec^=avc1][protocol^=http]+ba[ext=m4a][protocol^=http]/"
            "b[ext=mp4][vcodec^=avc1][protocol^=http]/"
            "bv[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4][vcodec^=avc1]/"
            "b[ext=mp4][protocol^=http]/b[ext=mp4]",
        )
        self.assertNotIn("height<=", selector)
        self.assertNotIn("bv*", selector)
        self.assertEqual(selector.rsplit("/", 1)[-1], "b[ext=mp4]")
        self.assertEqual(command[command.index("--merge-output-format") + 1], "mp4")
        self.assertNotIn("--remux-video", command)

    def test_audio_profile_prioritizes_original_language(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[-1],
            Path("/tmp/ffmpeg"),
            None,
        )
        self.assertIn("lang,br", command)

    def test_command_is_isolated_and_filename_is_filesystem_safe(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        )
        self.assertIn("--ignore-config", command)
        self.assertIn("--continue", command)
        self.assertIn("--no-quiet", command)
        output = command[command.index("--output") + 1]
        self.assertIn("%(title).150B", output)
        self.assertEqual(Path(output).name, "%(title).150B [%(id)s] compatible.%(ext)s")
        self.assertFalse(Path(output).is_absolute())

    def test_intermediary_files_use_a_hidden_folder_on_the_destination_drive(self):
        destination = Path("/Volumes/External/WatchTower")
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            destination,
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
        )
        paths = [command[index + 1] for index, item in enumerate(command) if item == "--paths"]
        self.assertEqual(paths, [f"home:{destination}", "temp:.tubesave-incomplete"])

    def test_visible_resume_files_are_moved_to_hidden_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            fragments = [
                destination / "Video [abcdefghijk] 1080p.f312.mp4.part",
                destination / "Video [abcdefghijk] 1080p.f312.mp4.part-Frag4.part",
                destination / "Video [abcdefghijk] 1080p.f312.mp4.ytdl",
            ]
            unrelated = destination / "Other [zyxwvutsrqp] 1080p.mp4.part"
            for path in (*fragments, unrelated):
                path.write_text("partial", encoding="utf-8")

            moved = hide_visible_partials(destination, "https://youtu.be/abcdefghijk")

            self.assertEqual(moved, 3)
            for path in fragments:
                self.assertFalse(path.exists())
                self.assertTrue((destination / ".tubesave-incomplete" / path.name).is_file())
            self.assertTrue(unrelated.is_file())

    def test_quality_suffix_avoids_skipping_an_older_lower_quality_file(self):
        video = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
        )
        audio = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[-1],
            Path("/tmp/ffmpeg"),
            None,
        )
        self.assertIn("compatible", video[video.index("--output") + 1])
        self.assertIn("audio", audio[audio.index("--output") + 1])

    def test_network_waits_are_bounded(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        )
        self.assertEqual(command[command.index("--socket-timeout") + 1], "30")
        self.assertEqual(command[command.index("--extractor-retries") + 1], "5")
        self.assertEqual(command[command.index("--retries") + 1], "10")
        self.assertEqual(command[command.index("--fragment-retries") + 1], "20")

    def test_child_output_is_unbuffered_for_live_error_detection(self):
        environment = child_environment(None)
        self.assertEqual(environment["PYTHONUNBUFFERED"], "1")

    def test_browser_is_optional_for_public_videos(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://youtu.be/abc",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
        )
        self.assertEqual(command[-1], "https://youtu.be/abc")

    def test_direct_media_can_receive_its_page_as_referer(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://cdn.example.com/video/master.m3u8",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
            "https://example.com/watch/42",
        )
        self.assertEqual(
            command[command.index("--referer") + 1],
            "https://example.com/watch/42",
        )
        self.assertEqual(command[-1], "https://cdn.example.com/video/master.m3u8")

    def test_vimeo_manifest_uses_page_title_and_stable_identity(self):
        command = build_download_command(
            ["python", "-m", "yt_dlp"],
            "https://vod-adaptive-ak.vimeocdn.com/exp=1/master.m3u8?token=signed",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
            "https://vimeo.com/18264915?utm_source=chatgpt.com",
            "X-ray of the pocket watch from the wreck of The Swan | Vimeo",
        )
        output = command[command.index("--output") + 1]
        self.assertIn("X-ray of the pocket watch", output)
        self.assertIn("[vimeo-18264915-", output)
        self.assertNotIn("%(title)", output)
        self.assertNotIn("%(id)", output)

    def test_manifest_literal_percent_is_escaped_for_yt_dlp_template(self):
        command = build_download_command(
            ["yt-dlp"],
            "https://cdn.example.com/master.m3u8",
            Path("/tmp"),
            PROFILES[0],
            Path("/tmp/ffmpeg"),
            None,
            "https://example.com/watch/42",
            "Démo 100%",
        )
        self.assertIn("100%%", command[command.index("--output") + 1])

    def test_network_errors_are_retried(self):
        self.assertTrue(is_retryable_output("ERROR: Network is unreachable"))
        self.assertTrue(is_retryable_output("The read operation timed out"))
        self.assertFalse(is_retryable_output("Requested format is not available"))

    def test_early_403_requests_browser_validation(self):
        line = "Got error: HTTP Error 403: Forbidden. Retrying fragment 1"
        self.assertTrue(authentication_required_output(line, download_started=False))
        self.assertFalse(authentication_required_output(line, download_started=True))
        self.assertTrue(authentication_required_output("Sign in to confirm you're not a bot"))

    def test_drm_diagnostic_is_recognized_without_matching_unrelated_text(self):
        self.assertTrue(drm_protected_output("ERROR: This video is DRM protected"))
        self.assertTrue(drm_protected_output("The stream is protected by DRM"))
        self.assertFalse(drm_protected_output("Copyright protected video"))

    def test_existing_download_path_is_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "Une vidéo [abcdefghijk] 1080p.mp4"
            existing.write_bytes(b"video")
            line = f"[download] {existing} has already been downloaded"
            self.assertEqual(already_downloaded_path(line), existing)
            self.assertIsNone(already_downloaded_path("[download] 100%"))

    def test_worker_recovers_without_reopening_the_app(self):
        class RecoveringWorker(DownloadWorker):
            def __init__(self):
                super().__init__(["yt-dlp"], queue.Queue(), {}, None)
                self.results = iter(
                    [
                        (1, True, False, False),
                        (0, False, False, False),
                    ]
                )

            def _download_once(self):
                return next(self.results)

        worker = RecoveringWorker()
        with patch("app.time.sleep"):
            worker._run()
        self.assertEqual(worker.events.get_nowait(), ("retry", 1))
        self.assertEqual(worker.events.get_nowait(), ("finished", None))

    def test_cookie_retry_keeps_url_last(self):
        command = ["yt-dlp", "--format", "best", "https://youtu.be/abc"]
        retried = with_browser_cookies(command, "chrome")
        self.assertEqual(retried[-1], "https://youtu.be/abc")
        self.assertEqual(retried[-3:-1], ["--cookies-from-browser", "chrome"])

    def test_automatic_browser_session_requires_an_explicit_true_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / "Library/Application Support/TubeSave/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                '{"use_browser_session_automatically": true}',
                encoding="utf-8",
            )
            self.assertTrue(automatic_browser_session_enabled(home))
            settings.write_text(
                '{"use_browser_session_automatically": "true"}',
                encoding="utf-8",
            )
            self.assertFalse(automatic_browser_session_enabled(home))

    def test_automatic_browser_session_defaults_to_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertFalse(automatic_browser_session_enabled(home))
            settings = home / "Library/Application Support/TubeSave/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text("not json", encoding="utf-8")
            self.assertFalse(automatic_browser_session_enabled(home))

    def test_worker_automatically_retries_with_authorized_browser_session(self):
        class AuthorizedWorker(DownloadWorker):
            def __init__(self):
                super().__init__(
                    ["yt-dlp", "https://youtu.be/abc"],
                    queue.Queue(),
                    {},
                    "chrome:Default",
                    automatic_cookies=True,
                )
                self.results = iter(
                    [
                        (1, False, True, False),
                        (0, False, False, False),
                    ]
                )

            def _download_once(self):
                return next(self.results)

        worker = AuthorizedWorker()
        worker._run()
        self.assertEqual(
            worker.events.get_nowait(),
            ("retry_with_cookies", "chrome:Default"),
        )
        self.assertEqual(worker.events.get_nowait(), ("finished", None))
        self.assertEqual(worker.command[-1], "https://youtu.be/abc")
        self.assertEqual(
            worker.command[-3:-1],
            ["--cookies-from-browser", "chrome:Default"],
        )

    def test_cookie_source_matches_browser(self):
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        brave = Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
        self.assertEqual(browser_cookie_source(chrome), "chrome")
        self.assertEqual(browser_cookie_source(brave), "brave")

    def test_last_used_chrome_profile_is_targeted(self):
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "Library/Application Support/Google/Chrome/Local State"
            state.parent.mkdir(parents=True)
            state.write_text('{"profile": {"last_used": "Profile 2"}}', encoding="utf-8")
            profile = last_used_browser_profile(chrome, root)
        self.assertEqual(profile, "Profile 2")
        self.assertEqual(browser_cookie_source(chrome, profile), "chrome:Profile 2")

    def test_extension_request_sets_quality_and_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            url, folder, quality, referer, source_title, job_id, premiere_project, premiere_bridge, completion_sound = extension_request_values(
                {
                    "url": "https://cdn.example.com/video/master.m3u8",
                    "quality": "best",
                    "destination": str(destination),
                    "referer": "https://example.com/watch/42",
                    "sourceTitle": "  Ma   vidéo  ",
                    "jobId": "job-42",
                    "completionSound": False,
                }
            )
        self.assertEqual(url, "https://cdn.example.com/video/master.m3u8")
        self.assertEqual(folder, destination)
        self.assertEqual(quality, PROFILES[0].label)
        self.assertEqual(referer, "https://example.com/watch/42")
        self.assertEqual(source_title, "Ma vidéo")
        self.assertEqual(job_id, "job-42")
        self.assertIsNone(premiere_project)
        self.assertIsNone(premiere_bridge)
        self.assertFalse(completion_sound)

    def test_extension_inbox_is_consumed(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            destination = inbox / "Videos"
            destination.mkdir()
            request = inbox / "001.json"
            request.write_text(
                '{"url":"https://www.youtube.com/watch?v=abcdefghijk",'
                '"quality":"1080","destination":"' + str(destination) + '"}',
                encoding="utf-8",
            )
            jobs = consume_extension_requests(inbox)
            self.assertFalse(request.exists())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0][2], PROFILES[0].label)
        self.assertIsNone(jobs[0][3])
        self.assertIsNone(jobs[0][4])
        self.assertIsNone(jobs[0][5])
        self.assertIsNone(jobs[0][6])
        self.assertIsNone(jobs[0][7])
        self.assertTrue(jobs[0][8])

    def test_premiere_import_is_queued_only_after_final_file_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "Montage" / "Film.prproj"
            media = project.parent / "Médias ClipFlow" / "Plan.mp4"
            media.parent.mkdir(parents=True)
            project.write_text("project", encoding="utf-8")
            media.write_text("media", encoding="utf-8")
            result = queue_premiere_import(media, project, "job-42", home)
            request = home / "Library/Application Support/ClipFlow/Premiere/Imports/job-42.json"
            payload = json.loads(request.read_text(encoding="utf-8"))
        self.assertEqual(payload["mediaPath"], str(media.resolve()))
        self.assertEqual(payload["projectPath"], str(project.resolve()))
        self.assertEqual(result.name, "job-42.json")

    def test_premiere_timeout_keeps_the_completed_download_successful(self):
        events = queue.Queue()
        with patch("app.time.monotonic", side_effect=[0.0, 1.0]):
            wait_for_premiere_import(Path("/missing/result.json"), events, timeout_seconds=0.5)
        event, payload = events.get_nowait()
        self.assertEqual(event, "premiere_import")
        self.assertIsNone(payload[0])
        self.assertIn("Fichier téléchargé", payload[1])

    def test_native_host_manifest_is_registered(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            host = home / "native_host"
            host.write_text("#!/bin/zsh\n", encoding="utf-8")
            host.chmod(0o755)
            manifest = ensure_chrome_native_host(home, host)
            self.assertIsNotNone(manifest)
            data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "fr.tubesave.chrome")
        self.assertEqual(data["path"], str(host.resolve()))
        self.assertEqual(
            data["allowed_origins"],
            ["chrome-extension://emfjpphkcgnjldilcnieaoppmfpfkhfg/"],
        )

    def test_watchdog_only_limits_youtube_validation(self):
        self.assertTrue(validation_timed_out(100.0, False, 161.0))
        self.assertFalse(validation_timed_out(100.0, True, 1000.0))

    def test_legacy_partial_is_renamed_for_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            legacy = destination / "Une vidéo [abcdefghijk] 20260818-212203-439790.f137.mp4.part"
            legacy.write_bytes(b"partial-video")
            renamed = resume_legacy_partials(
                destination,
                "https://www.youtube.com/watch?v=abcdefghijk",
            )
            resumable = destination / "Une vidéo [abcdefghijk].f137.mp4.part"
            self.assertEqual(renamed, 1)
            self.assertFalse(legacy.exists())
            self.assertEqual(resumable.read_bytes(), b"partial-video")


if __name__ == "__main__":
    unittest.main()
