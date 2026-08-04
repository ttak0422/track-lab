---
name: track-markdown
description: Write and edit note bodies in track's Markdown dialect - wikilinks with level-based heading anchors, block anchors, transclusion, rich embeds, GitHub alerts, task lines with states and date tokens, sidecar metadata, inline properties, and the canonical track fmt style. Use when writing or editing note bodies in a track vault, or when wikilink/transclusion/alert/task/property syntax questions come up. For creating, searching, or renaming notes use the track skills; this skill covers body syntax only.
---

# track Markdown

track note bodies are CommonMark plus GFM (tables, task lists, strikethrough, footnotes with back-links) with a small set of track-specific constructs. Standard Markdown is assumed knowledge; this skill covers only the deltas: no frontmatter, level-based heading anchors, block-level-only transclusion, and exactly five alert types.

## Preconditions

- Use the `track` CLI as the source of truth. In the track source repo, `go run ./cmd/track` is an acceptable substitute.
- Prefer the user's normal track config. `TRACK_VAULT` is for tests and one-off overrides.
- Commands print single-line JSON (`export` prints Markdown). Treat `{"error":...}` with exit code 1 as failure.
- This skill is about syntax inside note bodies. Creating, reading, and renaming notes belongs to the track-create-note / track-search-notes / track skills.

## Internal Links (Wikilinks)

```markdown
[[Title]]                Link to the note titled exactly "Title"
[[Title|display]]        Same target, shown as "display" (first | splits)
[[Note#Heading]]         Link to the h1 heading "Heading" in Note
[[Note##Heading]]        Link to the h2 heading "Heading" in Note
[[Note#^block-id]]       Link to the block marked "^block-id" in Note
```

- Resolution is **exact title match** only. No paths, no `.md` extension, no aliases — the title is the one link keyword, and titles are unique vault-wide.
- **Heading anchors are level-based**: the number of `#` selects the heading **level**. `[[Note#foo]]` targets `# foo` (h1), `[[Note##bar]]` targets `## bar` (h2), up to h6. The first heading matching both level and text by document order wins.
- `[[#Heading]]` (same-note anchor with no title) is **not** a link. Write the full title or drop it.
- Never rename a note by editing its body H1 — retitle with `track rename` so backlinks are rewritten:

```sh
track rename --title "<old title>" --to "<new title>"
```

## Block Anchors

A trailing `^id` on a paragraph or list item marks that block as a link target:

```markdown
The paragraph worth pointing at. ^explicit-links

- a list item worth citing ^li-1
```

- The id is `^`, then an alphanumeric, then letters, digits, `-`, `_`. It must be whitespace-separated from the text, so `foo^2` stays prose.
- **Ids are manual only** — track never generates one, and the renderer hides the marker. Keep ids unique within a note; the first occurrence wins.
- Target them with `[[Note#^id]]`, or transclude just that block with `![[Note#^id]]` (the marker is stripped on the way in).

## Transclusion and Media Embeds

`![[Note]]` on its own line embeds another note's content. It is **block-level only** — inside running text it is not a directive (the `[[...]]` part is still a plain link). It counts as a real link (graph, backlinks, rename) and is never recursively expanded.

```markdown
![[Note]]                          Embed the whole note body
![[Note##Heading]]                 Embed one h2 section
![[Note#^block-id]]                Embed one marked block
![[Note|caption]]                  Embed with a caption
![[Note##Heading]] :only-contents  Drop the heading line itself
![[Note]] :lines 4-5,8             Embed only these 1-based lines
```

`![[image.png]]` is **not** image syntax in track. Media uses standard Markdown pointing at the vault's single top-level `assets/` directory:

```sh
track asset import "<file>"    # copies into assets/ and prints the assets/<file> reference
```

```markdown
![alt](assets/file.png)
```

A standalone `![alt](url)` line is a rich embed — image, YouTube player, Google Maps, tweet, PDF viewer, or Open Graph card. Inline images inside a paragraph stay plain images. See [EMBEDS.md](references/EMBEDS.md) for the full transclusion grammar and embed catalog.

## Alerts

track callouts are GitHub alerts. Exactly five types, nothing else:

```markdown
> [!NOTE]
> Useful context the reader should notice.
```

| Type | Use for |
| --- | --- |
| `[!NOTE]` | Useful context |
| `[!TIP]` | Helpful suggestion |
| `[!IMPORTANT]` | Must-not-miss information |
| `[!WARNING]` | Something that needs care |
| `[!CAUTION]` | Risky action |

Nothing beyond those five exists: no other types, no custom titles after the marker, no foldable `-`/`+` modifiers. A blockquote without a `[!TYPE]` marker is an ordinary quote.

## Task Lines

A GFM checkbox item is a task, and the character inside the brackets names its state, from a **fixed** five-state set:

```markdown
- [ ] TODO — not started
- [/] DOING — in progress
- [?] WAITING — blocked on someone else
- [x] DONE — finished
- [-] CANCELLED — will not happen
```

Any other marker character is not a task; the line stays an ordinary list item. Bracket tokens anywhere on the line add metadata:

| Token | Meaning |
| --- | --- |
| `[#A]` | Priority, `A` highest (any single letter) |
| `[sched:2026-07-18]` | The day you plan to work on it |
| `[due:2026-07-24]` | Deadline |
| `[done:2026-07-09]` | Completion date — **written by the CLI**, never by hand |

Dates are always `YYYY-MM-DD`, independent of the vault's display format. A `[n/m]` or `[p%]` cookie on a heading or parent list item counts the tasks beneath it (a heading counts to the next heading of the same or shallower level; a list item counts its deeper-indented children).

```markdown
### Release checklist [1/3]

- [/] Write the announcement post [#A] [due:2026-07-24]
- [ ] Refresh the screenshots [#B] [sched:2026-07-18]
- [x] Tag the release candidate [done:2026-07-09]
```

**Do not hand-edit a state marker.** Use the CLI so the `[done:]` stamp, the parent cookies, the sidecar transition log, and the index all stay consistent:

```sh
track task set --title "<note>" --line <n> --state DOING   # --line is 1-based, as reported by track search/export
track task cycle --title "<note>" --line <n>               # advance to the next state, wrapping
track tasks --overdue --sort priority                      # query across the vault (JSON)
```

An empty ` ```taskboard ` fence renders the note's tasks as a kanban board; it reads the task lines, not the fence body.

## Metadata and Properties

**Never write YAML frontmatter.** All note metadata (title, tags, created, description, image, icon, typed props) lives in a per-note sidecar under `.track/`, set via the CLI only — `--tag` flags on `new`/`open`/`append`/`update`, and `track meta` for the rest. The body H1 is ordinary content, not the title.

```sh
track meta --title "<note>" --set status=draft --set rating=8
track new --title "<title>" --tag <tag> --body "<body>"
```

Inline typed properties in bodies are supported for data that belongs in prose: `key:: value` as a whole line or list item, or `[key:: value]` mid-sentence. Note-level facts (title, tags, icon) go in the sidecar instead. One inline field is structural: `up:: [[Parent]]` declares the note's parent for hierarchy navigation. See [PROPERTIES.md](references/PROPERTIES.md) for the sidecar shape, `track meta` usage, typing rules, and the `up` relation.

## Math and Rendering Fences

Math is LaTeX by KaTeX: inline `$...$`, block `$$...$$`.

Fenced blocks that render instead of showing code — ` ```mermaid `, ` ```dot `/` ```graphviz `, ` ```d2 `, ` ```mindmap `, ` ```viewspec `, ` ```track-query `, ` ```dashboard `, ` ```taskboard `, and babel-annotated language fences — are catalogued in the **track-create-note** skill, with full syntax in the track repo's `docs/help/`. Two non-obvious ones: an **empty** ` ```mindmap ` fence renders the note's own heading tree, and a ` ```viewspec ` block's `data.source` resolves under the vault's `data/` directory.

**A diagram names no colors.** Diagram fences are handed to the renderer as written, initialized with the reader's current theme and re-drawn when the theme changes — so a diagram that specifies no colors is legible in light and dark alike. Colors written into the source pass through untouched and hold in *both* themes, which means one of the two shows a diagram drawn for the other: dark text on a dark node, a pale line on a pale page. Write no `style` or `classDef` fill, no `%%{init: …}%%` block setting `themeVariables`, and no `fillcolor`/`bgcolor` in `dot`. Where a distinction matters, carry it with shape, label, or layout, which read the same either way. The exception is a diagram whose colors *are* the content (a palette, a traffic-light legend); there, set both foreground and background explicitly so the pair is self-contained.

## House Style (track fmt)

`track fmt` rewrites notes into a canonical style. Generate Markdown that already conforms so `fmt` is a no-op:

- `-` bullets only, never `*` or `+`.
- Exactly two blank lines before and one after each heading (none before a heading that starts the document — leading blank lines are dropped).
- Collapse other blank-line runs to a single blank line.
- No trailing whitespace; file ends with exactly one newline.
- Always fence code blocks — indented code blocks are not protected by `fmt`.

```sh
track fmt --check --all    # CI check; track fmt <path> formats in place
```

## Unsupported Syntax

These render as literal text — never emit them: `%%comments%%` (use `<!-- HTML comments -->`), `==highlight==`, inline `#tags` in bodies (tags are sidecar-only; `#tag` works only in search queries), inline footnotes `^[text]` (use GFM `[^label]` + definition), sized images `![alt|300](url)`, and cross-note ` ```tasks ` or ` ```query ` blocks (use ` ```taskboard ` for the note's own tasks, `track tasks` / `track search` from the CLI for the vault).

Audio and video have no player: link the asset instead — `[label](assets/file.mp3)`.
