# Embeds Reference

Two distinct mechanisms: `![[Note]]` transcludes another **note's body**; a standalone `![alt](src)` line embeds **media or a URL**. Obsidian's `![[file.ext]]` file-embed syntax does not exist in track.

## Transclusion: `![[...]]`

```markdown
![[Note]]                          Whole note body
![[Note##Heading]]                 One section (## = h2; # count selects the level)
![[Note#^block-id]]                One block marked with a trailing ^block-id
![[Note|caption]]                  Caption via the display alias
![[Note##Heading]] :only-contents  Section body without the heading line
![[Note]] :lines 1-20              Line slice of the extracted region
```

Rules:

- **Block-level only.** The `![[...]]` must start the line (leading whitespace allowed) with nothing else but the option tail. Inside running text it is not a directive — its `[[...]]` part still counts as an ordinary link, the `!` stays literal.
- The link part shares the full wikilink grammar: exact-title resolution key, level-based `##heading` anchors, `#^id` block anchors, `|display` alias. It is also a plain link — it appears in the graph and backlinks, is rewritten by `track rename`, and gets the unresolved-link diagnostic when the title does not match.
- Without an anchor, the whole note body is embedded. With a heading anchor, the region runs from the matched heading line through the line before the next heading of the same or shallower level. Headings inside fenced code blocks neither match nor terminate the region. With a block anchor, the region is the marked paragraph or list item, and the `^id` marker is stripped.
- A non-matching anchor renders as **unresolved** — it does not fall back to the whole note (unlike link navigation, which falls back to the note top).
- Leading and trailing blank lines of the extracted region are trimmed.
- **Not recursive**: an include line inside the embedded region renders as text, so include cycles are harmless.

### Option tail

Options come after the closing `]]`, Org-style `:key value` (same shape as the `:height` embed option):

- `:only-contents` — drop the matched heading line and embed only its body. A no-op without an anchor.
- `:lines 4-5,8` — 1-based inclusive ranges over the extracted region (applied after `:only-contents`), concatenated in the order written; out-of-range parts are clipped.

Unknown keys and malformed values surface as diagnostics rather than being silently ignored.

## Asset Images

Local media lives in the vault's single top-level `assets/` directory:

```sh
track asset import "<file>"    # copies the file into assets/ and prints the reference
```

```markdown
![track logo](assets/logo.png)
```

On its own line the image renders as an embed; inline inside a paragraph it stays a plain image. A relative `assets/<file>` reference is served from the vault and never treated as a remote URL.

## Rich URL Embeds

A standalone `![alt](src)` line is routed by target:

| Target | Renders as |
| --- | --- |
| Image file (asset or URL) | Image |
| YouTube watch/share/embed URL | Inline player |
| Google Maps share/embed URL | Inline map (short `maps.app.goo.gl` links fall back to an OGP card) |
| Tweet URL (`x.com` / `twitter.com` status) | The actual post via Twitter widgets |
| PDF (asset or URL) | Paged slide-deck viewer |
| Text asset (`.txt`, `.json`, `.yaml`, `.csv`, `.sh`, ...) | Syntax-highlighted code block |
| Mermaid source asset (`.mmd` / `.mermaid`) | Rendered diagram |
| `.viewspec.json` asset | Interactive chart |
| HTML asset or `http(s)` page URL ending in `.html` | Sandboxed iframe |
| Any other `http(s)` page | Open Graph card (title, description, preview image) |

HTML embeds take a `:height` option after the embed (bare number = pixels; `%` or `vh` = share of the viewport height):

```markdown
![Widget](assets/widget.html) :height 480
![Map](assets/map.html) :height 90%
```

## Fence Renderers

Special fenced blocks render instead of showing code: ` ```mermaid `, ` ```dot `/` ```graphviz `, ` ```d2 `, ` ```mindmap `, ` ```viewspec `, ` ```track-query `, ` ```dashboard `, ` ```taskboard `, and babel-annotated language fences. The **track-create-note** skill catalogues what each is for; full syntax lives in the track repo's `docs/help/{diagrams,mindmaps,charts,query,dashboard,babel}.md`, also published on the help site.

Two behaviours worth knowing while writing a body:

- An **empty** ` ```mindmap ` fence renders the note's own heading tree — no fence content needed.
- A ` ```viewspec ` block's `data.records` keeps it self-contained, while `data.source` reads a JSONL file relative to the vault's `data/` directory. Invalid specs show the error at the block's position rather than failing the note.
