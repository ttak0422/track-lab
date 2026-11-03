# track-lab

> [!CAUTION]
> This project is currently experimental. Destructive changes may be applied.

Agent plugins and skills for track-related workflows.

## Plugins

| Plugin | Description |
| ------ | ----------- |
| [note](plugins/note/) | Notes as the shared record between developer and agent: create/search notes, track-flavored Markdown, web clipping, research reports, Japanese report readability, news analyses, watch loops, topic explainers, and embeddable HTML tools |
| [task](plugins/task/) | Size-aware task handling: triage TODOs by size, record project work with plan notes, and work checklists through into dated worklogs |


## Platform support

The Nix flake supports Linux (`x86_64-linux`, `aarch64-linux`) and macOS on Apple Silicon (`aarch64-darwin`).
Intel macOS (`x86_64-darwin`) is no longer supported.

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

The PDF intake rehearsal also runs against an explicitly supplied compatible `track` binary in a temporary vault:

```sh
nix run path:.#check-pdf-intake -- /absolute/path/to/track
# CI entry point; same explicit binary requirement
scripts/ci-check-pdf-intake.sh /absolute/path/to/track
```

The Nix app pins the lab-side Python and Xberg engine. It does not fetch or build the track core repository: pass a binary that provides `source save/list` and fixed-version `cite`. Cross-repository CI should obtain that binary from a pinned compatible core build or published artifact and pass its path; do not silently track an unpublished branch. The rehearsal strips inherited `TRACK_*` settings and uses only its temporary config, vault, and cache.

## OpenSkills

OpenSkills can load the skills in any project with an `AGENTS.md`-aware agent. Node.js 20.6+ and Git are required. Install the complete set: note and task skills refer to one another by relative paths. Selecting only a subset can leave required references missing.

In the consuming project, after reviewing the source and checking the target for existing names:

```sh
npx --yes openskills@1.5.0 install ttak0422/track-lab --universal -y
npx --yes openskills@1.5.0 sync -y
npx --yes openskills@1.5.0 read track-task-runner
```

This installs copies to `.agent/skills/` and updates the project's `AGENTS.md`; `-y` overwrites matching skill names. The GitHub source follows its default branch, not a fixed revision. For a reproducible source, review and check out a specific commit locally, then pass that checkout's path to `install` instead. Pinning the top-level CLI version does not lock its transitive npm dependencies. The generated `AGENTS.md` invokes `npx openskills read`; use a locally locked OpenSkills dependency or update the generated invocation to `npx --yes openskills@1.5.0 read` after each sync if an exact CLI version is needed.

See [the migration guide](docs/openskills-migration.md) before replacing an existing plugin or OpenCode setup. Existing plugin manifests and the OpenCode sync script are retained for native consumers.

The offline layout check verifies that all source-resolving relative Markdown links still resolve in the copied set and that each bundled task runtime matches its canonical source:

```sh
python3 scripts/test-openskills-layout.py
```

To additionally exercise the real CLI, pre-populate npm's cache with `openskills@1.5.0`, then run `scripts/test-openskills-cli.sh`. The test uses an isolated temporary HOME and project and forces npm offline; it does not touch an existing agent setup or vault.
