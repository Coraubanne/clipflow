#!/bin/zsh

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

if [[ ! -x ".venv/bin/python" ]] || [[ ! -f ".venv/.tubesave-deps-v9" ]] || ! .venv/bin/python -c 'import importlib.metadata as m; import yt_dlp, certifi, imageio_ffmpeg; m.version("yt-dlp-ejs"); m.version("yt-dlp-apple-webkit-jsi")' >/dev/null 2>&1; then
  echo "Première utilisation ou mise à jour nécessaire…"
  zsh installer.command
  exit $?
fi

.venv/bin/python app.py
