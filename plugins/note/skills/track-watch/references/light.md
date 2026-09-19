# light: デイリーブリーフ（最小限に保つ）

前回からの変化に絞って、利用可能な Web 検索ツールで調べる。既存の状態とデータを再利用する。

1. 状態を読む: watch ノート（`track export`）、その未解決の懸念（`track tasks`）、前回のブリーフ
   （`track search --query "#<topic> #daily"` の最新ヒット）。
2. トピックにデータフィードがあれば先に更新する:
   `track-fetch-jquants --code <code> --out <vault>/data/<topic>.jsonl`: 対象期間・更新日時・単位・欠損を確認する。フィードにある数値を重ねて検索する必要はない。
3. 次の3つの問いを中心に調べる。矛盾や欠測があれば必要な追加確認を行う。
   - (a) 今日、未解決の懸念に応答するものはあったか？ (既存の結果で答えられなければ検索する);
   - (b) 真に新しいイベントは現れたか？
   - (c) その日の動き・数値は？（フィードがカバーしていない場合のみ）
4. 既存の同日ブリーフは本文を確認して未完了部分を更新する。初回だけ `track new --title "<YYYYMMDD> <topic> daily" --tag daily --tag <topic>` で作る。

   ```markdown
   from [[<topic> 定点観測]]

   ## 当日の動き
   ## 懸念への反応      ← one line per open concern; 「動きなし」 is a valid and useful answer
   ## 新規イベント
   ## 引き継ぎ          ← what this run changed in the watch note (resolved/added concerns, fired triggers)
                      ← 対象期間、取得・保存の成功／失敗、未確認範囲、再実行対象
   ```

   40行程度に保つ。チャートは描かない。watch ノートの `data.source` チャートが時系列を担う。
5. watch ノートを更新する: 懸念タスクの遷移、新規懸念の追加、発火したトリガーをレジスタ項目に
   記す。
6. その日、本格的な分析に値するイベントが生じた場合、ブリーフ内で深掘りしては**ならない**。
   ブリーフに深掘り候補として残す。詳細分析も依頼範囲に含まれる場合は `track-news-analysis` を使い、分析ノートを watch ノートとブリーフからリンクする。

検証は比例的に行う: 昨日の数値との算術比較、そしてブリーフが主張する重要な数値それぞれについて
一次ソースを確認する。食い違いが残る場合は追加確認するか、未確認と明示する。
