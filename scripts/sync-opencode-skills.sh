#!/usr/bin/env bash
# Regenerate the opencode skills symlinks from the plugin skill directories
# and link OpenCode-specific agents so both are available globally.
#
# opencode discovers agent skills in .opencode/skills/<name>/SKILL.md (and the
# Claude/agent-compatible .claude/skills, .agents/skills locations). Its
# discovery glob follows symlinks, so one symlink per skill is enough to expose
# every plugin skill without copying anything. Run this after adding, renaming,
# or removing a skill:
#
#   scripts/sync-opencode-skills.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$HOME/.config/opencode/skills"
agent_target="$HOME/.config/opencode/agents"

rm -rf "$target"
mkdir -p "$target"
mkdir -p "$agent_target"

count=0
for skill_dir in "$repo_root"/plugins/*/skills/*; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  ln -s "$skill_dir" "$target/$name"
  count=$((count + 1))
done

agent_count=0
for installed_agent in "$agent_target"/*.md; do
  [ -L "$installed_agent" ] || continue
  case "$(readlink "$installed_agent")" in
    "$repo_root"/plugins/*/agents/opencode/*.md) rm "$installed_agent" ;;
  esac
done

for agent_file in "$repo_root"/plugins/*/agents/opencode/*.md; do
  [ -f "$agent_file" ] || continue
  name="$(basename "$agent_file")"
  ln -sfn "$agent_file" "$agent_target/$name"
  agent_count=$((agent_count + 1))
done

echo "Linked $count skills into ~/.config/opencode/skills/"
echo "Linked $agent_count agents into ~/.config/opencode/agents/"
