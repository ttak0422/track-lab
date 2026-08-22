#!/usr/bin/env bash
# Sync track-lab plugin skills into an opencode skills directory as symlinks.
#
# opencode discovers agent skills at .opencode/skills/<name>/SKILL.md (project)
# and ~/.config/opencode/skills/<name>/SKILL.md (global). Its discovery glob
# follows symlinks, so one symlink per skill exposes every plugin skill without
# copying anything.
#
# Usage:
#   scripts/sync-opencode-skills.sh [plugin ...] [--project]
#
#   plugin ...  Plugin names to sync (e.g. "note memory"). Defaults to all
#               plugins in the repository.
#   --project   Link into <cwd>/.opencode/skills/ instead of the global
#               ~/.config/opencode/skills/.
#
# Re-run after adding, renaming, or removing a skill. Only symlinks that
# resolve back into this repository's plugins are touched; anything else in
# the target directory is left alone.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: scripts/sync-opencode-skills.sh [plugin ...] [--project]

Sync track-lab plugin skills into an opencode skills directory as symlinks.

  plugin ...  Plugin names to sync (e.g. "note memory"). Defaults to all.
  --project   Target <cwd>/.opencode/skills/ (default: ~/.config/opencode/skills/)
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugins_root="$repo_root/plugins"

scope_global=true
selected=()

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --project) scope_global=false ;;
    -*)
      echo "error: unknown option: $arg" >&2
      usage
      exit 2
      ;;
    *)
      if [ ! -d "$plugins_root/$arg" ]; then
        echo "error: unknown plugin: $arg" >&2
        exit 2
      fi
      selected+=("$arg")
      ;;
  esac
done

if [ "${#selected[@]}" -eq 0 ]; then
  for dir in "$plugins_root"/*/; do
    selected+=("$(basename "$dir")")
  done
fi

if $scope_global; then
  target="$HOME/.config/opencode/skills"
else
  target="$PWD/.opencode/skills"
fi

mkdir -p "$target"

linked=0
for plugin in ${selected[@]+"${selected[@]}"}; do
  skills_dir="$plugins_root/$plugin/skills"
  if [ ! -d "$skills_dir" ]; then
    echo "skip $plugin: no skills/ directory" >&2
    continue
  fi

  # Drop links previously owned by this plugin so renames/removals are picked up.
  for entry in "$target"/*; do
    [ -L "$entry" ] || continue
    dest="$(readlink "$entry")"
    case "$dest" in
      /*) resolved="$dest" ;;
      *) resolved="$(dirname "$entry")/$dest" ;;
    esac
    resolved="$(cd "$(dirname "$resolved")" 2>/dev/null && pwd)/$(basename "$resolved")" || continue
    case "$resolved" in
      "$skills_dir"|"$skills_dir"/*) rm "$entry" ;;
    esac
  done

  for skill_dir in "$skills_dir"/*; do
    [ -d "$skill_dir" ] || continue
    name="$(basename "$skill_dir")"
    entry="$target/$name"
    if [ -e "$entry" ] || [ -L "$entry" ]; then
      echo "skip $plugin/$name: $entry already exists and is not ours" >&2
      continue
    fi
    ln -s "$skill_dir" "$entry"
    linked=$((linked + 1))
  done
done

echo "Linked $linked skill(s) into $target"
