---
name: track-task-runner
description: >-
  Work through the TODO and Bug checklists recorded in a track note: locate the
  task note via the track CLI, then autonomously implement its unchecked items in
  the current project, easiest first, committing each and moving it out of the
  note into a dated worklog note that links back to the source. Follows a linked
  plan note when the item has one. Use when the user asks to process/work through
  a TODO or Bug list, "handle the task note", or address items tracked in a track
  note. Pairs with track-project-intake, which records and plans those items.
---

# Track Task Runner

Drive implementation work from a track note's `## TODO` and `## Bug` checklists. The note (in the
user's track vault) is the task source; the code changes happen in the current project's working
directory — the two may be different places. This skill pairs the track CLI (read the note, move done
items into a worklog note) with ordinary code work (implement, verify, commit).

When an item is finished it is **moved out** of the task note into a dated worklog note (one per
day per task note), so the task note's checklist only ever holds outstanding work and the worklog
note becomes the running log of what shipped, linked back to the source. Both notes are the
**shared record between the developer and the agent**: the checklist says what is outstanding, the
worklog says what was done and with which commit — write them so the developer does not have to ask.

It runs **autonomously and continuously**: pick the next tractable item, finish it end to end, then
move on, until nothing tractable remains.

## Prerequisites

- `track` CLI on `PATH`, resolving against the user's normal vault. (Inside the track source repo,
  `go run ./cmd/track` substitutes.) All track commands print single-line JSON; parse stdout and treat
  `{"error":...}` with exit code 1 as failure.
- A git working tree for the project whose tasks the note describes.

## 1. Locate the task note

- **Explicit**: if the user names the note (title / id / path), resolve it:
  ```sh
  track resolve --term "<title>"          # {"found":true,"note_id":N,"path":"…/note/<id>.md"}
  ```
- **Auto-discover**: otherwise find notes carrying the checklists. Search the body for the headings and
  keep candidates whose match is an actual `## TODO` / `## Bug` heading (inspect the `snippet`):
  ```sh
  track search --scope body --query "Bug" --limit 10
  track search --scope body --query "TODO" --limit 10
  ```
  Use the single note that has the sections. If several plausibly match, list them and ask which one
  before doing any work.

Read the full note to get the current checklist state:

```sh
track export --id <note_id>     # full Markdown body to stdout
```

Also capture the note's **title** — you need it to name the worklog note and to write the backlink.
`resolve` does not return it; read it from the frontmatter (or from the `search` result that found the
note):

```sh
track export --id <note_id> --frontmatter | sed -n 's/^title: //p'
```

## 2. Parse the checklist

- Unchecked items are `- [ ] <text>` lines under the `## TODO` or `## Bug` heading.
- `- [x] …` items are already done — skip them. Finished items are normally moved out into the
  worklog note (section 5), so the task note's checklist should hold mostly unchecked work; any
  stray `[x]` left behind is still skipped.
- Treat `## Bug` and `## TODO` items as one combined backlog of candidate work.

## 3. Choose order — easiest first, defer the hard

- Rank unchecked items by how tractable they look (small, localized, well-specified changes first).
- Start with the easiest. **If an item turns out difficult, ambiguous, or blocked, stop working it,
  leave it unchecked, and move to another item.** Never sink the whole run into one hard item.
- Re-evaluate after each item; a skipped item may be retried at the end if time allows.

## 4. Per-item loop (autonomous)

For each chosen item:

1. **Understand** the item. If its checklist line links a plan note (`→ [[…]]`), read it first —
   `track export --title "<plan note title>"`. Its **Approach** is a decision already settled with the
   developer, not a suggestion to re-open; implement the **Steps** in order and honor the **Risks**
   section's verification. Then read the relevant code.
2. **Implement** the change, matching the surrounding code's conventions.
3. **Verify** using the project's own rules — read `CLAUDE.md` / `AGENTS.md` / README for the canonical
   test and build commands, and run them (e.g. the project's test suite, a type-check, or a build).
   Do not mark an item done if verification fails.
4. **Commit** the change as one coherent unit, following the project's git conventions (branch policy,
   message style, required trailers). Stay on the user's chosen branch; if on the default branch,
   create a feature branch first. Do not push unless the user asked.
5. **Move the item to the worklog note** (next section): append it there, then delete it from the
   task note. Continue to the next item.

Keep going without pausing for confirmation between items — the point is an unattended sweep.

## 5. Move a completed item to the worklog note

A finished item is **moved**, not marked in place: it is appended to a dated worklog note and then
removed from the task note's checklist. The worklog note's title is today's date `YYYYMMDD` prefixed
to the task note's title, so each day gets its own log per task note. Example: task note `タスク` →
worklog note `20260617 タスク`.

1. **Ensure the worklog note exists.** Use `open` (idempotent — creates on first completion of the
   day, reuses it afterward), seeding a header that links back to the source note:
   ```sh
   printf 'from [[<task note title>]]\n\n## DONE\n' \
     | track open --title "<YYYYMMDD> <task note title>" --tag worklog
   ```
   Run this once per item; `open` is a no-op when the note already exists, so the header is written only
   on creation.

2. **Append the completed item** to the worklog note, carrying the original text, a dated reference
   to the commit that resolved it, and a `[[…]]` backlink to the source note:
   ```sh
   printf -- '- [x] <original text> (2026-06-17: `0216f6e` 概要を一行で)\n' \
     | track append --title "<YYYYMMDD> <task note title>"
   ```
   - Date is today; the hash is the short hash of the commit from step 4.
   - Write the summary in the note's existing language (match the surrounding entries).
   - `append` adds to the end, so items accumulate in worklog order under `## DONE`.

3. **Remove the item from the task note.** Delete the original `- [ ]` line in place from the task note
   file (path from step 1). This is the "move": the item leaves the source checklist entirely. Edit the
   body directly — track has no line-edit command, and `append` only adds to the end.

4. **Refresh the index** so search, links, and backlinks stay consistent across both notes:
   ```sh
   track reindex
   ```

## 6. Deferring difficult items

When you skip an item, leave its `- [ ]` unchecked. Optionally append a short
`(YYYY-MM-DD: 保留 — <reason>)` so the reason is recorded, but never mark it `[x]`. Move on.

## 7. Stop and report

Stop when no tractable unchecked items remain. Report a concise summary:

- **Done**: each finished item with its commit hash, now moved into the worklog note.
- **Deferred**: each skipped item with the reason it was hard or blocked (left in the task note).
- The branch the commits landed on, and the worklog note's title (`YYYYMMDD <task note title>`).

## Safety

- Autonomous within the working tree only: implement, test, and commit freely; treat anything
  outward-facing (push, PR, releases, deletions of work you did not create) as needing explicit
  approval.
- If verification fails and you cannot fix it quickly, revert or leave the change uncommitted, defer
  the item, and report it — never move a failing item to the worklog note.
- Only move an item out of the task note **after** its commit landed and it was appended to the
  worklog note, so a failed run never drops work on the floor.
