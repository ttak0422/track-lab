# 埋め込みリファレンス

2つの異なる仕組みがある: `![[Note]]` は別の**ノートの本文**をトランスクルージョンする。独立した `![alt](src)` 行は**メディアまたは URL** を埋め込む。`![[...]]` は常にノートを指す — これはファイル埋め込み構文ではないため、`![[image.png]]` は何も埋め込まない。

## トランスクルージョン: `![[...]]`

```markdown
![[Note]]                          Whole note body
![[Note##Heading]]                 One section (## = h2; # count selects the level)
![[Note#^block-id]]                One block marked with a trailing ^block-id
![[Note|caption]]                  Caption via the display alias
![[Note##Heading]] :only-contents  Section body without the heading line
![[Note]] :lines 1-20              Line slice of the extracted region
```

ルール:

- **ブロックレベル限定。** `![[...]]` は行頭に置く必要がある (先頭の空白は許容) が、行末にはオプションテイル以外を置かない。本文中の文章の途中ではディレクティブにならず — その `[[...]]` 部分は通常のリンクとして数えられ、`!` はリテラルのまま残る。
- リンク部分は完全な wikilink 文法を共有する: 完全一致タイトルの解決キー、レベルベースの `##heading` アンカー、`#^id` ブロックアンカー、`|display` エイリアス。これは通常のリンクでもある — グラフとバックリンクに現れ、`track rename` で書き換えられ、タイトルが一致しない場合は未解決リンクの診断が出る。
- アンカーがない場合、ノート本文全体が埋め込まれる。見出しアンカーの場合、範囲は一致した見出し行から、同じかより浅いレベルの次の見出しの前の行まで。フェンス付きコードブロック内の見出しは一致も範囲の終端にもならない。ブロックアンカーの場合、範囲はマークされた段落またはリスト項目で、`^id` マーカーは除去される。
- 一致しないアンカーは **unresolved** として描画される — ノート全体へのフォールバックはしない (リンクナビゲーションがノート先頭にフォールバックするのとは異なる)。
- 抽出された範囲の先頭と末尾の空行はトリミングされる。
- 再帰しない: 埋め込み範囲内の include 行はテキストとして描画されるため、include の循環は無害である。

### オプションテイル

オプションは閉じ括弧 `]]` の後に置き、Org スタイルの `:key value` 形式 (`:height` 埋め込みオプションと同じ形) をとる。

- `:only-contents` — 一致した見出し行を落とし、その本文だけを埋め込む。アンカーなしでは何もしない (no-op)。
- `:lines 4-5,8` — 抽出された範囲に対する1始まりの包括範囲 (`:only-contents` の後に適用)、書かれた順に連結される。範囲外の部分は切り詰められる。

未知のキーや不正な値は、黙って無視されるのではなく診断として表示される。

## アセット画像

ローカルメディアは vault の単一トップレベル `assets/` ディレクトリに置く。

```sh
track asset import "<file>"    # copies the file into assets/ and prints the reference
```

```markdown
![track logo](assets/logo.png)
```

画像はそれ自体が1行の場合に埋め込みとして描画され、段落の途中にインラインで置いた場合は通常の画像のまま。相対 `assets/<file>` 参照は vault から提供され、リモート URL として扱われることはない。

## リッチ URL 埋め込み

独立した `![alt](src)` 行は対象に応じてルーティングされる。

| 対象 | 描画結果 |
| --- | --- |
| 画像ファイル (アセットまたは URL) | 画像 |
| YouTube の watch/share/embed URL | インラインプレーヤー |
| Google Maps の share/embed URL | インラインマップ (短い `maps.app.goo.gl` リンクは OGP カードにフォールバック) |
| ツイート URL (`x.com` / `twitter.com` の status) | Twitter ウィジェットによる実際の投稿 |
| PDF (アセットまたは URL) | ページ送りのスライドデッキビューア |
| テキストアセット (`.txt`, `.json`, `.yaml`, `.csv`, `.sh`, ...) | シンタックスハイライト付きコードブロック |
| Mermaid ソースアセット (`.mmd` / `.mermaid`) | 描画されたダイアグラム |
| `.viewspec.json` アセット | インタラクティブチャート |
| HTML アセット (`.html` / `.htm`) | サンドボックス化された iframe |
| その他の `http(s)` ページ (`.html` を含む) | Open Graph カード (タイトル、説明、プレビュー画像) |

HTML 埋め込みは、埋め込みの後に `:height` オプションをとる (素の数値 = ピクセル。`%` または `vh` = ビューポート高の割合)。

```markdown
![Demo](assets/demo.html) :height 480
![Map](assets/map.html) :height 90%
```

## フェンスレンダラー

特別なフェンス付きブロックは、コードを表示する代わりに描画する: ` ```mermaid `, ` ```dot `/` ```graphviz `, ` ```d2 `, ` ```mindmap `, ` ```viewspec `, ` ```track-query `, ` ```dashboard `, ` ```taskboard `, および babel 注釈付き言語フェンス。**track-create-note** スキルがそれぞれの用途を目録化している。完全な構文は track リポジトリの `docs/help/{diagrams,mindmaps,charts,query,dashboard,babel}.md` にあり、ヘルプサイトにも公開されている。

本文を書く際に知っておくべき2つの挙動:

- **空の** ` ```mindmap ` フェンスは、そのノート自身の見出しツリーを描画する — フェンス内容は不要。
- ` ```viewspec ` ブロックの `data.records` は自己完結させ、`data.source` は vault の `data/` ディレクトリ相対で JSONL ファイルを読み込む。不正な spec は、ノート全体を失敗させるのではなく、そのブロックの位置にエラーを表示する。
