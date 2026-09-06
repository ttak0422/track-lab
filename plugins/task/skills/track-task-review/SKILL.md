---
name: track-task-review
description: タスクノートの対応完了後を整理する。取り残された完了項目を worklog へ移し、期限切れと WAITING を見直し、終わった議論を archive へ畳み、優先度を付け直す。チェックリストの棚卸しや overdue の掃除を頼まれたとき、定例の見直しの時間に使う。未処理の消化は track-task-runner、振り分けは track-task-triage の担当である。
---

# Track Task Review

CLI を使う前に[実行環境](../../references/runtime.md)を読む。振り分けは[track-task-triage](../track-task-triage/SKILL.md)、記録は[track-project-intake](../track-project-intake/SKILL.md)、消化は[track-task-runner](../track-task-runner/SKILL.md)に従う。このスキルはその後始末だけを担い、新規の記録や実装はそちらへ引き渡す。

タスクノート（ユーザーの track ボールト内）が整理の対象である。コードには触らない。読んで、状態を直して、畳むだけのスキルである。

## 使う場面

対応が一区切りついた後、定例の見直しの時間、overdue が溜まってきたと感じたときに発動する。典型的な言い回しは「タスクを整理して」「棚卸しして」「終わったものを畳んで」である。

未チェック項目の実装（`track-task-runner`）、新規依頼の記録（`track-project-intake`）、サイズの振り分け（`track-task-triage`）にはこれを使わない。

## 前提条件

- `track` CLI が `PATH` 上にあり、ユーザーの通常のボールトに対して解決できること。track のコマンドは通常1行の JSON を出力する（`export` は Markdown）。stdout をパースし、exit code 1 の `{"error":...}` は失敗として扱うこと。
- 整理対象のノートが決まっていること。決まっていなければタイトルで解決する。

```sh
track resolve --term "<title>"
track export --id <note_id>
```

## 1. 棚卸しする

未処理の分布を掴む。期限切れと今日の焦点は別に見る。

```sh
track tasks --id <note_id> --state TODO,DOING,WAITING --sort priority
track tasks --id <note_id> --overdue
track agenda --date 2026-09-05
```

`export` の本文と見比べ、何が終わっていて何が止まっているかを分ける。判断に迷う項目は動かさず、ステップ 6 の報告に残す。

## 2. 取り残された完了を worklog へ移す

チェックリストに残った DONE (`[x]`) は、コミットやテスト結果、ユーザーの完了報告などの証拠を先に確認する。証拠が不明な項目は状態を変えず、要確認として報告する。未チェックへ戻して再実装を誘発しない。

確認できた項目は日付つき worklog ノートへ移す。実装・コミットは行わず、元の完了日と証拠を維持する。未完了の子を含む親は移さない。

```sh
printf 'from [[<task note title>]]\n\n## DONE\n' \
  | track open --title "<YYYYMMDD> <task note title>" --tag worklog
printf -- '- [x] <original text> (2026-09-05: 対応済みを確認)\n' \
  | track append --title "<YYYYMMDD> <task note title>"
```

元の `- [x]` 行はノート本文からその場で削除する。検証の記録（コミットハッシュや確認日）が残っているものは、その一行を添えて移す。検証の形跡がないものは DONE へ移さず、未チェックに戻すか報告に残す。

## 3. 期限と待ちを見直す

期限切れは放置しない。理由と現在の見込みを確認し、終わる見込みの日へ `task date` で付け替える。ユーザーの指定や合意済み計画に新しい期限がある場合だけ変更し、根拠がなければ元の期限を保って報告する。着手条件が外にあるなら `WAITING` へ置き、待ち先を `(YYYY-MM-DD: <待ち先> 待ち)` と追記する。

```sh
track task date --id <note_id> --line <N> --due 2026-09-12
track task set --id <note_id> --line <N> --state WAITING
```

逆に待ち先が解消している `WAITING` は `TODO` へ戻す。戻す前に待ち先の解消を本文かユーザーへの確認で裏付ける。裏付けが取れないものは動かさない。

## 4. 終わった議論を畳む

対応が済んだ方針メモやバックログの節は `archive` でアーカイブノートへ移す。出典への `[[…]]` と日付は自動で刻まれる。別ノートへ育った節は `refile` で移す。

```sh
track archive "<title>#<heading>"
track refile --from "<title>#<heading>" --to "<other>#<heading>"
```

畳む前に `export` で節の範囲を確認する。現役の項目を含む節は畳まない。`rm` は使わない。消すのではなく畳むのがこのステップの約束である。

## 5. 優先度を付け直す

残った未処理に `[#A]` を付け直す。いま最も火が近いものだけに絞り、古い `[#A]` は外す。根拠のない `[#A]` の追加・削除はしない。優先度の付け替えは共通規約に従い本文の直接編集で行う。

## 6. 再インデックスして報告する

検索・リンク・バックリンクが一貫するよう再インデックスする。

```sh
track reindex
```

報告は短く、動かしたものごとに分ける。worklog へ移した件数とノート名、期限を付け替えた項目、WAITING へ置いた項目と待ち先、畳んだ節、判断を保留した項目とその理由を添える。

## 検証

`export` で移動した項目だけが元ノートから除かれ、チェックリストに取り残しの `[x]` がなく、要確認の `[x]` と未完了項目が残っていること、`tasks --overdue` が期待通りになったことを確認する。畳んだ節はアーカイブ先のノートに `[[…]]` 付きで入っていることを確かめる。

## 安全性

整理ではノートのタスク行と状態・期限・アーカイブの更新までに留める。実装・テスト・コミットは行わない。検証の形跡がない項目を DONE へ移さない。依頼外の削除はしない。
