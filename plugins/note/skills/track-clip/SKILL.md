---
name: track-clip
description: Web ページを track 用の Markdown として読む、またはボールトへクリップするときに使う。回答だけの依頼では保存しない。
---

# Track Clip

CLI を使う前に[実行環境](../track/references/runtime.md)を読む。
保存・再取得では[出典と時点の契約](../track/references/knowledge-intake.md)に従う。

`track-fetch-web` はページを取得し、ナビゲーション・サイドバー・広告・その他の付帯要素を取り除き、残りを Markdown に変換する。Markdown 抽出が必要な場合に使う。既に本文を取得できている場合は再取得しない。保存するときは取得記録と内容ハッシュを揃えてから `track new` に渡す。

## 前提条件

- 真実の情報源として `track` CLI を使う。実行ファイルは 1 回解決し、セッション中は使い続ける（通常は `PATH` 上の `track`、track のソースリポジトリ内では `go run ./cmd/track`。失敗した操作のエラーと保存状態を確認し、別の実行ファイルへ切り替えない）。
- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは単一行の JSON を出力する（`export` は Markdown を出力する）。exit code 1 の `{"error":...}` は失敗として扱う。人間向けと JSON を選べる場合は `--json` を付ける。
- `track-fetch-web` を `PATH` 上に置く。これは track に付属する別バイナリであり、track 本体はネットワーク通信をしない。ソースリポジトリからは `go run ./cmd/track-fetch-web` を使う。`track` と同じく 1 回解決して使い続ける。

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

デバッグするより想定しておくべき制限が2つある。JavaScript だけで描画されるページには抽出できる読み取り可能な HTML がないため、クリップはページのメタデータに落ちる。また、取得はプライベート・ループバック・リンクローカルアドレスを拒否する（SSRF ガード）。そのため内部ページは先にファイルへ保存し、URL ではなくパスとして渡す必要がある。

回答や実装の資料として読む依頼なら、取得した本文で元の作業を続ける。ノート保存は依頼範囲に含まれる場合に行う。

## ローカル PDF を読む

Poppler の `pdfinfo` と `pdftotext` を `PATH` に用意し、同梱スクリプトで取得済み PDF を抽出する。macOS では `brew install poppler`、Nix では `nix shell nixpkgs#poppler-utils` で導入できる。OCR は行わない。

```sh
python3 scripts/extract_pdf.py input.pdf --text-out /tmp/input.txt --original-out /tmp/input.pdf
python3 scripts/extract_pdf.py input.pdf --text-out /tmp/input.txt --original-out /tmp/input.pdf --timeout 60
```

本文は物理ページごとに `\f` で終わる UTF-8 である。JSON 出力の `text_path`、`original_path`、`page_count`、`empty_pages`、`source_sha256`、`text_sha256`、`extraction_method`、`warnings` を取得記録に使う。一部の空ページは警告付きで成功し、全ページが空なら OCR が必要な可能性を示して失敗する。依存不足、破損、タイムアウト、ページ境界不整合も失敗であり、本文・原本ファイルを残さない。入力 PDF と既存の出力ファイルは上書きしない。

スクリプトは入力を一度確保し、その同じバイト列から本文と `source_sha256` を作る。原本を保存する場合も入力パスを再読込せず、この確保済みバイト列を使う。抽出だけの依頼ではノートや原本を保存しない。

## ボールトにクリップする

本文を一度作業ファイルへ保存し、その後で読み取った内容からタイトルを選ぶ。版として保存する前に下記の「本文を仕上げる」を済ませ、ハッシュ対象を確定する。

```sh
track-fetch-web --note "<url>" > /tmp/clip.md
```

タイトルはノートの同一性であり、ボールト全体で一意で、他の全ノートが使う `[[link]]` キーワードになる。ページ自身のタイトルから始めるが、サイトの付帯要素を取り除き（`Growing tomatoes | Example Blog` → `Growing tomatoes`）、ボールト内で単独では曖昧すぎるタイトルは明確化する。

作成前に既存のクリップを探す。`track new` はタイトル衝突で失敗し、同じページが別のタイトルで既に保存されていることがある。

```sh
track search --query "<title>" --scope title
track search --query "<domain>"           # matches the Source line in already-clipped bodies
```

それから、`clip` タグを付けて作成する（`--body` を省略すると stdin が本文になる）。

```sh
track new --title "<title>" --tag clip < /tmp/clip.md
track meta --title "<title>" --description "<one line on what the page says>"
```

再クリップでは元の所在と内容ハッシュを照合し、同じ版なら既存ノートを使う。内容が変わった場合だけ版ノートを作り、旧本文と引用先を保持する。
取得本文に要約を混ぜない。要約が必要なら別の生成物として入力版と生成日時を残す。

今日のジャーナルにも記録しておくと、日付からもクリップに到達できる。既存本文を確認し、同じ版へのリンクがある場合は追記しない。`track journal` には `--body` を渡すこと。これがないとコマンドは stdin を読み込み、エージェントがハングする。

```sh
track journal --body ""                                        # ensure today's journal exists
track append --id "$(date +%Y%m%d)" --body "- [[<title>]]"     # journal ids are yyyyMMdd
```

## 本文を仕上げる

- 抽出器の出力を版として確定する前に必要な機械的変換を行い、変換方法とハッシュ対象を記録する。構文の扱いは **track-markdown** スキルを参照する。原文を変更する変換が必要なら、取得本文を添付として保持し、表示用本文を分ける。
- `track fmt` は版の確定前に行う。確定後の取得本文へ整形や関連リンクを追記しない。
- ジャーナルや関連ノートから版ノートへリンクし、`track export` と `track meta` で本文・ハッシュ・取得日時を確認する。

## データとしてのクリップ

`--note` を付けないと、このツールは Canonical Data Model レコードを1件 JSONL として出力する。これはすべての `track-fetch-*` ツールが従う契約であり、読書ログをグラフに供給できる。

```sh
track-fetch-web --out "$TRACK_VAULT/data/clips.jsonl" "<url>"   # prints a JSON summary including the title
```

`--out` はファイルを**上書き**するため、ログを蓄積するには stdout を追記する: `track-fetch-web "<url>" >> data/clips.jsonl`。この方法は、ユーザーが1ページを読みたいのではなく、クリップを時系列で集計・グラフ化したいときに使う。
