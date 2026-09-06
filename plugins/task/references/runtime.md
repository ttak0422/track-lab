# Runtime

The procedures in this plugin are shared across Codex / Claude Code / OpenCode. Use whatever tools the current session provides.

- Resolve relative paths against the directory of the `SKILL.md` being read. Read a related skill's `SKILL.md` when needed; loading every skill up front is unnecessary.
- Run `track` in the shell. Commands usually return single-line JSON (`export` returns Markdown). Parse stdout, and treat exit code 1 with `{"error":...}` as a failure.
- For commands taking the body from stdin, pipe the input or pass a file. Pass `--body ""` for creation/open without a body (except with `--template`).
- Use the vault the user specified, and otherwise follow the normal track configuration. Carry over the `vault` from search results, and add `--vault NAME` when handling IDs from another vault.
- The vault may live outside the workspace. A permission error does not mean the vault is absent. Do not change the destination on your own; use the environment's approval flow only for the operations that need it. When permission cannot be obtained, press on with non-write work, save the body in the work area, and report it as unapplied.
- Prioritize the user's request and already-granted approvals. Using a skill never authorizes unrequested publishing, sending, or deletion. For record-only requests, do not start implementing; when implementation is also requested, keep working after recording.
