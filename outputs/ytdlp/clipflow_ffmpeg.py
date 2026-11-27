"""Choose how to put a downloaded 4K source into an editable MP4."""

import re
import subprocess

from yt_dlp.globals import postprocessors
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError, FFmpegVideoConvertorPP


EDITABLE_H264 = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p")
EDITABLE_AAC = ("-c:a", "aac", "-b:a", "256k")
STREAM = re.compile(r"^\s*Stream #0:\d+[^\n]*?: (Video|Audio): (\w+)([^\n]*)", re.MULTILINE)


def mp4_track_options(stream_info: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    video = []
    audio = []
    for stream_type, codec, details in STREAM.findall(stream_info):
        if stream_type == "Audio":
            audio.append(codec)
        else:
            video.append((codec, details))

    video_options = EDITABLE_H264
    if video and all(codec == "h264" and re.search(r"\byuv420p\b", details) for codec, details in video):
        video_options = ("-c:v", "copy")
    elif video and all(
        codec == "hevc" and re.search(r"\(Main(?: 10)?\)", details)
        and re.search(r"\byuv420p(?:10le)?\b", details) for codec, details in video
    ):
        video_options = ("-c:v", "copy", "-tag:v", "hvc1")

    audio_options = ("-c:a", "copy") if audio and all(codec == "aac" for codec in audio) else EDITABLE_AAC
    return video_options, audio_options


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
            video, audio = mp4_track_options(probe.stderr)
        except (OSError, subprocess.TimeoutExpired):
            video, audio = EDITABLE_H264, EDITABLE_AAC

        if video != EDITABLE_H264 or audio != EDITABLE_AAC:
            try:
                if video != EDITABLE_H264:
                    self.to_screen("Copying compatible 4K video into MP4 without re-encoding")
                return super().run_ffmpeg(path, out_path, [*opts, *video, *audio], **kwargs)
            except FFmpegPostProcessorError:
                self.report_warning("Compatible MP4 stream copy failed; retrying with H.264 and AAC")

        return super().run_ffmpeg(path, out_path, [*opts, *EDITABLE_H264, *EDITABLE_AAC], **kwargs)


def register_clipflow_4k() -> None:
    postprocessors.value["ClipFlow4KPP"] = ClipFlow4KPP
