#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
project_dir="${script_dir:h}"
backup_date="$(date +%Y-%m-%d)"
output_path="${1:-${project_dir}/ClipFlow-PROJET-SAUVEGARDE-${backup_date}.zip}"
staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/clipflow-project.XXXXXX")"
archive_root="${staging_dir}/ClipFlow Projet"

cleanup() {
  rm -rf "${staging_dir}"
}
trap cleanup EXIT

mkdir -p "${archive_root}/distribution"

rsync -a \
  --exclude '.DS_Store' \
  --exclude '.tools/' \
  --exclude 'work/' \
  --exclude 'outputs/ClipFlow-complet-*.zip' \
  --exclude 'outputs/ClipFlow-Installer.dmg' \
  --exclude 'outputs/ytdlp/.venv/' \
  --exclude 'outputs/ytdlp/build/' \
  --exclude 'outputs/ytdlp/dist/' \
  --exclude '**/__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'ClipFlow-PROJET-SAUVEGARDE-*.zip' \
  "${project_dir}/" "${archive_root}/"

latest_distribution="$(find "${project_dir}/outputs" -maxdepth 1 -type f -name 'ClipFlow-complet-v*.zip' -print | sort -V | tail -n 1)"
if [[ -z "${latest_distribution}" ]]; then
  print -u2 "Aucune distribution ClipFlow-complet-v*.zip n'a été trouvée."
  exit 1
fi

cp -p "${latest_distribution}" "${archive_root}/distribution/"
if [[ -f "${project_dir}/outputs/ClipFlow-Installer.dmg" ]]; then
  cp -p "${project_dir}/outputs/ClipFlow-Installer.dmg" "${archive_root}/distribution/"
fi
mkdir -p "${output_path:h}"
rm -f "${output_path}"
ditto -c -k --sequesterRsrc --keepParent "${archive_root}" "${output_path}"
unzip -tq "${output_path}"

print "Sauvegarde créée et vérifiée :"
print "${output_path}"
shasum -a 256 "${output_path}"
