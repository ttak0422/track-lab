# mid: ウィークリーレビュー

デイリーがすでに集めた材料に対するメインループでの作業。調査のファンアウトなし。

1. 対象週の開始・終了・タイムゾーンを固定し、開始を含み終了を含まない範囲のブリーフを集める: `track search --query "#<topic> #daily"` → 該当分をエクスポートする。欠けた日と取得に失敗した日を記録する。
2. `<YYYYMMDD> <topic> weekly` を書く（タグは `weekly` ＋トピック）:

   ```markdown
   from [[<topic> 定点観測]]

   ## 週間推移        ← numbers and events; one viewspec if the series moved meaningfully
   ## トレンド評価    ← against previous weeklies (#<topic> #weekly): what continued, what broke
   ## 前提の点検      ← walk the register; only items with contrary evidence this week get a re-check search
   ## 来週の注視点    ← feeds back into the watch note's concern list
   ## 引き継ぎ        ← 対象期間、成功／失敗、未確認範囲、再実行対象
   ```

   同じ週のレビューがあれば本文を確認して未完了部分を更新する。
3. watch ノートを更新する: 見立ての段落、懸念リスト、実際に点検したレジスタ項目の `[checked::]` 日付。
