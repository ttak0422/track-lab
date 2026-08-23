# Note Plugin

`note` treats a track vault as the **shared record between the developer and the agent**: what was
decided, what was found out, and what is still outstanding. Every skill here writes or reads that
record through the `track` CLI.

Moved out of the [track](https://github.com/ttak0422/track) repository, where these skills shipped as
the `track` plugin. track itself now carries only the CLI and its tool-neutral contract
(`docs/spec/agent-workflows.md`); the agent-facing skills live and evolve here.

## Skills

| Skill | Purpose |
| ----- | ------- |
| [track-create-note](skills/track-create-note/SKILL.md) | Create or open notes, journals, and template-backed notes — including the rich body constructs (diagrams, mindmaps, charts, queries, babel, embeds) that plain prose leaves on the table. |
| [track-search-notes](skills/track-search-notes/SKILL.md) | Read-only discovery: search by title/body/tag, resolve links, export bodies, inspect backlinks and the local graph. |
| [track-project-intake](skills/track-project-intake/SKILL.md) | Record an incoming bug/TODO against the project's note, and draft a linked **plan note** when the work needs agreement before code. |
| [track-task-runner](skills/track-task-runner/SKILL.md) | Work through a project note's checklist autonomously, following any linked plan, and move each finished item into a dated **worklog note** with its commit. |
| [track-report](skills/track-report/SKILL.md) | File the findings of an investigation as a **report note**, so the answer survives the session. |
| [track-explainer](skills/track-explainer/SKILL.md) | Fold a topic's reports into one **explainer note** — the page a human actually opens, with a diagram and routes down into the reports and their sources. |
| [track-news-analysis](skills/track-news-analysis/SKILL.md) | Research a current-events topic from multiple lenses (a bundled Workflow script sweeps, verifies, and gap-fills) and file a visualized, source-cited **analysis note**. |
| [track-watch](skills/track-watch/SKILL.md) | Run a recurring watch loop over a topic at three depths — `light` daily brief, `mid` weekly review, `high` deep review (assumption excavation, break scenarios, falsifiable forecasts) — with a standing **watch note** as the loop state. |
| [track](skills/track/SKILL.md) | Vault maintenance: rename with backlink rewrite, doctor, reindex, generations, task toggles. |
| [track-markdown](skills/track-markdown/SKILL.md) | The body syntax itself: wikilinks and level-based heading anchors, block anchors, transclusion, GitHub alerts, task lines, inline properties, and the `track fmt` house style. |
| [track-clip](skills/track-clip/SKILL.md) | Read a web page as clean Markdown with `track-fetch-web` instead of WebFetch, and save it as a `clip`-tagged note with provenance. |
| [track-tool](skills/track-tool/SKILL.md) | Write a small single-file HTML tool for a note to embed: what survives the sandboxed iframe, and the one stylesheet that keeps a vault's tools looking like one set. |
| [track-japanese-report-readability](skills/track-japanese-report-readability/SKILL.md) | Keep a Japanese report readable while it stays detailed: conclusion-first layers, a density gradient, and a deletion pass over the writing an agent produced. |
| [track-japanese-tech-writing](skills/track-japanese-tech-writing/SKILL.md) | Sentence-and-paragraph craft for Japanese technical prose: formatting, argument rigor, reader load, and a ban on LLM filler. The base layer under every writing skill here. |
| [track-cognitive-rhythm-writing](skills/track-cognitive-rhythm-writing/SKILL.md) | Pacing for pages humans read start to finish: cognitive-mode switches, open tension, sentence beats, and the topic test for pruning filler. Applied to explainers. |

## The record

```mermaid
flowchart LR
  ask[Developer asks] --> kind{change or question?}
  kind -->|change| intake[track-project-intake]
  kind -->|question| report[track-report]
  intake --> checklist["project note<br/>## TODO / ## Bug"]
  intake -.needs agreement.-> plan["plan note<br/>#plan"]
  checklist --> runner[track-task-runner]
  plan --> runner
  runner --> worklog["worklog note<br/>#worklog"]
  report --> reportnote["report note<br/>#report"]
  reportnote --> explainer["explainer note<br/>#explainer"]
```

Four note kinds carry a tag so they stay findable: `plan`, `worklog`, `report`, `explainer`. Each links
back to the project note, so `track backlinks --title "<project>"` shows the whole trail.

The last arrow runs the other way from the rest. `plan`, `worklog` and `report` accumulate — one per
piece of work. An `explainer` is one per *topic*, rebuilt from the reports underneath it, and it is the
only one of the four written to be read rather than to be found. Reports optimise for coverage;
the explainer optimises for how fast someone understands the topic, which means it is mostly a
subtraction from what the reports hold.

`track-japanese-report-readability` is the odd one out: it touches no vault and runs no CLI. It governs the
prose an agent puts *into* those notes. A report nobody rereads is as lost as one nobody can find, and
the failure mode of an agent-written Japanese report is not missing detail — it is uniform detail with
no gradient, which costs the reader the same effort on the conclusion as on a footnote.

## Imported from obsidian-skills

`track-markdown` and `track-clip` are adapted from
[obsidian-skills](https://github.com/kepano/obsidian-skills) by Steph Ango (MIT) — the same strategy,
re-aimed at track primitives. `obsidian-markdown` became `track-markdown`, rewritten to describe track's
own dialect only — no frontmatter (metadata is a sidecar plus inline `key:: value` fields), GitHub
alerts, heading anchors that count `#` for the level. `defuddle` became `track-clip`, but the engine is
track's own `track-fetch-web` rather than a Node CLI, so the plugin adds no external dependency.

The skills themselves never mention Obsidian: an agent writing track notes has no use for what the
syntax used to be, so that context lives here in the README instead.

| obsidian-skills skill | Disposition |
| --------------------- | ----------- |
| `obsidian-markdown` | → `track-markdown` |
| `defuddle` | → `track-clip`, on `track-fetch-web` |
| `obsidian-cli` | Not imported — `track` and `track-search-notes` already cover the CLI. |
| `json-canvas` | Not imported — track has no `.canvas` surface (nearest: mermaid/dot/mindmap fences). |
| `obsidian-bases` | Not imported — track has no `.base` surface (nearest: `track-query` blocks and viewspec charts). |

## Referenced skills

Both start from gists by [k16shikano](https://gist.github.com/k16shikano) (Unlicense); provenance
lives here instead of inside the skills.

| Skill | Source | Relationship to upstream |
| ----- | ------ | ------------------------ |
| `track-japanese-tech-writing` | <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d> | Body byte-identical to upstream; `name:` prefixed |
| `track-cognitive-rhythm-writing` | <https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432> | Forked and re-aimed at explainer notes — track surfaces, figures, and wikilink routes replace the book-chapter vocabulary; the machinery (topic test, tension ledger, leak test) is preserved |

Division of labor: reports follow `track-japanese-tech-writing` + `track-japanese-report-readability`; explainers add
`track-cognitive-rhythm-writing` on top. Watch and project notes are history-first and are out of scope for all three.

## Requirements

- `track` CLI on `PATH`, resolving against the user's normal vault.
- `track-fetch-web` on `PATH` for `track-clip`. It ships with track as a separate binary.

## Layout

```text
plugins/note/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
└── skills/
    ├── track-clip/SKILL.md
    ├── track-cognitive-rhythm-writing/SKILL.md
    ├── track-create-note/SKILL.md
    ├── track-explainer/SKILL.md
    ├── track-japanese-report-readability/SKILL.md
    ├── track-japanese-tech-writing/SKILL.md
    ├── track-markdown/
    │   ├── SKILL.md
    │   └── references/{EMBEDS,PROPERTIES}.md
    ├── track-news-analysis/SKILL.md
    ├── track-project-intake/SKILL.md
    ├── track-report/SKILL.md
    ├── track-search-notes/SKILL.md
    ├── track-task-runner/SKILL.md
    ├── track-tool/SKILL.md
    ├── track-watch/SKILL.md
    └── track/SKILL.md
```

## Install

Claude Code (local development):

```sh
claude --plugin-dir ./plugins/note
```

Claude Code (marketplace):

```sh
claude plugin marketplace add ttak0422/track-lab
claude plugin install note@track-lab
```

Codex:

```sh
codex plugin marketplace add ttak0422/track-lab
codex plugin add note@track-lab
```

OpenCode:

```sh
scripts/sync-opencode-skills.sh note
```

Links this plugin's skills into `~/.config/opencode/skills/`, where opencode discovers them
natively; add `--project` to link into the current project's `.opencode/skills/` instead.
Run it from the repository root and re-run after adding, renaming, or removing a skill —
only links owned by the synced plugins are touched.

Standalone: copy or symlink `plugins/note/skills/<name>` into `.claude/skills/<name>` or
`.opencode/skills/<name>`.

If you previously installed the `track` plugin from the track repository, uninstall it first — the
skill names are the same and would otherwise collide.
