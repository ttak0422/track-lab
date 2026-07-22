# Memory Plugin

`memory` gives agents persistent, cross-session memory backed by a track vault, and a consolidation workflow (`dream`) to keep that memory clean over time.

Based on the memory-dream consolidation playbook, re-designed around track primitives: memories are tagged notes linked with `[[Title]]` wikilinks, recall is `track search`, deduplication uses `backlinks`/`graph`/`rename`, and non-destructive review uses track generations (`gen increment`/`undo`/`redo`/`peek`) instead of git commits.

## Skills

| Skill | Purpose |
| ----- | ------- |
| [memory](skills/memory/SKILL.md) | Record and recall facts as `memory`-tagged notes: one note per fact, dedup before create, absolute dates, liberal wikilinks. |
| [dream](skills/dream/SKILL.md) | Consolidate memory notes: merge duplicates into canonical notes, resolve contradictions, prune stale entries. Generation-based save point makes the whole run revertible with `track gen undo`. |

## Requirements

- `track` CLI with the `gen` and `rm` subcommands.

## Layout

```text
plugins/memory/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
└── skills/
    ├── memory/SKILL.md
    └── dream/SKILL.md
```

## Install

Claude Code (local development):

```sh
claude --plugin-dir ./plugins/memory
```

Claude Code (marketplace):

```text
/plugin marketplace add /path/to/track-lab
/plugin install memory@track-lab
/reload-plugins
```

Codex:

```sh
codex plugin marketplace add /path/to/track-lab
codex plugin add memory@track-lab
```

Standalone: copy or symlink `plugins/memory/skills/<name>` into `.claude/skills/<name>`.
