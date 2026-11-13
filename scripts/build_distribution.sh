#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
project_dir="${script_dir:h}"
cd "${project_dir}"

release_number="$(sed -n 's/.*"release"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' PROJECT_VERSION.json | head -n 1)"
if [[ -z "${release_number}" ]]; then
  print -u2 "Le numéro release manque dans PROJECT_VERSION.json."
  exit 1
fi

app="outputs/ytdlp/dist/ClipFlow.app"
for required in "${app}" "outputs/ClipFlow Chrome" "outputs/ClipFlow Premiere" \
  "outputs/ClipFlow Premiere.ccx" "outputs/LISEZ-MOI.md" "PROJECT_VERSION.json" \
  "LICENSE" "LEGAL.md" "LEGAL.fr.md" "PRIVACY.md" "THIRD_PARTY_NOTICES.md" \
  "LICENSES/GPL-2.0-or-later.txt"; do
  if [[ ! -e "${required}" ]]; then
    print -u2 "Composant introuvable : ${required}"
    exit 1
  fi
done

/usr/bin/codesign --verify --deep --strict "${app}"

work_dir="$(mktemp -d /tmp/clipflow-distribution.XXXXXX)"
trap 'rm -rf "${work_dir}"' EXIT
bundle="${work_dir}/ClipFlow complet"
mkdir -p "${bundle}"

/usr/bin/ditto "${app}" "${bundle}/ClipFlow.app"
/usr/bin/ditto "outputs/ClipFlow Chrome" "${bundle}/ClipFlow Chrome"
/usr/bin/ditto "outputs/ClipFlow Premiere" "${bundle}/ClipFlow Premiere"
/usr/bin/ditto "outputs/ClipFlow Premiere.ccx" "${bundle}/ClipFlow Premiere.ccx"
/usr/bin/ditto "outputs/LISEZ-MOI.md" "${bundle}/LISEZ-MOI.md"
/usr/bin/ditto "PROJECT_VERSION.json" "${bundle}/PROJECT_VERSION.json"
/usr/bin/ditto "LICENSE" "${bundle}/LICENSE"
/usr/bin/ditto "LEGAL.md" "${bundle}/LEGAL.md"
/usr/bin/ditto "LEGAL.fr.md" "${bundle}/LEGAL.fr.md"
/usr/bin/ditto "PRIVACY.md" "${bundle}/PRIVACY.md"
/usr/bin/ditto "THIRD_PARTY_NOTICES.md" "${bundle}/THIRD_PARTY_NOTICES.md"
mkdir -p "${bundle}/LICENSES"
/usr/bin/ditto "LICENSES/GPL-2.0-or-later.txt" "${bundle}/LICENSES/GPL-2.0-or-later.txt"

archive="outputs/ClipFlow-complet-v${release_number}.zip"
rm -f "${archive}" "${archive}.sha256"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "${bundle}" "${archive}"
unzip -tq "${archive}"
hash="$(shasum -a 256 "${archive}" | awk '{print $1}')"
print "${hash}  ${archive:t}" > "${archive}.sha256"
print "Distribution créée : ${archive}"
