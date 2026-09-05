# track-lab

> [!CAUTION]
> This project is currently experimental. Destructive changes may be applied.

Agent plugins and skills for track-related workflows.

## Plugins

| Plugin | Description |
| ------ | ----------- |
| [memory](plugins/memory/) | Persistent agent memory and consolidation (dream) backed by a track vault |
| [note](plugins/note/) | Notes as the shared record between developer and agent: create/search notes, track-flavored Markdown, web clipping, research reports, Japanese report readability, news analyses, watch loops, topic explainers, and embeddable HTML tools |
| [task](plugins/task/) | Size-aware task handling: triage TODOs by size, record project work with plan notes, and work checklists through into dated worklogs |


## Lint

Skill prose is checked with [textlint-rule-preset-ai-writing](https://github.com/textlint-ja/textlint-rule-preset-ai-writing), pinned in `nix/textlint/` so every run reports the same findings.

```sh
nix run .#lint                    # all SKILL.md files
nix run .#lint -- path/to/note.md # any Markdown file
```

The preset detects what the writing skills already forbid in prose (hype, empty emphasis, redundancy) plus two patterns they did not cover: bold list labels (`- **label**: text`) and predicate-plus-colon before a block (`実行します:`). Detection lives in the linter; how to rewrite a hit lives in `track-japanese-tech-writing`.
