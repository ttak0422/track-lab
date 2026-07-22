---
name: memory
description: Persistent agent memory backed by a track vault. Use when the user asks to remember or recall something across sessions, when durable facts emerge (corrections, preferences, decisions, project constraints), or before substantial tasks to recall relevant context.
---

# Memory

Store agent memory as track notes so knowledge survives across sessions. One note holds one fact. The `memory` tag marks memory notes. Titles are link keywords: write `[[Title]]` in bodies to link related notes.

## Titles and Scope

Titles express scope the way Confluence page titles do: `foo / bar` is a child of `foo`. Use ` / ` (a slash with surrounding spaces) as the separator.

- A fact lives at the **broadest scope where it applies**. Facts that hold everywhere get an unprefixed title (`zsh completion quirks`); project-scoped facts go under the project title (`track / gen design decisions`).
- Never restate a broader fact in a deeper note; link to it with `[[Title]]` instead. When the same fact appears at two depths, the shallower note owns it.
- List children of a scope with `track search --scope title --query "<parent> /"`.
- Renaming a parent does not rename its children — rename descendants with `track rename` as well.

## Preconditions

- Use the `track` CLI as the source of truth. In the track source repo, `go run ./cmd/track` is an acceptable substitute.
- Prefer the user's normal track config. `TRACK_VAULT` is for tests and one-off overrides.
- Commands print single-line JSON (`export` prints Markdown). Treat `{"error":...}` with exit code 1 as failure.

## Recall

At the start of a substantial task, or when stored context about the user, project, or workflow might exist:

```sh
track search --query "#memory <keywords>" --limit 10
track export --id <id>
```

- Try a few keyword variants; search covers titles and bodies.
- Read the full note with `export` before relying on it.
- Memories are point-in-time observations, not live state. Verify facts that name files, flags, or commands before acting on them.

## Record

Save a memory when the user asks to remember something, corrects how you work, or a durable non-obvious fact emerges (who the user is, goals, constraints, confirmed approaches). Do not save what the project already records (code, docs, git history), what the host's always-loaded instructions (CLAUDE.md / AGENTS.md) already state, or details that only matter to the current session.

1. Deduplicate first — search for an existing memory covering the fact and revise it instead of creating a duplicate:

```sh
track search --query "#memory <topic>"
track update --id <id> --body "<revised fact>"
```

2. Otherwise create one note per fact. Pick the title by scope (see Titles and Scope). Start the body with a one-line summary, then details:

```sh
track new --title "<scope-prefixed topic>" --tag memory --body "<one-line summary>

<details>"
```

3. Convert relative dates ("yesterday", "last week") to absolute dates before saving.
4. Link liberally: reference related memories and project notes with `[[Title]]`. Backlinks are what make later consolidation possible.

## Correct and Remove

- A memory that turns out to be wrong: fix it with `track update`, or soft-delete it with `track rm --id <id>` (moves the note into trash).
- Never leave two notes asserting contradictory facts; update the outdated one to the current truth.

## Maintenance

When recall starts returning duplicated, contradictory, or stale hits, run the dream skill to consolidate memory.
