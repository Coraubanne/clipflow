import os
import unittest
from pathlib import Path


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]

    def test_single_user_facing_installer_is_built_and_published(self):
        builder = self.root / "scripts/build_installer_dmg.sh"
        publisher = self.root / "scripts/publish_github_release.sh"
        installer = self.root / "installer/ClipFlowInstaller"

        self.assertTrue(os.access(builder, os.X_OK))
        self.assertTrue(os.access(installer, os.X_OK))
        self.assertIn('output="outputs/ClipFlow-Installer.dmg"', builder.read_text())
        self.assertIn('installer="outputs/ClipFlow-Installer.dmg"', publisher.read_text())
        self.assertIn('release edit "${tag}"', publisher.read_text())

    def test_installer_contains_all_three_user_components(self):
        source = (self.root / "installer/ClipFlowInstaller").read_text()

        self.assertIn('source_app="${payload_dir}/ClipFlow.app"', source)
        self.assertIn('source_extension="${payload_dir}/ClipFlow Chrome"', source)
        self.assertIn('source_premiere="${payload_dir}/ClipFlow Premiere"', source)
        self.assertIn('/Applications/ClipFlow.app', source)
        self.assertNotIn('/Applications/Utilities/Terminal.app', source)

    def test_readme_routes_users_away_from_source_archive(self):
        for name in ("README.md", "README.fr.md"):
            content = (self.root / name).read_text()
            self.assertIn("releases/latest/download/ClipFlow-Installer.dmg", content)
            self.assertIn("Download ZIP", content)


if __name__ == "__main__":
    unittest.main()
