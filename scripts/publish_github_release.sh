#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
project_dir="${script_dir:h}"
cd "${project_dir}"

gh_bin="$(command -v gh 2>/dev/null || true)"
if [[ -z "${gh_bin}" ]]; then
  gh_bin="$(find "${project_dir}/.tools" -type f -path '*/bin/gh' -print 2>/dev/null | sort -V | tail -n 1)"
fi

if [[ -z "${gh_bin}" ]]; then
  print -u2 "GitHub CLI (gh) n'est pas installé. Installez-le ou publiez avec la connexion GitHub de Codex."
  exit 1
fi

"${gh_bin}" auth status >/dev/null

release_number="$(sed -n 's/.*"release"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' PROJECT_VERSION.json | head -n 1)"
if [[ -z "${release_number}" ]]; then
  print -u2 "Le numéro release manque dans PROJECT_VERSION.json."
  exit 1
fi

tag="${1:-v${release_number}}"
archive="outputs/ClipFlow-complet-v${release_number}.zip"
checksum="${archive}.sha256"
release_notes="docs/releases/v${release_number}.md"

if [[ ! -f "${archive}" ]]; then
  print -u2 "Archive introuvable : ${archive}"
  exit 1
fi

archive_name="${archive:t}"
archive_hash="$(shasum -a 256 "${archive}" | awk '{print $1}')"
print "${archive_hash}  ${archive_name}" > "${checksum}"

if [[ -n "$(git status --porcelain)" ]]; then
  print -u2 "Le dépôt contient des changements non enregistrés. Faites un commit avant la publication."
  exit 1
fi

if ! git rev-parse "${tag}" >/dev/null 2>&1; then
  git tag -a "${tag}" -m "ClipFlow ${tag}"
fi

git push origin main
git push origin "${tag}"

if "${gh_bin}" release view "${tag}" >/dev/null 2>&1; then
  "${gh_bin}" release upload "${tag}" "${archive}" "${checksum}" --clobber
else
  if [[ -f "${release_notes}" ]]; then
    "${gh_bin}" release create "${tag}" "${archive}" "${checksum}" \
      --title "ClipFlow ${tag}" \
      --notes-file "${release_notes}"
  else
    "${gh_bin}" release create "${tag}" "${archive}" "${checksum}" \
      --title "ClipFlow ${tag}" \
      --notes "Version complète de ClipFlow. Le ZIP contient l’application macOS, l’extension Chrome et le module Premiere Pro."
  fi
fi

# gh creates a temporary draft while uploading large assets. If its final
# publication request is skipped or interrupted, make the release visible
# instead of silently leaving a complete ZIP under an untagged draft URL.
if [[ "$("${gh_bin}" release view "${tag}" --json isDraft --jq '.isDraft')" == "true" ]]; then
  "${gh_bin}" release edit "${tag}" \
    --draft=false \
    --tag "${tag}" \
    --title "ClipFlow ${tag}"
fi

print "Version ${tag} publiée avec ${archive} et son empreinte SHA-256."
