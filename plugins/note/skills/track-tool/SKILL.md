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
| JavaScript の実行、`window.open` | 動く |
| CDN からの読み込み | 動く（sandbox が切るのはオリジンであって通信ではない） |
| localStorage, sessionStorage, IndexedDB, Cookie | 動かない（SecurityError） |
| 同一オリジンへの fetch | 動かない |
| フォーム送信 | 動かない（`allow-forms` がない） |
| `alert`, `confirm`, `prompt` | 動かない（`allow-modals` がない） |
| `<a download>` によるダウンロード | 動かない（`allow-downloads` がない） |
| `navigator.clipboard` | 当てにしない（Permissions Policy の既定は `self`） |
| 親ノートへの結果の返却 | 動かない（受け手がない） |

保存先がないので、ツールは入力から出力までを一度で閉じる形になる。
計算機、変換器、ジェネレータ、可視化は成立する。
下書きが残るエディタと、API キーを保持する種類のツールは成立しない。

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
      body {
        padding: 1rem;
      }
    </style>
  </head>
  <body>
    <main><!-- 入力と出力 --></main>
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
7. フッターに生成元のノート名を1行置く。どこから来たツールかを追えるようにする。

## 置いて埋め込む

```sh
track asset import ./<tool>.html     # assets/<tool>.html を返す
```

返ってきた参照を、ノート本文に埋め込む。

```markdown
![<ツール名>](assets/<tool>.html) :height 480
```

面に貼り込むなら `:frame none` を足す。
高さの指定と枠の扱いは `../track-markdown/references/EMBEDS.md` に揃える。

## 確認

ブラウザで直接開いた結果は当てにならない。
直接開いた場合はオリジンを持つので、sandbox で落ちるはずの機能が動いてしまう。
同じ sandbox 属性を持つラッパーを1枚作って、その中で確かめる。

```html
<iframe src="./<tool>.html" sandbox="allow-scripts allow-popups" style="width:100%;height:480px"></iframe>
```

storage、ダウンロード、`alert` に触れていないことを、この状態で確認する。
