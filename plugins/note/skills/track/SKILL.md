---
name: track
description: >-
  リンク付き Markdown のナレッジベース保守のために track CLI を使う。基本的なノート作成や読み取り専用の検索を超える用途
  （ノートのリネームとバックリンク修正、バックリンク/グラフの確認、診断の実行、インデックスの保守、
  複数ステップにわたる vault ワークフローの調整）が対象。ノートの作成には track-create-note を、
  ノートの検索・閲覧には track-search-notes を使うこと。
---

# track CLI

track CLI はノート、インデックス、検索、リンク解決の信頼できる唯一の情報源である。Go エンジンがノートをパースし、SQLite インデックスを保守し、`[[links]]` を解決する。

## 使う場面

この汎用スキルは、ノートのリネームとバックリンク修正、ワークフローの一部としてのバックリンク/グラフ文脈の確認、再インデックス/診断、複数の track 操作の調整といった保守タスクに使う。

より対象を絞ったスキルが当てはまる場合はそちらを使う。

- `track-create-note`: ノート、ジャーナル、テンプレート由来のノートを作成/開く。
- `track-search-notes`: ノートを変更せずに検索、解決、書き出し/閲覧、バックリンク、グラフ検査を行う。
- `track-project-intake`: 入ってきたバグ/TODO をプロジェクトのノートに記録し、その計画を下書きする。
- `track-task-runner`: プロジェクトノートのチェックリストを処理し、出荷した内容を記録する。
- `track-report`: 調査内容をレポートノートとして書き上げる。

## 前提条件

- `track` バイナリが `PATH` 上にあること。(track 自体を開発していて、ソースリポジトリを作業ディレクトリにしている場合のみ、`go run ./cmd/track` が代替として機能する。)
- ユーザーが普段使っている track 設定を優先する。`TRACK_VAULT` はテストや一回限りの上書き専用。

## 主なコマンド

- `track rename (--id N | --title S | --path P) --to <s>`: タイトルをリネームし、バックリンクを書き換える。
- `track backlinks (--id N | --path P)` / `track graph (--id N | --path P)`: 被リンク / ローカルグラフ。
- `track doctor [--fix]`: 現在のビルドで利用可能な場合、vault/インデックスのずれを診断または修復する。
- `track reindex [--full]`: SQLite インデックスを再構築する。
- `track vault list|current|which <name>`: 名前付き vault レジストリ (マシン設定の `vaults:`) を調べる。任意のコマンドにグローバルな `--vault NAME` を付けると、その 1 回の実行に限ってその vault を対象にする。レジストリがあり `--vault` を付けない場合、doctor/reindex/refresh-all は登録された全 vault を走査し、vault ごとの行を報告する。
- `track export (--id N | --title S | --path P)`: ノート全文の Markdown を標準出力に出す。
- `track toggle (--id N | --title S | --path P) --line N [--state toggle|check|uncheck]`: タスクチェックボックスを切り替えるか設定する。
- `track rm (--id N | --title S | --path P)`: ノートを `.track/trash` にソフトデリートし (track がそれを空にすることは決してない)、再インデックスする。
- `track gen increment|undo|redo|list|peek`: vault 世代スナップショット (バルク編集をまたぐ undo/redo)。下記参照。

## 世代 (バルク編集の安全網)

`track gen` は vault のノートとメタデータを、undo/redo カーソル付きの番号付き世代としてスナップショットする。
そのリリースモデル: `increment` が不変のセーブポイントを切り、`undo`/`redo` が 1 つずつ出し入れする。
バルク書き換え (大量のリネーム/更新/削除、メモリ整理) は必ず世代で挟み、その実行を
レビュー可能かつ却下可能にする。

```sh
track gen increment    # seal the pre-run state
# ... rename / update / rm notes ...
track gen increment    # approve the result
# or
track gen undo         # reject; the run's output is auto-saved, redo revisits it
```

- `track gen list` は世代、`cursor`、`dirty` (未保存の変更) を報告する。`undo`/`redo` の前に `dirty` を確認すること:
  先頭から外れると、カーソル移動が未保存の変更を破棄する。
- `track gen peek [--gen N] (--id N | --title S | --path P)` は、何も動かさずに、ある世代 (デフォルト: カーソル) 時点の
  ノートの Markdown を表示する。削除済みノートは `--id` で peek する。部分的な復元には、peek した本文を
  現在のノートと diff し、必要な箇所を `track update` で書き戻す。
- スナップショットが対象にするのはノート本文、ジャーナル、サイドカーのみ。`assets/` は除外される。

## タスクチェックボックスの更新

`- [ ]`/`- [x]` のタスク項目を変更するには、Markdown を手で編集するより `track toggle` を優先する: それは
1 つのボックスだけを正確に切り替え、周囲のテキストはそのまま残す。まずボックスの行番号を特定する
(`track search --scope body …` と `track export` はどちらも 1 始まりの行番号を報告する)。それから、次を実行する。

```sh
track toggle --id 1781359469000 --line 14            # flip the box on line 14
track toggle --title "Tasks" --line 3 --state check  # idempotent: force checked
```

結果は、結果としての `checked` 状態と、何か `changed` したかを報告する。`--state check`/`uncheck` は冪等なので、再実行しても安全である。切り替えるとノートは自動的に再インデックスされる。

## 出力の契約

すべてのコマンドは単一行の JSON を出力する。エラーは終了コード 1 で `{"error":...}`。標準出力を JSON としてパースすること。

## 規約

- タイトルはリンクのキーワードである。本文に `[[Title]]` と書くとリンクになる。タイトルは本文ではなくサイドカーのメタデータに置かれるため、本文は任意の `#` 見出しで始めてよい。

## 典型的なワークフロー

保守ワークフローでは、対象を確認し (`resolve` で特定し、`export`、`backlinks`、`graph` で周辺を見る) → `rename` や `doctor --fix` などの保守コマンドを適用し → search/backlinks/export で検証する。単純なノート作成や読み取り専用の検索には、より対象を絞った create/search スキルを優先する。

## 例

```sh
track rename --title "Old title" --to "New title"
```

## track コントリビューター向け

track のソースリポジトリ内で作業している場合 (作業ディレクトリがリポジトリルート)、正式な、より完全な CLI 契約は `docs/spec/agent-workflows.md` にある。このスキルを使う必要は必ずしもない。上記のコマンドは自己完結している。
