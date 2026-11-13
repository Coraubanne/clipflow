# Security policy

## Supported version

Security fixes target the latest published ClipFlow release. Older releases should be upgraded before a report is reproduced.

## Private reporting

Please use **GitHub → Security → Report a vulnerability** to open a private security advisory. Do not disclose a vulnerability in a public issue before a fix is available.

Include:

- the affected ClipFlow version and macOS version;
- clear reproduction steps;
- the security impact and affected data;
- a minimal proof of concept with secrets, cookies and personal data removed.

The project aims to acknowledge a complete report within seven days. Timelines for validation and remediation depend on severity and upstream dependencies.

## Scope

Relevant reports include unsafe native messaging, update integrity failures, path traversal, command injection, unintended browser-session exposure and local privilege issues.

Site extractor breakage, unavailable videos and requests to bypass DRM are not security vulnerabilities. Use a regular issue for non-sensitive compatibility bugs.
