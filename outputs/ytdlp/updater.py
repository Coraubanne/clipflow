#!/usr/bin/env python3
"""Signed-release updater shared by ClipFlow's native messaging host."""

from __future__ import annotations

import codecs
import fcntl
import hashlib
import hmac
import json
import os
import plistlib
import posixpath
import re
import shutil
import ssl
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import certifi


GITHUB_OWNER = "Coraubanne"
GITHUB_REPOSITORY = "clipflow"
CURRENT_RELEASE = 75
CURRENT_VERSION = "2.18.0"
APP_BUNDLE_ID = "fr.clipflow.app"
EXTENSION_ID = "emfjpphkcgnjldilcnieaoppmfpfkhfg"
PREMIERE_PLUGIN_ID = "fr.clipflow.premiere.bridge"
PREMIERE_INSTALL_DIRECTORY = "Library/Application Support/Adobe/UXP/Plugins/External"
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_FILES = 30_000


class UpdateError(RuntimeError):
    """A user-facing update failure."""


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward a GitHub token to an asset CDN."""

    def redirect_request(self, request, fp, code, message, headers, new_url):
        redirected = super().redirect_request(request, fp, code, message, headers, new_url)
        if redirected is None:
            return None
        old_host = urllib.parse.urlparse(request.full_url).hostname
        new_host = urllib.parse.urlparse(new_url).hostname
        if old_host != new_host:
            redirected.remove_header("Authorization")
        return redirected


def parse_release_number(tag: object) -> int:
    match = re.fullmatch(r"v([1-9][0-9]*)", str(tag or ""))
    if not match:
        raise UpdateError("La version publiée sur GitHub est invalide.")
    return int(match.group(1))


def parse_semantic_version(value: object) -> tuple[int, int, int]:
    match = re.fullmatch(r"(?:v)?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", str(value or ""))
    if not match:
        raise UpdateError("La version publiée sur GitHub est invalide.")
    return tuple(map(int, match.groups()))


def normalized_release_tag(value: object) -> str:
    raw = str(value or "")
    if re.fullmatch(r"v[1-9][0-9]*", raw):
        return raw
    if re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", raw):
        return raw
    raise UpdateError("La version publiée sur GitHub est invalide.")


def release_is_newer(tag: str) -> bool:
    if re.fullmatch(r"v[1-9][0-9]*", tag):
        return parse_release_number(tag) > CURRENT_RELEASE
    return parse_semantic_version(tag) > parse_semantic_version(CURRENT_VERSION)


def _read_gh_token(home: Path) -> str:
    configured = os.environ.get("CLIPFLOW_GITHUB_TOKEN", "").strip()
    if configured:
        return configured
    hosts = home / ".config/gh/hosts.yml"
    try:
        content = hosts.read_text(encoding="utf-8")
    except OSError:
        return ""
    # GitHub CLI writes this value either at the host level or below the user.
    tokens = re.findall(r"^\s*oauth_token:\s*([^#\s]+)", content, flags=re.MULTILINE)
    return tokens[-1].strip("'\"") if tokens else ""


def github_token(home: Path | None = None) -> str:
    return _read_gh_token((home or Path.home()).resolve())


def _opener() -> urllib.request.OpenerDirector:
    context = ssl.create_default_context(cafile=certifi.where())
    return urllib.request.build_opener(
        SafeRedirectHandler(),
        urllib.request.HTTPSHandler(context=context),
    )


def _request(url: str, token: str, accept: str) -> urllib.request.Request:
    headers = {
        "Accept": accept,
        "User-Agent": f"ClipFlow/{CURRENT_VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _github_json(url: str, token: str) -> object:
    try:
        with _opener().open(
            _request(url, token, "application/vnd.github+json"), timeout=20
        ) as response:
            if int(response.headers.get("Content-Length", "0") or 0) > 2 * 1024 * 1024:
                raise UpdateError("La réponse de GitHub est anormalement volumineuse.")
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 404}:
            raise UpdateError(
                "ClipFlow n’arrive pas à accéder à la release GitHub publique. "
                "Réessayez plus tard ou vérifiez l’état de GitHub."
            ) from None
        raise UpdateError(f"GitHub a refusé la vérification (erreur {error.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise UpdateError("Impossible de joindre GitHub. Vérifiez la connexion Internet.") from None


def _release_assets(release: dict[str, object], tag: str) -> tuple[dict[str, object], dict[str, object]]:
    expected_zip = f"ClipFlow-complet-{tag}.zip"
    expected_sum = f"{expected_zip}.sha256"
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("Cette release GitHub ne contient aucun fichier installable.")
    by_name = {
        asset.get("name"): asset
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    archive = by_name.get(expected_zip)
    checksum = by_name.get(expected_sum)
    if not isinstance(archive, dict) or not isinstance(checksum, dict):
        raise UpdateError("La release GitHub est incomplète; installation annulée.")
    return archive, checksum


def latest_release(home: Path | None = None) -> dict[str, object]:
    token = github_token(home)
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
    payload = _github_json(url, token)
    if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
        raise UpdateError("Aucune release stable de ClipFlow n’est disponible.")
    tag = normalized_release_tag(payload.get("tag_name"))
    legacy_number = parse_release_number(tag) if re.fullmatch(r"v[1-9][0-9]*", tag) else None
    published_version = (
        str(payload.get("name") or "").removeprefix("ClipFlow ").strip()
        if legacy_number is not None
        else tag.removeprefix("v")
    )
    if legacy_number is not None:
        try:
            parse_semantic_version(published_version)
        except UpdateError:
            published_version = str(legacy_number)
    available = release_is_newer(tag)
    result: dict[str, object] = {
        "ok": True,
        "currentRelease": CURRENT_RELEASE,
        "currentVersion": CURRENT_VERSION,
        "latestRelease": legacy_number if legacy_number is not None else published_version,
        "latestVersion": published_version,
        "releaseTag": tag,
        "available": available,
        "version": str(payload.get("name") or tag)[:100],
    }
    if available:
        archive, checksum = _release_assets(payload, tag)
        result["archiveAssetId"] = int(archive.get("id", 0))
        result["checksumAssetId"] = int(checksum.get("id", 0))
    return result


def _download_asset(asset_id: int, target: Path, token: str, max_bytes: int) -> None:
    if asset_id <= 0:
        raise UpdateError("Le fichier de mise à jour GitHub est invalide.")
    url = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}"
        f"/releases/assets/{asset_id}"
    )
    try:
        with _opener().open(
            _request(url, token, "application/octet-stream"), timeout=60
        ) as response, target.open("wb") as output:
            declared = int(response.headers.get("Content-Length", "0") or 0)
            if declared > max_bytes:
                raise UpdateError("Le fichier de mise à jour est trop volumineux.")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UpdateError("Le fichier de mise à jour est trop volumineux.")
                output.write(chunk)
    except UpdateError:
        raise
    except urllib.error.HTTPError as error:
        raise UpdateError(f"Le téléchargement GitHub a échoué (erreur {error.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise UpdateError("Le téléchargement de la mise à jour a échoué.") from None


def verify_checksum(archive: Path, checksum_file: Path) -> None:
    try:
        checksum_text = checksum_file.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise UpdateError("L’empreinte de la mise à jour est illisible.") from None
    match = re.fullmatch(r"([0-9a-fA-F]{64})(?:\s+\*?[^\s]+)?", checksum_text)
    if not match:
        raise UpdateError("L’empreinte de la mise à jour est invalide.")
    digest = hashlib.sha256()
    try:
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise UpdateError("Impossible de vérifier la mise à jour téléchargée.") from None
    if not hmac.compare_digest(digest.hexdigest(), match.group(1).lower()):
        raise UpdateError("La mise à jour est corrompue; installation annulée.")


def safe_extract(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            if len(members) > MAX_ARCHIVE_FILES:
                raise UpdateError("L’archive de mise à jour contient trop de fichiers.")
            total = 0
            for member in members:
                name = PurePosixPath(member.filename)
                if name.is_absolute() or ".." in name.parts or not name.parts:
                    raise UpdateError("L’archive de mise à jour contient un chemin dangereux.")
                mode = member.external_attr >> 16
                file_type = mode & 0o170000
                if file_type not in {0, 0o040000, 0o100000, 0o120000}:
                    raise UpdateError("L’archive de mise à jour contient un fichier interdit.")
                if file_type == 0o120000:
                    try:
                        link_target = package.read(member).decode("utf-8")
                    except (UnicodeError, OSError):
                        raise UpdateError("L’archive contient un lien symbolique invalide.") from None
                    normalized = posixpath.normpath(str(name.parent / link_target))
                    if link_target.startswith("/") or normalized == ".." or normalized.startswith("../"):
                        raise UpdateError("L’archive contient un lien symbolique dangereux.")
                total += member.file_size
                if total > MAX_EXTRACTED_BYTES:
                    raise UpdateError("L’archive de mise à jour est trop volumineuse.")
            for member in members:
                name = PurePosixPath(member.filename)
                target = destination.joinpath(*name.parts)
                mode = member.external_attr >> 16
                file_type = mode & 0o170000
                if member.is_dir() or file_type == 0o040000:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if file_type == 0o120000:
                    target.symlink_to(package.read(member).decode("utf-8"))
                    continue
                with package.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                permissions = mode & 0o777
                if permissions:
                    target.chmod(permissions)
    except UpdateError:
        raise
    except (zipfile.BadZipFile, OSError):
        raise UpdateError("L’archive de mise à jour est illisible.") from None


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        raise UpdateError(f"Le fichier {path.name} de la mise à jour est invalide.") from None
    if not isinstance(value, dict):
        raise UpdateError(f"Le fichier {path.name} de la mise à jour est invalide.")
    return value


def validate_bundle(root: Path, expected_release: int | str) -> dict[str, Path]:
    metadata = _read_json(root / "PROJECT_VERSION.json")
    expected_matches = (
        metadata.get("release") == expected_release
        if isinstance(expected_release, int)
        else metadata.get("version") == normalized_release_tag(expected_release).removeprefix("v")
    )
    if not expected_matches:
        raise UpdateError("Le numéro de l’archive ne correspond pas à la release GitHub.")

    app = root / "ClipFlow.app"
    extension = root / "ClipFlow Chrome"
    premiere = root / "Creator Bridge"
    try:
        with (app / "Contents/Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException):
        raise UpdateError("L’application ClipFlow de la mise à jour est invalide.") from None
    if info.get("CFBundleIdentifier") != "fr.clipflow.app" or info.get("LSUIElement") is not True:
        raise UpdateError("L’identité de l’application téléchargée est invalide.")
    extension_manifest = _read_json(extension / "manifest.json")
    premiere_manifest = _read_json(premiere / "manifest.json")
    extension_name = extension_manifest.get("name")
    if extension_name == "__MSG_extensionName__":
        locale = extension_manifest.get("default_locale")
        if locale not in {"en", "fr"}:
            raise UpdateError("L’extension Chrome téléchargée est invalide.")
        localized = _read_json(extension / "_locales" / str(locale) / "messages.json")
        extension_name = localized.get("extensionName", {}).get("message")
    if extension_name != "ClipFlow" or extension_manifest.get("key") is None:
        raise UpdateError("L’extension Chrome téléchargée est invalide.")
    if premiere_manifest.get("id") != PREMIERE_PLUGIN_ID:
        raise UpdateError("Le module Premiere Pro téléchargé est invalide.")
    verification = subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    if verification.returncode != 0:
        raise UpdateError("La signature de l’application téléchargée est invalide.")
    return {"app": app, "extension": extension, "premiere": premiere}


def chrome_extension_paths(home: Path | None = None) -> list[Path]:
    user_home = (home or Path.home()).resolve()
    chrome = user_home / "Library/Application Support/Google/Chrome"
    found: list[Path] = []
    for preferences in chrome.glob("*/Secure Preferences"):
        try:
            payload = json.loads(preferences.read_text(encoding="utf-8"))
            raw = payload["extensions"]["settings"][EXTENSION_ID]["path"]
            path = Path(raw).expanduser().resolve()
        except (OSError, ValueError, TypeError, KeyError):
            continue
        try:
            path.relative_to(user_home)
        except ValueError:
            continue
        if path.is_dir() and path not in found:
            found.append(path)
    return found


def premiere_plugin_installations(home: Path | None = None) -> list[tuple[tuple[int, int, int], Path]]:
    """Return only validated Creator Bridge/legacy ClipFlow bridge installations."""
    root = (home or Path.home()).resolve() / PREMIERE_INSTALL_DIRECTORY
    found: list[tuple[tuple[int, int, int], Path]] = []
    for path in root.glob(f"{PREMIERE_PLUGIN_ID}_*"):
        if path.is_symlink() or any(
            not (path / name).is_file() or (path / name).is_symlink()
            for name in ("manifest.json", "index.html", "index.js", "styles.css")
        ):
            continue
        try:
            manifest = _read_json(path / "manifest.json")
            if manifest.get("id") != PREMIERE_PLUGIN_ID:
                continue
            found.append((parse_semantic_version(manifest.get("version")), path))
        except (OSError, UpdateError):
            continue
    return found


def cleanup_premiere_duplicates(user_home: Path) -> int:
    root = user_home / PREMIERE_INSTALL_DIRECTORY
    if not root.is_dir() or root.is_symlink():
        return 0
    removed = 0
    try:
        descriptor = os.open(root / ".creator-bridge.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.lockf(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            premiere = premiere_plugin_installations(user_home)
            if premiere:
                _, keep = max(premiere, key=lambda item: (item[0], item[1].name))
                for _, path in premiere:
                    if path == keep:
                        continue
                    try:
                        shutil.rmtree(path)
                        removed += 1
                    except OSError:
                        pass
        finally:
            os.close(descriptor)
    except OSError:
        pass
    return removed


def clipflow_application_installations(
    home: Path | None = None,
    roots: tuple[Path, ...] | None = None,
) -> list[tuple[tuple[int, int, int], Path]]:
    """Find real ClipFlow app bundles only in the two macOS application roots."""
    user_home = (home or Path.home()).resolve()
    application_roots = roots or (Path("/Applications"), user_home / "Applications")
    found: list[tuple[tuple[int, int, int], Path]] = []
    for root in application_roots:
        try:
            candidates = list(root.glob("*.app"))
        except OSError:
            continue
        for path in candidates:
            if path.is_symlink() or not path.is_dir():
                continue
            try:
                with (path / "Contents/Info.plist").open("rb") as info_file:
                    info = plistlib.load(info_file)
                if info.get("CFBundleIdentifier") != APP_BUNDLE_ID:
                    continue
                version = parse_semantic_version(info.get("CFBundleShortVersionString"))
            except (OSError, LookupError, ValueError, TypeError, UpdateError, plistlib.InvalidFileException):
                continue
            found.append((version, path))
    return found


def _extension_identity(path: Path) -> tuple[int, int, int] | None:
    try:
        manifest = _read_json(path / "manifest.json")
        name = manifest.get("name")
        if name == "__MSG_extensionName__":
            locale = str(manifest.get("default_locale") or "")
            name = _read_json(path / "_locales" / locale / "messages.json").get(
                "extensionName", {}
            ).get("message")
        if name != "ClipFlow" or not manifest.get("key"):
            return None
        return parse_semantic_version(manifest.get("version"))
    except (OSError, TypeError, UpdateError):
        return None


def managed_extension_installations(home: Path | None = None) -> list[tuple[tuple[int, int, int], Path]]:
    """Return known installed copies without ever scanning or touching project sources."""
    user_home = (home or Path.home()).resolve()
    candidates = [
        user_home / "Documents/ClipFlow/ClipFlow Chrome",
        user_home / "Documents/ClipFlow Chrome",
        user_home / "Documents/TubeSave Extension",
        user_home / "Documents/Codex/TubeSave Extension",
    ]
    found: list[tuple[tuple[int, int, int], Path]] = []
    for path in candidates:
        version = _extension_identity(path)
        if version is not None:
            found.append((version, path))
    return found


def cleanup_installed_duplicates(
    active_app: Path,
    home: Path | None = None,
    app_roots: tuple[Path, ...] | None = None,
) -> dict[str, int]:
    """Remove only verified, obsolete ClipFlow components while keeping active copies safe."""
    user_home = (home or Path.home()).resolve()
    active_app = active_app.resolve()
    removed = {"applications": 0, "extensions": 0, "premiere": 0}

    applications = clipflow_application_installations(user_home, app_roots)
    active_entry = next((item for item in applications if item[1].resolve() == active_app), None)
    if active_entry is not None:
        active_version = active_entry[0]
        # Never remove another app if it is newer than the one currently running.
        if not any(version > active_version for version, _path in applications):
            for version, path in applications:
                if path.resolve() == active_app or version > active_version:
                    continue
                try:
                    shutil.rmtree(path)
                    removed["applications"] += 1
                except OSError:
                    pass

    removed["premiere"] = cleanup_premiere_duplicates(user_home)

    active_extensions = {path.resolve() for path in chrome_extension_paths(user_home)}
    managed_extensions = managed_extension_installations(user_home)
    active_versions = [
        version for version, path in managed_extensions if path.resolve() in active_extensions
    ]
    if active_versions:
        cleanup_ceiling = max(active_versions)
        for version, path in managed_extensions:
            if path.resolve() in active_extensions or version > cleanup_ceiling:
                continue
            try:
                shutil.rmtree(path)
                removed["extensions"] += 1
            except OSError:
                pass
    elif managed_extensions:
        newest_extension = max(version for version, _path in managed_extensions)
        keep_extension = next(
            path.resolve() for version, path in managed_extensions if version == newest_extension
        )
        for version, path in managed_extensions:
            if path.resolve() == keep_extension or version > newest_extension:
                continue
            try:
                shutil.rmtree(path)
                removed["extensions"] += 1
            except OSError:
                pass
    return removed


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, copy_function=shutil.copy2, symlinks=True)


def _atomic_replace(source: Path, target: Path) -> Path | None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / f".{target.name}.clipflow-new"
    backup = target.parent / f".{target.name}.clipflow-previous"
    if staged.exists():
        shutil.rmtree(staged)
    if backup.exists():
        shutil.rmtree(backup)
    _copy_tree(source, staged)
    previous = None
    if target.exists():
        os.replace(target, backup)
        previous = backup
    try:
        os.replace(staged, target)
    except Exception:
        if previous and previous.exists() and not target.exists():
            os.replace(previous, target)
        raise
    return previous


def install_release(
    release: int | str,
    archive_asset_id: int,
    checksum_asset_id: int,
    current_app: Path,
    home: Path | None = None,
    *,
    allow_without_chrome: bool = False,
) -> dict[str, object]:
    tag = normalized_release_tag(f"v{release}" if isinstance(release, int) else release)
    if not release_is_newer(tag):
        return {"ok": True, "installed": False, "release": CURRENT_RELEASE, "version": CURRENT_VERSION}
    user_home = (home or Path.home()).resolve()
    token = github_token(user_home)
    published = latest_release(user_home)
    if (
        published.get("releaseTag") != tag
        or published.get("archiveAssetId") != archive_asset_id
        or published.get("checksumAssetId") != checksum_asset_id
    ):
        raise UpdateError("La release GitHub a changé. Relancez la recherche de mise à jour.")
    with tempfile.TemporaryDirectory(prefix="clipflow-update-") as temporary:
        workspace = Path(temporary)
        archive = workspace / f"ClipFlow-complet-{tag}.zip"
        checksum = workspace / f"{archive.name}.sha256"
        _download_asset(archive_asset_id, archive, token, MAX_ARCHIVE_BYTES)
        _download_asset(checksum_asset_id, checksum, token, 4096)
        verify_checksum(archive, checksum)
        extracted = workspace / "extracted"
        extracted.mkdir()
        safe_extract(archive, extracted)
        root = extracted / "ClipFlow complet"
        expected_identity: int | str = parse_release_number(tag) if re.fullmatch(r"v[1-9][0-9]*", tag) else tag
        components = validate_bundle(root, expected_identity)

        extension_targets = chrome_extension_paths(user_home)
        if not extension_targets and not allow_without_chrome:
            raise UpdateError("L’extension Chrome ClipFlow installée est introuvable.")
        app_target = current_app.resolve()
        if (
            not app_target.is_dir()
            or app_target.name != "ClipFlow.app"
            or not os.access(app_target, os.W_OK)
        ):
            raise UpdateError("L’application ClipFlow installée ne peut pas être mise à jour.")
        replacements: list[tuple[Path, Path | None]] = []
        # Binary Info.plist files may contain UTF-16 strings. Cache their codec
        # while PyInstaller can still load resources from the running bundle.
        codecs.lookup("utf-16be")
        try:
            for target in extension_targets:
                replacements.append((target, _atomic_replace(components["extension"], target)))
            # Contents can be replaced atomically even when /Applications itself
            # is not writable. The already-running native host keeps its open image.
            app_contents = app_target / "Contents"
            replacements.append((
                app_contents,
                _atomic_replace(components["app"] / "Contents", app_contents),
            ))
            # A backup inside the .app root is seen as an unsealed bundle item.
            # Keep it in the private update workspace while codesign checks the
            # newly installed Contents, then delete it only after full success.
            app_backup = replacements[-1][1]
            if app_backup is not None:
                external_backup = workspace / "previous-app-contents"
                shutil.move(str(app_backup), external_backup)
                replacements[-1] = (app_contents, external_backup)
            verification = subprocess.run(
                ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app_target)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
            if verification.returncode != 0:
                raise UpdateError("La nouvelle application n’a pas passé la vérification finale.")
            helper = app_target / "Contents/Resources/ytdlp/creator-bridge-update.sh"
            subprocess.run(
                ["/bin/zsh", str(helper), "install-local", str(components["premiere"]), str(user_home)],
                capture_output=True, timeout=30, check=True,
            )
        except Exception as error:
            for target, backup in reversed(replacements):
                try:
                    if target.exists():
                        shutil.rmtree(target)
                    if backup and backup.exists():
                        os.replace(backup, target)
                except OSError:
                    pass
            if isinstance(error, UpdateError):
                raise
            raise UpdateError(f"L’installation automatique a échoué : {error}") from None
        for _target, backup in replacements:
            if backup and backup.exists():
                shutil.rmtree(backup, ignore_errors=True)
        cleanup_installed_duplicates(app_target, user_home)

    return {
        "ok": True,
        "installed": True,
        "release": published.get("latestRelease"),
        "version": published.get("latestVersion"),
        "message": "ClipFlow a été mis à jour. Redémarrez Premiere Pro s’il était ouvert.",
    }
