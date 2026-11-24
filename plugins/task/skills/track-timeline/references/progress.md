# Record explicit Timeline progress

Use this only when the user asks to record progress or interval reports.
Keep the exact confirmed vault, project and opaque run. These notes are
additions to a task already owned by that run, not new task states. Keep an
active task active when it has a verified partial result or a concrete next
step. If it is actually blocked, update its state separately.

Before adding a progress note, run `track timeline-project intervals --help` in
the same environment. Require a successful usage response advertising
`-evidence-version`. If unavailable, keep ordinary Timeline task updates, tell
the user the limitation if relevant, and do not send progress markers. Do not
install a build or infer support from a version number.

1. Read `track --vault "$VAULT" timeline-session show --project "$PROJECT"`
   and take the current revision and the exact existing `tasks[].id` whose
   `owner` equals the confirmed run. Use the full recorded ID, not the local
   value passed to `--task`. For a verified unregistered vault, use the exact
   inline `TRACK_VAULT="$VAULT_PATH" track` binding for both read and write.
   If the task or binding cannot be verified, do not write. A delegated worker
   should report the finding to the owner of the run, not append it itself.
2. Choose one category: `result` for an observed outcome, `blocker` for a
   concrete obstacle, or `next` for a planned action. Write one printable line,
   at most 512 UTF-8 bytes, with ordinary spaces only and no leading, trailing
   or repeated whitespace. Keep it factual and intended for the record.
   Do not copy task titles, raw output, prompts, logs, private paths, secrets or
   sensitive text. Skip unchanged or trivial facts.
3. Generate a fresh opaque UID (for example, 16 random bytes in lowercase
   hexadecimal) once for this fact and retain the exact request until its
   outcome is known. With a JSON serializer, build the request below and pipe
   it to `track --vault "$VAULT" timeline-project apply --id "$PROJECT"` using
   the same vault. Set both IDs to `progress-<category>-<UID>`, and set the
   author to the bound opaque Track run. The values below are examples.

```json
{
  "source": "interval-progress-v1",
  "event_id": "progress-result-e3b8ce823eb99edfef69134343a398f7",
  "expected_revision": 12,
  "kind": "discussion.add",
  "payload": {
    "id": "progress-result-e3b8ce823eb99edfef69134343a398f7",
    "target_type": "task",
    "target_id": "run-example-implement",
    "author": "run-example",
    "text": "The fixture now passes the duplicate-row case."
  }
}
```

An uncertain response is not a reason to send another marker with a new ID.
Reread the same project; if needed, retry only the exact same operation with
the same ID and content. For a revision conflict, recheck the binding,
ownership and relevance and use the current revision only if the original
fact is not already recorded and still needs a write. A duplicate ID with
different content is a conflict, not permission to change or add another
record. Ordinary discussion comments are not progress markers.
