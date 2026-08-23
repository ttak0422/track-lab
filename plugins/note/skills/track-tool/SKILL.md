---
name: track-tool
description: track ノートに埋め込む、HTML 1枚で完結する小さなツールを書く。計算機、変換器、ジェネレータ、可視化ウィジェットなど。埋め込み先はサンドボックス iframe なので、localStorage もダウンロードもフォーム送信も効かない。その制約の中で成立する形と、ボールト全体で見た目を揃えるための決めごとを扱う。ノートに置くツールやウィジェットを作ってほしいと言われたとき、既存の埋め込みツールを直すときに使う。埋め込み構文そのものは track-markdown の担当である。
---

# Track Tool

ノートに埋め込むツールは、HTML アセット1枚として置かれ、サンドボックス iframe の中で動く。
このスキルは、その制約の中で成立するツールの形を定める。
埋め込みの構文（`:height`、`:frame none`、リモート URL）は
`../track-markdown/references/EMBEDS.md` の担当なので、ここでは繰り返さない。

## 前提条件

- 真実の情報源として `track` CLI を使う。track のソースリポジトリでは `go run ./cmd/track` を代わりに使ってよい。
- 成果物は HTML ファイル1枚である。ビルド、npm、React は使わない。
- 埋め込まれたページは `sandbox="allow-scripts allow-popups"` で動く。`allow-same-origin` は付かない。

## 動くものと動かないもの

sandbox に `allow-same-origin` がないため、フレームは一意の不透明オリジンを持つ。
オリジンに紐づく機能はすべて落ちる。

| 機能 | 可否 |
| --- | --- |
| JavaScript の実行 | 動く |
| CDN からの読み込み | 動く（sandbox が切るのはオリジンであって通信ではない） |
| `window.open` と `target="_blank"` | 窓は開く。ただし開いた先も同じ sandbox を引き継ぐ（`allow-popups-to-escape-sandbox` がない） |
| 親タブの遷移 | 動かない（`allow-top-navigation` がない） |
| localStorage, sessionStorage, IndexedDB, Cookie | 動かない（SecurityError） |
| 同一オリジンへの fetch | 動かない |
| フォーム送信 | 動かない（`allow-forms` がない）。検証も走らず、無言で何も起きない |
| `alert`, `confirm`, `prompt` | 動かない（`allow-modals` がない） |
| `<a download>` によるダウンロード | 動かない（`allow-downloads` がない） |
| `navigator.clipboard` | 当てにしない（Permissions Policy の既定は `self`） |
| 親ノートへの結果の返却 | 動かない（受け手がない） |

保存先がないので、ツールは入力から出力までを一度で閉じる形になる。
計算機、変換器、ジェネレータ、可視化は成立する。
下書きが残るエディタと、API キーを保持する種類のツールは成立しない。

外部サイトへ送り出すツールも成立しない。
検索フォームは submit が無言で落ちる。
`<form>` を使わずに JS で窓を開いても、その窓が同じ sandbox を引き継ぐため、Cookie もストレージもない状態で相手のサイトが開く。
URL を組み立てて画面に出し、読者にコピーさせるところまでが、この面でできることである。

## 骨組み

見た目は Pico.css で揃える。ボールト内に共有スタイルシートを置くことはできない。
アセットは live で `/api/asset?path=…` から配られ、静的書き出しでは内容由来の名前に変わるため、
アセット同士の相対参照はどちらでも解決しないからである。

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="light dark" />
    <title><ツール名></title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css" />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;500;600&display=swap"
    />
    <style>
      :root {
        --pico-font-family-sans-serif: "IBM Plex Sans JP", system-ui, sans-serif;
      }
      html,
      body {
        height: 100%;
      }
      body {
        display: flex;
        flex-direction: column;
        margin: 0;
        padding: 1rem;
      }
      /* 伸びるのはここだけにする。操作部と出典は常に見えたままになる。 */
      main {
        flex: 1;
        min-height: 0;
        overflow: auto;
      }
    </style>
  </head>
  <body>
    <section><!-- 入力。常に見える位置に置く --></section>
    <main><!-- 出力 --></main>
    <footer><!-- from <ノート名> --></footer>
    <script>
      // 状態は持たない。入力が変わったら出力を作り直す。
    </script>
  </body>
</html>
```

Pico は `prefers-color-scheme` を持つので、OS の設定には自動で追従する。
track 本体のテーマ（`:root` の `data-theme`）はフレームから読めないため、
アプリ側で明示的に light か dark を選んでいる場合、ツールだけ OS 設定のまま残る。

## 規則

1. 1ファイルで完結させる。自前の CSS と JS はインラインに置く。
2. 見た目の土台は Pico.css v2 に任せる。生の色を直に書かない。
3. フォントを揃えるのは `--pico-font-family-sans-serif` の1行に留める。
4. ライブラリを読むなら版を固定し、読めなかったときの表示を DOM に持たせる。
5. 状態を持たせない。値の保存が要る設計になったら、ツールではなくノートに書く。
6. 出力は画面表示に寄せる。コピーが要るなら `document.execCommand("copy")` へ落とすか、選択できるテキストとして出す。
7. 縦に伸び続けるレイアウトにしない。伸びる領域だけを `overflow: auto` に閉じ込め、操作部は常に見えるようにする。
8. 埋め込みでは `:height` に実寸を指定し、`:frame none` を既定にする。
9. フッターに生成元のノート名を1行置く。どこから来たツールかを追えるようにする。

## 置いて埋め込む

```sh
track asset import ./<tool>.html     # assets/<tool>.html を返す
```

返ってきた参照を、ノート本文に埋め込む。オプションは並べて書ける。

```markdown
![<ツール名>](assets/<tool>.html) :height 560 :frame none
```

`:frame none` を既定にする。枠と角丸が消え、ツールがノートの面に直接乗る。sandbox は変わらない。

高さは書き手が決める。
フレームは自分の高さを親へ伝えられない（不透明オリジンであり、受け手もない）ので、`:height` を省くと既定の 360px のまま中身が縦にスクロールする。
実際に使う画面幅で測った高さを指定し、スクロールが出ない状態にする。
オプションの完全な形は `../track-markdown/references/EMBEDS.md` にある。

## 確認

ブラウザで直接開いた結果は当てにならない。
直接開いた場合はオリジンを持つので、sandbox で落ちるはずの機能が動いてしまう。
同じ sandbox 属性を持つラッパーを1枚作って、その中で確かめる。

```html
<iframe src="./<tool>.html" sandbox="allow-scripts allow-popups" style="width:100%;height:480px"></iframe>
```

埋め込みに書く `:height` と同じ高さで開き、storage とダウンロードと `alert` に触れていないこと、そして縦スクロールが出ないことを確認する。
