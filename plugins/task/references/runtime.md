# Runtime

The procedures in this plugin are shared across Codex / Claude Code / OpenCode. Use whatever tools the current session provides.

- Resolve relative paths against the directory of the `SKILL.md` being read. Read a related skill's `SKILL.md` when needed; loading every skill up front is unnecessary.
- Resolve the `track` executable once per session and keep using it. In the track source repository, `go run ./cmd/track` is also an option chosen at the start. Commands usually return JSON (`export` returns Markdown). Check the exit code and output; on failure, stop that operation and report the exact error. Do not switch builds or guess unsupported commands or flags.
- For commands taking the body from stdin, pipe the input or pass a file. Pass `--body ""` for creation/open without a body (except with `--template`).
- Use the vault the user specified, and otherwise follow the normal track configuration. Carry over the `vault` from search results, and add `--vault NAME` when handling IDs from another vault.
- The vault may live outside the workspace. A permission error does not mean the vault is absent. Do not change the destination on your own; use the environment's approval flow only for the operations that need it. When permission cannot be obtained, press on with non-write work, save the body in the work area, and report it as unapplied.
- Prioritize the user's request and already-granted approvals. Using a skill never authorizes unrequested publishing, sending, or deletion. For record-only requests, do not start implementing; when implementation is also requested, keep working after recording.
- Use today's local date for agenda and worklog operations; literal dates in examples are placeholders. Preserve original completion dates when moving older work.

## Task conventions

- The default project backlog uses `## TODO` and `## Bug`. An explicitly selected flat TODO note uses its task list without adding headings. Read the entire note; code fences and unrelated sections are not backlog items. Confirm that the note belongs to the working project before implementing.
- Task states are `TODO` (`[ ]`), `DOING` (`[/]`), `WAITING` (`[?]`), `DONE` (`[x]`), and `CANCELLED` (`[-]`). Use `task set` for a known target state and `task date` for dates so completion stamps, transition logs, and progress cookies stay consistent. Do not hand-edit existing state markers or date tokens.
- Use the CLI for adding or moving items when it supports the operation (`append` for a flat list, `refile --line` for a list item). Direct body edits are limited to inserting under a heading, clarifying text, priority, and splitting items. Preserve unrelated text and metadata; respect stricter policies embedded in a note.
- Re-read the source before each write and locate the intended text again. Line numbers become stale after inserts, removals, and moves. `--expect` on state changes checks the state, not the identity of the line. Reindex after direct edits and verify with `export`.
- Parent items summarize phased work. Record dependencies and acceptance criteria when splitting. Run eligible leaves in dependency order; do not implement the parent again. Keep the parent until all required children are complete and its acceptance criteria pass. A WAITING or CANCELLED ancestor blocks automatic execution of its children.
