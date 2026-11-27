"""Choose how to put a downloaded 4K source into an editable MP4."""

import re
import subprocess

from yt_dlp.globals import postprocessors
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError, FFmpegVideoConvertorPP


STREAM = re.compile(r"^\s*Stream #0:\d+[^\n]*?: (Video|Audio): (\w+)([^\n]*)", re.MULTILINE)
LOSSLESS_H264 = ("-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-fps_mode", "passthrough", "-xerror")
LOSSLESS_UNSUPPORTED = "ClipFlow 4K lossless: unsupported tracks"


def lossless_track_options(stream_info: str) -> tuple[str, ...]:
    streams = STREAM.findall(stream_info)
    video = [(codec, details) for kind, codec, details in streams if kind == "Video"]
    if len(video) != 1:
        raise FFmpegPostProcessorError(LOSSLESS_UNSUPPORTED)
    codec, details = video[0]
    if not re.search(r"\b\d{4}x2160\b", details):
        raise FFmpegPostProcessorError(LOSSLESS_UNSUPPORTED)
    if any(kind == "Audio" and codec != "aac" for kind, codec, _ in streams):
        raise FFmpegPostProcessorError(LOSSLESS_UNSUPPORTED)
    if (
        codec == "hevc" and re.search(r"\(Main(?: 10)?\)", details)
        and re.search(r"\byuv420p(?:10le)?\b", details)
    ):
        return ("-c:v", "copy", "-tag:v", "hvc1", "-c:a", "copy")
    if not re.search(r"\byuv420p\b", details):
        raise FFmpegPostProcessorError(LOSSLESS_UNSUPPORTED)
    return ("-c:v", "copy", "-c:a", "copy") if codec == "h264" else (*LOSSLESS_H264, "-c:a", "copy")


class ClipFlow4KPP(FFmpegVideoConvertorPP):
    def __init__(self, downloader=None):
        super().__init__(downloader, preferedformat="mp4")

    def run_ffmpeg(self, path, out_path, opts, **kwargs):
        try:
            # FFmpeg prints stream metadata before requesting an output file.
            probe = subprocess.run(
                [self.executable, "-hide_banner", "-i", self._ffmpeg_filename_argument(path)],
                capture_output=True, text=True, timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            stream_info = ""
        else:
            stream_info = probe.stderr

        track_options = lossless_track_options(stream_info)
        if track_options[:2] == ("-c:v", "copy"):
            self.to_screen("Copying compatible 4K video into MP4 without re-encoding")
        return super().run_ffmpeg(path, out_path, [*opts, *track_options], **kwargs)


def register_clipflow_4k() -> None:
    postprocessors.value["ClipFlow4KPP"] = ClipFlow4KPP
