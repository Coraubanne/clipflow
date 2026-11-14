#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
project_dir="${script_dir:h}"
cd "${project_dir}"

version="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' PROJECT_VERSION.json | head -n 1)"
build="$(sed -n 's/.*"application_build"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' PROJECT_VERSION.json | head -n 1)"
app="outputs/ytdlp/dist/ClipFlow.app"
extension="outputs/ClipFlow Chrome"
premiere="outputs/ClipFlow Premiere"
installer_source="installer/ClipFlowInstaller"
info_source="installer/Info.plist"
output="outputs/ClipFlow-Installer.dmg"

for required in "${app}" "${extension}" "${premiere}" "${installer_source}" "${info_source}"; do
  if [[ ! -e "${required}" ]]; then
    print -u2 "Composant introuvable : ${required}"
    exit 1
  fi
done

/usr/bin/codesign --verify --deep --strict "${app}"

work_dir="$(mktemp -d /tmp/clipflow-installer.XXXXXX)"
trap 'rm -rf "${work_dir}"' EXIT
installer_app="${work_dir}/volume/Installer ClipFlow.app"
contents="${installer_app}/Contents"
resources="${contents}/Resources"
payload="${resources}/Payload"
/bin/mkdir -p "${contents}/MacOS" "${payload}"

/usr/bin/sed \
  -e "s/__CLIPFLOW_VERSION__/${version}/g" \
  -e "s/__CLIPFLOW_BUILD__/${build}/g" \
  "${info_source}" > "${contents}/Info.plist"
/usr/bin/install -m 755 "${installer_source}" "${contents}/MacOS/ClipFlowInstaller"

icon="$(find "${app}/Contents/Resources" -maxdepth 1 -type f -name '*.icns' -print | head -n 1)"
if [[ -z "${icon}" ]]; then
  print -u2 "Icône ClipFlow introuvable."
  exit 1
fi
/usr/bin/ditto "${icon}" "${resources}/ClipFlow.icns"
/usr/bin/ditto "${app}" "${payload}/ClipFlow.app"
/usr/bin/ditto "${extension}" "${payload}/ClipFlow Chrome"
/usr/bin/ditto "${premiere}" "${payload}/ClipFlow Premiere"
/usr/bin/ditto "LICENSE" "${resources}/LICENSE"
/usr/bin/ditto "LEGAL.md" "${resources}/LEGAL.md"
/usr/bin/ditto "LEGAL.fr.md" "${resources}/LEGAL.fr.md"
/usr/bin/ditto "PRIVACY.md" "${resources}/PRIVACY.md"
/usr/bin/ditto "THIRD_PARTY_NOTICES.md" "${resources}/THIRD_PARTY_NOTICES.md"

/usr/bin/codesign --force --deep --sign - "${installer_app}"
/usr/bin/codesign --verify --deep --strict "${installer_app}"

/bin/rm -f "${output}"
/usr/bin/hdiutil create \
  -volname "ClipFlow Installer" \
  -srcfolder "${work_dir}/volume" \
  -format UDZO \
  -imagekey zlib-level=9 \
  "${output}"
/usr/bin/hdiutil verify "${output}"

print "Installateur créé : ${output}"
