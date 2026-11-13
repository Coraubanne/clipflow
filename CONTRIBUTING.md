# Contributing to ClipFlow

Thank you for helping improve ClipFlow. Contributions should keep the product focused on reliable, authorized media workflows for editors and audiovisual research teams.

## Before opening an issue

- Search existing issues and test the latest release.
- Do not post authentication cookies, signed media URLs, account data or copyrighted media samples.
- For a site compatibility report, provide the public page URL, macOS and ClipFlow versions, expected result and sanitized error text.
- Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
- Requests to bypass DRM, paywalls or access controls are outside the project scope and will be closed.

## Development workflow

1. Fork the repository and create a focused branch.
2. Keep changes small and document user-visible behaviour in English and French where relevant.
3. Run the full test suite:

   ```bash
   PYTHONPATH=outputs/ytdlp outputs/ytdlp/.venv/bin/python -m unittest discover -s outputs/ytdlp/tests
   ```

4. Do not commit generated applications, release archives, browser profiles, cookies, logs or downloaded media.
5. Open a pull request explaining the problem, the solution, the tests and any privacy or compatibility impact.

By contributing, you agree that your contribution may be distributed under the repository's MIT License.
