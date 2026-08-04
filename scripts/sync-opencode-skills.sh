#!/usr/bin/env bash
# Regenerate the .opencode/skills symlinks from the plugin skill directories.
#
# opencode discovers agent skills in .opencode/skills/<name>/SKILL.md (and the
# Claude/agent-compatible .claude/skills, .agents/skills locations). Its
# discovery glob follows symlinks, so one relative symlink per skill is enough
# to expose every plugin skill without copying anything. Run this after adding,
# renaming, or removing a skill:
#
#   scripts/sync-opencode-skills.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$repo_root/.opencode/skills"

rm -rf "$target"
mkdir -p "$target"

count=0
for skill_dir in "$repo_root"/plugins/*/skills/*; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  ln -s "../../${skill_dir#"$repo_root"/}" "$target/$name"
  count=$((count + 1))
done

echo "Linked $count skills into .opencode/skills/"
