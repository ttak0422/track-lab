---
name: track-news-analysis
description: Research a current-events topic (a market move, a policy decision, an incident) from multiple independent lenses and file a visualized, source-cited analysis note in the track vault. Use when the user asks for a multi-angle analysis note, a 多角分析/時事分析 of an event, or to "analyze what happened around <date>". Pairs with track-report for single-question investigations and with track-watch for the recurring daily/weekly loop; this skill is the one-shot deep dive for events that need several perspectives and charts.
---

# Track News Analysis

Turn one news event into two vault artifacts: a **multi-lens analysis note** (charts, timeline,
causal graph, cited sources) and a short **work memo** recording how it was made. The research runs
as a Workflow of parallel web-searching agents; the note is written with track's rich constructs and
every figure is validated before it is embedded.

Use the `track` CLI as the source of truth. Mind an ambient `TRACK_VAULT` in the shell — strip it
(`env -u TRACK_VAULT`) unless the user asked for a specific vault.

## Preconditions

- The Workflow tool (agents need WebSearch/WebFetch via ToolSearch).
- A vault `analysis` template (`track template list`); create one from the skill's structure below if
  absent.
- For market events: `track-fetch-market` (J-Quants; `TRACK_JQUANTS_REFRESH_TOKEN`) can supply real
  OHLCV bars for a `data.source` candlestick. Without credentials, chart researched values inline.

## Workflow

### 1. Frame the event and its lenses

Write down the event as one sentence **including the user's premise verbatim** — premises are
claims to verify, not facts to inherit. Pick 4–6 lenses; the default set generalizes well:

1. 事実関係・定量データ (the numbers: what exactly happened, how big, compared to what)
2. 国内要因 (domestic context and preconditions)
3. 海外要因 (international context)
4. キーパーソンの発言・政策 (statements with exact quotes, timeline, and what was NOT said)
5. 前後の推移とその後 (the days before/after, daily series if numeric, expert views)

### 2. Run the research workflow

Invoke the Workflow tool with the bundled script (in this skill's base directory):

```
Workflow({
  scriptPath: "<skill base dir>/workflow.js",
  args: {
    event: "<one-sentence event description, premise included>",
    today: "<YYYY-MM-DD>",
    lenses: [{ key: "facts", focus: "<lens instruction>" }, ...]   // optional; defaults built in
  }
})
```

The script runs sweep → adversarial verify → completeness critic, **harvest-first**: sweeps complete
before verifiers spend budget, so hitting a session limit loses verification, never the research.
If verify agents die (session limits), fall back to: (a) cross-agent number agreement, (b) arithmetic
consistency (deltas, percentages, week sums), (c) WebFetch the 2–3 load-bearing primary articles
yourself. Record which method backed each key claim.

### 3. Write the analysis note

Create from the template: `track new --title "<YYYYMMDD> <event question>" --template analysis --tag report`.
Fill it with the researched material, and treat these as hard rules:

- **Premise check first**: if the user's premise turned out wrong or imprecise, say so in an
  `[!IMPORTANT]` alert in the conclusion, with the primary sources. Anchor the verdict paragraph
  (`^premise`) for transclusion.
- **Validate every figure before embedding**: `viewspec` JSON via `track render --spec` on a scratch
  copy; `d2` blocks via the `d2` CLI (reserved words like `link` are not node names); keep mermaid
  syntax conservative. A broken fence ships as an error box.
- Chart with sources attached: event-marker overlays with `display: "box"` carry a `url` per event,
  so the chart doubles as an index of evidence. Bands for periods, threshold lines for historical
  baselines.
- Researched daily series (the sweep's `daily_closes`) become inline records with one jq line — no
  generator program needed:

  ```sh
  jq -c '.[] | {name: "<series>", time: .date, value: .close, change: .change}' closes.json
  ```

  Paste the lines into a `metric`-kind viewspec: `y[0]` the value as a line, `change` as bars on
  `axis: "y2"`. Real OHLCV from `track-fetch-market` skips this entirely — `data.source` it.
- Cite with GFM footnotes, split into "primary-verified" and "agent-collected". Flag anything
  unverified in a `[!WARNING]` alert and list it under 未解決の問い as checkboxes.
- Set sidecar metadata: `track meta --description ... --set subject-date=... --set verify-status=...`
  (ASCII property keys only).

### 4. Record the work memo and wire the graph

- A short memo note (`from [[<project>]]`, tag `memo`): what ran, what failed, what was learned,
  candidates worth mechanizing — as task lines with priorities.
- Transclude the analysis note's `^premise` block into the memo instead of restating it.
- Link both from the project/task note, `track fmt` the touched notes, `track reindex`, then verify
  with `track backlinks`.

## Verify

- `track export --title "<analysis note>"` renders; every fence was validated pre-embed.
- `track backlinks` shows the memo and project note pointing at the analysis note.
- Tell the user the note titles, the premise verdict, and what remains unverified — in one short
  paragraph, not a re-paste of the note.
