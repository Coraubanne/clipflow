#!/usr/bin/env python3
"""Build Firefox from the shared ClipFlow WebExtension sources."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SOURCE = Path(__file__).resolve().parents[1] / "outputs" / "ClipFlow Chrome"
EXTENSION_ID = "clipflow@coraubanne"


def build_firefox_extension(target: Path) -> None:
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("key", None)
    manifest["background"] = {"scripts": ["background.js"]}
    manifest["browser_specific_settings"] = {
        "gecko": {
            "id": EXTENSION_ID,
            "strict_min_version": "140.0",
            "data_collection_permissions": {"required": ["none"]},
        }
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for name in ("background.js", "popup.js", "popup.html", "popup.css"):
            archive.write(SOURCE / name, name)
        for folder in ("icons", "_locales"):
            for path in sorted((SOURCE / folder).rglob("*")):
                if path.is_file() and not path.name.startswith("."):
                    archive.write(path, str(path.relative_to(SOURCE)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    build_firefox_extension(parser.parse_args().target)
