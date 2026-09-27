---
name: track-clip
description: Web ページやローカル PDF を読み、track 用の本文として抽出またはボールトへクリップするときに使う。回答だけの依頼では vault へ保存しない。
---

# Track Clip

CLI を使う前に[実行環境](../track/references/runtime.md)を読む。
保存・再取得では[出典と時点の契約](../track/references/knowledge-intake.md)に従う。

`track-fetch-web` はページを取得し、ナビゲーション・サイドバー・広告・その他の付帯要素を取り除き、残りを Markdown に変換する。Markdown 抽出が必要な場合に使う。既に本文を取得できている場合は再取得しない。保存するときは URL を一度だけ取得し、返された版の本文と原本を対にして `track` に渡す。

## 前提条件

- 真実の情報源として `track` CLI を使う。実行ファイルは 1 回解決し、セッション中は使い続ける（通常は `PATH` 上の `track`、track のソースリポジトリ内では `go run ./cmd/track`。失敗した操作のエラーと保存状態を確認し、別の実行ファイルへ切り替えない）。
- ユーザーの通常の track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き用である。
- コマンドは単一行の JSON を出力する（`export` は Markdown を出力する）。exit code 1 の `{"error":...}` は失敗として扱う。人間向けと JSON を選べる場合は `--json` を付ける。
- `track-fetch-web` を `PATH` 上に置く。これは track に付属する別バイナリであり、track 本体はネットワーク通信をしない。ソースリポジトリからは `go run ./cmd/track-fetch-web` を使う。`track` と同じく 1 回解決して使い続ける。
- 保存・引用が必要な Web クリップでは、使う前に選択済みバイナリの `--help` で `--snapshot-dir` を確認する。途中で別のバイナリへ切り替えない。

## ページを読む

```sh
track-fetch-web --note "<url>"                 # Markdown note body on stdout
track-fetch-web --note --timeout 60s "<url>"   # the fetch timeout defaults to 30s
```

`--note` の本文は取得日ラベルとリード画像で始まり、その後に内容が続く。取得日ラベルは日付精度の legacy 記録であり、正確な取得時刻や保存対象の原本を示さない。

```markdown
[Source](https://example.com/essays/growing-tomatoes) — clipped 2026-07-26

![](https://example.com/images/tomatoes-lead.jpg)

Container gardening rewards small, steady adjustments…
```

デバッグするより想定しておくべき制限が2つある。JavaScript だけで描画されるページには抽出できる読み取り可能な HTML がないため、クリップはページのメタデータに落ちる。また、取得はプライベート・ループバック・リンクローカルアドレスを拒否する（SSRF ガード）。そのため内部ページは先にファイルへ保存し、URL ではなくパスとして渡す必要がある。

回答や実装の資料として読む依頼なら、取得した本文で元の作業を続ける。ノート保存は依頼範囲に含まれる場合に行う。

## ローカル PDF を読む

`track-extract-pdf` で取得済み PDF を抽出する。Xberg の native PDF エンジンを使い、OCR は行わない。
Nix パッケージが Rust 製エンジンと Python 実行環境をまとめて固定する。
`PATH` にない場合は `nix run github:ttak0422/track-lab#extract-pdf -- <引数>` を使う。
このリポジトリの作業コピーを検証するときは、そのルートで `nix run path:.#extract-pdf -- <引数>` を使う。

```sh
track-extract-pdf input.pdf --text-out /tmp/input.txt --original-out /tmp/input.pdf --timeout 60
```

本文は物理ページごとに `\f` で終わる UTF-8 である。JSON 出力の `text_path`、`original_path`、`page_count`、`empty_pages`、`source_sha256`、`text_sha256`、`extraction_method`、`warnings` を取得記録に使う。一部の空ページは警告付きで成功し、全ページが空なら OCR が必要な可能性を示して失敗する。依存不足、破損、抽出器の診断、タイムアウト、ページ境界不整合も失敗であり、本文・原本ファイルを残さない。入力 PDF と既存の出力ファイルは上書きしない。

スクリプトは入力を一度確保し、その同じバイト列から本文、ローカルの `original_path`、`source_sha256` を作る。vault へ原本を保存する場合も入力パスを再読込せず、`original_path` を使う。抽出だけの依頼では vault へノートや原本を保存しない。PDF 本文には `track fmt`、出典行、要約を混ぜない。保存や引用まで依頼された場合は[出典と時点の契約](../track/references/knowledge-intake.md)の、選択済み CLI に対応する保存・引用機能へ進む。

## 固定版として Web クリップを保存する

`--snapshot-dir` は URL を一度取得し、成功時に manifest v1 を stdout へ1行出力する。指定した DIR はコンテナであり、その下に一意の `snapshot-*` 子ディレクトリが作られる。manifest の `original_path` は取得した `original.html`、`text_path` は抽出本文だけの `text.md` を指す。`text.md` に Source 行、要約、取得日を足してはならない。

```sh
snapshot_dir="$(mktemp -d)"
manifest_path="$snapshot_dir/manifest.json"
track-fetch-web --snapshot-dir "$snapshot_dir" "<url>" > "$manifest_path"
```

manifest について `schema_version: 1`、要求 URL、リダイレクト後の `final_url`、RFC 3339 の `retrieved_at`、SHA-256 形式、`original.html` と `text.md` の実在パスを確認する。実ファイルのハッシュを再計算し、manifest と一致するまでノートを作らない。保存には manifest が返したファイルをそのまま使い、URL や作業用コピーから取り直さない。

タイトルはノートの同一性であり、ボールト全体で一意で、他の全ノートが使う `[[link]]` キーワードになる。ページ自身のタイトルから始めるが、サイトの付帯要素を取り除き（`Growing tomatoes | Example Blog` → `Growing tomatoes`）、ボールト内で単独では曖昧すぎるタイトルは明確化する。

作成前に URL とタイトルから既存候補を探し、`export`、`meta`、`source list --id <ID>` の保存版を調べる。同じ URL・原本ハッシュ・本文ハッシュがある場合は既存版を再利用する。新しい本文は同じノートへ更新して新しい `source save` 版にし、内容が異なるなら既存版を上書きせず版の系譜を保つ。既存の CLI で再利用できるか確認できない場合は重複作成せず、照合できなかった点を残す。

```sh
text_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["text_path"])' "$manifest_path")"
source_url="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_url"])' "$manifest_path")"
retrieved_at="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["retrieved_at"])' "$manifest_path")"
original_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["original_path"])' "$manifest_path")"
track new --title "<title>" --tag clip < "$text_path"
track source save --id <ID> --source "$source_url" \
  --format text/html --at "$retrieved_at" --original "$original_path"
track source list --id <ID>
track cite --id <record.note_id> --version <record.version> --heading '<見出し>'
```

`source save` の入力は要求元 `source_url`、実際の `retrieved_at`、取得済みの `original_path`。戻り値の `record.note_id` と `record.version` を必ず後続の引用に使う。`record.original_hash` は保存した原本、`record.content_hash` は `track export` した保存本文の SHA-256 と照合する。抽出本文の `text_sha256` と保存本文の `content_hash` は、CLI が末尾改行を加える場合があるため同一視しない。

引用では `heading`、`block`、または確認済み行位置を固定版に対して指定する。`pinned: true`、ID、版、位置、版全体の `content_hash` を確認し、戻った本文に引用断片があることを読む。失敗した場合は現行ページや別版で代替せず、引用未解決として残す。

出典記録には要求元 `source_url` とリダイレクト後 `final_url` を区別して残す。公開・更新日時は manifest の `raw`、`precision`、`timestamp` をそのまま記録する。`timestamp: null`、`date`、`local_datetime`、`unknown`、`absent` から時刻を作らない。`modified` を公開日時として扱わず、`retrieved_at` は取得日時のまま保つ。

一部の古い `track-fetch-web` が `--snapshot-dir` を持たない場合は、`--help` で未対応を確認してから `--note` による明示的な限定フォールバックを使う。旧出力の取得日ラベルしかない場合は正確な取得時刻・原本バイト・固定版引用を「不明／未提供」とし、`track source save` 済みの固定版と呼ばない。回答だけに使うか、限定版で保存することを利用者に明示する。`date now`、ファイル時刻、公表日時を取得日時として補わない。

要約が必要なら取得本文から分離し、入力版・固定引用・生成日時・処理方法を記録する。取得に成功した後にノート作成や保存で失敗した場合、snapshot ディレクトリを残して `track source list` を確認し、欠けた段階だけ再実行する。取得・保存・固定引用が全て検証できた後だけ、一時 snapshot の削除を検討する。

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
