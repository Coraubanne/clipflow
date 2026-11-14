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

release_tag="$(sed -n 's/.*"release_tag"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' PROJECT_VERSION.json | head -n 1)"
product_version="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' PROJECT_VERSION.json | head -n 1)"
if [[ -z "${release_tag}" || -z "${product_version}" ]]; then
  print -u2 "La version ou le tag release manque dans PROJECT_VERSION.json."
  exit 1
fi

tag="${1:-${release_tag}}"
archive="outputs/ClipFlow-complet-${release_tag}.zip"
checksum="${archive}.sha256"
installer="outputs/ClipFlow-Installer.dmg"
release_notes="docs/releases/${release_tag}.md"

for required in "${archive}" "${installer}"; do
  if [[ ! -f "${required}" ]]; then
    print -u2 "Distribution introuvable : ${required}"
    exit 1
  fi
done

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
  "${gh_bin}" release upload "${tag}" "${installer}" "${archive}" "${checksum}" --clobber
  if [[ -f "${release_notes}" ]]; then
    "${gh_bin}" release edit "${tag}" \
      --title "ClipFlow ${product_version}" \
      --notes-file "${release_notes}"
  fi
else
  if [[ -f "${release_notes}" ]]; then
    "${gh_bin}" release create "${tag}" "${installer}" "${archive}" "${checksum}" \
      --title "ClipFlow ${product_version}" \
      --notes-file "${release_notes}"
  else
    "${gh_bin}" release create "${tag}" "${installer}" "${archive}" "${checksum}" \
      --title "ClipFlow ${product_version}" \
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
    --title "ClipFlow ${product_version}"
fi

print "Version ${tag} publiée avec l’installateur macOS, l’archive de mise à jour et son empreinte SHA-256."
