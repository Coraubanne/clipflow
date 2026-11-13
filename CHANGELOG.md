# Changelog

All notable user-facing changes are documented here.

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
