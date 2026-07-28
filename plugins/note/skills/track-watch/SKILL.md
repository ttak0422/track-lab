---
name: track-watch
description: Run a recurring watch loop over a topic in the track vault, at three thinking depths — light (the daily brief, token-lean, the day's moves / reactions to open concerns / new events), mid (the weekly review, trend + assumption check), and high (on-demand deep review, assumption excavation, break-scenario analysis, falsifiable forecasts). Use when the user asks for a daily brief, weekly review, 定点観測, デイリー/ウィークリー分析, a light/mid/high watch run, or to set up or continue a recurring news/market watch. Pairs with track-news-analysis, which deep-dives one event; this skill runs the loop between events.
---

# Track Watch

A watch is a loop, not a report. Each run reads what previous runs left behind, adds one day's (or
one week's) delta, and updates the shared state so the next run starts smarter. The vault **is** the
loop state; tags are the retrieval index. The one sin in this skill is re-researching what a
previous run already established.

Use the `track` CLI as the source of truth. Mind an ambient `TRACK_VAULT` in the shell — strip it
(`env -u TRACK_VAULT`) unless the user asked for a specific vault.

## Depth tiers

Runs are named by thinking depth, not cadence — the cadence is just each tier's usual schedule:

| Depth | Usual cadence | Output note | Focus |
| --- | --- | --- | --- |
| `light` | daily (the anchor run) | daily brief | the day's moves, reactions to open concerns, new events |
| `mid` | weekly | weekly review | trend over the week, assumption check against evidence |
| `high` | on demand (monthly, or when mid finds cracks) | weekly review + extra sections | assumption excavation, break scenarios, falsifiable forecasts |

## The loop state: three kinds of notes

| Note | Cadence | Tags | Role |
| --- | --- | --- | --- |
| watch note | standing, one per topic | `watch` + topic tag | accumulator: stance, open concerns, assumptions register, live chart |
| daily brief | daily | `daily` + topic tag | the day's delta — short |
| weekly review | weekly | `weekly` + topic tag | trend, assumption audit, forecasts |

Pick one kebab-case **topic tag** per watch (e.g. `jp-market`) and stamp it on every note of the
loop: `track search --query "#<topic> #daily"` then replays the history in one call.

### The watch note (created on first run)

`track new --title "<topic> 定点観測" --tag watch --tag <topic>` with:

- `## 概況` — the current stance, one paragraph, revised in place by weekly runs (history lives in
  the dated notes, not here). For market topics add a `viewspec` fence with
  `data.source: "<topic>.jsonl"` — the chart re-renders whenever the fetcher refreshes that file, so
  the dashboard stays current at **zero token cost** (`track-fetch-jquants` is cron-safe).
- `## 懸念` — open concerns as task lines, priority-tagged (`[#A]` = tomorrow's run checks first).
  This is what "事前に懸念していた事項" means mechanically: daily runs answer to this list, resolve
  items via `track task set ... --state DONE`, and append new ones.
- `## 前提` — the assumptions register: what the current stance silently depends on, made explicit,
  one list item each with inline props:

  ```markdown
  - 中東情勢は現状の低烈度衝突が続く [checked:: 2026-07-28] [trigger:: ホルムズ海峡の完全封鎖、または停戦合意]
  ```

  Slow-moving context (a geopolitical situation, a policy regime) lives here and is **not**
  re-researched on a cadence: a daily run only flags when a `trigger` fires; a weekly `high` run
  re-checks items that are stale or triggered. This is where token efficiency comes from.

## light — the daily brief, kept lean

Budget discipline: **no Workflow, no verification fleet.** One research pass — direct WebSearch in
the main loop, or at most one agent — with a handful of queries. The loop state does the heavy
lifting:

1. Read the state: the watch note (`track export`), its open concerns (`track tasks`), and the
   previous brief (`track search --query "#<topic> #daily"`, newest hit).
2. If the topic has a data feed, refresh it first:
   `track-fetch-jquants --code <code> --out <vault>/data/<topic>.jsonl` — numbers from the feed are
   already validated; never spend searches on what the feed answers.
3. Research exactly three questions, nothing else:
   - (a) did anything today respond to an open concern? — at most one query per open concern;
   - (b) what genuinely new events appeared?
   - (c) what were the day's moves/numbers (only where no feed covers them)?
4. Write the brief — `track new --title "<YYYYMMDD> <topic> daily" --tag daily --tag <topic>`:

   ```markdown
   from [[<topic> 定点観測]]

   ## 当日の動き
   ## 懸念への反応      ← one line per open concern; 「動きなし」 is a valid and useful answer
   ## 新規イベント
   ## 引き継ぎ          ← what this run changed in the watch note (resolved/added concerns, fired triggers)
   ```

   Keep it around 40 lines. No charts — the watch note's `data.source` chart carries the series.
5. Update the watch note: concern task transitions, new concerns appended, fired triggers noted on
   the register item.
6. If the day produced an event that deserves real analysis, do **not** deep-dive inside the brief:
   hand off to `track-news-analysis`, then link the analysis note from the watch note and the brief.

Verification is proportional: arithmetic against yesterday's numbers, plus one primary source for
any load-bearing number the brief asserts. Nothing more.

## mid — the weekly review

Main-loop work over material the dailies already gathered — no research fan-out:

1. Collect the week: `track search --query "#<topic> #daily"` → export the week's briefs.
2. Write `<YYYYMMDD> <topic> weekly` (tags `weekly` + topic):

   ```markdown
   from [[<topic> 定点観測]]

   ## 週間推移        ← numbers and events; one viewspec if the series moved meaningfully
   ## トレンド評価    ← against previous weeklies (#<topic> #weekly): what continued, what broke
   ## 前提の点検      ← walk the register; only items with contrary evidence this week get a re-check search
   ## 来週の注視点    ← feeds back into the watch note's concern list
   ```

3. Update the watch note: stance paragraph, concern list, `[checked::]` dates on the register.

## high — the deep review (on demand)

Runs monthly, or when mid keeps finding cracks in the register. Everything in mid, plus the bundled
workflow (in this skill's base directory):

```
Workflow({
  scriptPath: "<skill base dir>/weekly-workflow.js",
  args: {
    topic: "<topic>", today: "<YYYY-MM-DD>",
    stance: "<the watch note's 概況 paragraph>",
    week_digest: "<condensed digest of the week's briefs>",
    assumptions: [{ text, checked, trigger, due }],   // due: stale or triggered
    concerns: ["..."]
  }
})
```

The workflow runs harvest-first: **excavate → stress → forecast → critic**.

- *Excavate*: an adversarial agent names assumptions the stance depends on that the register does
  not yet list — the 暗黙の前提.
- *Stress*: each due/triggered/newly-excavated assumption (capped) gets an independent web check:
  current evidence, what would break it, the consequence if it breaks, and the recommended response.
- *Forecast*: expectations for the coming period inferred from past patterns — **every forecast
  carries a falsification marker** (何が起きたらこの予想を捨てるか); one without it is not written.
- *Critic*: a completeness pass over the whole review.

Results land in extra sections of the weekly note — `## 暗黙の前提の洗い出し`,
`## シナリオ(前提が壊れたら)`, `## 予想(反証条件つき)` — and new assumptions join the register with
today's `[checked::]` date.

## Cadence and loop execution

light (daily) is the anchor; mid closes each week; high runs when scheduled or triggered. A caveat
for looped execution: an OneDrive-backed vault is not writable from background sessions — run the
loop in an interactive session (`/loop`, or a scheduled interactive run); only the fetcher belongs
in cron.

## Verify

- `track backlinks` on the watch note shows the dated briefs/reviews accumulating.
- Open-concern task states match the latest 引き継ぎ section.
- Report the delta to the user (what moved, what got resolved, what fired) — not the whole brief.
