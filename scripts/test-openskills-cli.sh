#!/usr/bin/env bash
# Run against the real pinned CLI without network. Pre-populate npm's cache first.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/project" "$tmp/source"
cp -R "$root/plugins" "$tmp/source/"
cd "$tmp/project"
export HOME="$tmp/home"
printf 'Existing project instructions.\n' > AGENTS.md
npx --offline --yes openskills@1.5.0 install "$tmp/source" --universal -y
rm -rf "$tmp/source"
npx --offline --yes openskills@1.5.0 read track-task-runner > "$tmp/read.txt"
npx --offline --yes openskills@1.5.0 sync -y
grep -q 'Existing project instructions.' AGENTS.md
test "$(grep -c '<name>' AGENTS.md)" -eq "$(find "$root/plugins" -name SKILL.md | wc -l | tr -d ' ')"
grep -q 'track-task-runner' "$tmp/read.txt"
test -f .agent/skills/track-task-runner/references/runtime.md
test ! -L .agent/skills/track-task-runner/references/runtime.md
cmp "$root/plugins/task/references/runtime.md" .agent/skills/track-task-runner/references/runtime.md
echo 'OpenSkills install/read/sync after source removal: OK'
