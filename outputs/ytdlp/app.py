#!/usr/bin/env python3
"""ClipFlow, interface macOS minimaliste autour du projet officiel yt-dlp."""

from __future__ import annotations

import hashlib
import json
import ipaddress
import os
import queue
import re
import shutil
import signal
import ssl
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import END, HORIZONTAL, LEFT, RIGHT, X, filedialog, messagebox, ttk
from urllib.parse import parse_qs, urlparse


APP_NAME = "ClipFlow"
CHROME_EXTENSION_ID = "emfjpphkcgnjldilcnieaoppmfpfkhfg"
NATIVE_HOST_NAME = "fr.tubesave.chrome"
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)
RETRYABLE_OUTPUT_MARKERS = (
    "http error 403",
    "token minting failed",
    "unable to download video data",
    "unable to download webpage",
    "connection reset",
    "network is unreachable",
    "remote end closed connection",
    "temporary failure in name resolution",
    "nodename nor servname provided",
    "name or service not known",
    "timed out",
)
AUTHENTICATION_OUTPUT_MARKERS = (
    "sign in to confirm you’re not a bot",
    "sign in to confirm you're not a bot",
    "login_required",
)
DRM_OUTPUT_MARKERS = (
    "this video is drm protected",
    "protected by drm",
    "drm protected",
)
QUALITY_FORMAT_OUTPUT_MARKERS = (
    "requested format is not available",
    "requested format not available",
)
COMPLETION_SOUNDS = (
    Path("/System/Library/Sounds/Pop.aiff"),
    Path("/System/Library/Sounds/Glass.aiff"),
)


@dataclass(frozen=True)
class QualityProfile:
    label: str
    max_height: int | None = None
    audio_only: bool = False
    mode: str = "original"


PROFILES = (
    QualityProfile("Meilleur MP4 compatible", mode="compatible"),
    QualityProfile("Audio uniquement · MP3", audio_only=True),
)
EXTENSION_PROFILE_BY_KEY = {
    "best": PROFILES[0].label,
    # Compatibilité avec les requêtes créées par les anciennes versions.
    "1080": PROFILES[0].label,
    "720": PROFILES[0].label,
    "480": PROFILES[0].label,
    "audio": PROFILES[1].label,
}


def frozen_application() -> bool:
    return bool(getattr(sys, "frozen", False))


def application_resources() -> Path:
    if frozen_application():
        return Path(sys.executable).resolve().parents[1] / "Resources"
    return Path(__file__).resolve().parent


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and (parsed.hostname or "").lower() in YOUTUBE_HOSTS
        and bool(parsed.path)
    )


def is_web_url(value: object) -> bool:
    """Accept public HTTP(S) pages while refusing local or credential-bearing URLs."""
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


def youtube_video_id(value: str) -> str | None:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if (parsed.hostname or "").lower() in {"youtu.be", "www.youtu.be"}:
        identifier = parsed.path.strip("/").split("/", 1)[0]
    else:
        identifier = parse_qs(parsed.query).get("v", [""])[0]
    return identifier if re.fullmatch(r"[A-Za-z0-9_-]{6,20}", identifier) else None


def resume_legacy_partials(destination: Path, url: str) -> int:
    identifier = youtube_video_id(url)
    if not identifier:
        return 0
    marker = f"[{identifier}] "
    renamed = 0
    try:
        candidates = list(destination.iterdir())
    except OSError:
        return 0
    for source in candidates:
        if not source.is_file() or marker not in source.name or not source.name.endswith(".part"):
            continue
        prefix, legacy_suffix = source.name.rsplit(marker, 1)
        match = re.fullmatch(r"\d{8}-\d{6}-\d{6}(\..+\.part)", legacy_suffix)
        if not match:
            continue
        target = source.with_name(f"{prefix}[{identifier}]{match.group(1)}")
        if target.exists():
            continue
        try:
            source.rename(target)
            renamed += 1
        except OSError:
            pass
    return renamed


def hide_visible_partials(destination: Path, url: str) -> int:
    """Move yt-dlp resume files out of sight without breaking resumability."""
    identifier = youtube_video_id(url)
    if not identifier:
        return 0
    marker = f"[{identifier}]"
    temporary = destination / ".tubesave-incomplete"
    moved = 0
    try:
        candidates = list(destination.iterdir())
    except OSError:
        return 0
    for source in candidates:
        if (
            not source.is_file()
            or marker not in source.name
            or not any(token in source.name for token in (".part", ".ytdl"))
        ):
            continue
        try:
            temporary.mkdir(mode=0o700, exist_ok=True)
            target = temporary / source.name
            if target.exists():
                continue
            source.rename(target)
            moved += 1
        except OSError:
            pass
    return moved


def validation_timed_out(last_output_at: float, download_started: bool, now: float | None = None) -> bool:
    current_time = now if now is not None else time.monotonic()
    return not download_started and current_time - last_output_at > 60


def is_retryable_output(line: str) -> bool:
    normalized = line.casefold()
    return any(marker in normalized for marker in RETRYABLE_OUTPUT_MARKERS)


def quality_format_unavailable_output(line: str) -> bool:
    """Detect a transient YouTube response that exposes only low-quality formats."""
    normalized = line.casefold()
    return any(marker in normalized for marker in QUALITY_FORMAT_OUTPUT_MARKERS)


def authentication_required_output(line: str, download_started: bool = False) -> bool:
    """Recognize site verification failures without misclassifying a late transfer error."""
    normalized = line.casefold()
    return any(marker in normalized for marker in AUTHENTICATION_OUTPUT_MARKERS) or (
        not download_started and "http error 403" in normalized
    )


def drm_protected_output(line: str) -> bool:
    """Recognize a confirmed DRM diagnostic without matching generic copyright text."""
    normalized = line.casefold()
    return any(marker in normalized for marker in DRM_OUTPUT_MARKERS)


def already_downloaded_path(line: str) -> Path | None:
    """Recover the existing result path from yt-dlp's skip message."""
    prefix = "[download] "
    suffix = " has already been downloaded"
    if not line.startswith(prefix) or not line.endswith(suffix):
        return None
    candidate = Path(line[len(prefix) : -len(suffix)])
    return candidate if candidate.is_file() else None


def extension_inbox(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/TubeSave/Inbox"


def extension_status_directory(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/TubeSave/Status"


def write_extension_status(
    job_id: str | None,
    state: str,
    progress: float,
    message: str,
    home: Path | None = None,
) -> None:
    if not job_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", job_id):
        return
    directory = extension_status_directory(home)
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = directory / f"{job_id}.json"
        temporary = directory / f".{job_id}.tmp"
        payload = {
            "state": state,
            "progress": max(0, min(100, round(progress))),
            "message": str(message)[:500],
            "updatedAt": int(time.time() * 1000),
        }
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(target)
    except OSError:
        pass


def settings_file(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/TubeSave/settings.json"


def automatic_browser_session_enabled(home: Path | None = None) -> bool:
    """Return the user's explicit, locally stored browser-session preference."""
    try:
        settings = json.loads(settings_file(home).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    return (
        isinstance(settings, dict)
        and settings.get("use_browser_session_automatically") is True
    )


def extension_request_values(
    request: object,
) -> tuple[str, Path, str, str | None, str | None, str | None, Path | None, Path | None, bool]:
    if not isinstance(request, dict):
        raise ValueError("Demande Chrome invalide.")
    url = request.get("url")
    quality_key = request.get("quality")
    raw_destination = request.get("destination")
    if not is_web_url(url):
        raise ValueError("Adresse de page ou de vidéo invalide.")
    if quality_key not in EXTENSION_PROFILE_BY_KEY:
        raise ValueError("Qualité Chrome invalide.")
    if not isinstance(raw_destination, str) or len(raw_destination) > 4096:
        raise ValueError("Dossier Chrome invalide.")
    destination = Path(raw_destination).expanduser()
    if not destination.is_absolute() or not destination.is_dir():
        raise ValueError("Le dossier choisi dans Chrome n’est plus disponible.")
    raw_referer = request.get("referer")
    if raw_referer is not None and not is_web_url(raw_referer):
        raise ValueError("Adresse de page d’origine invalide.")
    referer = str(raw_referer) if raw_referer is not None else None
    raw_source_title = request.get("sourceTitle")
    if raw_source_title is not None and (
        not isinstance(raw_source_title, str) or len(raw_source_title) > 300
    ):
        raise ValueError("Titre de la vidéo invalide.")
    source_title = " ".join(raw_source_title.split()) if isinstance(raw_source_title, str) else None
    if not source_title:
        source_title = None
    raw_job_id = request.get("jobId")
    job_id = str(raw_job_id) if isinstance(raw_job_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,96}", raw_job_id) else None
    completion_sound = request.get("completionSound", True) is not False
    raw_premiere_project = request.get("premiereProjectPath")
    premiere_project: Path | None = None
    premiere_bridge: Path | None = None
    if raw_premiere_project is not None:
        if not isinstance(raw_premiere_project, str) or len(raw_premiere_project) > 4096:
            raise ValueError("Projet Premiere Pro invalide.")
        premiere_project = Path(raw_premiere_project).expanduser()
        if (
            not premiere_project.is_absolute()
            or premiere_project.suffix.casefold() != ".prproj"
            or not premiere_project.is_file()
        ):
            raise ValueError("Le projet Premiere Pro n’est plus disponible.")
        premiere_project = premiere_project.resolve()
        raw_premiere_bridge = request.get("premiereBridgePath")
        if not isinstance(raw_premiere_bridge, str) or len(raw_premiere_bridge) > 4096:
            raise ValueError("Pont Premiere Pro invalide.")
        premiere_bridge = Path(raw_premiere_bridge).expanduser()
        if not premiere_bridge.is_absolute() or not premiere_bridge.is_dir():
            raise ValueError("Le module ClipFlow de Premiere Pro n’est plus disponible.")
        premiere_bridge = premiere_bridge.resolve()
        legacy = premiere_bridge_directory().resolve()
        adobe_layout = (
            premiere_bridge.name == "PluginData"
            and premiere_bridge.parent.name == "fr.clipflow.premiere.bridge"
            and premiere_bridge.parent.parent.name == "External"
        )
        if premiere_bridge != legacy and not adobe_layout:
            raise ValueError("Pont Premiere Pro invalide.")
    return (
        str(url),
        destination,
        EXTENSION_PROFILE_BY_KEY[str(quality_key)],
        referer,
        source_title,
        job_id,
        premiere_project,
        premiere_bridge,
        completion_sound,
    )


def consume_extension_requests(
    inbox: Path,
    limit: int = 20,
) -> list[tuple[str, Path, str, str | None, str | None, str | None, Path | None, Path | None, bool]]:
    requests: list[tuple[str, Path, str, str | None, str | None, str | None, Path | None, Path | None, bool]] = []
    if limit <= 0:
        return requests
    try:
        files = sorted(inbox.glob("*.json"))[:limit]
    except OSError:
        return requests
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            requests.append(extension_request_values(payload))
        except (OSError, ValueError, TypeError):
            pass
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    return requests


def premiere_bridge_directory(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library/Application Support/ClipFlow/Premiere"


def queue_premiere_import(
    media_path: Path,
    project_path: Path,
    job_id: str | None = None,
    home: Path | None = None,
    bridge_path: Path | None = None,
) -> Path:
    """Atomically enqueue a finished media file for the Premiere UXP bridge."""
    media = media_path.expanduser().resolve()
    project = project_path.expanduser().resolve()
    if not media.is_file():
        raise ValueError("Le fichier téléchargé est introuvable.")
    if project.suffix.casefold() != ".prproj" or not project.is_file():
        raise ValueError("Le projet Premiere Pro n’est plus disponible.")
    identifier = job_id if job_id and re.fullmatch(r"[A-Za-z0-9_-]{1,96}", job_id) else uuid.uuid4().hex
    bridge = (bridge_path or premiere_bridge_directory(home)).expanduser().resolve()
    inbox = bridge / "Imports"
    results = bridge / "Results"
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    results.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = {
        "jobId": identifier,
        "mediaPath": str(media),
        "projectPath": str(project),
        "requestedAt": int(time.time() * 1000),
    }
    target = inbox / f"{identifier}.json"
    temporary = inbox / f".{identifier}.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(target)
    return results / f"{identifier}.json"


def wait_for_premiere_import(
    result_path: Path,
    events: queue.Queue[tuple[str, object]],
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            time.sleep(0.25)
            continue
        except (OSError, ValueError, TypeError) as error:
            events.put(("premiere_import", (False, f"Réponse Premiere Pro invalide : {error}")))
            return
        finally:
            if result_path.exists():
                try:
                    result_path.unlink()
                except OSError:
                    pass
        success = isinstance(payload, dict) and payload.get("state") == "complete"
        message = str(payload.get("message", "")) if isinstance(payload, dict) else ""
        events.put(("premiere_import", (success, message)))
        return
    events.put(
        (
            "premiere_import",
            (
                None,
                "Fichier téléchargé dans Médias ClipFlow · import Premiere Pro encore en attente.",
            ),
        )
    )


def ensure_chrome_native_host(home: Path | None = None, host: Path | None = None) -> Path | None:
    native_host = (host or (application_resources() / "ytdlp" / "native_host")).resolve()
    if not native_host.is_file() and not frozen_application():
        native_host = (application_resources() / "native_host").resolve()
    if not native_host.is_file() or not os.access(native_host, os.X_OK):
        return None
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "Liaison locale entre Chrome et ClipFlow",
        "path": str(native_host),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{CHROME_EXTENSION_ID}/"],
    }
    target = (
        (home or Path.home())
        / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
        / f"{NATIVE_HOST_NAME}.json"
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
            os.chmod(target, 0o600)
    except OSError:
        return None
    return target


def yt_dlp_prefix() -> list[str] | None:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        executable = shutil.which("yt-dlp")
        return [executable] if executable else None
    if frozen_application():
        return [sys.executable, "--tubesave-yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def ca_bundle() -> Path | None:
    try:
        import certifi

        bundle = Path(certifi.where())
        if bundle.is_file():
            return bundle
    except (ImportError, OSError):
        pass
    system_bundle = ssl.get_default_verify_paths().cafile
    return Path(system_bundle) if system_bundle and Path(system_bundle).is_file() else None


def chromium_browser() -> Path | None:
    return next(
        (Path(candidate) for candidate in BROWSERS if Path(candidate).is_file()),
        None,
    )


def browser_cookie_source(browser: Path | None, profile: str | None = None) -> str | None:
    if not browser:
        return None
    path = str(browser).lower()
    if "google chrome" in path:
        name = "chrome"
    elif "chromium" in path:
        name = "chromium"
    elif "brave" in path:
        name = "brave"
    elif "microsoft edge" in path:
        name = "edge"
    else:
        return None
    return f"{name}:{profile}" if profile else name


def last_used_browser_profile(browser: Path | None, home: Path | None = None) -> str | None:
    if not browser:
        return None
    path = str(browser).lower()
    relative_root = None
    if "google chrome" in path:
        relative_root = "Google/Chrome"
    elif "chromium" in path:
        relative_root = "Chromium"
    elif "brave" in path:
        relative_root = "BraveSoftware/Brave-Browser"
    elif "microsoft edge" in path:
        relative_root = "Microsoft Edge"
    if not relative_root:
        return None
    local_state = (home or Path.home()) / "Library/Application Support" / relative_root / "Local State"
    try:
        data = json.loads(local_state.read_text(encoding="utf-8"))
        profile = data.get("profile", {}).get("last_used")
    except (OSError, ValueError, AttributeError):
        return None
    return profile if isinstance(profile, str) and "/" not in profile and ":" not in profile else None


def with_browser_cookies(command: list[str], browser_name: str) -> list[str]:
    """Add yt-dlp's in-memory browser cookie option before the final URL."""
    return [
        *command[:-1],
        "--cookies-from-browser",
        browser_name,
        command[-1],
    ]


def without_minimum_video_height(command: list[str]) -> list[str]:
    """Allow a genuine SD-only YouTube video after bounded HD retries."""
    relaxed = list(command)
    try:
        format_index = relaxed.index("--format") + 1
    except ValueError:
        return relaxed
    if format_index < len(relaxed):
        relaxed[format_index] = relaxed[format_index].replace("[height>=720]", "")
    return relaxed


def ffmpeg_executable() -> Path | None:
    system = shutil.which("ffmpeg")
    if system:
        return Path(system)

    # Finder may launch the framework Python through Python.app and lose the
    # virtual environment's import path. Locate the bundled executable directly
    # before relying on imageio_ffmpeg's Python package.
    embedded_environment = Path(__file__).resolve().parent / ".venv" / "lib"
    for bundled in embedded_environment.glob(
        "python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"
    ):
        if bundled.is_file() and os.access(bundled, os.X_OK):
            return bundled

    try:
        import imageio_ffmpeg

        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        return bundled if bundled.is_file() else None
    except (ImportError, OSError, RuntimeError):
        return None


def child_environment(bundle: Path | None) -> dict[str, str]:
    environment = os.environ.copy()
    # The frozen yt-dlp process writes to a pipe rather than a Terminal. Without
    # unbuffered output, errors can remain invisible until the validation watchdog
    # fires, preventing the UI from reacting to an early site-level 403.
    environment["PYTHONUNBUFFERED"] = "1"
    if bundle:
        environment["SSL_CERT_FILE"] = str(bundle)
    return environment


def play_completion_sound(
    player: Path = Path("/usr/bin/afplay"),
    sounds: tuple[Path, ...] = COMPLETION_SOUNDS,
) -> bool:
    """Play a short native macOS sound without opening a visible process."""
    sound = next((candidate for candidate in sounds if candidate.is_file()), None)
    if not player.is_file() or sound is None:
        return False
    try:
        subprocess.Popen(
            [str(player), str(sound)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    return True


def direct_stream_output_template(
    url: str,
    referer: str | None,
    title_hint: str | None,
    quality_suffix: str,
) -> str | None:
    """Give generic manifests a stable, human title instead of `playlist`."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    hostname = (parsed.hostname or "").casefold()
    path = parsed.path.casefold()
    direct_stream = (
        path.endswith((".m3u8", ".mpd"))
        or "vimeocdn.com" in hostname
        or ".ism/" in path
    )
    if not direct_stream or not title_hint:
        return None

    title = re.sub(r"[\\/:]+", " – ", title_hint)
    title = re.sub(r"[\x00-\x1f\x7f]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .")[:140].rstrip(" .")
    if not title:
        return None

    normalized_referer = ""
    vimeo_id: str | None = None
    if referer:
        try:
            page = urlparse(referer)
            normalized_referer = page._replace(query="", fragment="").geturl()
            page_host = (page.hostname or "").casefold()
            first_path_part = page.path.strip("/").split("/", 1)[0]
            if (page_host == "vimeo.com" or page_host.endswith(".vimeo.com")) and first_path_part.isdigit():
                vimeo_id = first_path_part
        except ValueError:
            normalized_referer = referer
    stable_stream = parsed._replace(query="", fragment="").geturl()
    digest = hashlib.sha256(f"{normalized_referer}|{stable_stream}".encode("utf-8")).hexdigest()[:8]
    identity = f"vimeo-{vimeo_id}-{digest}" if vimeo_id else f"source-{digest}"
    escaped_title = title.replace("%", "%%")
    return f"{escaped_title} [{identity}] {quality_suffix}.%(ext)s"


def build_download_command(
    prefix: list[str],
    url: str,
    destination: Path,
    profile: QualityProfile,
    ffmpeg: Path | None,
    browser: Path | None,
    referer: str | None = None,
    title_hint: str | None = None,
) -> list[str]:
    if not ffmpeg:
        raise ValueError("FFmpeg est nécessaire. Relancez installer.command.")

    quality_suffix = "audio" if profile.audio_only else "compatible"
    output_template = direct_stream_output_template(url, referer, title_hint, quality_suffix)
    if output_template is None:
        output_template = f"%(title).150B [%(id)s] {quality_suffix}.%(ext)s"
    command = [
        *prefix,
        "--ignore-config",
        "--newline",
        "--no-colors",
        "--no-playlist",
        # Let yt-dlp's generic extractor use the bundled curl-cffi browser
        # impersonation when a page is protected by Cloudflare. Specialized
        # extractors (YouTube, Vimeo, Dailymotion, etc.) remain unchanged.
        "--extractor-args",
        "generic:impersonate",
        "--socket-timeout",
        "30",
        "--extractor-retries",
        "5",
        "--retries",
        "10",
        "--fragment-retries",
        "20",
        "--retry-sleep",
        "linear=1::2",
        "--retry-sleep",
        "fragment:linear=1::2",
        "--retry-sleep",
        "extractor:linear=1::2",
        "--continue",
        "--concurrent-fragments",
        "4",
        "--progress-template",
        "download:[progress]%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--print",
        "before_dl:[format]%(height)s|%(vcodec)s|%(tbr)s|%(language)s",
        "--print",
        "after_move:[done]%(filepath)s",
        # --print implicitly enables yt-dlp's quiet mode. Turn it back off so
        # extraction errors and fragment 403s reach the GUI as they happen.
        "--no-quiet",
        "--paths",
        f"home:{destination}",
        "--paths",
        "temp:.tubesave-incomplete",
        "--output",
        output_template,
    ]
    if ffmpeg:
        command.extend(["--ffmpeg-location", str(ffmpeg)])
    if referer:
        command.extend(["--referer", referer])

    if profile.audio_only:
        command.extend(
            [
                "--format-sort-force",
                "--format-sort",
                "lang,br",
                "--format",
                "bestaudio/best",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
            ]
        )
    else:
        command.extend(
            [
                "--format-sort-force",
                "--format-sort",
                "res,lang,br,fps",
            ]
        )
        # Select direct HTTPS H.264/AVC MP4 tracks first. YouTube's HLS links
        # can expire during long downloads, whereas its direct DASH tracks are
        # resumable and reliable. Keep HLS as a fallback for other sites.
        minimum_height = "[height>=720]" if is_youtube_url(url) else ""
        direct = f"bv[ext=mp4][vcodec^=avc1]{minimum_height}[protocol^=http]+ba[ext=m4a][protocol^=http]"
        direct_combined = f"b[ext=mp4][vcodec^=avc1]{minimum_height}[protocol^=http]"
        fallback = (
            f"bv[ext=mp4][vcodec^=avc1]{minimum_height}+ba[ext=m4a]/"
            f"bv[ext=mp4][vcodec^=avc1]{minimum_height}+ba[ext=mp4]/"
            f"b[ext=mp4][vcodec^=avc1]{minimum_height}"
        )
        # Generic direct MP4 links often omit codec metadata even when the
        # actual file is H.264/AAC (for example SeeArtTV). Keep them as a final
        # no-conversion fallback after the stricter AVC choices.
        generic_mp4 = (
            f"b[ext=mp4]{minimum_height}[protocol^=http]/"
            f"b[ext=mp4]{minimum_height}"
        )
        selector = f"{direct}/{direct_combined}/{fallback}/{generic_mp4}"
        command.extend(
            [
                "--format",
                selector,
                "--merge-output-format",
                "mp4",
            ]
        )
    command.append(url)
    return command


class DownloadWorker:
    def __init__(
        self,
        command: list[str],
        events: queue.Queue[tuple[str, object]],
        environment: dict[str, str],
        cookie_browser: str | None,
        automatic_cookies: bool = False,
    ) -> None:
        self.command = command
        self.youtube_hd_guard = is_youtube_url(command[-1]) and any(
            "[height>=720]" in argument for argument in command
        )
        self.events = events
        self.environment = environment
        self.cookie_browser = cookie_browser
        self.automatic_cookies = automatic_cookies
        self.process: subprocess.Popen[str] | None = None
        self.cancelled = False
        self.cookie_decision = threading.Event()
        self.cookies_allowed = False
        self._last_output_at = time.monotonic()
        self._attempt_timed_out = False
        self._download_started = False
        self._download_component = 0

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def cancel(self) -> None:
        self.cancelled = True
        self.cookie_decision.set()
        self._terminate(self.process)

    @staticmethod
    def _terminate(process: subprocess.Popen[str] | None) -> None:
        if process and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

    def allow_browser_cookies(self, allowed: bool) -> None:
        self.cookies_allowed = allowed
        self.cookie_decision.set()

    def _run(self) -> None:
        try:
            automatic_retries = 0
            quality_retries = 0
            quality_fallback_used = False
            cookies_attempted = False
            while True:
                return_code, retryable, authentication_required, timed_out, quality_unavailable = self._download_once()
                if self.cancelled:
                    self.events.put(("cancelled", None))
                    return
                if return_code == 0:
                    self.events.put(("finished", None))
                    return
                if quality_unavailable and self.youtube_hd_guard and not quality_fallback_used:
                    if quality_retries < 2:
                        quality_retries += 1
                        self.events.put(("retry_quality", quality_retries))
                        time.sleep(quality_retries)
                        continue
                    self.command = without_minimum_video_height(self.command)
                    quality_fallback_used = True
                    self.events.put(("quality_fallback", None))
                    continue
                if authentication_required and self.cookie_browser and not cookies_attempted:
                    cookies_attempted = True
                    if self.automatic_cookies:
                        self.command = with_browser_cookies(self.command, self.cookie_browser)
                        self.events.put(("retry_with_cookies", self.cookie_browser))
                        continue
                    self.events.put(("needs_cookies", self.cookie_browser))
                    self.cookie_decision.wait()
                    if self.cancelled:
                        self.events.put(("cancelled", None))
                        return
                    if self.cookies_allowed:
                        self.command = with_browser_cookies(self.command, self.cookie_browser)
                        self.events.put(("retry_with_cookies", self.cookie_browser))
                        continue
                    self.events.put(("failed", return_code))
                    return
                if automatic_retries < 2 and (retryable or timed_out):
                    automatic_retries += 1
                    self.events.put(("retry", automatic_retries))
                    time.sleep(automatic_retries)
                    continue
                if timed_out:
                    self.events.put(("timeout", None))
                    return
                self.events.put(("failed", return_code))
                return
        except Exception as error:
            self.events.put(("error", str(error)))

    def _watch_process(self, process: subprocess.Popen[str]) -> None:
        while process.poll() is None and not self.cancelled:
            time.sleep(1)
            if validation_timed_out(self._last_output_at, self._download_started):
                self._attempt_timed_out = True
                self._terminate(process)
                return

    def _download_once(self) -> tuple[int, bool, bool, bool, bool]:
        self._attempt_timed_out = False
        self._last_output_at = time.monotonic()
        self._download_started = False
        self._download_component = 0
        self.events.put(("phase", "Connexion au site vidéo…"))
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=self.environment,
            start_new_session=True,
        )
        threading.Thread(
            target=self._watch_process,
            args=(self.process,),
            daemon=True,
        ).start()
        assert self.process.stdout is not None
        retryable = False
        authentication_required = False
        quality_unavailable = False
        for raw_line in self.process.stdout:
            self._last_output_at = time.monotonic()
            line = raw_line.strip()
            if line.startswith("[progress]"):
                self._download_started = True
                parts = line.removeprefix("[progress]").split("|", 2)
                try:
                    percent = float(parts[0].strip().replace("%", ""))
                except ValueError:
                    percent = 0.0
                if self._download_component >= 2:
                    percent = 85.0 + (percent * 0.14)
                else:
                    percent = percent * 0.85
                self.events.put(
                    ("progress", (percent, parts[1].strip() if len(parts) > 1 else "", parts[2].strip() if len(parts) > 2 else ""))
                )
            elif line.startswith("[format]"):
                self.events.put(("format", line.removeprefix("[format]").split("|", 3)))
            elif line.startswith("[done]"):
                self.events.put(("file", line.removeprefix("[done]").strip()))
            elif existing := already_downloaded_path(line):
                self.events.put(("file", str(existing)))
                self.events.put(("existing", str(existing)))
            elif line:
                if authentication_required_output(line, self._download_started):
                    authentication_required = True
                    if "http error 403" in line.casefold() and not self._download_started:
                        self.events.put(("phase", "Flux refusé par le site · validation nécessaire…"))
                        self._terminate(self.process)
                if is_retryable_output(line):
                    retryable = True
                if quality_format_unavailable_output(line):
                    quality_unavailable = True
                if "Extracting cookies from" in line:
                    self.events.put(("phase", "Lecture autorisée de la session Chrome…"))
                elif "Extracted " in line and "cookies" in line:
                    self.events.put(("phase", "Session Chrome chargée · validation du site…"))
                elif "Downloading webpage" in line:
                    self.events.put(("phase", "Page reçue · analyse de la vidéo…"))
                elif "Downloading" in line and "player API" in line:
                    self.events.put(("phase", "Vérification de la vidéo auprès du site…"))
                elif "Destination:" in line:
                    self._download_component += 1
                    self.events.put(("phase", "Flux sélectionnés · téléchargement…"))
                elif line.startswith("[Merger]"):
                    self.events.put(("phase", "Assemblage audio et vidéo sans réencodage…"))
                self.events.put(("log", line))
        return (
            self.process.wait(),
            retryable,
            authentication_required,
            self._attempt_timed_out,
            quality_unavailable,
        )


class HeadlessValue:
    """Small in-memory replacement for Tk variables used by the agent."""

    def __init__(self, value: object = "") -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class HeadlessControl:
    """Accept widget-style state updates without creating a macOS window."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def __setitem__(self, key: str, value: object) -> None:
        self.values[key] = value

    def configure(self, **values: object) -> None:
        self.values.update(values)


class TubeSaveApp(tk.Tk):
    BG = "#F5F5F7"
    CARD = "#FFFFFF"
    TEXT = "#1D1D1F"
    MUTED = "#6E6E73"
    BLUE = "#0A84FF"
    BLUE_ACTIVE = "#0071E3"
    LINE = "#D2D2D7"
    SOFT = "#E9E9EB"
    SHADOW = "#DEDEE3"
    IDLE_SHUTDOWN_SECONDS = 45.0

    def __init__(self) -> None:
        # useTk=False creates only a Tcl event interpreter. No NSApplication,
        # WindowServer connection, Dock tile or hidden macOS window is created.
        super().__init__(useTk=False)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: DownloadWorker | None = None
        self.last_file: Path | None = None
        self.result_was_existing = False
        self.logs: list[str] = []
        self.log_file = Path(os.environ.get("TMPDIR", "/tmp")) / "ClipFlow-download.log"
        self.prefix = yt_dlp_prefix()
        self.bundle = ca_bundle()
        self.browser = chromium_browser()
        self.ffmpeg = ffmpeg_executable()
        self.format_details = ""
        self.extension_jobs: deque[
            tuple[str, Path, str, str | None, str | None, str | None, Path | None, Path | None, bool]
        ] = deque()
        self.active_job_id: str | None = None
        self.active_premiere_project: Path | None = None
        self.active_premiere_bridge: Path | None = None
        self.background_job = False
        self.completion_sound_enabled = True
        self.current_progress = 0.0
        self.last_activity_at = time.monotonic()
        self.premiere_import_pending = False
        self.request_referer: str | None = None
        self.request_source_title: str | None = None
        self.extension_inbox = extension_inbox()
        self.native_host_manifest = ensure_chrome_native_host()
        self.automatic_browser_session = automatic_browser_session_enabled()

        self.url = HeadlessValue()
        self.folder = HeadlessValue(str(Path.home() / "Downloads"))
        self.audio_only = HeadlessValue(False)
        self.status = HeadlessValue("Prêt à télécharger")
        self.details = HeadlessValue(self._environment_status())
        self.bar = HeadlessControl()
        self.percent = HeadlessControl()
        self.download = HeadlessControl()
        self.cancel = HeadlessControl()
        self.open_result = HeadlessControl()
        self.after(100, self._poll)
        self.after(250, self._poll_extension_requests)
        self.after(5000, self._idle_shutdown_check)

    def run_forever(self) -> None:
        """Run Tcl timers without ever loading the graphical Tk framework."""
        self.tk.call("vwait", "::clipflow_agent_running")

    def _environment_status(self) -> str:
        missing = []
        if not self.prefix: missing.append("yt-dlp")
        if not self.bundle: missing.append("certificats")
        if not self.ffmpeg: missing.append("FFmpeg")
        return "Prêt · MP4 H.264 compatible · sans conversion" if not missing else "Manque : " + ", ".join(missing)

    def _show_window(self) -> None:
        return

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.configure(
            "ClipFlow.Horizontal.TProgressbar",
            background=self.BLUE,
            borderwidth=0,
            lightcolor=self.BLUE,
            darkcolor=self.BLUE,
            troughcolor="#E5E5EA",
            thickness=7,
        )

        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(18, 16))

        header = tk.Frame(body, bg=self.BG)
        header.pack(fill=X, pady=(0, 14))
        if self.brand_icon:
            tk.Label(header, image=self.brand_icon, bg=self.BG).pack(side=LEFT, padx=(0, 14))
        title_block = tk.Frame(header, bg=self.BG)
        title_block.pack(side=LEFT, anchor="center")
        tk.Label(title_block, text="ClipFlow", font=("SF Pro Display", 21, "bold"), fg=self.TEXT, bg=self.BG).pack(anchor="w")

        card_shadow = tk.Frame(body, bg=self.SHADOW)
        card_shadow.pack(fill=X)
        card = tk.Frame(card_shadow, bg=self.CARD)
        card.pack(fill=X, padx=(0, 3), pady=(0, 4))
        form = tk.Frame(card, bg=self.CARD)
        form.pack(fill=X, padx=16, pady=14)
        self._label(form, "Lien vidéo")
        row = tk.Frame(form, bg=self.CARD)
        row.pack(fill=X, pady=(6, 12))
        entry = tk.Entry(
            row,
            textvariable=self.url,
            font=("Helvetica Neue", 11),
            relief="flat",
            bd=0,
            bg="#FBFBFD",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            highlightthickness=0,
        )
        entry.pack(side=LEFT, fill=X, expand=True, ipady=10)
        entry.bind("<Return>", lambda _event: self._start())
        self._button(row, "Coller", self._paste).pack(side=RIGHT, padx=(9, 0))

        split = tk.Frame(form, bg=self.CARD)
        split.pack(fill=X)
        left = tk.Frame(split, bg=self.CARD)
        left.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        right = tk.Frame(split, bg=self.CARD)
        right.pack(side=RIGHT, padx=(10, 0), anchor="s")
        self._label(left, "Enregistrer dans")
        folder_row = tk.Frame(left, bg=self.CARD)
        folder_row.pack(fill=X, pady=(7, 0))
        tk.Entry(
            folder_row,
            textvariable=self.folder,
            font=("Helvetica Neue", 10),
            relief="flat",
            bd=0,
            bg="#FBFBFD",
            fg=self.TEXT,
            highlightthickness=0,
        ).pack(side=LEFT, fill=X, expand=True, ipady=9)
        self._button(folder_row, "Choisir", self._choose).pack(side=RIGHT, padx=(8, 0))
        tk.Checkbutton(
            right,
            text="Audio uniquement (MP3)",
            variable=self.audio_only,
            font=("Helvetica Neue", 11),
            bg=self.CARD,
            fg=self.TEXT,
            activebackground=self.CARD,
            activeforeground=self.TEXT,
            selectcolor=self.CARD,
            highlightthickness=0,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            right,
            text="MP4 compatible avec macOS",
            font=("Helvetica Neue", 9),
            bg=self.CARD,
            fg=self.MUTED,
        ).pack(anchor="w")

        progress_shadow = tk.Frame(body, bg=self.SHADOW)
        progress_shadow.pack(fill=X, pady=(10, 0))
        progress_card = tk.Frame(progress_shadow, bg=self.CARD)
        progress_card.pack(fill=X, padx=(0, 3), pady=(0, 4))
        inside = tk.Frame(progress_card, bg=self.CARD)
        inside.pack(fill=X, padx=16, pady=12)
        status_row = tk.Frame(inside, bg=self.CARD)
        status_row.pack(fill=X)
        tk.Label(status_row, textvariable=self.status, font=("Helvetica Neue", 12, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=LEFT)
        self.percent = tk.Label(status_row, text="0 %", font=("SF Pro Display", 22, "bold"), bg=self.CARD, fg=self.BLUE)
        self.percent.pack(side=RIGHT)
        self.bar = ttk.Progressbar(inside, orient=HORIZONTAL, maximum=100, style="ClipFlow.Horizontal.TProgressbar")
        tk.Label(inside, textvariable=self.details, font=("Helvetica Neue", 10), bg=self.CARD, fg=self.MUTED).pack(anchor="w", pady=(8, 0))

        actions = tk.Frame(body, bg=self.BG)
        actions.pack(fill=X, pady=(12, 0))
        self.download = tk.Button(
            actions,
            text="Télécharger",
            command=self._start,
            bg=self.BLUE,
            fg="white",
            activebackground=self.BLUE_ACTIVE,
            activeforeground="white",
            font=("Helvetica Neue", 11, "bold"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=22,
            pady=11,
        )
        self.download.pack(side=RIGHT)
        self.cancel = self._button(actions, "Annuler", self._cancel)
        self.cancel.configure(state="disabled")
        self.cancel.pack(side=RIGHT, padx=(0, 9))
        self.open_result = self._button(actions, "Afficher le fichier", self._reveal)
        self.open_result.configure(state="disabled")
        self.open_result.pack(side=LEFT)

    def _label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, font=("Helvetica Neue", 10, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w")

    def _button(self, parent: tk.Widget, text: str, command: object) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Helvetica Neue", 10, "bold"),
            relief="flat",
            bd=0,
            bg=self.SOFT,
            fg=self.TEXT,
            activebackground="#DCDCE0",
            activeforeground=self.TEXT,
            highlightthickness=0,
            padx=13,
            pady=9,
        )

    def _paste(self) -> None:
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            messagebox.showinfo(APP_NAME, "Le presse-papiers ne contient pas de texte.")

    def _choose(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.folder.get() or str(Path.home()))
        if selected: self.folder.set(selected)

    def _start_error(self, message: str, warning: bool = False) -> None:
        write_extension_status(self.active_job_id, "error", 0, message)
        self.active_job_id = None
        self.background_job = False

    def _start(self) -> None:
        if self.worker: return
        if not is_web_url(self.url.get()):
            self._start_error("Collez un lien public de page ou de vidéo valide.", warning=True)
            return
        if not all((self.prefix, self.bundle, self.ffmpeg)):
            self._start_error("Des composants manquent. Réinstallez ClipFlow.")
            return
        destination = Path(self.folder.get()).expanduser()
        try: destination.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self._start_error(f"Dossier inutilisable : {error}")
            return
        resume_legacy_partials(destination, self.url.get().strip())
        hide_visible_partials(destination, self.url.get().strip())
        profile = PROFILES[1] if self.audio_only.get() else PROFILES[0]
        try:
            command = build_download_command(
                self.prefix,
                self.url.get().strip(),
                destination,
                profile,
                self.ffmpeg,
                self.browser,
                self.request_referer,
                self.request_source_title,
            )
        except ValueError as error:
            self._start_error(str(error))
            return
        self.request_referer = None
        self.request_source_title = None
        profile_name = last_used_browser_profile(self.browser)
        cookie_source = browser_cookie_source(self.browser, profile_name)
        self.last_file = None
        self.result_was_existing = False
        self.logs.clear()
        self.format_details = ""
        try:
            self.log_file.write_text("", encoding="utf-8")
        except OSError:
            pass
        self.bar["value"] = 0
        self.current_progress = 0.0
        self.percent.configure(text="0 %")
        self.status.set("Validation auprès du site…")
        self.details.set("Analyse de la page vidéo en arrière-plan")
        self.download.configure(state="disabled")
        self.cancel.configure(state="normal")
        self.open_result.configure(state="disabled")
        self.worker = DownloadWorker(
            command,
            self.events,
            child_environment(self.bundle),
            cookie_source,
            self.automatic_browser_session and is_youtube_url(self.url.get()),
        )
        self.last_activity_at = time.monotonic()
        write_extension_status(self.active_job_id, "running", 1, "Analyse de la vidéo…")
        self.worker.start()

    def _poll_extension_requests(self) -> None:
        try:
            # Never remove several requests from disk while a download or a
            # Premiere import is active. If this process becomes stale, the
            # native host can see the pending file and launch a fresh instance.
            if not self.worker and not self.premiere_import_pending:
                if not self.extension_jobs:
                    self.extension_jobs.extend(
                        consume_extension_requests(self.extension_inbox, limit=1)
                    )
                if self.extension_jobs:
                    url, destination, quality, referer, source_title, job_id, premiere_project, premiere_bridge, completion_sound = self.extension_jobs.popleft()
                    self.active_job_id = job_id
                    self.active_premiere_project = premiere_project
                    self.active_premiere_bridge = premiere_bridge
                    # Every queued request comes from Chrome, including legacy requests
                    # without a job identifier. It must therefore stay non-interactive.
                    self.background_job = True
                    self.completion_sound_enabled = completion_sound
                    self.url.set(url)
                    self.folder.set(str(destination))
                    self.audio_only.set(quality == PROFILES[1].label)
                    self.request_referer = referer
                    self.request_source_title = source_title
                    self.status.set("Vidéo détectée par l’extension")
                    self.details.set("ClipFlow prépare le téléchargement…")
                    self.last_activity_at = time.monotonic()
                    write_extension_status(job_id, "running", 1, "Préparation du téléchargement…")
                    self.after(120, self._start)
        except Exception as error:
            write_extension_status(
                self.active_job_id,
                "error",
                self.current_progress,
                f"Le moteur ClipFlow a redémarré après une erreur : {error}",
            )
            self._reset()
        finally:
            self.after(400, self._poll_extension_requests)

    def _cancel(self) -> None:
        if self.worker:
            self.cancel.configure(state="disabled")
            self.worker.cancel()

    def _poll(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            try:
                self._event(event, payload)
            except Exception as error:
                self.logs.append(f"Erreur interne : {error}")
                write_extension_status(
                    self.active_job_id,
                    "error",
                    self.current_progress,
                    "ClipFlow s’est rétabli après une erreur interne. Relancez le téléchargement.",
                )
                self._reset()
        self.after(100, self._poll)

    def _idle_shutdown_check(self) -> None:
        pending_on_disk = False
        try:
            pending_on_disk = next(self.extension_inbox.glob("*.json"), None) is not None
        except OSError:
            pass
        if self.worker or self.premiere_import_pending or self.extension_jobs or pending_on_disk:
            self.last_activity_at = time.monotonic()
        elif time.monotonic() - self.last_activity_at >= self.IDLE_SHUTDOWN_SECONDS:
            self.tk.setvar("::clipflow_agent_running", "idle")
            return
        self.after(5000, self._idle_shutdown_check)

    def _event(self, event: str, payload: object) -> None:
        if event == "progress":
            value, speed, eta = payload  # type: ignore[misc]
            self.current_progress = float(value)
            self.last_activity_at = time.monotonic()
            self.bar["value"] = value
            self.percent.configure(text=f"{value:.0f} %")
            self.status.set("Téléchargement en cours")
            transfer = f"{speed} · reste {eta}" if eta and eta != "<NA>" else str(speed)
            self.details.set(" · ".join(part for part in (self.format_details, transfer) if part))
            write_extension_status(self.active_job_id, "running", self.current_progress, self.details.get())
        elif event == "format":
            parts = list(payload)  # type: ignore[arg-type]
            height = parts[0] if parts else "?"
            codec = parts[1] if len(parts) > 1 else "codec original"
            bitrate = parts[2] if len(parts) > 2 else ""
            language = parts[3] if len(parts) > 3 else ""
            rate = f"{bitrate} kb/s" if bitrate not in {"", "NA", "None"} else "débit source"
            audio = f"audio original {language}" if language not in {"", "NA", "None"} else "audio original"
            self.format_details = f"Flux source {height}p · {codec} · {audio} · {rate} · sans conversion"
            self.details.set(self.format_details)
        elif event == "file":
            self.last_file = Path(str(payload))
        elif event == "existing":
            self.result_was_existing = True
            self.status.set("Vidéo déjà téléchargée")
            self.details.set(Path(str(payload)).name)
        elif event == "log":
            line = str(payload)
            self.logs.append(line)
            self.logs = self.logs[-8:]
            try:
                with self.log_file.open("a", encoding="utf-8") as log:
                    log.write(line + "\n")
            except OSError:
                pass
        elif event == "phase":
            self.details.set(str(payload))
            write_extension_status(self.active_job_id, "running", max(1, self.current_progress), str(payload))
        elif event == "retry":
            self.status.set("Connexion rétablie · nouvel essai…")
            self.details.set(f"Reprise automatique {payload}/2 · le fichier partiel est conservé")
            write_extension_status(self.active_job_id, "running", max(1, self.current_progress), self.details.get())
        elif event == "retry_quality":
            self.status.set("Recherche de la meilleure qualité…")
            self.details.set(f"YouTube n’a renvoyé que la basse définition · nouvelle analyse {payload}/2")
            write_extension_status(self.active_job_id, "running", max(1, self.current_progress), self.details.get())
        elif event == "quality_fallback":
            self.status.set("Qualité maximale de la source…")
            self.details.set("Aucun flux HD disponible après vérification · téléchargement du meilleur flux proposé")
            write_extension_status(self.active_job_id, "running", max(1, self.current_progress), self.details.get())
        elif event == "needs_cookies":
            browser_name = str(payload).capitalize()
            write_extension_status(
                self.active_job_id,
                "error",
                self.current_progress,
                f"Connexion au site requise dans {browser_name}.",
            )
            if self.worker:
                self.worker.allow_browser_cookies(False)
            return
        elif event == "retry_with_cookies":
            browser_name = str(payload).capitalize()
            self.status.set(f"Nouvel essai avec la session {browser_name}…")
            self.details.set("Autorisation mémorisée sur ce Mac · session utilisée temporairement")
            write_extension_status(self.active_job_id, "running", max(1, self.current_progress), self.details.get())
        elif event == "finished":
            self.current_progress = 100.0
            self.bar["value"] = 100
            self.percent.configure(text="100 %")
            if self.completion_sound_enabled and not self.result_was_existing and self.last_file is not None:
                play_completion_sound()
            if self.active_premiere_project is not None:
                if self.last_file is None:
                    self._finish_premiere_import(
                        False,
                        "Le téléchargement est terminé, mais son fichier final est introuvable.",
                    )
                    return
                try:
                    result_path = queue_premiere_import(
                        self.last_file,
                        self.active_premiere_project,
                        self.active_job_id,
                        bridge_path=self.active_premiere_bridge,
                    )
                except (OSError, ValueError) as error:
                    self._finish_premiere_import(False, str(error))
                    return
                self.worker = None
                self.premiere_import_pending = True
                self.cancel.configure(state="disabled")
                self.status.set("Import dans Premiere Pro…")
                self.details.set(self.last_file.name)
                write_extension_status(
                    self.active_job_id,
                    "running",
                    99,
                    "Téléchargé · import dans Premiere Pro…",
                )
                threading.Thread(
                    target=wait_for_premiere_import,
                    args=(result_path, self.events),
                    daemon=True,
                ).start()
                return
            self.status.set(
                "Vidéo déjà présente dans le dossier"
                if self.result_was_existing
                else "Téléchargement terminé"
            )
            self.details.set(self.last_file.name if self.last_file else "Fichier prêt")
            write_extension_status(self.active_job_id, "complete", 100, self.details.get())
            self._reset()
            if self.last_file: self.open_result.configure(state="normal")
        elif event == "premiere_import":
            success, message = payload  # type: ignore[misc]
            self._finish_premiere_import(success, str(message))
        elif event == "cancelled":
            self.status.set("Téléchargement annulé")
            self.details.set("Vous pouvez recommencer")
            write_extension_status(self.active_job_id, "cancelled", self.current_progress, "Téléchargement annulé")
            self._reset()
        elif event == "timeout":
            self.status.set("Validation interrompue")
            self.details.set("Aucune réponse après trois essais automatiques")
            write_extension_status(self.active_job_id, "error", self.current_progress, self.details.get())
            self._reset()
        elif event in {"failed", "error"}:
            details = "\n".join(self.logs[-5:]) or str(payload)
            self.status.set("Échec du téléchargement")
            self.details.set("Vous pouvez réessayer sans fermer ClipFlow")
            if drm_protected_output(details):
                concise_error = "Cette source est protégée par DRM."
            elif authentication_required_output(details):
                concise_error = "Connectez-vous au site dans Chrome, puis réessayez."
            else:
                concise_error = "Le téléchargement n’a pas pu être terminé."
            write_extension_status(self.active_job_id, "error", self.current_progress, concise_error)
            self._reset()
            return

    def _reset(self) -> None:
        self.worker = None
        self.premiere_import_pending = False
        self.active_job_id = None
        self.active_premiere_project = None
        self.active_premiere_bridge = None
        self.background_job = False
        self.completion_sound_enabled = True
        self.last_activity_at = time.monotonic()
        self.download.configure(state="normal")
        self.cancel.configure(state="disabled")

    def _finish_premiere_import(self, success: bool | None, message: str) -> None:
        job_id = self.active_job_id
        background_job = self.background_job
        downloaded = self.last_file is not None and self.last_file.is_file()
        if success is True:
            self.status.set("Ajouté à Premiere Pro")
            self.details.set(self.last_file.name if self.last_file else "Média importé")
            write_extension_status(job_id, "complete", 100, "Téléchargé et ajouté à Premiere Pro")
        elif success is None and downloaded:
            self.status.set("Téléchargement terminé")
            self.details.set(message or "Fichier prêt dans Médias ClipFlow")
            write_extension_status(job_id, "complete", 100, self.details.get())
        else:
            self.status.set("Téléchargé · import Premiere impossible")
            self.details.set(message or "Le fichier reste disponible dans Médias ClipFlow")
            write_extension_status(
                job_id,
                "complete" if downloaded else "error",
                100 if downloaded else self.current_progress,
                self.details.get(),
            )
        self._reset()
        if self.last_file:
            self.open_result.configure(state="normal")

    def _reveal(self) -> None:
        target = self.last_file or Path(self.folder.get())
        try:
            subprocess.Popen(["open", "-R", str(target)] if target.is_file() else ["open", str(target)])
        except OSError as error:
            messagebox.showerror(APP_NAME, str(error))

    def _close(self) -> None:
        if self.worker: self.worker.cancel()
        self.tk.setvar("::clipflow_agent_running", "stopped")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--tubesave-yt-dlp":
        if frozen_application():
            import yt_dlp_plugins.extractor.ytjsc  # noqa: F401
            os.environ["YTDLP_NO_PLUGINS"] = "1"
        import yt_dlp

        yt_dlp.main(sys.argv[2:])
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--tubesave-native-host":
        import native_host

        return native_host.main()
    TubeSaveApp().run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
