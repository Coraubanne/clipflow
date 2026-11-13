import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from updater import (
    UpdateError,
    chrome_extension_paths,
    github_token,
    latest_release,
    normalized_release_tag,
    parse_release_number,
    parse_semantic_version,
    release_is_newer,
    safe_extract,
    verify_checksum,
    _request,
)


class UpdaterTests(unittest.TestCase):
    def test_release_tags_are_strict(self):
        self.assertEqual(parse_release_number("v67"), 67)
        for value in ("67", "v0", "v67-beta", "../v67"):
            with self.assertRaises(UpdateError):
                parse_release_number(value)

    def test_semantic_versions_are_strict_and_ordered(self):
        self.assertEqual(parse_semantic_version("2.9.1"), (2, 9, 1))
        self.assertEqual(normalized_release_tag("v2.10.0"), "v2.10.0")
        self.assertFalse(release_is_newer("v2.9.1"))
        self.assertTrue(release_is_newer("v2.9.2"))
        self.assertTrue(release_is_newer("v3.0.0"))
        for value in ("2.9", "v2.09.1", "v2.9.1-beta", "../v2.9.2"):
            with self.assertRaises(UpdateError):
                normalized_release_tag(value)

    def test_latest_release_accepts_future_semantic_tag(self):
        payload = {
            "tag_name": "v2.9.2",
            "name": "ClipFlow 2.9.2",
            "draft": False,
            "prerelease": False,
            "assets": [
                {"id": 101, "name": "ClipFlow-complet-v2.9.2.zip"},
                {"id": 102, "name": "ClipFlow-complet-v2.9.2.zip.sha256"},
            ],
        }
        with patch("updater._github_json", return_value=payload):
            result = latest_release(Path("/nonexistent"))
        self.assertTrue(result["available"])
        self.assertEqual(result["releaseTag"], "v2.9.2")
        self.assertEqual(result["latestVersion"], "2.9.2")
        self.assertEqual(result["archiveAssetId"], 101)

    def test_github_token_is_read_without_exposing_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/gh/hosts.yml"
            config.parent.mkdir(parents=True)
            config.write_text("github.com:\n  oauth_token: secret-token\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(github_token(home), "secret-token")

    def test_public_release_requests_do_not_require_authentication(self):
        request = _request("https://api.github.com/repos/Coraubanne/clipflow/releases/latest", "", "application/json")
        self.assertIsNone(request.get_header("Authorization"))

    def test_checksum_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "update.zip"
            archive.write_bytes(b"trusted update")
            checksum = root / "update.zip.sha256"
            checksum.write_text(
                f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  update.zip\n",
                encoding="ascii",
            )
            verify_checksum(archive, checksum)
            archive.write_bytes(b"changed")
            with self.assertRaisesRegex(UpdateError, "corrompue"):
                verify_checksum(archive, checksum)

    def test_safe_extract_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("../escape", "bad")
            with self.assertRaisesRegex(UpdateError, "dangereux"):
                safe_extract(archive, root / "out")
            self.assertFalse((root / "escape").exists())

    def test_chrome_path_is_discovered_only_inside_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            extension = home / "ClipFlow Extension"
            extension.mkdir()
            preferences = home / "Library/Application Support/Google/Chrome/Default/Secure Preferences"
            preferences.parent.mkdir(parents=True)
            preferences.write_text(
                json.dumps({
                    "extensions": {"settings": {
                        "emfjpphkcgnjldilcnieaoppmfpfkhfg": {"path": str(extension)}
                    }}
                }),
                encoding="utf-8",
            )
            self.assertEqual(chrome_extension_paths(home), [extension.resolve()])


if __name__ == "__main__":
    unittest.main()
