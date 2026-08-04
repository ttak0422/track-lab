# track-lab

> [!CAUTION]
> This project is currently experimental. Destructive changes may be applied.

Agent plugins and skills for track-related workflows.

## Plugins

| Plugin | Description |
| ------ | ----------- |
| [memory](plugins/memory/) | Persistent agent memory and consolidation (dream) backed by a track vault |
| [note](plugins/note/) | Notes as the shared record between developer and agent: create/search notes, track-flavored Markdown, web clipping, project intake with plan notes, research reports, Japanese report readability, news analyses, watch loops, topic explainers, and task worklogs |

## OpenCode

opencode discovers Agent Skills in `.opencode/skills/<name>/SKILL.md`, so this repository
ships relative symlinks from [`.opencode/skills/`](.opencode/skills/) to every plugin skill.
Open an opencode session with this repository as the working directory and the skills are
available via the `skill` tool — no marketplace or install step needed.

Install the skills globally so they are available in every project:

```sh
scripts/sync-opencode-skills.sh
```

This creates symlinks in `~/.config/opencode/skills/` pointing to the plugin skill
directories. Run it again after adding, renaming, or removing a skill.
