# Privacy

ClipFlow is designed as a local application.

- No ClipFlow analytics or advertising service is contacted.
- No browsing history or downloaded media is uploaded to a ClipFlow server.
- The Chrome and Firefox extensions inspect the active page after the user opens ClipFlow. A persistent permission limited to TF1 is used to discover its media streams. ClipFlow may reuse TF1's media authorization header in a request to the same TF1 service.
- When a site supplies no useful thumbnail, the extension may capture and crop the visible video area after the user opens ClipFlow. This image stays in the popup's temporary memory; it is not saved, logged or uploaded by ClipFlow.
- When you download a video, the extension sends the selected media URL, the source page URL when needed, and the media title to the ClipFlow macOS companion. The companion contacts the source hosts needed to download the chosen media.
- GitHub is contacted to check for public ClipFlow releases.
- Browser-session data may be read locally when a compatible source requires authentication and the relevant authorization is available. ClipFlow does not create a permanent cookie export.
- Temporary job state and logs stay on the Mac and can contain source URLs. Users should treat logs as potentially sensitive.

Third-party websites, GitHub, Google Chrome and Adobe products operate under their own privacy policies. Review the source site's policy before downloading media.
