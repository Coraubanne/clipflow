# Third-party notices

ClipFlow's original code is licensed under MIT. The application also uses independent third-party projects under their own terms.

| Component | Purpose | Licence / source |
| --- | --- | --- |
| yt-dlp | Media extraction and download engine | [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE), [source](https://github.com/yt-dlp/yt-dlp) |
| FFmpeg 7.1 | Media inspection, merging and conversion | The bundled build reports GPL v2 or later. [FFmpeg licence](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md), [7.1 source](https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz) |
| imageio-ffmpeg | Python wrapper and FFmpeg binary provider | [BSD-2-Clause](https://github.com/imageio/imageio-ffmpeg/blob/main/LICENSE), [source](https://github.com/imageio/imageio-ffmpeg) |
| curl-cffi | Browser-compatible HTTP transport | [MIT](https://github.com/lexiforest/curl_cffi/blob/main/LICENSE), [source](https://github.com/lexiforest/curl_cffi) |
| certifi | CA certificate bundle | [MPL-2.0](https://github.com/certifi/python-certifi/blob/master/LICENSE), [source](https://github.com/certifi/python-certifi) |
| PyInstaller | macOS application packaging | GPL-2.0-or-later with bootloader exception, [source](https://github.com/pyinstaller/pyinstaller) |

The distributed FFmpeg executable is invoked as a separate process. Its complete build configuration can be displayed with `ffmpeg -version`; it includes `--enable-gpl`. The binary is supplied unchanged through `imageio-ffmpeg`. FFmpeg and its linked libraries retain their original copyrights and licence obligations.

Python package metadata and licence files are preserved inside the application bundle where provided by upstream distributions. This summary is not a replacement for those licence texts.
