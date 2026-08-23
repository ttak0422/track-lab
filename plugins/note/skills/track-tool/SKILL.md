---
name: track-tool
description: track ノートに埋め込む、HTML 1枚で完結する小さなツールを書く。計算機、変換器、ジェネレータ、可視化ウィジェットなど。埋め込み先はサンドボックス iframe なので、localStorage もフォーム送信も効かない。その制約の中で成立する形と、ボールト全体で見た目を揃えるための決めごとを扱う。ノートに置くツールやウィジェットを作ってほしいと言われたとき、既存の埋め込みツールを直すときに使う。埋め込み構文そのものは track-markdown の担当である。
---

# Track Tool

ノートに埋め込むツールは、HTML アセット1枚として置かれ、サンドボックス iframe の中で動く。
このスキルは、その制約の中で成立するツールの形を定める。
埋め込みの構文（`:height`、`:frame none`、リモート URL）は
`../track-markdown/references/EMBEDS.md` の担当なので、ここでは繰り返さない。

## 前提条件

- 真実の情報源として `track` CLI を使う。track のソースリポジトリでは `go run ./cmd/track` を代わりに使ってよい。
- 成果物は HTML ファイル1枚である。ビルド、npm、React は使わない。
- 埋め込まれたページは `sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads allow-modals"` と `allow="clipboard-write"` で動く。`allow-same-origin` は付かない。

## 動くものと動かないもの

sandbox に `allow-same-origin` がないため、フレームは一意の不透明オリジンを持つ。
オリジンに紐づく機能はすべて落ちる。

| 機能 | 可否 |
| --- | --- |
| JavaScript の実行 | 動く |
| CDN からの読み込み | 動く（sandbox が切るのはオリジンであって通信ではない） |
| `window.open` と `target="_blank"` | 窓は開き、開いた先は通常の閲覧文脈になる（`allow-popups-to-escape-sandbox` がある） |
| 親タブの遷移 | 動かない（`allow-top-navigation` がない） |
| localStorage, sessionStorage, IndexedDB, Cookie | 動かない（SecurityError） |
| 同一オリジンへの fetch | 動かない |
| フォーム送信 | 動かない（`allow-forms` がない）。検証も走らず、無言で何も起きない |
| `alert`, `confirm`, `prompt`, `print` | 動く（`allow-modals` がある） |
| `<a download>` によるダウンロード | 動く（`allow-downloads` がある） |
| `navigator.clipboard` | `allow="clipboard-write"` で許可される。ただし不透明オリジンへの委譲は未検証なので、確実なのは `document.execCommand("copy")` |
| 親ノートへの結果の返却 | 動かない（受け手がない） |

保存先がないので、ツールは入力から出力までを一度で閉じる形になる。
計算機、変換器、ジェネレータ、可視化は成立する。
下書きが残るエディタと、API キーを保持する種類のツールは成立しない。

外部サイトへ送り出すツールは成立する。
`<form>` の submit は `allow-forms` がないため無言で落ちるが、URL を組み立てて `window.open` かリンクで開けば、開いた先は通常の閲覧文脈になる（`allow-popups-to-escape-sandbox`）。
Cookie もセッションもある状態で相手のサイトが開くので、検索フォームは「URL を組み立てて窓を開く」形にする。

## 骨組み

見た目は Pico.css で揃える（指示が無ければ）。ボールト内に共有スタイルシートを置くことはできない。
アセットは live で `/api/asset?path=…` から配られ、静的書き出しでは内容由来の名前に変わるため、
アセット同士の相対参照はどちらでも解決しないからである。
埋め込む内容のデザイン（色・余白・階層の考え方）は指示が無ければ `docs/spec/design.md` を参考にする。
ツールの primary（salient）は design.md の `--mark` に揃える。Pico 既定の primary は青系で、
ノート面の vermilion と衝突するため、下の骨組みで `--pico-primary` 系を上書きしている。

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
        /* design.md の salient（--mark）に揃える。Pico 既定の primary は青系で、ノート面の vermilion と衝突する。 */
        --pico-primary: light-dark(#c13a1e, #f4785e);
        --pico-primary-hover: light-dark(#a32f16, #ff8a6b);
        --pico-primary-focus: light-dark(#c13a1e, #f4785e);
        --pico-primary-inverse: light-dark(#ffffff, #191c1e);
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

この骨組みは出力が大きい計算機型（入力小・出力大）を想定している。
入力主体で出力が1行のツールは `main` の flex/overflow が空振りして空のスクロールが出るので、
`html,body { height:100% }` と `main { flex:1; overflow:auto }` を外し、通常の縦フローに任せる。

Pico は `prefers-color-scheme` を持つので、OS の設定には自動で追従する。
track 本体のテーマ（`:root` の `data-theme`）はフレームから読めないため、
アプリ側で明示的に light か dark を選んでいる場合、ツールだけ OS 設定のまま残る。
Pico は CDN 依存なので、オフラインでは無スタイルに落ちる。致命的でなければ許容する。

## 規則

1. 1ファイルで完結させる。自前の CSS と JS はインラインに置く。
2. 見た目の土台は Pico.css v2 に任せる（指示が無ければ）。生の色を直に書かない。埋め込む内容のデザインは `docs/spec/design.md` を参考にし、ツールの primary は `--pico-primary` 系を `--mark` に上書きする。
3. フォントを揃えるのは `--pico-font-family-sans-serif` の1行に留める。
4. ライブラリを読むなら版を固定し、読めなかったときの表示を DOM に持たせる。
5. 状態を持たせない。値の保存が要る設計になったら、ツールではなくノートに書く。
6. 出力は画面表示に寄せる。コピーが要るなら `document.execCommand("copy")` へ落とすか、選択できるテキストとして出す。
7. 縦に伸び続けるレイアウトにしない。伸びる領域だけを `overflow: auto` に閉じ込め、操作部は常に見えるようにする。これは出力主体の骨組みで、入力主体・出力1行のツールは通常の縦フローに任せる。
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
<iframe src="./<tool>.html" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads allow-modals" allow="clipboard-write" style="width:100%;height:480px"></iframe>
```

埋め込みに書く `:height` と同じ高さで開き、storage に触れていないこと、そして縦スクロールが出ないことを確認する。

`:height` の実寸は、レンダリングして `document.body.scrollHeight` を読むと正確に出る。
ロード後に高さを `<title>` へ書き出す計測用スクリプトを仕込み、ヘッドレス Chrome の `--dump-dom` で `<title>` を読む（`--window-size` は実際の列幅に合わせる）。
