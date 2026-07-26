# Properties Reference

Note metadata never lives in the body: there is **no YAML frontmatter** in track. Each note has a sidecar file (`.track/notes/<id>.yaml`) holding its title, tags, created timestamp, description, cover image, icon, and typed properties under `props`. The body stays plain Markdown, and its H1 is ordinary content — the sidecar title is the authoritative name and the link keyword. Edit metadata through the CLI, not by hand-editing the sidecar.

## Sidecar Metadata via the CLI

Tags are set with `--tag` flags on the authoring commands (repeat the flag for multiple tags); `track update --clear-tags` removes them:

```sh
track new --title "<title>" --tag <tag> --tag <tag2> --body "<body>"
track append --title "<title>" --tag <extra-tag> --body "<more>"
```

Everything else goes through `track meta`:

```sh
track meta --title "<note>"                                        # print metadata incl. props (JSON)
track meta --title "<note>" --description "<one-line summary>"
track meta --title "<note>" --image "assets/cover.png" --icon "<emoji>"
track meta --title "<note>" --set status=draft --set rating=8
track meta --title "<note>" --set "authors=[[Ada Lovelace]], [[Alan Turing]]"
track meta --title "<note>" --unset rating
```

`--set` accepts repeated `key=value` pairs; `--unset` removes a key. Values are typed from their text (see Typing Rules); a comma-separated value becomes a list.

### `--edit` applies whole state

`track meta --edit -` reads a **complete metadata document** from stdin and applies it atomically — it replaces the whole editable state (title, tags, description, image, icon, props), not a patch. A changed title is a rename. To use it safely: print the current document with a plain `track meta` call, modify it, and pipe the full result back. For point edits prefer `--set`/`--unset`.

```sh
track meta --title "<note>" --edit -    # full metadata document on stdin
```

## Inline Fields (`key:: value`)

The sidecar is the home for note-level facts. When a data point belongs **in the prose** — a `weight:: 68.2` line in a journal is a line of the journal — write it directly in the body. Three placements:

```markdown
status:: draft
- rating:: 8
Met with [owner:: [[Ada Lovelace]]] about the plan.
```

- **Whole line** — `key:: value` on its own line.
- **List item** — `- key:: value` (numbered items included).
- **Bracketed, mid-sentence** — `[key:: value]` inside a paragraph.

Inline fields are indexed into the same property index as sidecar values, each with the body line it came from, and keep rendering as the text you wrote — they are data and prose at once. Code is never scanned: `std::vector` in a fence stays code, and a `[key:: value]` inside inline code never becomes data.

Choosing a home: a fact that is not prose (a title, a tag, an icon, a status that describes the note itself) belongs in the sidecar via `track meta`; a fact that reads as part of the text belongs inline.

## `up`: The One Structural Property

`up` is an ordinary property with one conventional meaning: it names the note's parent, and track derives hierarchy navigation from it — breadcrumbs, a children list, and `track nav`. There is no outline file to maintain. Obsidian vaults and org-mode use the same `up`/`parent` convention.

```markdown
up:: [[Projects]]
```

```sh
track meta --title "<note>" --set "up=[[Projects]]"
track nav --id <id>    # ancestor trail + children, as JSON (--id or --path only, not --title)
```

- **Only a link-typed value counts.** `up:: draft` is just a string property and creates no parent.
- Several parents are allowed: the breadcrumb trail follows the first, every parent still lists the note among its children.
- A cycle (`A → B → A`) is harmless — the trail stops where it would repeat.
- The note view does not show `up` in the property strip: the breadcrumbs *are* its display.

## Typing Rules

The same detection applies everywhere — sidecar `props`, inline fields, and `--set` values:

| Value text | Type |
| --- | --- |
| `true`, `false` | boolean |
| `8`, `-3.5` | number |
| `2026-07-11` (a real calendar date) | date |
| `[[Title]]` | link |
| `go, lua` (top-level commas) | list — each item typed on its own |
| anything else | string |

A link value keeps its resolution key (`[[Ada Lovelace|Ada]]` stores `Ada Lovelace`) and resolves like any wikilink. Commas inside `[[...]]` do not split a list.

## Schema and Diagnostics

Optionally declare a schema in the track config file (`config.yml` under the track config directory, e.g. `~/.config/track/config.yml`; `TRACK_CONFIG` overrides — not a vault file) to constrain keys:

```yaml
properties:
  status:
    type: string
    values: [draft, review, done]
  rating:
    type: number
```

`type` is one of `string`, `number`, `boolean`, `date`, `link`; `values` is an optional enum. Undeclared keys stay unconstrained. `track doctor` reports every value that breaks the schema, with the note and body line it came from, and the editor LSP completes declared keys and values.

## Where Properties Show Up

- The web workspace and published site show a property strip above the body: sidecar values first, then inline fields in body order.
- `track meta` prints them as JSON for scripts.
- The index stores every value typed and with line provenance for filtering and search.
