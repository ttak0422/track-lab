# mid: ウィークリーレビュー

デイリーがすでに集めた材料に対するメインループでの作業。調査のファンアウトなし。

1. 1週間分を集める: `track search --query "#<topic> #daily"` → その週のブリーフをエクスポートする。
2. `<YYYYMMDD> <topic> weekly` を書く（タグは `weekly` ＋トピック）:

   ```markdown
   from [[<topic> 定点観測]]

   ## 週間推移        ← numbers and events; one viewspec if the series moved meaningfully
   ## トレンド評価    ← against previous weeklies (#<topic> #weekly): what continued, what broke
   ## 前提の点検      ← walk the register; only items with contrary evidence this week get a re-check search
   ## 来週の注視点    ← feeds back into the watch note's concern list
   ```

3. watch ノートを更新する: 見立ての段落、懸念リスト、レジスタの `[checked::]` 日付。
