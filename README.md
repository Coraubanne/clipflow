# ClipFlow

<img src="outputs/ytdlp/assets/ClipFlow.png" width="88" align="right" alt="ClipFlow icon">

Collect web video for editing, archival research and documentary production. ClipFlow finds compatible media in your browser and saves it on your Mac. For Premiere Pro workflows, it can also import the finished file into your project.

**[Download ClipFlow for macOS](https://github.com/Coraubanne/clipflow/releases/latest/download/ClipFlow-Installer.dmg)** · [Release notes](https://github.com/Coraubanne/clipflow/releases/latest) · [Français](README.fr.md)

Apple Silicon · macOS 12+ · Chrome or Firefox 140+

## Install

1. Download `ClipFlow-Installer.dmg`, open it and run **Installer ClipFlow**. The installer adds the background app, the browser files and the Creator Bridge panel.
2. Load ClipFlow in your browser.

   | Browser | Setup |
   | --- | --- |
   | Google Chrome | Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked** and select `~/Documents/ClipFlow/ClipFlow Chrome`. |
   | Firefox | Open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on** and select `~/Documents/ClipFlow/ClipFlow-Firefox-unsigned.xpi`. Load it again after quitting and reopening Firefox. |

GitHub’s **Code → Download ZIP** option downloads the source code. Use the DMG for installation. The Firefox extension is currently distributed as an unsigned test build. [Mozilla’s temporary installation guide](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/)

## Download a video

1. Open the video’s page and start playback if ClipFlow needs to detect the stream.
2. Open the ClipFlow toolbar popup, check the thumbnail and choose **Download**.
3. Find the file in **Downloads** or change the destination from the settings. Use **Audio only** to save an MP3.

ClipFlow looks for the highest quality it can deliver as MP4, including 4K where a compatible stream is available. It prioritizes the original audio track when the source identifies it and asks before converting a detected WebM. Finished files use a name such as `Channel — Video title [identifier].mp4`.

Cards show the detected resolution. When ClipFlow finds a 4K MKV or separate 4K streams it can merge into MKV, a separate card downloads and converts the video to 2160p MP4. The finished file has a `4K` suffix. The progress panel shows conversion progress and lets you cancel queued or active jobs.

Site compatibility depends on the player and the media formats it exposes. Use ClipFlow for media you’re authorized to download. DRM-protected streams are unsupported. [Usage and legal notes](LEGAL.md)

## Send a file to Premiere Pro

Open a saved project in **Premiere Pro 25.6 or later**, then open **Window → UXP Plug-ins → Creator Bridge**. Choose **Premiere Pro** as the ClipFlow destination before starting the download. ClipFlow saves the file next to the project and asks Creator Bridge to import it into the Project panel. [Creator Bridge](https://github.com/Coraubanne/CreatorBridge)

## Updates

Open **Settings → Check for updates** in ClipFlow. The companion verifies the GitHub archive’s SHA-256 checksum before installing. Selecting Premiere Pro as the destination also enables a separate Creator Bridge check. For Firefox, download the current XPI from the release page and load it as a temporary add-on. [Version history](CHANGELOG.md)

## Project and support

- [Report a reproducible issue](https://github.com/Coraubanne/clipflow/issues) · [Contribution policy](CONTRIBUTING.md)
- [Privacy](PRIVACY.md) · [Security reports](SECURITY.md)
- [Publication and backups](GITHUB.md) · [Test workflow](https://github.com/Coraubanne/clipflow/actions/workflows/test.yml)
- [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

<details>
<summary>Build and test</summary>

The Firefox package is built from the shared browser source under `outputs/ClipFlow Chrome`. The macOS companion uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) and FFmpeg.

```sh
git submodule update --init
cd outputs/ytdlp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests
.venv/bin/pyinstaller --clean --noconfirm TubeSave.spec
```

</details>
