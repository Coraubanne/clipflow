#!/bin/zsh

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 est nécessaire pour installer ClipFlow."
  read -r "?Appuyez sur Entrée pour fermer…"
  exit 1
fi

echo "Installation et mise à jour de ClipFlow…"
python3 -m venv .venv || exit 1
.venv/bin/python -m pip install --upgrade -r requirements.txt
if [[ $? -ne 0 ]]; then
  echo "L’installation a échoué. Vérifiez votre connexion Internet."
  read -r "?Appuyez sur Entrée pour fermer…"
  exit 1
fi

.venv/bin/python -m pip uninstall -y yt-dlp-getpot-wpc nodriver >/dev/null 2>&1
touch .venv/.tubesave-deps-v9
echo "Installation terminée."
.venv/bin/python app.py
