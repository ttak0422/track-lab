---
name: track-markdown
description: track の Markdown 方言でノート本文を書いたり編集したりする。レベルベースの見出しアンカーを持つ wikilink、ブロックアンカー、トランスクルージョン、リッチ埋め込み、GitHub アラート、状態と日付トークンを持つタスク行、サイドカーメタデータ、インライン・プロパティ、そして track fmt の標準スタイルを扱う。track ボールトでノート本文を書いたり編集したりするとき、または wikilink／トランスクルージョン／アラート／タスク／プロパティの構文についての疑問が生じたときに使う。ノートの作成・検索・リネームには track 系スキルを使う。このスキルが扱うのは本文の構文のみ。
---

# track Markdown

track のノート本文は、CommonMark に GFM（表、タスクリスト、取り消し線、戻りリンク付き脚注）を加え、さらに track 固有の小さな構成要素を載せたものです。標準的な Markdown は既知とみなし、このスキルが扱うのは差分のみです。すなわち、frontmatter なし、レベルベースの見出しアンカー、ブロックレベルのみのトランスクルージョン、そしてちょうど5種類のアラート型です。

## 前提条件

- 真実の源として `track` CLI を使うこと。track のソースリポジトリでは `go run ./cmd/track` で代用してもかまいません。
- ユーザーの通常の track 設定を優先すること。`TRACK_VAULT` はテストや一時的な上書き用です。
- コマンドは1行の JSON を出力します（`export` は Markdown を出力します）。終了コード1の `{"error":...}` は失敗として扱います。
- このスキルはノート本文の中の構文についてのものです。ノートの作成・閲覧・リネームは track-create-note / track-search-notes / track スキルの担当です。

## 内部リンク（Wikilink）

```markdown
[[Title]]                Link to the note titled exactly "Title"
[[Title|display]]        Same target, shown as "display" (first | splits)
[[Note#Heading]]         Link to the h1 heading "Heading" in Note
[[Note##Heading]]        Link to the h2 heading "Heading" in Note
[[Note#^block-id]]       Link to the block marked "^block-id" in Note
```

- 解決は**タイトルの完全一致**のみです。パスも `.md` 拡張子もエイリアスも使えません。タイトルが唯一のリンクキーワードであり、タイトルはボールト全体で一意です。
- **見出しアンカーはレベルベース**です。`#` の数が見出しの**レベル**を選びます。`[[Note#foo]]` は `# foo` (h1) を指し、`[[Note##bar]]` は `## bar` (h2) を指し、h6 まで続きます。レベルとテキストの両方が文書順で最初に一致する見出しが選ばれます。
- `[[#Heading]]`（タイトルのない同一ノート内アンカー）はリンクでは**ありません**。完全なタイトルを書くか、省いてください。
- 本文の H1 を編集してノートをリネームしてはいけません。`track rename` でタイトルを変更し、バックリンクを書き換えてもらいます。

```sh
track rename --title "<old title>" --to "<new title>"
```

## ブロックアンカー

段落やリスト項目の末尾の `^id` は、そのブロックをリンク先としてマークします。

```markdown
The paragraph worth pointing at. ^explicit-links

- a list item worth citing ^li-1
```

- id は `^` の後に英数字、その後に文字・数字・`-`・`_` が続きます。テキストとは空白で区切られている必要があるため、`foo^2` は散文のままです。
- **id は手動のみ**です。track が自動生成することはなく、レンダラーはマーカーを隠します。ノート内で id を一意に保ってください。最初に現れたものが優先されます。
- `[[Note#^id]]` でそれを指すか、`![[Note#^id]]` でそのブロックだけをトランスクルードします（マーカーは取り込み時に取り除かれます）。

## トランスクルージョンとメディア埋め込み

`![[Note]]` を単独の行に置くと、別のノートの内容を埋め込みます。これは**ブロックレベルのみ**で、本文の途中ではディレクティブになりません（`[[...]]` の部分は通常のリンクのままです）。これは実在するリンク（グラフ・バックリンク・リネーム）として扱われ、再帰的に展開されることはありません。

```markdown
![[Note]]                          Embed the whole note body
![[Note##Heading]]                 Embed one h2 section
![[Note#^block-id]]                Embed one marked block
![[Note|caption]]                  Embed with a caption
![[Note##Heading]] :only-contents  Drop the heading line itself
![[Note]] :lines 4-5,8             Embed only these 1-based lines
```

track では `![[image.png]]` は画像構文では**ありません**。メディアには、ボールトの唯一のトップレベル `assets/` ディレクトリを指す標準 Markdown を使います。

```sh
track asset import "<file>"    # copies into assets/ and prints the assets/<file> reference
```

```markdown
![alt](assets/file.png)
```

単独の `![alt](url)` 行はリッチ埋め込みです。画像・YouTube プレイヤー・Google マップ・ツイート・PDF ビューア・Open Graph カードになります。段落内のインライン画像は通常の画像のままです。トランスクルージョンの完全な文法と埋め込みカタログは [EMBEDS.md](references/EMBEDS.md) を参照してください。

## アラート

track のコールアウトは GitHub アラートです。ちょうど5種類だけで、それ以外はありません。

```markdown
> [!NOTE]
> Useful context the reader should notice.
```

| 種類 | 用途 |
| --- | --- |
| `[!NOTE]` | 役立つ文脈 |
| `[!TIP]` | 役立つ提案 |
| `[!IMPORTANT]` | 見逃してはいけない情報 |
| `[!WARNING]` | 注意が必要な事柄 |
| `[!CAUTION]` | 危険を伴う操作 |

この5種類以外は存在しません。他の型も、マーカーの後の独自タイトルも、折りたたみ用の `-`/`+` 修飾子もありません。`[!TYPE]` マーカーのない引用ブロックは通常の引用です。

## タスク行

GFM のチェックボックス項目はタスクであり、括弧内の文字がその状態を表します。状態は**固定**の5種類から選びます。

```markdown
- [ ] TODO — not started
- [/] DOING — in progress
- [?] WAITING — blocked on someone else
- [x] DONE — finished
- [-] CANCELLED — will not happen
```

それ以外のマーカー文字はタスクではありません。行は通常のリスト項目のままです。行のどこかに置いた括弧トークンはメタデータを追加します。

| トークン | 意味 |
| --- | --- |
| `[#A]` | 優先度。`A` が最高（任意の1文字） |
| `[sched:2026-07-18]` | 作業を予定している日 |
| `[due:2026-07-24]` | 期限 |
| `[done:2026-07-09]` | 完了日。**CLI が書き込む**もので、手では書きません |

日付は常に `YYYY-MM-DD` で、ボールトの表示形式には依存しません。見出しや親リスト項目にある `[n/m]` や `[p%]` のクッキーは、その下のタスク数を数えます（見出しは同じか浅いレベルの次の見出しまで数え、リスト項目はより深くインデントされた子を数えます）。

```markdown
### Release checklist [1/3]

- [/] Write the announcement post [#A] [due:2026-07-24]
- [ ] Refresh the screenshots [#B] [sched:2026-07-18]
- [x] Tag the release candidate [done:2026-07-09]
```

**状態マーカーを手で編集してはいけません。** `[done:]` のスタンプ、親のクッキー、サイドカーの遷移ログ、インデックスがすべて整合を保つよう、CLI を使います。

```sh
track task set --title "<note>" --line <n> --state DOING   # --line is 1-based, as reported by track search/export
track task cycle --title "<note>" --line <n>               # advance to the next state, wrapping
track tasks --overdue --sort priority                      # query across the vault (JSON)
```

空の ` ```taskboard ` フェンスは、ノートのタスクをかんばんボードとして描画します。フェンスの本文ではなくタスク行を読み取ります。

## メタデータとプロパティ

**YAML frontmatter は絶対に書かないでください。** ノートのメタデータ（title, tags, created, description, image, icon, 型付き props）はすべて、`.track/` の下のノートごとのサイドカーに置き、CLI でのみ設定します。`new`/`open`/`append`/`update` の `--tag` フラグと、それ以外は `track meta` です。本文の H1 はタイトルではなく通常のコンテンツです。

```sh
track meta --title "<note>" --set status=draft --set rating=8
track new --title "<title>" --tag <tag> --body "<body>"
```

散文に属するデータについては、本文中のインライン型付きプロパティがサポートされています。行全体またはリスト項目としての `key:: value`、文の途中での `[key:: value]` です。ノートレベルの事実（title, tags, icon）は代わりにサイドカーへ置きます。構造的役割を持つインライン項目が1つあります。`up:: [[Parent]]` は階層ナビゲーションのためにノートの親を宣言します。サイドカーの形、`track meta` の使い方、型付けルール、`up` リレーションについては [PROPERTIES.md](references/PROPERTIES.md) を参照してください。

## 数式と描画フェンス

数式は KaTeX による LaTeX です。インラインは `$...$`、ブロックは `$$...$$`。

コードを表示するのではなく描画するフェンス — ` ```mermaid `, ` ```dot `/` ```graphviz `, ` ```d2 `, ` ```mindmap `, ` ```viewspec `, ` ```track-query `, ` ```dashboard `, ` ```taskboard `, および babel 注釈付き言語フェンス — は **track-create-note** スキルにカタログされており、完全な構文は track リポジトリの `docs/help/` にあります。自明でない2つを挙げます。**空の** ` ```mindmap ` フェンスはノート自身の見出しツリーを描画し、` ```viewspec ` ブロックの `data.source` はボールトの `data/` ディレクトリの下で解決されます。

**ダイアグラムには色を書かない。** ダイアグラムフェンスは書かれたとおりにレンダラーへ渡され、読者の現在のテーマで初期化され、テーマが変わると再描画されます。そのため、色を指定しないダイアグラムはライトでもダークでも同様に判読できます。ソースに書き込まれた色はそのまま素通りし、*両方*のテーマで維持されます。つまり、どちらか一方のテーマでは、もう一方のために描かれたダイアグラムが見えることになります。暗いノードの上の暗い文字、薄いページの上の薄い線、といった具合です。`style` や `classDef` の塗り、`themeVariables` を設定する `%%{init: …}%%` ブロック、`dot` の `fillcolor`/`bgcolor` は書かないでください。区別が重要な場合は、形・ラベル・レイアウトで表現します。これらはどちらのテーマでも同じように読めます。例外は、色そのものが内容であるダイアグラム（パレット、信号機の凡例など）です。その場合は前景と背景の両方を明示的に設定し、その組だけで自己完結させます。

**ダイアグラムは縦に伸ばします。** `flowchart` は `TB` を既定にし、`LR` は3〜4ノードの短い流れに限ります。本文カラムの幅は `--measure`（既定 40em）に固定されています。それを超える図が読書面いっぱいに広がる経路はありますが、効くのは読者ビューの最上位に置かれた図だけで、編集中・入れ子の中・その他の面では効きません。そこでは横に伸びた図が幅に合わせて縮小され、ノードの文字が読めなくなります。縦に伸びる図はどの面でも同じ大きさで読め、画面が狭いほど差が開きます。`sequence` や `gantt` のように幅が要素数で決まる図は向きを変えられないので、参加者や行のほうを絞ります。

## ハウススタイル（track fmt）

`track fmt` はノートを標準スタイルに書き換えます。`fmt` が何もしなくて済むよう、すでに準拠した Markdown を生成してください。

- 箇条書きは `-` のみ。`*` や `+` は使わない。
- 各見出しの前にはちょうど2行の空行、後には1行の空行を置く（文書の先頭にある見出しの前には置かない。先頭の空行は削除される）。
- その他の連続する空行は1行の空行にまとめる。
- 末尾の空白は置かない。ファイルはちょうど1つの改行で終わる。
- コードブロックは常にフェンスで囲む。インデントされたコードブロックは `fmt` の保護対象外です。

```sh
track fmt --check --all    # CI check; track fmt <path> formats in place
```

## 非対応の構文

これらはリテラルテキストとして表示されます。生成してはいけません。`%%comments%%`（代わりに `<!-- HTML comments -->` を使う）、`==highlight==`、本文中のインライン `#tags`（タグはサイドカーのみ。`#tag` は検索クエリでのみ機能する）、インライン脚注 `^[text]`（GFM の `[^label]`＋定義を使う）、サイズ付き画像 `![alt|300](url)`、そしてノートをまたぐ ` ```tasks ` や ` ```query ` ブロック（ノート自身のタスクには ` ```taskboard ` を、ボールト全体には CLI の `track tasks` / `track search` を使う）です。

音声と動画にはプレイヤーがありません。代わりにアセットへリンクします — `[label](assets/file.mp3)`。
