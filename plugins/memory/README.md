# Memory Plugin

`memory` gives Claude, Codex, and OpenCode one persistent, cross-session memory backed by a track vault, plus a consolidation workflow (`dream`) to keep that memory clean over time. Its trigger description tells agents to recall project context proactively before substantial repository work, not only when the user explicitly says "remember".

Based on the memory-dream consolidation playbook, re-designed around track primitives: memories are tagged notes linked with `[[Title]]` wikilinks, recall is `track search`, deduplication uses `backlinks`/`graph`/`rename`, and non-destructive review uses track generations (`gen increment`/`undo`/`redo`/`peek`) instead of git commits.

## Skills

| Skill | Purpose |
| ----- | ------- |
| [memory](skills/memory/SKILL.md) | Recall project-scoped facts before non-trivial work, then record durable knowledge as exact-`memory`-tagged notes: one note per fact, dedup before create, absolute dates, liberal wikilinks. |
| [dream](skills/dream/SKILL.md) | Consolidate memory notes: merge duplicates into canonical notes, resolve contradictions, prune stale entries. Generation-based save point makes the whole run revertible with `track gen undo`. |

## Requirements

- `track` CLI with the `gen` and `rm` subcommands.
- A configured track vault visible to every agent environment that should share memory.

## How recall works

All three agents initially see the skill's name and description. The description front-loads concrete project-work triggers so the agent selects the skill before planning, implementation, debugging, review, refactoring, research, or project questions. Once selected, the skill:

1. derives a project key from the git root and remote;
2. searches exact-`memory`-tagged titles for that project scope;
3. searches task keywords across titles and bodies, then filters results to the exact `memory` tag;
4. exports and verifies relevant notes before acting.

The track vault is authoritative. Do not also store the same facts in an agent-specific memory store. In Claude Code, auto memory is enabled by default; disable it for projects using this plugin with the `/memory` toggle or this project setting:

```json
{
  "autoMemoryEnabled": false
}
```

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

```sh
claude plugin marketplace add ttak0422/track-lab
claude plugin install memory@track-lab
```

Codex:

```sh
codex plugin marketplace add ttak0422/track-lab
codex plugin add memory@track-lab
```

OpenCode: the repository-local symlinks under `.opencode/skills/` work while developing in this repository. To make the skills available in every project, run `scripts/sync-opencode-skills.sh` from the repository root; it links them into `~/.config/opencode/skills/`.

Standalone: copy or symlink `plugins/memory/skills/<name>` into `.claude/skills/<name>`, `.agents/skills/<name>`, or `.opencode/skills/<name>`.
