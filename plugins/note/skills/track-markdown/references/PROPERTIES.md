# プロパティリファレンス

ノートのメタデータは本文には置かれません。track には **YAML frontmatter はありません**。各ノートにはサイドカーファイル（`.track/notes/<id>.yaml`）があり、title、tags、作成タイムスタンプ、description、カバー画像、icon、`props` の下の型付きプロパティを保持します。本文はプレーンな Markdown のままで、その H1 は通常のコンテンツです。サイドカーの title が正式な名前であり、リンクキーワードになります。メタデータはサイドカーを手で編集するのではなく、CLI を通して編集します。

## CLI によるサイドカーメタデータ

タグは、作成系コマンドの `--tag` フラグで設定します（複数タグはフラグを繰り返します）。`track update --clear-tags` はそれらを削除します。

```sh
track new --title "<title>" --tag <tag> --tag <tag2> --body "<body>"
track append --title "<title>" --tag <extra-tag> --body "<more>"
```

それ以外はすべて `track meta` を通します。

```sh
track meta --title "<note>"                                        # print metadata incl. props (JSON)
track meta --title "<note>" --description "<one-line summary>"
track meta --title "<note>" --image "assets/cover.png" --icon "<emoji>"
track meta --title "<note>" --set status=draft --set rating=8
track meta --title "<note>" --set "authors=[[Ada Lovelace]], [[Alan Turing]]"
track meta --title "<note>" --unset rating
```

`--set` は `key=value` の組を繰り返し受け取ります。`--unset` はキーを削除します。値はそのテキストから型付けされます（型付けルール参照）。カンマ区切りの値はリストになります。

### `--edit` は状態全体を適用する

`track meta --edit -` は stdin から**完全なメタデータドキュメント**を読み取り、アトミックに適用します。パッチではなく、編集可能な状態全体（title, tags, description, image, icon, props）を置き換えます。title を変更するとリネームになります。安全に使うには、素の `track meta` 呼び出しで現在のドキュメントを出力し、それを変更して、完全な結果をパイプで戻します。一点だけの編集には `--set`/`--unset` を優先してください。

```sh
track meta --title "<note>" --edit -    # full metadata document on stdin
```

## インラインフィールド（`key:: value`）

サイドカーはノートレベルの事実の置き場です。データが**散文の中に**属する場合 — 日誌の `weight:: 68.2` の行は日誌の一行である — は、本文に直接書きます。配置は3通りです。

```markdown
status:: draft
- rating:: 8
Met with [owner:: [[Ada Lovelace]]] about the plan.
```

- **行全体** — 単独の行に `key:: value`。
- **リスト項目** — `- key:: value`（番号付き項目も含む）。
- **括弧付き・文中** — 段落内の `[key:: value]`。

インラインフィールドは、サイドカーの値と同じプロパティインデックスに、それぞれ出所の本文行とともにインデックスされ、書いたテキストのまま描画され続けます。データであると同時に散文です。コードはスキャンされません。フェンス内の `std::vector` はコードのままですし、インラインコード内の `[key:: value]` がデータになることはありません。

置き場所の選び方。散文ではない事実（title、tag、icon、ノート自身を表す status）は `track meta` でサイドカーに置きます。テキストの一部として読める事実はインラインに置きます。

## `up`: 唯一の構造プロパティ

`up` は、1つの慣習的な意味を持つ通常のプロパティです。ノートの親を指し、track はそこから階層ナビゲーション（パンくず、子リスト、`track nav`）を導出します。保守すべきアウトラインファイルはありません。

```markdown
up:: [[Projects]]
```

```sh
track meta --title "<note>" --set "up=[[Projects]]"
track nav --id <id>    # ancestor trail + children, as JSON (--id or --path only, not --title)
```

- **リンク型の値だけが対象です。** `up:: draft` はただの文字列プロパティであり、親を作りません。
- 親は複数許されます。パンくずトレイルは最初の親をたどり、どの親もノートを自分の子の一覧に載せます。
- 循環（`A → B → A`）は無害です。トレイルは繰り返しになるところで止まります。
- ノートビューは `up` をプロパティストリップに表示しません。パンくず*そのもの*がその表示だからです。

## 型付けルール

同じ判定がどこでも適用されます — サイドカーの `props`、インラインフィールド、`--set` の値です。

| 値のテキスト | 型 |
| --- | --- |
| `true`, `false` | boolean |
| `8`, `-3.5` | number |
| `2026-07-11`（実在する暦日） | date |
| `[[Title]]` | link |
| `go, lua`（トップレベルのカンマ） | list — 各項目が個別に型付けされる |
| それ以外 | string |

リンク値はその解決キーを保持し（`[[Ada Lovelace|Ada]]` は `Ada Lovelace` を保存）、他の wikilink と同様に解決されます。`[[...]]` 内のカンマはリストを分割しません。

## スキーマと診断

キーを制約するため、track 設定ファイル（track 設定ディレクトリの `config.yml`。例: `~/.config/track/config.yml`。`TRACK_CONFIG` で上書きされる — ボールトのファイルではない）にスキーマを宣言することもできます。

```yaml
properties:
  status:
    type: string
    values: [draft, review, done]
  rating:
    type: number
```

`type` は `string`, `number`, `boolean`, `date`, `link` のいずれかです。`values` は任意の列挙です。宣言されていないキーは制約を受けません。`track doctor` はスキーマに違反するすべての値を、その値の出所のノートと本文行とともに報告し、エディタの LSP は宣言されたキーと値を補完します。

## プロパティが表示される場所

- Web ワークスペースと公開サイトは、本文の上にプロパティストリップを表示します。サイドカーの値が先、その後に本文順のインラインフィールドです。
- `track meta` はスクリプト向けにこれらを JSON で出力します。
- インデックスはすべての値を型付きで、かつ行の出所付きで保存し、フィルタリングと検索に供します。
