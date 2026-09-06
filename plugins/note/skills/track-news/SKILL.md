---
name: track-news
description: vaultに溜まった自動生成記事（agent生成の調査レポート・ハイライト取り込み等）をnews番組風に紹介する。指定タグを持つ新着ノートを発見し、news節として今日のjournalへ差し込む新着ダイジェスト導線。ユーザーが「news」「新着ダイジェスト」「自動生成記事を紹介」と頼んだとき、またはjournalに生成記事の目次を足したいときに使う。
---

# Track News

自動生成ノートの山を、読める導線に変える。このスキルが行うのは1つのことだけである:

**「新着の自動生成記事」を発見して、今日のjournalにnewsダイジェストを差し込む。**

発見は `track` CLI、差し込みは既存の capture/append 流儀で行う。新しい保存形式や新しいサブシステムは作らない。

## 用語

- **自動生成記事**: agent が生成した調査レポート・ハイライト取り込み・集計ノート。人間の手書きノートと区別するために共通タグを付ける（既定は `#auto`。vault ごとに `TRACK_NEWS_TAG` で上書き可）。
- **newsダイジェスト**: 生成記事を「today's top」として番組風に並べたリスト。journal の `## News` 見出しの下に置く。各項目は `[[タイトル]]` へのリンク＋一行の襟（description）。

## 手順

### 1. 発見 — 新着の自動生成記事を列挙する

生成記事はタグで拾う。新着順に並べた `track notes` の結果から共通タグを持つ行を選ぶのが基本:

```sh
TRACK_VAULT=<path> track notes
```

`{"notes":[{"note_id":…,"title":…,"tags":…}, …]}` が新しい順に返る（journal は除外済み）。tags に共通タグを含むものを拾う。

件数を絞って探索するなら `track search --query "#<tag> <term>"`、日付で引くなら `track agenda --date YYYY-MM-DD` を使う。既に紹介済みの記事を二重に出すのを避けるため、session 内で紹介した `note_id` を保持し、journal に既に載っている `[[タイトル]]` を除外する。

### 2. 整形 — 番組風の見出しと襟をつくる

各記事に一行の襟（まとめ）を付ける。まとめは note の `description`（`track meta --id N` の `description`）を優先し、無ければ本文冒頭から一言に要約する。要約は本文に書かれている事実だけを使い、存在しない情報を補わない。

見出しは日付入りの節。journal は `yyyyMMdd` がタイトル兼IDである（`track journal` が自動作成）。

```markdown
## News

- [[タイトルA]] — 襟の一文。
- [[タイトルB]] — 襟の一文。
```

### 3. 差し込み — 既存の capture/append 流儀で journal へ

- その日の journal の ID は `track journal` 的には `yyyyMMdd`、実体は `track append --id <yyyyMMdd>` で追記できる。
- `## News` 見出しの下にまとめて載せたいときは `track capture --target "<yyyyMMdd>#News" --body "..."` を使う。見出しがまだ無ければ、`track append --id <yyyyMMdd>` で `## News` 見出しを作ってから capture する。

```sh
TRACK_VAULT=<path> track append --id "$(date +%Y%m%d)" --body $'## News\n'
TRACK_VAULT=<path> track capture --target "$(date +%Y%m%d)#News" --body "$digest"
```

`track capture` は `--target` を省略すると設定済み `capture_inbox` に落ちる。journal へ差し込む場合は必ず `--target "<yyyyMMdd>#News"` を明示すること。見出し名は既存の journal 本文と整合させる。

既存のジョウブ独自ルール（`capture_inbox` 先、見出し命名）は vault の `.track/config.yml` に従い、慣習が見えないときは質問して確定してから書く。

## スクリプト

`scripts/news-digest.sh` はこの手順のドラフト実装である。単体で動くインベントリ抽出＋ダイジェスト生成の雛形として読み、本番では agent が上記手順をCLIで直に組み立てる。スクリプトは `track notes` / `track search` の JSON を `jq` で読むことを前提とし、書き込み（journal への差し込み）は行わない（dry-run）。

```sh
TRACK_VAULT=/path/to/vault ./scripts/news-digest.sh --tag auto --limit 10
```

## 制約

- 推測禁止。本文・description に無い内容を襟に書かない。
- 二重紹介を避ける。既に journal の `## News` に載っている `[[タイトル]]` は出さない。
- 数字・タイトルは CLI の返値をそのまま引用する。
- 差し込みは `track capture` / `track append` に限定し、ファイルを直接手で書かない（sidecar と index の整合を CLI に任せる）。
