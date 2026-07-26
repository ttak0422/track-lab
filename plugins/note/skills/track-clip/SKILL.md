---
name: track-clip
description: Read a web page as clean Markdown with track-fetch-web, and save it into the track vault as a note when it is worth keeping. Use instead of WebFetch when the user provides a URL to read, analyze, clip, or save — online docs, articles, blog posts — or says "clip this page". Do NOT use for URLs ending in .md (already Markdown; fetch them directly), and skip the save step when the user only wants a quick answer from a page.
---

# Track Clip

`track-fetch-web` fetches a page, drops navigation, sidebars, ads, and the rest of the furniture, and converts what is left to Markdown. Read pages with it instead of WebFetch — the output is smaller and already in the vault's format. When a page is worth keeping, the same output pipes straight into `track new`.

## Preconditions

- Use the `track` CLI as the source of truth. In the track source repo, `go run ./cmd/track` is an acceptable substitute.
- Prefer the user's normal track config. `TRACK_VAULT` is for tests and one-off overrides.
- Commands print single-line JSON (`export` prints Markdown). Treat `{"error":...}` with exit code 1 as failure.
- `track-fetch-web` on `PATH`. It ships with track as a separate binary — track itself never talks to the network. From the source repo: `go run ./cmd/track-fetch-web`.

## Read a page

```sh
track-fetch-web --note "<url>"                 # Markdown note body on stdout
track-fetch-web --note --timeout 60s "<url>"   # the fetch timeout defaults to 30s
```

The body starts with a provenance line and the lead image, then the content:

```markdown
[Source](https://example.com/essays/growing-tomatoes) — clipped 2026-07-26

![](https://example.com/images/tomatoes-lead.jpg)

Container gardening rewards small, steady adjustments…
```

Two limits to expect rather than debug: a page rendered entirely by JavaScript has no readable HTML to extract, so the clip degrades to the page metadata; and fetches refuse private, loopback, and link-local addresses (an SSRF guard), so an internal page has to be saved to a file first and passed as a path instead of a URL.

If the user only wanted an answer from the page, stop here. Do not create a note.

## Clip it into the vault

Save the body once, then choose the title from what you just read:

```sh
track-fetch-web --note "<url>" > /tmp/clip.md
```

The title is the note's identity — unique vault-wide, and the `[[link]]` keyword every other note will use. Start from the page's own title, but strip the site furniture (`Growing tomatoes | Example Blog` → `Growing tomatoes`) and disambiguate one that is too generic to stand alone in a vault.

Look for an existing clip before creating: `track new` fails on a title collision, and the same page may already be saved under a different title.

```sh
track search --query "<title>" --scope title
track search --query "<domain>"           # matches the Source line in already-clipped bodies
```

Then create it, tagged `clip` (stdin becomes the body when `--body` is omitted):

```sh
track new --title "<title>" --tag clip < /tmp/clip.md
track meta --title "<title>" --description "<one line on what the page says>"
```

Re-clipping a page you already have: replace that note's body rather than inventing a suffixed title — `track update --id <id> < /tmp/clip.md`.

Optionally log it in today's journal so the clip is also reachable by date. Pass `--body` to `track journal`: without it the command reads stdin and will hang an agent.

```sh
track journal --body ""                                        # ensure today's journal exists
track append --id "$(date +%Y%m%d)" --body "- [[<title>]]"     # journal ids are yyyyMMdd
```

## Finish the body

- The extractor emits ordinary Markdown, but a page can still carry syntax track renders literally — `==highlight==`, `%%comments%%`, inline `#tags`, `![[file]]` embeds. Convert them; the **track-markdown** skill has the full table.
- Run `track fmt <path>` on the note (the create JSON prints its path) so the body matches the vault's canonical formatting.
- Add `[[links]]` to the notes this one relates to. A clip nothing links to is a clip nobody finds again.

## Clipping as data

Without `--note` the tool emits one Canonical Data Model record as JSONL — the contract every `track-fetch-*` tool follows — so a reading log can feed a chart:

```sh
track-fetch-web --out "$TRACK_VAULT/data/clips.jsonl" "<url>"   # prints a JSON summary including the title
```

`--out` **overwrites** the file, so accumulate a log by appending stdout instead: `track-fetch-web "<url>" >> data/clips.jsonl`. Use this path when the user wants clips counted or plotted over time, not when they want one page to read.
