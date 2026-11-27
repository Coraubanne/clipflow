# Changelog

All notable user-facing changes are documented here.

## 2.18.0 — 2026-11-27

- Added cancellation from the extension for queued downloads, active transfers and conversions.
- Displayed measured FFmpeg progress when converting video or audio.
- Showed detected resolutions and gave the standard MP4 and optional 4K conversion separate cards.

## 2.17.1 — 2026-11-27

- Show the MP4 conversion stage in the extension after the download finishes.

## 2.17.0 — 2026-11-27

- Added an optional 4K download for MKV sources and compatible split streams. ClipFlow converts the result to a 2160p MP4 after confirmation.

## 2.16.3 — 2026-11-27

- Version-only release to test the updater.

## 2.16.2 — 2026-11-26

- Fixed an encoding error during automatic update on Macs with binary application metadata.
- Kept unrelated application metadata from blocking ClipFlow duplicate cleanup.

## 2.16.1 — 2026-11-26

- Added a Firefox extension backed by the same macOS companion used by Chrome.
- Added a separate Creator Bridge update check when Premiere Pro is selected as the destination.
- Serialized shared plugin installation and cleanup with a common lock.
- Kept the update ZIP compatible with earlier ClipFlow installers.

## 2.14.0 — 2026-11-24

- Added verified duplicate cleanup after installation, automatic update and background startup.
- Kept only the newest validated ClipFlow application and Premiere bridge while preserving newer copies and unrelated applications.
- Removed inactive legacy extension folders only when their ClipFlow identity and version are verified; active Chrome profile paths are never removed.
- Removed superseded local ZIP/checksum build artifacts only after the replacement distribution and installer pass their integrity checks.

## 2.13.3 — 2026-11-19

- Prevented multiple background download engines from running concurrently and corrupting otherwise valid downloads near completion.
- Recovered unfinished extension jobs left behind by a previous crash while preserving requests that are still genuinely queued.

## 2.13.2 — 2026-11-16

- Fixed direct MP4 naming on sites such as Hostinger: finished files now use the originating website and human page title instead of an opaque CDN hostname and identifier.
- Confirmed Hostinger's embedded Cloudflare Stream MP4 remains an original H.264 source with no slow video conversion.

## 2.13.1 — 2026-11-13

- Removed browser notification counters such as `(168)` or `[168]` from displayed media titles and finished filenames.
- Added a single-file macOS installer image and a prominent user download button, while retaining the technical source archive and updater assets separately.

## 2.13.0 — 2026-11-13

- Turned settings into a dedicated view that temporarily replaces video results and file options until the gear is clicked again.
- Made Amazon video thumbnails reliable by locally inlining the public poster image exposed by each player.
- Kept the Amazon thumbnail workaround permission-free and memory-only.

## 2.12.1 — 2026-11-13

- Invalidated the cached update status whenever the installed Chrome extension version changes.
- Prevented the settings panel from displaying the previous ClipFlow version after a successful update.

## 2.12.0 — 2026-11-13

- Redesigned the Chrome extension around a clearer visual hierarchy, larger controls and more readable video cards.
- Added a restrained translucent monochrome treatment with soft blue gradients, native dark mode and reduced-motion support.
- Enlarged thumbnails and added a visual progress track while preserving the numeric percentage.
- Simplified destinations to Downloads, Premiere Pro and a custom folder; legacy Movies or Desktop choices migrate to Downloads.
- Updated yt-dlp, FFmpeg packaging and the Brotli, Pillow and Setuptools dependencies to their current security-fixed versions.

## 2.11.1 — 2026-11-13

- Published a maintenance release with no functional change to validate the complete in-extension update workflow.

## 2.11.0 — 2026-11-13

- Standardized finished filenames as `Channel — Video title [identifier].extension`.
- Made the channel mandatory, with creator, website domain and extractor fallbacks for non-YouTube sources.
- Applied the same stable naming logic to direct HLS/DASH streams and audio-only downloads.

## 2.10.0 — 2026-11-13

- Reorganized detected-video cards around larger, clearer 16:10 thumbnails.
- Added local video-frame capture and visible-player cropping when sites expose only a generic logo.
- Added a layered thumbnail fallback for YouTube, HTML video posters, structured metadata and embedded players.
- Kept captured preview images temporary and local to the open extension popup.

## 2.9.2 — 2026-11-13

- Removed the explanatory sentence below the extension-language selector for a cleaner settings panel.
- Added a thumbnail to each detected-video card when the page or player exposes one.
- Published the first release using the semantic `vMAJOR.MINOR.PATCH` tag format.

## 2.9.1 — 2026-11-13

- Gave the expanded settings area a distinct blue treatment while keeping the compact Apple-style layout.
- Clarified that the language selector controls the extension interface, not video audio.
- Added the extension version at the bottom of the popup.
- Made YouTube explicitly prefer tracks marked as original audio, with a safe fallback when metadata is missing.
- Started the transition from legacy numeric releases to professional semantic versioning.

## v68 — 2026-11-13

- Added an Automatic, Français and English interface-language selector to the Chrome extension.
- Localized video detection, download progress, errors, update controls and native-host responses.
- Added localized Chrome extension metadata while preserving existing user settings during migration.

## v67 — 2026-11-13

- Opened the project for public distribution with professional English and French documentation.
- Allowed the updater to check and install public GitHub releases without an account.
- Added responsible-use, privacy, security, contribution and third-party notices.
- Added continuous tests and structured GitHub issue forms.

## v66 — 2026-11-13

- Added secure automatic updates for the macOS app, Chrome extension and Premiere Pro panel.
- Added SHA-256 release verification, safe archive extraction, component validation and transactional rollback.
- Added a daily update check and a manual update control in the Chrome extension.

Earlier release history remains available in [GitHub Releases](https://github.com/Coraubanne/clipflow/releases).
