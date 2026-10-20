#!/usr/bin/env python3
"""Secure Chrome Native Messaging bridge for ClipFlow."""

from __future__ import annotations

import json
import ipaddress
import os
import struct
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse


MAX_MESSAGE_SIZE = 1024 * 1024
QUALITY_KEYS = {"best", "audio", "1080", "720", "480"}
DESTINATION_KEYS = {"downloads", "movies", "desktop", "custom", "premiere"}
JOB_ID_LENGTH_LIMIT = 96
PREMIERE_STATE_MAX_AGE_SECONDS = 15
PREMIERE_MEDIA_DIRECTORY = "Médias ClipFlow"
PREMIERE_PLUGIN_ID = "fr.clipflow.premiere.bridge"


def is_public_web_url(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 8192:
        return False
    try:
        parsed = urlparse(value.strip())
        hostname = (parsed.hostname or "").rstrip(".").casefold()
    except ValueError:
        return False
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or hostname == "localhost"
        or hostname.endswith(".localhost")
    ):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def is_supported_video_request_url(value: object) -> bool:
    """Reject YouTube navigation pages while preserving generic site pages."""
    if not is_public_web_url(value):
        return False
    parsed = urlparse(str(value).strip())
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    if hostname == "youtu.be":
        return bool(parsed.path.strip("/"))
    if hostname == "youtube.com" or hostname.endswith(".youtube.com"):
        path = parsed.path.rstrip("/") or "/"
        if path == "/watch":
            return bool(parse_qs(parsed.query).get("v", [""])[0])
        return any(path.startswith(prefix) for prefix in ("/shorts/", "/live/", "/embed/", "/clip/"))
    return True


def premiere_bridge_directory(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/ClipFlow/Premiere"


def premiere_bridge_directories(home: Path | None = None) -> list[Path]:
    """Return Adobe's private plugin folders, then the legacy bridge folder."""
    user_home = home or Path.home()
    storage = user_home / "Library/Application Support/Adobe/UXP/PluginsStorage/PPRO"
    try:
        adobe = sorted(
            storage.glob(f"*/External/{PREMIERE_PLUGIN_ID}/PluginData"),
            reverse=True,
        )
    except OSError:
        adobe = []
    return adobe + [premiere_bridge_directory(user_home)]


def active_premiere_connection(
    home: Path | None = None,
    now: float | None = None,
) -> tuple[Path, Path]:
    """Return the project and bridge folder exposed by the Premiere plugin."""
    states: list[tuple[float, dict[str, object], Path]] = []
    for bridge in premiere_bridge_directories(home):
        try:
            state = json.loads((bridge / "active-project.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError, TypeError):
            continue
        if isinstance(state, dict):
            updated_at = state.get("updatedAt")
            order = float(updated_at) if isinstance(updated_at, (int, float)) else 0.0
            states.append((order, state, bridge))
    if not states:
        raise ValueError(
            "Ouvrez un projet enregistré dans Premiere Pro et activez le module ClipFlow."
        ) from None
    _, state, bridge = max(states, key=lambda item: item[0])
    updated_at = state.get("updatedAt")
    if not isinstance(updated_at, (int, float)):
        raise ValueError("Premiere Pro ne répond pas. Rouvrez le panneau ClipFlow dans Premiere.")
    current = time.time() if now is None else now
    if current - (float(updated_at) / 1000.0) > PREMIERE_STATE_MAX_AGE_SECONDS:
        raise ValueError("Premiere Pro ne répond pas. Rouvrez le panneau ClipFlow dans Premiere.")
    raw_path = state.get("projectPath")
    if not isinstance(raw_path, str) or not raw_path or len(raw_path) > 4096:
        raise ValueError("Enregistrez d’abord le projet Premiere Pro.")
    project = Path(raw_path).expanduser()
    if not project.is_absolute() or project.suffix.casefold() != ".prproj" or not project.is_file():
        raise ValueError("Le projet Premiere Pro actif n’est pas encore enregistré.")
    return project.resolve(), bridge.resolve()


def active_premiere_project(
    home: Path | None = None,
    now: float | None = None,
) -> Path:
    return active_premiere_connection(home, now)[0]


def premiere_destination(
    home: Path | None = None,
    now: float | None = None,
) -> tuple[Path, Path, Path]:
    project, bridge = active_premiere_connection(home, now)
    destination = project.parent / PREMIERE_MEDIA_DIRECTORY
    try:
        destination.mkdir(parents=False, exist_ok=True)
    except OSError as error:
        raise ValueError(f"Impossible de créer le dossier média du projet : {error}") from None
    return destination.resolve(), project, bridge


def resolve_destination(message: dict[str, object], home: Path | None = None) -> Path:
    user_home = (home or Path.home()).resolve()
    destination = message.get("destination", "downloads")
    if destination not in DESTINATION_KEYS:
        raise ValueError("Dossier de destination invalide.")
    if destination == "downloads":
        return user_home / "Downloads"
    if destination == "movies":
        return user_home / "Movies"
    if destination == "desktop":
        return user_home / "Desktop"
    if destination == "premiere":
        return premiere_destination(home)[0]

    raw_path = message.get("destinationPath")
    if not isinstance(raw_path, str) or not raw_path or len(raw_path) > 4096:
        raise ValueError("Choisissez un dossier de destination.")
    path = Path(raw_path).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("Le dossier choisi n’est plus disponible.")
    return path.resolve()


def validated_download_job(message: dict[str, object], home: Path | None = None) -> dict[str, object]:
    url = message.get("url")
    if not is_supported_video_request_url(url):
        raise ValueError("Cette page ne correspond pas à une vidéo téléchargeable.")
    quality = message.get("quality", "best")
    if quality not in QUALITY_KEYS:
        raise ValueError("Qualité de téléchargement invalide.")
    quality = "audio" if quality == "audio" else "best"
    destination_key = message.get("destination", "downloads")
    premiere_project: Path | None = None
    premiere_bridge: Path | None = None
    if destination_key == "premiere":
        destination, premiere_project, premiere_bridge = premiere_destination(home)
    else:
        destination = resolve_destination(message, home)
    job = {
        "url": str(url),
        "quality": str(quality),
        "destination": str(destination),
        "completionSound": message.get("completionSound", True) is not False,
    }
    if premiere_project is not None:
        job["premiereProjectPath"] = str(premiere_project)
        job["premiereBridgePath"] = str(premiere_bridge)
    referer = message.get("referer")
    if referer is not None:
        if not is_public_web_url(referer):
            raise ValueError("Adresse de page d’origine invalide.")
        job["referer"] = str(referer)
    source_title = message.get("sourceTitle")
    if source_title is not None:
        if not isinstance(source_title, str) or len(source_title) > 300:
            raise ValueError("Titre de la vidéo invalide.")
        source_title = " ".join(source_title.split())
        if source_title:
            job["sourceTitle"] = source_title
    return job


def inbox_directory(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/TubeSave/Inbox"


def status_directory(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/TubeSave/Status"


def valid_job_id(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > JOB_ID_LENGTH_LIMIT:
        raise ValueError("Identifiant de téléchargement invalide.")
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in value):
        raise ValueError("Identifiant de téléchargement invalide.")
    return value


def status_path(job_id: object, home: Path | None = None) -> Path:
    return status_directory(home) / f"{valid_job_id(job_id)}.json"


def write_status(job_id: str, state: str, progress: int, message: str) -> None:
    directory = status_directory()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = status_path(job_id)
    temporary = directory / f".{job_id}.tmp"
    payload = {
        "state": state,
        "progress": max(0, min(100, int(progress))),
        "message": str(message)[:500],
        "updatedAt": int(time.time() * 1000),
    }
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(target)


def read_status(message: dict[str, object]) -> dict[str, object]:
    path = status_path(message.get("jobId"))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"ok": True, "state": "unknown", "progress": 0, "message": "Préparation…"}
    except (OSError, ValueError, TypeError):
        raise RuntimeError("État du téléchargement indisponible.")
    if not isinstance(payload, dict):
        raise RuntimeError("État du téléchargement invalide.")
    return {
        "ok": True,
        "state": str(payload.get("state", "unknown")),
        "progress": max(0, min(100, int(payload.get("progress", 0)))),
        "message": str(payload.get("message", ""))[:500],
        "updatedAt": int(payload.get("updatedAt", 0)),
    }


def app_bundle() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[2]
    return Path(__file__).resolve().parents[3]


def launch_app_for_job(job_path: Path, bundle: Path | None = None, wait_seconds: float = 4.0) -> None:
    """Open ClipFlow and recover from a stale LaunchServices instance."""
    app = bundle or app_bundle()

    def launch(*options: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/usr/bin/open", "-g", "-j", *options, str(app), "--args", "--tubesave-background"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )

    result = launch()
    if result.returncode != 0:
        raise RuntimeError("ClipFlow n’a pas pu être ouvert.")

    deadline = time.monotonic() + max(0.0, wait_seconds)
    while job_path.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if not job_path.exists():
        return

    # `open` can successfully target an old, unresponsive process. A fresh
    # instance safely consumes the still-pending file exactly once.
    result = launch("-n")
    if result.returncode != 0:
        raise RuntimeError("ClipFlow est bloqué et n’a pas pu être relancé.")


def queue_download(message: dict[str, object]) -> dict[str, object]:
    job = validated_download_job(message)
    inbox = inbox_directory()
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    identifier = f"{time.time_ns()}-{uuid.uuid4().hex}"
    job["jobId"] = identifier
    temporary = inbox / f".{identifier}.tmp"
    destination = inbox / f"{identifier}.json"
    temporary.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    write_status(identifier, "queued", 1, "Préparation du téléchargement…")

    try:
        launch_app_for_job(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    destination_path = Path(job["destination"])
    return {
        "ok": True,
        "message": "Demande envoyée à ClipFlow.",
        "destination": str(destination_path),
        "destinationLabel": (
            "Premiere Pro · Médias ClipFlow"
            if "premiereProjectPath" in job
            else destination_path.name or str(destination_path)
        ),
        "jobId": identifier,
    }


def choose_folder() -> dict[str, object]:
    script = (
        'POSIX path of (choose folder with prompt "Choisissez où ClipFlow enregistrera les vidéos" '
        "default location (path to downloads folder))"
    )
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Sélection du dossier annulée.")
    selected = Path(result.stdout.rstrip("\n"))
    if not selected.is_absolute() or not selected.is_dir():
        raise RuntimeError("Le dossier sélectionné est invalide.")
    return {"ok": True, "path": str(selected), "label": selected.name or str(selected)}


def handle_message(message: object) -> dict[str, object]:
    if not isinstance(message, dict):
        raise ValueError("Message invalide.")
    action = message.get("action")
    if action == "download":
        return queue_download(message)
    if action == "status":
        return read_status(message)
    if action == "choose_folder":
        return choose_folder()
    if action == "ping":
        return {"ok": True, "version": "2.1"}
    raise ValueError("Action inconnue.")


def read_message(stream: object = None) -> object:
    source = stream or sys.stdin.buffer
    raw_length = source.read(4)
    if len(raw_length) != 4:
        raise EOFError("Message Chrome incomplet.")
    length = struct.unpack("@I", raw_length)[0]
    if length > MAX_MESSAGE_SIZE:
        raise ValueError("Message Chrome trop volumineux.")
    payload = source.read(length)
    if len(payload) != length:
        raise EOFError("Message Chrome tronqué.")
    return json.loads(payload.decode("utf-8"))


def write_message(message: dict[str, object], stream: object = None) -> None:
    target = stream or sys.stdout.buffer
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    target.write(struct.pack("@I", len(payload)))
    target.write(payload)
    target.flush()


def main() -> int:
    try:
        response = handle_message(read_message())
    except Exception as error:  # Chrome must always receive a structured response.
        response = {"ok": False, "error": str(error)}
    write_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
