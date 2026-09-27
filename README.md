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

The preset flags hype, empty emphasis, redundancy, bold list labels (`- **label**: text`), and predicate-plus-colon before a block (`実行します:`). Interpret wording findings with `track-japanese-tech-writing`; formatting conventions live in [track's prose style](plugins/note/skills/track-markdown/references/PROSE_STYLE.md). Findings are review prompts, not permission to remove necessary qualifications or source records.

## PDF extraction

The note plugin reads local PDFs through Xberg's native Rust engine.
Nix supplies the engine and the Python standard-library wrapper that retains originals, validates physical pages, and enforces timeouts.
Xberg is built with only its PDF and async-runtime features; OCR, model downloads, and additional input formats are not enabled by the wrapper.

```sh
nix run path:.#extract-pdf -- input.pdf --text-out /tmp/input.txt --original-out /tmp/input.pdf
nix build path:.#checks.aarch64-darwin.pdf-extraction # use your host's Nix system
```

`nix develop path:.` exposes `track-extract-pdf`, its engine, and the development tools.
For an installed plugin, use `nix run github:ttak0422/track-lab#extract-pdf -- <arguments>` or install that package into a Nix profile.
The supported input for this workflow remains PDF. Web clipping continues to use `track-fetch-web`.
