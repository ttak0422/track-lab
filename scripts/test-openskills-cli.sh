#!/usr/bin/env bash
# Run against the real pinned CLI without network. Pre-populate npm's cache first.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cache="$(npm config get cache)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/project" "$tmp/source"
cp -R "$root/plugins" "$tmp/source/"
cd "$tmp/project"
export HOME="$tmp/home" npm_config_cache="$cache"
printf 'Existing project instructions.\n' > AGENTS.md
npx --offline --yes openskills@1.5.0 install "$tmp/source" --universal -y
# A reinstall merges directories and does not remove retired skills or files.
# Demonstrate the limitation, then reconcile only these test-owned synthetic paths.
printf 'obsolete\n' > .agent/skills/track-task-runner/obsolete-test-file
mkdir -p .agent/skills/retired-test-skill
printf '%s\n' '---' 'name: retired-test-skill' 'description: synthetic test' '---' > .agent/skills/retired-test-skill/SKILL.md
npx --offline --yes openskills@1.5.0 install "$tmp/source" --universal -y
test -f .agent/skills/track-task-runner/obsolete-test-file
test -f .agent/skills/retired-test-skill/SKILL.md
rm .agent/skills/track-task-runner/obsolete-test-file
rm -rf .agent/skills/retired-test-skill
rm -rf "$tmp/source"
for skill in track-task-runner track-timeline track-timeline-interval-reports; do
  npx --offline --yes openskills@1.5.0 read "$skill" > "$tmp/$skill.txt"
  grep -q "name: $skill" "$tmp/$skill.txt"
done
test -f .agent/skills/track-timeline-interval-reports/../track-timeline/SKILL.md
grep -Fq '[track-timeline skill](../track-timeline/SKILL.md)' "$tmp/track-timeline-interval-reports.txt"
for skill in track-timeline track-timeline-interval-reports; do
  test -f ".agent/skills/$skill/agents/openai.yaml"
done
npx --offline --yes openskills@1.5.0 sync -y
grep -q 'Existing project instructions.' AGENTS.md
test "$(grep -c '<name>' AGENTS.md)" -eq "$(find "$root/plugins" -name SKILL.md | wc -l | tr -d ' ')"
test -f .agent/skills/track-task-runner/references/runtime.md
test ! -L .agent/skills/track-task-runner/references/runtime.md
cmp "$root/plugins/task/references/runtime.md" .agent/skills/track-task-runner/references/runtime.md
echo 'OpenSkills install/read/sync after source removal: OK'
