---
name: track-search-notes
description: track ノートの検索・閲覧や、保存済みの決定・過去の作業を確かめるときに使う。バックリンクとグラフの読み取りも扱う。
---

# Track Search Notes

CLI を使う前に[実行環境](../track/references/runtime.md)を読む。

ノート検索・インデックス・リンク解決・バックリンク・グラフクエリの真実の情報源として `track` CLI を使う。track のソースリポジトリでは、`go run ./cmd/track` を `track` の代わりとして使ってよい。

## 前提条件

- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは通常、単一行の JSON を出力する（`export` は Markdown）。stdout を JSON としてパースし、exit code 1 の `{"error":...}` は失敗として扱う。
- このスキルは読み取り専用の調査に使う。ノートの作成・追記が必要なタスクでは `track-create-note` を使う。

## 検索

ノートのタイトルとインデックス済みフィールドを横断して検索する。

```sh
track search --query "distributed systems" --limit 20
```

範囲を絞り込む。

```sh
track search --scope title --query "roadmap"
track search --scope body --query "TODO"
```

`#tag` の語でタグ絞り込みができる。複数のタグは残りのテキストと組み合わされる。

```sh
track search --query "#project"
track search --query "#graph #web Workspace"
```

結果には、ノート ID・タイトル・ファイル種別・利用可能な場合はパス・タグ・本文ヒット時の本文スニペットと行番号が含まれる。ヒットしない検索は空の `results` 配列を返す。

マシン設定で名前付きボールトが登録されている場合（`vaults:`）、検索はアクティブなボールトと登録済みの全ボールトを横断する。各ヒットには `vault` 名（`""` = アクティブな未登録ボールト）が付き、応答には到達不能なボールト用の `unavailable` 配列が追加される。ノート ID はボールト内でのみ一意なので、別のボールトからのヒットを追うときは `--vault <name>`（グローバルフラグ、どのコマンドでも可）を渡す。`--vault NAME` は検索自体もそのボールト1つに限定する。

ノートは他ボールトを `[[vault:title]]` の形で参照できる（プレフィックスは登録済みボールト名でなければならない）。`track resolve --term "vault:title"` はそのような参照を解決し、`track backlinks` はボールトをまたぐ内向き参照を `external` の下に、到達不能なボールトを `unavailable` の下に列挙する。

## 解決と閲覧

完全一致のタイトル/リンク語をノートに解決する。

```sh
track resolve --term "Title"
```

既知ノートの完全な Markdown を読む。

```sh
track export --title "Title"
track export --id 123
track export --path /path/to/note.md
```

ノートの内容について断定する前に `export` を使うこと。

## 質問に必要な根拠を読む

1. 質問と必要な根拠を決め、検索・閲覧の上限を置く。指定がなければ検索3回、本文を開くノート5件から始める。
2. タイトル検索で候補を絞り、必要なら本文検索やバックリンクを使う。候補の選択と根拠の確認を分け、タイトルやスニペットだけで回答しない。
3. 選んだノートを `export` し、見出しから必要な節とその脚注を読む。部分読み出しがない CLI では全文を取得して手元で節を選ぶ。取得量が減ったとは報告しない。
4. 主張に対応する本文、版、位置を確認してから回答する。引用先の見出し・ブロックが存在するか確認し、欠けた位置を推測で補わない。
5. 相反する根拠は資料の時点とともに示す。上限到達、到達不能な vault、未読の候補を未調査範囲として残し、網羅的な調査と表現しない。

複数の質問を比較するときは、質問と期待する根拠ノート・位置を固定し、従来の検索とこの手順それぞれの取り逃し、検索回数、開いた件数、取得文字数を記録する。
一致しなかった根拠も残す。意味検索の追加は、実際の質問で不足を確認してから判断する。

## リンクとグラフ

内向きリンクを調べる。

```sh
track backlinks --id 123
track backlinks --path /path/to/note.md
```

ノート周辺のローカルノートグラフを調べる。

```sh
track graph --id 123
track graph --path /path/to/note.md
```

バックリンクとグラフの出力は JSON であり、ユーザーが生の出力を求める場合を除き、ユーザー向けに要約すべきである。
