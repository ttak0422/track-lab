---
name: track-create-note
description: track CLI を使って、track ボールトにリンク付き Markdown ノート・ジャーナル・テンプレート由来のノートを作成または開く。ボールトは開発者とエージェントの共有知識源なので、永続的な発見・決定・残作業は、明示的な「ノートを取って」を待たず、発生し次第自発的にそこへ記録する。ユーザーがノートを取るよう頼んだとき、タイトルでノートを作成/開くとき、今日/昨日/明日のジャーナルを作成するとき、テンプレートからノートを作成するとき、ノートテンプレートを管理するときにも使う。
---

# Track Create Note

ノート作成・ID・サイドカーメタデータ・インデックス・リンク解決の真実の情報源として `track` CLI を使う。track のソースリポジトリでは、`go run ./cmd/track` を `track` の代わりとして使ってよい。

track ボールトは**開発者とエージェントの共有記録**である。決定・発見・残作業。相手 (人間でもエージェントでも) が後で問い直さずに行動できるように各ノートを書くこと。経緯だけでなく結論を述べ、依存するノートをリンクする。

## 前提条件

- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは単一行の JSON を出力する。stdout を JSON としてパースし、exit code 1 の `{"error":...}` は失敗として扱う。
- タイトルはリンク語である。本文で `[[Title]]` を使って関連ノートをリンクする。
- 本文テキストは Markdown の見出しで始まってよい。ノートタイトルはサイドカーメタデータに保存される。

## ノートの作成とオープン

新しいノートを作成し、タイトルが既に存在する場合は失敗する。

```sh
track new --title "Title" --body "Markdown body" --tag project
```

タイトルで冪等に作成または開く。

```sh
track open --title "Title" --body "Initial body used only when created"
```

ジャーナルを開くか作成する。

```sh
track journal              # today
track journal --offset -1  # yesterday
track journal --offset 1   # tomorrow
```

既存のノートに追記する。

```sh
track append --title "Title" --body "Additional Markdown"
track append --id 123 --tag project
```

## 本文のリッチコンテンツ

ノート本文は散文だけではない。内容が構造的な場合は、段落や ASCII の図よりも、対応する構文を使うこと:

| 構文 | フェンス / 構文 | 用途 |
| --- | --- | --- |
| ダイアグラム | ` ```mermaid `, ` ```dot `, ` ```d2 ` | フロー、シーケンス、ER、状態機械。色は使わない (下記参照) |
| マインドマップ | ` ```mindmap ` | インデント付きアウトラインをマインドマップとして描画 |
| チャート | ` ```viewspec ` | ボールト内の JSONL データをプロット |
| クエリ | ` ```track-query ` | ノート上のライブなテーブル/ボード/ギャラリー/カレンダー |
| ダッシュボード | ` ```dashboard ` | 最近/ピン留めのウィジェット |
| Babel | ` ```lua :name hello :results output ` | 実行可能なコードブロック。結果はサイドカーに保持され、noweb で合成、ファイルへタングル可能 |
| 埋め込み | 単独行の `![alt](url)` | YouTube、Google マップ、ツイート、PDF、`assets/` メディア |

完全な構文は track リポジトリのヘルプボールト (`docs/help/note/`。Diagrams、Charts、Embeds などのノート) にあり、ヘルプサイトにも公開されている。

### ダイアグラムを書く

ダイアグラムは読者のテーマから色を取り、テーマが変わると再描画する。よってソースから色を除くこと。`style`/`classDef` の fill なし、`%%{init: …}%%` の `themeVariables` なし、`fillcolor`/`bgcolor` なし。ダイアグラムに書き込んだ色は*両方の*テーマで保持されるため、一方は他方向けに描かれたダイアグラム、つまり暗いノード上の暗いテキストを表示することになる。代わりに形・ラベル・レイアウトで区別を持たせる。**track-markdown** スキルにその規則の完全版があり、色が内容そのものになる唯一のケースも含まれている。

ダイアグラムは縦に伸ばす。`flowchart` は `TB` を既定にし、`LR` は3〜4ノードの短い流れに限る。本文カラムは既定 40em で、横に伸びた図はそこへ収めるために縮小され、ノードの文字が読めなくなる。縦に伸びる図はどの面でも同じ大きさで読める。幅が要素数で決まる `sequence` や `gantt` は、向きではなく参加者や行の数を絞る。

ノードが十数個を超えて辺が交差し始めたら、レイアウトエンジンを ELK に替える。mermaid は図の frontmatter に `config: { layout: elk }`、`d2` は本文の先頭に `vars: { d2-config: { layout-engine: elk } }` と書く。書き方は **track-markdown** スキルにある。

### チャートを書く

viewspec に書くのは**何を意味するか**であって、どう見えるかではない。色・大きさ・目盛りはテーマとレンダラーが決める。スキーマが未知フィールドを拒否するので書けるものは元から絞られているが、テーマの外へ出られる穴が1つある。`color.colors` は生の CSS 色を受け取るので、色そのものが意味を持つとき (買いと売り、合格と不合格) だけ使う。

`title` には**発見そのもの**を一文で書く。「AAPL close」ではなく「決算後に前四半期の高値を割り込んだ」である。`Jan` や `Chrome` は自分が何者か名乗るが、`26` や `0.42` は名乗らない。その名乗りを与えるのが見出しであり、測った対象と単位は `encoding.x.title` と `encoding.y[].title` が担う。自前のキャプションを持つ図では省いてよい。省いても壊れず、軸ラベルが代わりを務める。

埋め込む前に、使い捨てのコピーを通す。

```sh
track render --spec /tmp/spec.json --out /tmp/spec.html
```

成功すると `{"path": …, "records": N}` を返す。`N` が想定した件数かを見る。そのうえで確かめる。

- `data.kind` が正準の5種 (`event` / `price` / `metric` / `entity` / `annotation`) のどれかである。
- `encoding` が参照する `field` がすべて実在する。kind の定義済みフィールドか、レコードが実際に持つ追加フィールドである。
- 種類に必要なチャネルが揃っている。`treemap` は `size`、`rect` は量的な `color`、`candlestick` は OHLC を含意する。
- `title` が列名ではなく結論になっている。
- 大きなデータを `data.records` に貼っていない。ファイルは `data.source` で指す。
- 合計行と内訳行が同じ系列に混ざっていない。積み上げや色分けで二重に数えられる。

## テンプレートによる作成

使う前にテンプレートを作成または開く。

```sh
track template new --name meeting
track template open --name meeting
track template list
```

テンプレートファイルは `template/` の下にあり、ディレクティブで始まる。

```markdown
<!-- track-template
name: meeting
-->
# {{ title }}

date: {{ date }}
kind: {{ kind }}
id: {{ id }}
```

サポートされる置換は安全な組み込みのみである。`{{ title }}`、`{{ id }}`、`{{ date }}`、`{{ kind }}`。ディレクティブは生成されたノートから除去される。

ノートやジャーナルを作成するときにテンプレートを使う。

```sh
track new --title "Project meeting" --template meeting
track open --title "Project meeting" --template meeting
track journal --offset 0 --template daily
```

`--body` と `--template` は相互に排他的である。`track open --template` と `track journal --template` は、新しいファイルを作成するときだけテンプレートを使う。既存のノート/ジャーナルは変更されずに返される。

## 検証

作成したノートを確認する。

```sh
track resolve --term "Title"
track export --title "Title"
```

## ユーザーへの報告

ノートを書き換えたら、ユーザーへの報告にそのタイトルを含める。ボールトには多くのノートがあるため、「ノートに記録しました」「ノートを更新しました」のような報告だけでは、どれが変わったのか伝わらない。操作と対象のタイトルを1行で述べる。

> ノート (`<Title>`) を作成しました。
>
> ノート (`<Title>`) の `<見出し>` に追記しました。
