---
name: track-news-analysis
description: 時事トピック（相場の動き、政策判断、事件）を複数の独立したレンズで調査し、可視化・出典付きの分析 note を track vault に書き出す。複数視点の分析 note、ある事象の 多角分析/時事分析 を求められたとき、あるいは「analyze what happened around <date>」と頼まれたときに使う。単一の問いの調査は track-report と、日次/週次の反復ループは track-watch と組み合わせる。この skill は、複数の視点と chart を要する事象を対象とした一回きりの深掘りである。
---

# Track News Analysis

一つのニュース事象を、vault に二つの成果物として落とす。**多レンズの分析 note**（chart、タイムライン、
因果グラフ、出典付き）と、それがどう作られたかを記録する短い**作業メモ**である。調査は並列に Web 検索する
agent 群の Workflow として走り、note は track のリッチな構文で書かれ、図は埋め込む前にすべて検証される。

`track` CLI を真実の源として使う。シェルの環境変数 `TRACK_VAULT` に注意し、ユーザーが特定の vault を
指定していない限りは除去する（`env -u TRACK_VAULT`）。

## 前提条件

- Workflow ツール（agent は ToolSearch 経由で WebSearch/WebFetch を要する）。
- vault の `analysis` テンプレート（`track template list`）。無ければ、この skill の下記の構造から
  作成する。
- 相場系の事象では、`track-fetch-jquants`（J-Quants; `TRACK_JQUANTS_REFRESH_TOKEN`）が `data.source` の
  ローソク足に実 OHLCV を供給できる。認証情報が無ければ、調査した値をそのまま chart に埋め込む。

## Workflow

### 1. 事象とレンズを定める

事象を一文で書き出す。**ユーザーの前提をそのまま含める**こと。前提は検証すべき主張であって、
引き継ぐ事実ではない。レンズを 4〜6 個選ぶ。デフォルトの組み合わせが多くの場合に通用する。

1. 事実関係・定量データ (数字: 何がどの規模で起きたか、何と比べてどうか)
2. 国内要因 (国内の文脈と伏線)
3. 海外要因 (国際的な文脈)
4. キーパーソンの発言・政策 (正確な引用・タイムライン・言及されなかったことを伴う発言)
5. 前後の推移とその後 (前後の日々、数値があれば日次系列、専門家の見方)

### 2. 調査ワークフローを走らせる

同梱のスクリプト（この skill の base directory 内）で Workflow ツールを呼び出す。

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

スクリプトは sweep → 敵対的 verify → 完全性 critic の順に走り、**harvest-first**（収穫優先）である。
sweep が完了してから verifier が予算を消費するため、セッション上限に当たっても失われるのは検証であって
調査ではない。verify agent が（セッション上限で）死んだ場合は、次の方法で代替する: (a) agent 間での
数値の一致、(b) 計算の整合性（差分・パーセンテージ・週次合計）、(c) 重要な一次記事 2〜3 本を自分で
WebFetch する。どの方法が各重要主張を裏付けたかを記録すること。

### 3. 分析 note を書く

テンプレートから作成する: `track new --title "<YYYYMMDD> <event question>" --template analysis --tag analysis`。
分析 note は事象時点のスナップショットであり、日付付きタイトルと履歴が本体である。`report` タグは付けない。report の契約（無日期タイトル、時系列を積まない）はこの note 種には適用されない。
調査した素材で埋め、以下を絶対のルールとして扱う。

- 前提の検証が先: ユーザーの前提が誤りまたは不正確と判明したら、結論部の `[!IMPORTANT]` alert で
  一次ソースとともにそう述べる。判定の段落（`^premise`）を transclusion 用にアンカーする。
- 埋め込む前に図をすべて検証する: `viewspec` の JSON は使い捨てコピーに対して `track render --spec` で、
  `d2` ブロックは `d2` CLI で検証する（`link` などの予約語はノード名にしない）。mermaid の構文は保守的に
  保つ。壊れた fence はエラーボックスとして出力されてしまう。
- 出典を添えた chart: `display: "box"` のイベントマーカーのオーバーレイは事象ごとに `url` を持ち、chart が
  そのまま証拠の索引を兼ねる。期間は帯で、過去の基準値は閾値線で示す。
- 調査した日次系列（sweep の `daily_closes`）は、jq 一行で inline record になる。生成プログラムは不要:

  ```sh
  jq -c '.[] | {name: "<series>", time: .date, value: .close, change: .change}' closes.json
  ```

  その行を `metric` 種の viewspec に貼り付ける。`y[0]` を値の線として、`change` を `axis: "y2"` 上の
  棒として置く。`track-fetch-jquants` による実 OHLCV はこれを省略し、`data.source` で扱う。
- GFM 脚注で引用し、「primary-verified」（一次検証済み）と「agent-collected」（agent 収集）に分ける。
  未検証のものは `[!WARNING]` alert で示し、未解決の問い の下に checkbox として列挙する。
- sidecar メタデータを設定する: `track meta --description ... --set subject-date=... --set verify-status=...`
  （property のキーは ASCII のみ）。

### 4. 作業メモを記録しグラフを配線する

- 短いメモ note（`from [[<project>]]`、tag `memo`）: 何を走らせ、何が失敗し、何が分かり、機械化に値する
  候補は何か。優先度付きの task line として書く。
- 分析 note の `^premise` ブロックを、書き直さずにメモへ transclusion する。
- 両方をプロジェクト/task note からリンクし、触れた note を `track fmt` し、`track reindex` し、
  `track backlinks` で検証する。

## Verify

- `track export --title "<analysis note>"` がレンダリングできる。すべての fence は埋め込み前に検証済みである。
- `track backlinks` が、メモと project note が分析 note を指していることを示す。
- note のタイトル、前提の判定、未検証のまま残ったものをユーザーに伝える。note の再貼り付けではなく、
  短い一段落で。
