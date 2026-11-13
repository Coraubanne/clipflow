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
    parse_release_number,
    safe_extract,
    verify_checksum,
)


class UpdaterTests(unittest.TestCase):
    def test_release_tags_are_strict(self):
        self.assertEqual(parse_release_number("v66"), 66)
        for value in ("66", "v0", "v66-beta", "../v66"):
            with self.assertRaises(UpdateError):
                parse_release_number(value)

    def test_github_token_is_read_without_exposing_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/gh/hosts.yml"
            config.parent.mkdir(parents=True)
            config.write_text("github.com:\n  oauth_token: secret-token\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(github_token(home), "secret-token")

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
