---
name: dream
description: Consolidate track-based agent memory - merge duplicates, resolve contradictions, refresh stale facts, prune noise. Use when the user says "dream", asks to clean up or reorganize memory, or when memory recall returns duplicated or outdated hits.
---

# Dream

Reorganize the memory notes in a track vault (memory consolidation). Recording is local and incremental, so after enough sessions the store accumulates duplicates, contradictions, and stale entries, and recall degrades from an aid into noise — dream restores the signal. Merge duplicates, replace stale values with current ones, and extract repeated patterns into concise knowledge. Track generations (`gen`) make every step revertible, so edits are applied directly and reviewed afterward.

## Triggers

- Right after a large refactor (mass renames, framework migration, API restructuring) — stale entries actively mislead, so this takes priority.
- When many sessions have accumulated since the last dream (roughly 20-30 sessions in practice). `track gen list` shows generation labels — a long gap since the last `dream`-labeled generation is a signal to suggest a dream.
- When the user says "dream" or asks to tidy memory, or recall returns duplicated or contradictory hits.

## Preconditions

- `track` CLI with the `gen` (including `increment --label` and `status`), `rm`, and `graph --orphans` features. In the track source repo, `go run ./cmd/track` is an acceptable substitute.
- Scope is memory notes (tag `memory`). Do not edit journals: they are history, not memory. Extracting durable facts from journals into memory notes is allowed; rewriting journals is not.
- Memory titles encode scope as `parent / child` (see the memory skill); the shallower note owns a shared fact.

## Workflow

1. **Save point.** Record the pre-dream state as a generation; everything after is revertible with one `undo`:

```sh
track gen increment --label pre-dream
```

2. **Survey.** List all memory notes and check vault health:

```sh
track search --query "#memory" --limit 200
track graph --orphans
track doctor
```

`graph --orphans` reports vault-wide link-graph hygiene in one call:

- **`orphans`**: notes with no inbound link (journals excluded) — a memory note here with weak title keywords is effectively undiscoverable. Plan a link to it from a related note, or fold it into one.
- **`dangling_prefixes`**: a `foo / bar` note whose `foo` note no longer exists — the parent was renamed or deleted without cascading.

3. **Consolidate.** Apply the edits directly — they are reversible:

- One concept, one canonical note. Find duplicate clusters via search, `track backlinks`, and `track graph`; merge content into the canonical note with `track update`, and replace restatements elsewhere with a `[[Title]]` link.
- Choosing the canonical: the **shallowest applicable scope wins** (shortest title prefix — a fact stated at both `foo` and `foo / bar` belongs in `foo`, so delete the restatement on the deeper side). Between notes at the same depth, prefer the one with more backlinks and the better link-keyword title.
- Use `track rename` when the canonical title should change; backlinks are rewritten automatically. Renaming a parent requires renaming its `parent / child` descendants too.
- Resolve contradictions to the newest value. Ask the user when genuinely ambiguous.
- Convert relative dates to absolute dates.
- Remove references to files, functions, or flags that no longer exist, or verify and update them.
- Re-link orphans found in the survey; soft-delete notes with no remaining value: `track rm --id <id>`.

4. **Report.** Enumerate the changes mechanically, then summarize to the user what was merged into what, what was deleted, what was updated:

```sh
track gen status
```

lists every file added, changed, or deleted since the save point (vault-relative; a body edit shows `note/<id>.md`, a metadata-only change its sidecar) — build the report from it, not from self-report. To show a specific change:

```sh
diff <(track gen peek --id <id>) <(track export --id <id>)
```

`gen peek` reads the save-point snapshot without moving the cursor. Notes deleted during the dream resolve by `--id` only.

5. **Adopt or revert.**

```sh
track gen increment --label dream   # approved: the consolidated state becomes the
                                    # new head; the label dates the last dream
track gen undo                      # rejected: restore the save point (the rejected
                                    # state is auto-saved; revisit with `track gen redo`)
```

For partial adoption, write back individual sections from `gen peek` output with `track update`, then `increment`.

`gen undo`/`redo` rebuild the index automatically; no manual `reindex` is needed.

## Content Rules

- Keep only currently-true knowledge, rules, and reproducible procedures. Strip provenance and history from note bodies: who said it, when it was learned, how often it recurred. Technical causality ("A breaks B, so do C") stays.
- Never restate a fact another note owns; link to it with `[[Title]]`.
- The host's always-loaded instructions (CLAUDE.md / AGENTS.md) are the layer above the vault: silently delete memory notes that restate rules defined there — the host side is not yours to edit.
- Consolidation can hallucinate: merged text may assert things no source note said. Present the changes for review before the final `increment`; never adopt silently.

## Checklist

- [ ] `gen increment --label pre-dream` taken before any edit
- [ ] duplicates merged into canonical notes (shallowest scope owns); restatements replaced with links
- [ ] orphans re-linked or folded in; parentless `parent / child` prefixes repaired
- [ ] contradictions resolved to the newest value (user asked when ambiguous)
- [ ] relative dates converted to absolute
- [ ] dead references removed or verified
- [ ] provenance and history stripped from note bodies
- [ ] changes reported from `gen status`; user adopted (`increment --label dream`) or reverted (`undo`)
