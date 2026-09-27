# バッチ状態

永続保存または再開のときだけ使う。保存先はユーザー指定に限る。状態は再開用の索引であり、ノート本文の複製や自動再実行キューではない。strict read-only では作成しない。

## 最小フィールド

- `schema`, `batch_id`, `vault_identity`, `scope`, `mode`, `status`, `limits`, `counts`。再開をまたいでも対象数・本文を読んだノート数・提案数・経過時間の上限を累積する。
- `targets[]` は `target_id`、`input_versions`、`dependencies[]`、`decision`、`execution_state`、`approved_operations[]` を持つ。コード入力なら repository identity と commit/作業ツリーの版を記録する。
- 各入力・依存元は ID と revision/hash、その取得方法を記録する。版のない依存元や `unknown` は変更なしと扱わない。
- タグ・タイトル・タスク状態など判断に用いたメタデータも版の照合対象に含める。本文 hash だけでその不変性を保証しない。TODO はノート ID と本文・周辺見出しでも再特定し、保存した行番号だけで更新しない。
- `decision` は `proposed` / `hold` / `no_action` と根拠・参照位置を持つ。`execution_state` は `proposed` / `approved` / `in_progress` / `applied` / `verified` / `held` のいずれか。
- 承認操作は対象 ID、操作、変更内容または移動先、承認記録、承認時の入力・依存元の版に結び付ける。一般的な「続けて」は対象操作の承認として保存しない。
- `in_progress` の操作には試行前の版と、確認できた場合は期待する完了状態を記録する。結果不明を成功扱いしない。

## 例

```yaml
schema: 1
batch_id: weekly-notes-2026-09-27
vault_identity: notes-main
scope: "2026/Q3 の指定プロジェクトノート"
mode: apply-approved
status: paused
limits: { targets: 30, minutes: 60, parallel: 2, proposals: 10 }
counts: { targets: 2, notes_read: 3, proposals: 2, elapsed_minutes: 18 }
targets:
  - target_id: "merge:n-17+n-20"
    input_versions: { "n-17": "sha256:<digest>", "n-20": "sha256:<digest>" }
    dependencies: [{ id: "n-31", version: "sha256:<digest>" }]
    decision: { status: proposed, reason: "同じ手順を重複記録", evidence: ["n-17#運用", "n-20#手順"] }
    execution_state: in_progress
    approved_operations:
      - operation: "n-17 に統合し、出典と条件を保持する"
        approval: "user:2026-09-27"
        input_versions: { "n-17": "sha256:<digest>", "n-20": "sha256:<digest>", "n-31": "sha256:<digest>" }
    attempt: { before: "sha256:<digest>", outcome: unknown }
  - target_id: "task:n-44#TODO-3"
    input_versions: { "n-44": "sha256:<digest>" }
    dependencies: []
    decision: { status: proposed, reason: "依存先が未確認", evidence: ["n-44#TODO"] }
    execution_state: proposed
    approved_operations: []
```

## 再開と中断

まず vault identity と scope を照合する。異なる場合はその状態を使わない。次に対象と依存元を再読し、記録された版・承認操作と比較する。`in_progress` は下記の完了結果照合を先に行う。それ以外でどれかが変化した対象は再判定し、承認を失効させる。独立していて全入力版と操作が一致する承認だけが新たな書き込みに有効である。

`in_progress` は必ず実データと照合する。承認された完了状態がすべて存在すれば、適用によって試行前の hash と異なっていても、再書き込みせず検証済みにできる。新たな書き込みの承認とは区別する。試行前状態と完全一致し、入力・依存元の版と元の承認がまだ有効なら未実施操作として一度だけ続けられる。部分適用、他者の変更、版の不明、結果の不一致があれば保留し、全体 undo や自動再試行で覆い隠さない。
