import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]

    def test_single_user_facing_installer_is_built_and_published(self):
        builder = self.root / "scripts/build_installer_dmg.sh"
        distribution_builder = self.root / "scripts/build_distribution.sh"
        publisher = self.root / "scripts/publish_github_release.sh"
        installer = self.root / "installer/ClipFlowInstaller"

        self.assertTrue(os.access(builder, os.X_OK))
        self.assertTrue(os.access(installer, os.X_OK))
        self.assertIn('output="outputs/ClipFlow-Installer.dmg"', builder.read_text())
        self.assertIn('installer="outputs/ClipFlow-Installer.dmg"', publisher.read_text())
        self.assertIn('release edit "${tag}"', publisher.read_text())
        self.assertIn('outputs/ClipFlow-complet-v*.zip', distribution_builder.read_text())
        self.assertIn('"${archive}.sha256"', distribution_builder.read_text())

    def test_installer_contains_all_three_user_components(self):
        source = (self.root / "installer/ClipFlowInstaller").read_text()
        builder = (self.root / "scripts/build_installer_dmg.sh").read_text()

        self.assertIn('source_app="${payload_dir}/ClipFlow.app"', source)
        self.assertIn('source_extension="${payload_dir}/ClipFlow Chrome"', source)
        self.assertIn('source_premiere="${payload_dir}/Creator Bridge"', source)
        self.assertIn('creator-bridge-update.sh" install-local', source)
        self.assertIn('/Applications/ClipFlow.app', source)
        self.assertNotIn('/Applications/Utilities/Terminal.app', source)
        self.assertIn('Creator Bridge/.gitignore', builder)

    def test_readme_routes_users_away_from_source_archive(self):
        for name in ("README.md", "README.fr.md"):
            content = (self.root / name).read_text()
            self.assertIn("releases/latest/download/ClipFlow-Installer.dmg", content)
            self.assertIn("Download ZIP", content)

    def test_firefox_uses_the_shared_sources_and_a_gecko_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ClipFlow.xpi"
            subprocess.run(
                [sys.executable, self.root / "scripts/build_firefox_extension.py", target],
                check=True,
            )
            with ZipFile(target) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertNotIn("key", manifest)
                self.assertEqual(manifest["background"], {"scripts": ["background.js"]})
                self.assertEqual(manifest["browser_specific_settings"]["gecko"]["id"], "clipflow@coraubanne")
                self.assertEqual(archive.read("popup.js"), (self.root / "outputs/ClipFlow Chrome/popup.js").read_bytes())


if __name__ == "__main__":
    unittest.main()
