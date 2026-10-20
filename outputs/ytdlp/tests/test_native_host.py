import io
import json
import struct
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from native_host import (
    active_premiere_project,
    is_public_web_url,
    is_supported_video_request_url,
    launch_app_for_job,
    read_message,
    resolve_destination,
    validated_download_job,
    write_message,
)


class NativeHostTests(unittest.TestCase):
    def test_validated_job_uses_selected_quality_and_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            job = validated_download_job(
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "quality": "best",
                    "destination": "downloads",
                    "completionSound": False,
                },
                home,
            )
        self.assertEqual(job["quality"], "best")
        self.assertEqual(job["destination"], str(home.resolve() / "Downloads"))
        self.assertFalse(job["completionSound"])

    def test_generic_video_url_and_referer_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            job = validated_download_job(
                {
                    "url": "https://cdn.example.com/movie/master.m3u8",
                    "referer": "https://example.com/watch/42",
                    "sourceTitle": "  Film   de démonstration  ",
                    "quality": "best",
                    "destination": "downloads",
                },
                Path(directory),
            )
        self.assertEqual(job["url"], "https://cdn.example.com/movie/master.m3u8")
        self.assertEqual(job["referer"], "https://example.com/watch/42")
        self.assertEqual(job["sourceTitle"], "Film de démonstration")

    def test_custom_destination_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = Path(directory)
            destination = resolve_destination(
                {
                    "destination": "custom",
                    "destinationPath": str(selected),
                }
            )
        self.assertEqual(destination, selected.resolve())

    def test_premiere_destination_uses_saved_active_project(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "Montage" / "Film.prproj"
            project.parent.mkdir()
            project.write_text("project", encoding="utf-8")
            state = home / "Library/Application Support/ClipFlow/Premiere/active-project.json"
            state.parent.mkdir(parents=True)
            state.write_text(
                json.dumps({"projectPath": str(project), "updatedAt": int(time.time() * 1000)}),
                encoding="utf-8",
            )
            job = validated_download_job(
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "quality": "best",
                    "destination": "premiere",
                },
                home,
            )
        self.assertEqual(job["destination"], str((project.parent / "Médias ClipFlow").resolve()))
        self.assertEqual(job["premiereProjectPath"], str(project.resolve()))
        self.assertEqual(job["premiereBridgePath"], str(state.parent.resolve()))

    def test_premiere_prefers_adobe_plugin_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "Montage" / "Film.prproj"
            project.parent.mkdir()
            project.write_text("project", encoding="utf-8")
            bridge = home / (
                "Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/26/External/"
                "fr.clipflow.premiere.bridge/PluginData"
            )
            bridge.mkdir(parents=True)
            (bridge / "active-project.json").write_text(
                json.dumps({"projectPath": str(project), "updatedAt": int(time.time() * 1000)}),
                encoding="utf-8",
            )
            job = validated_download_job(
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "quality": "best",
                    "destination": "premiere",
                },
                home,
            )
        self.assertEqual(job["premiereBridgePath"], str(bridge.resolve()))

    def test_stale_premiere_bridge_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "Library/Application Support/ClipFlow/Premiere/active-project.json"
            state.parent.mkdir(parents=True)
            state.write_text(
                json.dumps({"projectPath": str(home / "Film.prproj"), "updatedAt": 1_000}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "ne répond pas"):
                active_premiere_project(home, now=30)

    def test_legacy_video_quality_is_upgraded_to_best(self):
        with tempfile.TemporaryDirectory() as directory:
            job = validated_download_job(
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "quality": "480",
                    "destination": "downloads",
                },
                Path(directory),
            )
        self.assertEqual(job["quality"], "best")

    def test_local_and_non_web_urls_are_refused(self):
        self.assertFalse(is_public_web_url("http://127.0.0.1/video.mp4"))
        self.assertFalse(is_public_web_url("http://192.168.0.8/video.mp4"))
        with self.assertRaises(ValueError):
            validated_download_job(
                {
                    "url": "file:///tmp/video.mp4",
                    "quality": "1080",
                    "destination": "downloads",
                }
            )

    def test_youtube_navigation_pages_are_refused(self):
        self.assertFalse(is_supported_video_request_url("https://www.youtube.com/results?search_query=test"))
        self.assertFalse(is_supported_video_request_url("https://www.youtube.com/@openai"))
        self.assertTrue(is_supported_video_request_url("https://www.youtube.com/watch?v=abcdefghijk"))
        self.assertTrue(is_supported_video_request_url("https://youtu.be/abcdefghijk"))

    def test_native_message_round_trip(self):
        output = io.BytesIO()
        write_message({"ok": True, "label": "Vidéos"}, output)
        output.seek(0)
        self.assertEqual(read_message(output), {"ok": True, "label": "Vidéos"})
        output.seek(0)
        size = struct.unpack("@I", output.read(4))[0]
        self.assertEqual(json.loads(output.read(size)), {"ok": True, "label": "Vidéos"})

    @patch("native_host.subprocess.run")
    def test_stale_app_is_recovered_with_a_fresh_instance(self, run):
        run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / "pending.json"
            job.write_text("{}", encoding="utf-8")
            launch_app_for_job(job, Path("/Applications/ClipFlow.app"), wait_seconds=0)

        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "/usr/bin/open", "-g", "-j", "/Applications/ClipFlow.app",
                "--args", "--tubesave-background",
            ],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "/usr/bin/open", "-g", "-j", "-n", "/Applications/ClipFlow.app",
                "--args", "--tubesave-background",
            ],
        )


if __name__ == "__main__":
    unittest.main()
