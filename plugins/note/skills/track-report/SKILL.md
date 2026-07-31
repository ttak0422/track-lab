---
name: track-report
description: File the findings of an investigation as a report note in the track vault. Use when the user asks you to investigate, research, analyze, compare, or find out why something behaves the way it does — write the answer up as a note so the finding survives the session instead of scrolling away. Pairs with track-project-intake, which records work to be done rather than what was found out.
---

# Track Report

An investigation the user asked for produces two things: an answer in the conversation, and a finding
that is worth keeping. This skill handles the second. The report note is the **shared record between
the developer and the agent** — the next person to ask the same question, human or agent, reads the
note instead of redoing the work.

Use the `track` CLI as the source of truth for note creation. In the track source repo,
`go run ./cmd/track` is an acceptable substitute for `track`.

## When to write a report

Write one when the user asked you to **find something out** and the answer took real work:

- "why is X slow / failing / behaving like this" — a diagnosis with evidence.
- "how does X work" — reading a subsystem, a dependency, or a spec end to end.
- "should we use A or B" — a comparison with a recommendation.
- "look into X" / "調査して" — anything explicitly framed as investigation.

Do **not** write one when:

- The answer came from a single lookup, one file, or one command — that is a reply, not a finding.
- The user asked for a change, not an answer. That is `track-project-intake` (record it) or
  `track-task-runner` (do it).
- The finding is already recorded. Search first (below) and update the existing note instead.

When in doubt, ask the user whether to file it — do not silently skip a report they expected.

## Workflow

### 1. Investigate first

Do the actual work — read the code, run the commands, check the sources. This skill governs how the
result is recorded, not how it is found. Never write a report from assumption; every claim in it has to
be one you verified.

### 2. Check for an existing report

```sh
track search --query "#report <topic keywords>"
```

If a report already covers the question, update that note (`track append`, or edit the body directly to
revise a section) rather than filing a near-duplicate. Note the date of the update in the body.

### 3. Create the report note

Title it with today's date and a summary of the *question*, not the answer — that is what a future
search looks for. Tag it `report`, and link the project or subject note it belongs to:

```sh
printf 'from [[<project>]]\n\n## Question\n\n## Answer\n\n## Evidence\n\n## Open questions\n' \
  | track new --title "<YYYYMMDD> <question summary>" --tag report
```

Then fill it in:

- **Question** — what was asked, in the form it was asked. One or two lines.
- **Answer** — the conclusion, stated directly, at the top. If the answer is "it depends", say what it
  depends on. If the investigation was inconclusive, say so — an inconclusive report is still a
  finding, and prevents the next agent from re-running a dead end.
- **Evidence** — what the conclusion rests on: file and line references (`internal/cli/note.go:88`),
  command output, measurements, links to sources. Enough that a reader can check the reasoning without
  redoing it, not a transcript of everything you read.
- **Open questions** — what remains unanswered, and anything deliberately left out of scope.

Prefer track's rich constructs over prose when the finding is structural — a `mermaid` diagram for a
flow you traced, a `viewspec` chart for measurements, a table for a comparison. See
`track-create-note` for what note bodies support.

### 4. Link it back

A report nobody can find is not a record. Make sure it is reachable:

- The `from [[<project>]]` line gives the project note a backlink — verify with
  `track backlinks --title "<project>"`.
- If the report answers a checklist item in a project note, link it from that line:
  `- [ ] <item> → [[<YYYYMMDD> <question summary>]]`.
- If it supersedes an earlier report, link that one and say what changed.

### 5. Reindex

```sh
track reindex
```

### 6. Update the topic's explainer

```sh
track search --query "#explainer <topic>"
```

If the topic has an explainer note — the page a human opens instead of the reports — add a route to
this report from it, with a line saying why someone would go down there. A report nobody routes to is
findable but unread. See `track-explainer`; if no explainer exists yet and the topic now has more than
about three reports, that skill covers building one.

## Verify

```sh
track export --title "<YYYYMMDD> <question summary>"
```

Then tell the user the note's title in one line, so they know where the finding went. Do not paste the
whole report back into the conversation — answer their question, and point at the note for the detail.
