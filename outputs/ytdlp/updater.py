#!/usr/bin/env python3
"""Signed-release updater shared by ClipFlow's native messaging host."""

from __future__ import annotations

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
CURRENT_RELEASE = 67
EXTENSION_ID = "emfjpphkcgnjldilcnieaoppmfpfkhfg"
PREMIERE_PLUGIN_ID = "fr.clipflow.premiere.bridge"
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
        "User-Agent": f"ClipFlow/{CURRENT_RELEASE}",
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


def _release_assets(release: dict[str, object], number: int) -> tuple[dict[str, object], dict[str, object]]:
    expected_zip = f"ClipFlow-complet-v{number}.zip"
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
    number = parse_release_number(payload.get("tag_name"))
    result: dict[str, object] = {
        "ok": True,
        "currentRelease": CURRENT_RELEASE,
        "latestRelease": number,
        "available": number > CURRENT_RELEASE,
        "version": str(payload.get("name") or payload.get("tag_name") or f"v{number}")[:100],
    }
    if number > CURRENT_RELEASE:
        archive, checksum = _release_assets(payload, number)
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


def validate_bundle(root: Path, expected_release: int) -> dict[str, Path]:
    metadata = _read_json(root / "PROJECT_VERSION.json")
    if metadata.get("release") != expected_release:
        raise UpdateError("Le numéro de l’archive ne correspond pas à la release GitHub.")

    app = root / "ClipFlow.app"
    extension = root / "ClipFlow Chrome"
    premiere = root / "ClipFlow Premiere"
    try:
        with (app / "Contents/Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException):
        raise UpdateError("L’application ClipFlow de la mise à jour est invalide.") from None
    if info.get("CFBundleIdentifier") != "fr.clipflow.app" or info.get("LSUIElement") is not True:
        raise UpdateError("L’identité de l’application téléchargée est invalide.")
    extension_manifest = _read_json(extension / "manifest.json")
    premiere_manifest = _read_json(premiere / "manifest.json")
    if extension_manifest.get("name") != "ClipFlow" or extension_manifest.get("key") is None:
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
    number: int,
    archive_asset_id: int,
    checksum_asset_id: int,
    current_app: Path,
    home: Path | None = None,
) -> dict[str, object]:
    if number <= CURRENT_RELEASE:
        return {"ok": True, "installed": False, "release": CURRENT_RELEASE}
    user_home = (home or Path.home()).resolve()
    token = github_token(user_home)
    published = latest_release(user_home)
    if (
        published.get("latestRelease") != number
        or published.get("archiveAssetId") != archive_asset_id
        or published.get("checksumAssetId") != checksum_asset_id
    ):
        raise UpdateError("La release GitHub a changé. Relancez la recherche de mise à jour.")
    with tempfile.TemporaryDirectory(prefix="clipflow-update-") as temporary:
        workspace = Path(temporary)
        archive = workspace / f"ClipFlow-complet-v{number}.zip"
        checksum = workspace / f"{archive.name}.sha256"
        _download_asset(archive_asset_id, archive, token, MAX_ARCHIVE_BYTES)
        _download_asset(checksum_asset_id, checksum, token, 4096)
        verify_checksum(archive, checksum)
        extracted = workspace / "extracted"
        extracted.mkdir()
        safe_extract(archive, extracted)
        root = extracted / "ClipFlow complet"
        components = validate_bundle(root, number)

        extension_targets = chrome_extension_paths(user_home)
        if not extension_targets:
            raise UpdateError("L’extension Chrome ClipFlow installée est introuvable.")
        app_target = current_app.resolve()
        if (
            not app_target.is_dir()
            or app_target.name != "ClipFlow.app"
            or not os.access(app_target, os.W_OK)
        ):
            raise UpdateError("L’application ClipFlow installée ne peut pas être mise à jour.")
        premiere_version = str(_read_json(components["premiere"] / "manifest.json").get("version", ""))
        premiere_target = (
            user_home / "Library/Application Support/Adobe/UXP/Plugins/External"
            / f"{PREMIERE_PLUGIN_ID}_{premiere_version}"
        )

        replacements: list[tuple[Path, Path | None]] = []
        try:
            for target in extension_targets:
                replacements.append((target, _atomic_replace(components["extension"], target)))
            replacements.append((premiere_target, _atomic_replace(components["premiere"], premiere_target)))
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

    return {
        "ok": True,
        "installed": True,
        "release": number,
        "message": "ClipFlow a été mis à jour. Redémarrez Premiere Pro s’il était ouvert.",
    }
