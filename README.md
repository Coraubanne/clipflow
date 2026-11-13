<p align="center">
  <img src="outputs/ytdlp/assets/ClipFlow.png" width="112" alt="ClipFlow icon">
</p>

<h1 align="center">ClipFlow</h1>

<p align="center">
  Media acquisition for video editors, audiovisual researchers and documentary teams.
</p>

<p align="center">
  <a href="https://github.com/Coraubanne/clipflow/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/Coraubanne/clipflow?style=flat-square"></a>
  <a href="https://github.com/Coraubanne/clipflow/actions/workflows/test.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/Coraubanne/clipflow/test.yml?branch=main&style=flat-square&label=tests"></a>
  <img alt="macOS Apple Silicon" src="https://img.shields.io/badge/macOS-Apple%20Silicon-111111?style=flat-square&logo=apple">
  <img alt="Chrome Manifest V3" src="https://img.shields.io/badge/Chrome-Manifest%20V3-4285F4?style=flat-square&logo=googlechrome&logoColor=white">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-2ea44f?style=flat-square"></a>
</p>

<p align="center">
  <strong>English</strong> · <a href="README.fr.md">Français</a>
</p>

ClipFlow turns web video discovery into a clean post-production workflow. Its Chrome extension identifies compatible media on the active page, its local macOS engine retrieves the best compatible source with [yt-dlp](https://github.com/yt-dlp/yt-dlp), and its optional Premiere Pro panel can place the finished file next to the active project and import it automatically.

It is designed for video editors, audiovisual documentalists, archive researchers, journalists and production teams who need to collect media they are authorized to use without breaking their editorial flow.

## Highlights

- Detects compatible page videos, direct media, HLS/DASH streams and embedded players.
- Shows a large thumbnail beside each detected video and locally captures the visible player when a site exposes only a generic image.
- Selects the highest available MP4/H.264 quality, including 4K when a compatible source exists.
- Names every finished file `Channel — Video title [identifier].mp4`, with the creator or website as a reliable fallback.
- Preserves the original audio language whenever the source exposes it.
- Labels the interface language separately from video audio and displays the installed extension version.
- Offers an audio-only MP3 mode.
- Keeps temporary fragments in a hidden workspace and exposes only completed files.
- Runs as an invisible macOS background agent; Chrome is the main interface.
- Offers an automatic, French or English interface from the extension settings.
- Saves beside an active Premiere Pro project and requests automatic import through the optional UXP panel.
- Checks GitHub Releases for updates, verifies SHA-256 integrity, then updates the app, extension and Premiere panel together.
- Contains no telemetry or advertising.

## Workflow

| Stage | Component | Role |
| --- | --- | --- |
| Discover | Chrome extension | Inspects only the active tab after the user opens ClipFlow. |
| Retrieve | macOS background app | Uses yt-dlp and FFmpeg to download, merge or convert compatible media. |
| Organize | Local filesystem | Writes the final file to Downloads, Movies, Desktop, a chosen folder or the Premiere project folder. |
| Edit | Premiere Pro panel | Optionally imports the completed file into the active project. |

## Install

ClipFlow currently targets Apple Silicon Macs and is distributed outside the Mac App Store and Chrome Web Store.

1. Download the latest `ClipFlow-complet-v*.zip` from [GitHub Releases](https://github.com/Coraubanne/clipflow/releases/latest).
2. Move `ClipFlow.app` to `/Applications`. On first launch, Control-click the app, choose **Open**, then confirm macOS' prompt.
3. Keep the `ClipFlow Chrome` folder in a permanent location. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select that folder.
4. Pin ClipFlow to the Chrome toolbar. Open a page containing a video, start playback if necessary, then open ClipFlow and select **Download**.
5. Optional: install `ClipFlow Premiere.ccx`, then keep **Window → UXP Plugins → ClipFlow** open while using the Premiere destination.

After the first installation, use **Settings → Check for updates** in the Chrome extension. Public releases can be checked and installed without a GitHub account.

## Compatibility

| Requirement | Supported configuration |
| --- | --- |
| Operating system | macOS 12 or later |
| Processor | Apple Silicon (ARM64) |
| Browser | Google Chrome with Manifest V3 support |
| Premiere integration | Adobe Premiere Pro 25.6 or later |
| Media | Public or otherwise authorized, non-DRM sources supported by yt-dlp or exposed as compatible web media |

Site compatibility changes over time and depends partly on upstream extractors. A website being visible in a browser does not guarantee that its media can be downloaded.

## Privacy and security

ClipFlow processes URLs and media locally. It does not operate an analytics service, upload browsing history or sell usage data. The extension uses active-tab access and a narrowly scoped TF1 network permission. Browser session access is used only when a compatible site requires authentication and ClipFlow has the relevant local authorization.

Release archives are published with SHA-256 checksums. The updater rejects mismatched archives, unsafe ZIP paths, unexpected component identities and invalid application signatures. See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Responsible use

ClipFlow is a general-purpose media workflow tool. It does not decrypt or bypass DRM. Use it only for media you own, media in the public domain, media covered by an applicable licence or exception, or media you otherwise have permission to download. You remain responsible for copyright, privacy, contractual and platform-rule compliance in your jurisdiction.

ClipFlow is not affiliated with or endorsed by YouTube, Google, Adobe, TF1, Vimeo, Dailymotion or any other platform. Read [LEGAL.md](LEGAL.md) before use.

## Development

```bash
cd outputs/ytdlp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests
.venv/bin/pyinstaller --clean --noconfirm TubeSave.spec
```

The repository contains the macOS engine, Chrome extension, Premiere UXP panel, tests and release tooling. Contributions are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md).

ClipFlow follows semantic versioning for user-facing releases. Version 2.9.1 is distributed through one final legacy bridge tag so installations on v68 can migrate without breaking automatic updates; later tags use the `vMAJOR.MINOR.PATCH` format directly.

## Credits

ClipFlow is built around [yt-dlp](https://github.com/yt-dlp/yt-dlp) and uses FFmpeg for compatible media processing. Third-party projects retain their own licences and trademarks; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

ClipFlow's original source code is available under the [MIT License](LICENSE). Bundled third-party components remain governed by their respective licences.
