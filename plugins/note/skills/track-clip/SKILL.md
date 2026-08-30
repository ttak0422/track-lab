---
name: track-clip
description: track-fetch-web で Web ページをきれいな Markdown として読み、保存に値する場合は track ボールトにノートとして保存する。ユーザーが読む・分析する・クリップする・保存するための URL (オンラインドキュメント・記事・ブログ投稿など) を渡したときや、「このページをクリップして」 ("clip this page") と言ったときは WebFetch の代わりに使う。末尾が .md の URL (すでに Markdown なので、直接取得する) には使わないこと。ユーザーがページから手早く答えだけ欲しい場合は保存の手順を省略する。
---

# Track Clip

`track-fetch-web` はページを取得し、ナビゲーション・サイドバー・広告・その他の付帯要素を取り除き、残りを Markdown に変換する。WebFetch の代わりにこれでページを読むこと。出力はより小さく、すでにボールトの形式になっている。保存に値するページは、同じ出力をそのまま `track new` にパイプで渡せる。

## 前提条件

- 真実の情報源として `track` CLI を使う。track のソースリポジトリでは、`go run ./cmd/track` を代わりとして使ってよい。
- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは単一行の JSON を出力する (`export` は Markdown を出力する)。exit code 1 の `{"error":...}` は失敗として扱う。
- `track-fetch-web` を `PATH` 上に置く。これは track に付属する別バイナリであり、track 本体はネットワーク通信をしない。ソースリポジトリからは `go run ./cmd/track-fetch-web`。

## ページを読む

```sh
track-fetch-web --note "<url>"                 # Markdown note body on stdout
track-fetch-web --note --timeout 60s "<url>"   # the fetch timeout defaults to 30s
```

本文は出典行とリード画像で始まり、その後に内容が続く。

```markdown
[Source](https://example.com/essays/growing-tomatoes) — clipped 2026-07-26

![](https://example.com/images/tomatoes-lead.jpg)

Container gardening rewards small, steady adjustments…
```

デバッグするより想定しておくべき制限が2つある。JavaScript だけで描画されるページには抽出できる読み取り可能な HTML がないため、クリップはページのメタデータに落ちる。また、取得はプライベート・ループバック・リンクローカルアドレスを拒否する (SSRF ガード)。そのため内部ページは先にファイルへ保存し、URL ではなくパスとして渡す必要がある。

ユーザーがページから答えだけ欲しかった場合は、ここで止める。ノートを作成しない。

## ボールトにクリップする

本文を一度保存し、その後で読み取った内容からタイトルを選ぶ。

```sh
track-fetch-web --note "<url>" > /tmp/clip.md
```

タイトルはノートの同一性であり、ボールト全体で一意で、他の全ノートが使う `[[link]]` キーワードになる。ページ自身のタイトルから始めるが、サイトの付帯要素を取り除き (`Growing tomatoes | Example Blog` → `Growing tomatoes`)、ボールト内で単独では曖昧すぎるタイトルは明確化する。

作成前に既存のクリップを探す。`track new` はタイトル衝突で失敗し、同じページが別のタイトルで既に保存されていることがある。

```sh
track search --query "<title>" --scope title
track search --query "<domain>"           # matches the Source line in already-clipped bodies
```

それから、`clip` タグを付けて作成する (`--body` を省略すると stdin が本文になる)。

```sh
track new --title "<title>" --tag clip < /tmp/clip.md
track meta --title "<title>" --description "<one line on what the page says>"
```

すでに持っているページを再クリップする場合: 接尾辞付きタイトルを新たに作らず、そのノートの本文を置き換える。`track update --id <id> < /tmp/clip.md`。

今日のジャーナルにも記録しておくと、日付からもクリップに到達できる。`track journal` には `--body` を渡すこと。これがないとコマンドは stdin を読み込み、エージェントがハングする。

```sh
track journal --body ""                                        # ensure today's journal exists
track append --id "$(date +%Y%m%d)" --body "- [[<title>]]"     # journal ids are yyyyMMdd
```

## 本文を仕上げる

- 抽出器は通常の Markdown を出力するが、ページには track が文字どおり描画する構文 (`==highlight==`、`%%comments%%`、インラインの `#tags`、`![[file]]` 埋め込み) が残ることがある。これらを変換する。完全な表は **track-markdown** スキルにある。
- ノート (作成時の JSON がパスを出力する) に `track fmt <path>` を実行し、本文をボールトの正規形式に合わせる。
- このノートが関連するノートへ `[[links]]` を追加する。何からもリンクされないクリップは、二度と誰にも見つからないクリップである。

## データとしてのクリップ

`--note` を付けないと、このツールは Canonical Data Model レコードを1件 JSONL として出力する。これはすべての `track-fetch-*` ツールが従う契約であり、読書ログをグラフに供給できる。

```sh
track-fetch-web --out "$TRACK_VAULT/data/clips.jsonl" "<url>"   # prints a JSON summary including the title
```

`--out` はファイルを**上書き**するため、ログを蓄積するには stdout を追記する: `track-fetch-web "<url>" >> data/clips.jsonl`。この方法は、ユーザーが1ページを読みたいのではなく、クリップを時系列で集計・グラフ化したいときに使う。
