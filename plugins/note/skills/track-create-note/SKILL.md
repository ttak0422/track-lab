---
name: track-create-note
description: track のノート、ジャーナル、テンプレートを作成・更新するときに使う。共有すべき決定や発見を記録する。
---

# Track Create Note

CLI を使う前に[実行環境](../track/references/runtime.md)を読む。

ノート作成・ID・サイドカーメタデータ・インデックス・リンク解決の真実の情報源として `track` CLI を使う。track のソースリポジトリでは、`go run ./cmd/track` を `track` の代わりとして使ってよい。

track ボールトは**開発者とエージェントの共有記録**である。決定・発見・残作業。相手（人間でもエージェントでも）が後で問い直さずに行動できるように各ノートを書くこと。経緯だけでなく結論を述べ、依存するノートをリンクする。

## 前提条件

- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは通常、単一行の JSON を出力する（`export` は Markdown）。stdout を JSON としてパースし、exit code 1 の `{"error":...}` は失敗として扱う。
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
track journal --body ""              # today
track journal --offset -1 --body ""  # yesterday
track journal --offset 1 --body ""   # tomorrow
```

既存のノートに追記する。

```sh
track append --title "Title" --body "Additional Markdown"
track append --id 123 --tag project
```

## 図表や埋め込みを使う場合

図表には [描画フェンス](../track-markdown/references/DRAWING.md)、メディアには [埋め込み構文](../track-markdown/references/EMBEDS.md)を参照する。必要な種類の説明だけを読む。

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
