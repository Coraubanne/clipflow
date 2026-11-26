import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


@unittest.skipUnless(Path("/bin/zsh").is_file() and Path("/usr/bin/ditto").is_file(), "requires macOS")
class CreatorBridgeUpdateTests(unittest.TestCase):
    def test_checks_and_installs_once_across_both_companions(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release_version = "1.2.0"
            archive = root / f"CreatorBridge-v{release_version}.zip"
            manifest = {
                "id": "fr.clipflow.premiere.bridge", "version": release_version,
                "host": {"app": "premierepro"}, "main": "index.html",
            }
            plugin = root / "bundled-plugin"
            plugin.mkdir()
            (plugin / "manifest.json").write_text(json.dumps({**manifest, "version": "1.1.0"}))
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("manifest.json", json.dumps(manifest))
                for name in ("index.html", "index.js", "styles.css", "LICENSE"):
                    (plugin / name).write_text("test fixture")
                    package.write(plugin / name, name)
            metadata = root / "release.json"
            release = {
                "draft": False,
                "prerelease": False,
                "tag_name": f"v{release_version}",
                "assets": [{"name": archive.name, "digest": "sha256:" + "0" * 64}],
            }
            metadata.write_text(json.dumps(release))
            curl = root / "curl"
            curl.write_text(
                "#!/bin/zsh\n"
                "while [[ ${1:-} != -o ]]; do shift; done\n"
                f"if [[ ${3:-} == -w ]]; then /bin/cp '{metadata}' \"$2\"; print -n 200;\n"
                f"else /bin/cp '{archive}' \"$2\"; fi\n"
            )
            curl.chmod(0o700)
            source = (project / "creator-bridge-update.sh").read_text()
            helper = root / "updater.sh"
            helper.write_text(source.replace("/usr/bin/curl", str(curl)))
            other_helper = root / "other-updater.sh"
            shutil.copyfile(helper, other_helper)
            home = root / "home"
            install_root = home / "Library/Application Support/Adobe/UXP/Plugins/External"
            old_install = install_root / "fr.clipflow.premiere.bridge_1.1.0"
            shutil.copytree(plugin, old_install, ignore=shutil.ignore_patterns(".git*"))

            def invoke(script, mode, version=""):
                return subprocess.run(
                    ["/bin/zsh", str(script), mode, version, str(home)],
                    text=True, capture_output=True, timeout=15,
                )

            self.assertTrue(json.loads(invoke(helper, "check").stdout)["available"])
            self.assertNotEqual(invoke(helper, "install", release_version).returncode, 0)
            self.assertTrue(old_install.is_dir())

            release["assets"][0]["digest"] = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
            metadata.write_text(json.dumps(release))
            commands = [
                ["/bin/zsh", str(script), "install", release_version, str(home)]
                for script in (helper, other_helper)
            ]
            with subprocess.Popen(commands[0], text=True, stdout=subprocess.PIPE) as first:
                second = subprocess.run(commands[1], text=True, capture_output=True, check=True, timeout=15)
                output, _ = first.communicate(timeout=15)
                self.assertEqual(first.returncode, 0)
            self.assertEqual(sum(result["installed"] for result in map(json.loads, (output, second.stdout))), 1)
            self.assertFalse(old_install.exists())
            current = json.loads(invoke(other_helper, "check").stdout)
            self.assertEqual(current["currentVersion"], release_version)
            self.assertFalse(current["available"])
            bundled = invoke(other_helper, "install-local", str(plugin))
            self.assertEqual(bundled.returncode, 0, bundled.stderr)
            self.assertFalse(json.loads(bundled.stdout)["installed"])
            self.assertFalse(old_install.exists())
