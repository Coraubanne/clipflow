#!/bin/zsh
# Both desktop companions ship this updater for the same Premiere plugin.
set -euo pipefail
umask 077
autoload -Uz is-at-least

mode=${1:-}
expected=${2:-}
preference=${4:-}
install_root="${3:-${HOME}}/Library/Application Support/Adobe/UXP/Plugins/External"
plugin_id=fr.clipflow.premiere.bridge
repository=Coraubanne/CreatorBridge
files=(manifest.json index.html index.js styles.css LICENSE)
workspace="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/creator-bridge-update.XXXXXX")"
trap '/bin/rm -rf -- "$workspace"' EXIT

valid_version() {
  [[ "$1" =~ '^(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})$' ]]
}

manifest_value() {
  /usr/bin/plutil -extract "$2" raw -o - "$1/manifest.json" 2>/dev/null
}

valid_plugin() {
  local folder=$1 file
  [[ -d "$folder" && ! -L "$folder" ]] || return 1
  for file in manifest.json index.html index.js styles.css; do
    [[ -s "$folder/$file" && ! -L "$folder/$file" ]] || return 1
  done
  [[ "$(manifest_value "$folder" id)" == "$plugin_id" &&
     "$(manifest_value "$folder" host.app)" == premierepro &&
     "$(manifest_value "$folder" main)" == index.html ]]
}

installed_version() {
  local folder version newest=0.0.0
  for folder in "$install_root"/${plugin_id}_*(N/); do
    valid_plugin "$folder" || continue
    version="$(manifest_value "$folder" version)"
    valid_version "$version" || continue
    [[ "${folder:t}" == "${plugin_id}_${version}" ]] || continue
    if is-at-least "$newest" "$version"; then newest=$version; fi
  done
  print -r -- "$newest"
}

result() {
  printf '{"ok":true,"currentVersion":"%s","latestVersion":"%s","available":%s,"installed":%s}\n' "$1" "$2" "$3" "$4"
}

premiere_selected() {
  [[ -z "$preference" || "$(/usr/bin/plutil -extract outputMode raw -o - "$preference" 2>/dev/null)" == premiere ]]
}

install_payload() {
  local payload=$1 latest=$2 current folder version target lock bridge_lock
  valid_plugin "$payload"
  [[ "$(manifest_value "$payload" version)" == "$latest" ]]
  /bin/mkdir -p "$install_root"
  [[ -d "$install_root" && ! -L "$install_root" ]]
  zmodload zsh/system
  lock="$install_root/.creator-bridge.lock"
  [[ ! -L "$lock" ]]
  : >> "$lock"
  zsystem flock -t 10 -f bridge_lock "$lock"
  premiere_selected

  current="$(installed_version)"
  if is-at-least "$latest" "$current"; then
    result "$current" "$latest" false false
    return 0
  fi

  target="$install_root/${plugin_id}_${latest}"
  [[ ! -e "$target" && ! -L "$target" ]]
  stage="$(/usr/bin/mktemp -d "$install_root/.creator-bridge-stage.XXXXXX")"
  trap '/bin/rm -rf -- "$workspace" "$stage"' EXIT
  /usr/bin/ditto "$payload" "$stage/plugin"
  /bin/mv "$stage/plugin" "$target"
  for folder in "$install_root"/${plugin_id}_*(N/); do
    valid_plugin "$folder" || continue
    version="$(manifest_value "$folder" version)"
    valid_version "$version" || continue
    [[ "${folder:t}" == "${plugin_id}_${version}" && "$version" != "$latest" ]] || continue
    if is-at-least "$version" "$latest"; then
      /bin/rm -rf -- "$folder" || true
    fi
  done
  result "$latest" "$latest" false true
}

if [[ "$mode" == install-local ]]; then
  bundled_version="$(manifest_value "$expected" version)"
  valid_version "$bundled_version"
  install_payload "$expected" "$bundled_version"
  exit 0
fi

# Use a stable release and its GitHub-provided digest. The browser never supplies URLs.
premiere_selected
current="$(installed_version)"
release="$workspace/release.json"
http_status="$(/usr/bin/curl -q -sS --proto '=https' --connect-timeout 4 --max-time 10 \
  --max-filesize 1048576 -H 'Accept: application/vnd.github+json' \
  -o "$release" -w '%{http_code}' "https://api.github.com/repos/$repository/releases/latest")"
if [[ "$http_status" == 404 && "$mode" == check ]]; then
  result "$current" "" false false
  exit 0
fi
[[ "$http_status" == 200 ]]
[[ "$(/usr/bin/plutil -extract draft raw -o - "$release")" == false &&
   "$(/usr/bin/plutil -extract prerelease raw -o - "$release")" == false ]]
tag="$(/usr/bin/plutil -extract tag_name raw -o - "$release")"
latest=${tag#v}
[[ "$tag" == "v$latest" ]]
valid_version "$latest"
if is-at-least "$latest" "$current"; then
  result "$current" "$latest" false false
  exit 0
fi

asset="CreatorBridge-$tag.zip"
digest=""
for (( index = 0; index < 100; index++ )); do
  name="$(/usr/bin/plutil -extract "assets.$index.name" raw -o - "$release" 2>/dev/null)" || break
  [[ "$name" == "$asset" ]] || continue
  digest="$(/usr/bin/plutil -extract "assets.$index.digest" raw -o - "$release")"
  break
done
[[ "$digest" =~ '^sha256:[0-9a-f]{64}$' ]]
if [[ "$mode" == check ]]; then
  result "$current" "$latest" true false
  exit 0
fi
[[ "$mode" == install && "$expected" == "$latest" ]]

archive="$workspace/$asset"
/usr/bin/curl -q -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 4 --max-time 25 \
  --max-filesize 2097152 -o "$archive" "https://github.com/$repository/releases/download/$tag/$asset"
actual="$(/usr/bin/shasum -a 256 "$archive")"
[[ "${actual%% *}" == "${digest#sha256:}" ]]

payload="$workspace/plugin"
/bin/mkdir "$payload"
# Read only the five expected files and cap expanded file size. Never extract archive paths.
for file in "${files[@]}"; do
  (ulimit -f 2048; /usr/bin/unzip -p "$archive" "$file" > "$payload/$file")
done
install_payload "$payload" "$latest"
