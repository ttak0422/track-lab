# PDF 抽出の Rust 移行候補調査

調査日: 2026-09-23

この文書は主に本文抽出ライブラリの比較を扱う。
文書構造解析、OCR、VLM、エージェント向けツールまで広げた選定は、追加の [AI 向け PDF 解析ツール調査](ai-pdf-parsing-tools.md) を参照する。

**提案は、当面 Poppler を維持して実行環境を Nix で固定し、Rust への移行は `pdf_oxide` による比較検証を通してから判断すること。**
純 Rust の候補はあるが、現在の「抽出に失敗したページを成功扱いしない」という契約まで、ライブラリを差し替えるだけで維持できる候補は確認できなかった。
Rust を採用する価値は Python・Poppler の実行時依存を減らせる点にある。
一方、Nix による依存の供給と、PDF エンジンの実装言語は別々に判断できる。

## 先に変更する Nix の実行入口

現在の [`flake.nix`](../../flake.nix) は lint とその開発環境だけを提供し、PDF 抽出の Python と Poppler は含まない。
[`track-clip`](../../plugins/note/skills/track-clip/SKILL.md) の `nix shell nixpkgs#poppler-utils` は利用者の registry が解決する Nixpkgs を使うため、このリポジトリの `flake.lock` に固定された入口にはなっていない。
開発用 shell へ依存を追加するだけでは、別プロジェクトからインストール済み skill を呼ぶ場合の供給も保証できない。

提案は、既存の `writeShellApplication` を再利用し、PDF 抽出を一つの Nix package として公開すること。
次は `packages` 内へ追加する案であり、今回は実装には適用していない。

```nix
extract-pdf = pkgs.writeShellApplication {
  name = "track-extract-pdf";
  runtimeInputs = [ pkgs.python3 pkgs.poppler-utils ];
  inheritPath = false;
  text = ''
    exec python3 ${./plugins/note/skills/track-clip/scripts/extract_pdf.py} "$@"
  '';
};
```

`runtimeInputs` は実行時の PATH を構成し、`inheritPath = false` は利用者の PATH を引き継がない。
Python と PDF エンジンの依存自体は残るが、導入とバージョン固定を Nix が引き受ける。
[Nixpkgs の writeShellApplication](https://nixos.org/manual/nixpkgs/stable/#trivial-builder-writeShellApplication)

実装時は次の範囲で足りる。

1. ローカルでは `nix run .#extract-pdf -- ...`、配布時は skill の版に対応する固定 revision の package を使う。インストール済み skill の作業ディレクトリをリポジトリ直下と仮定しない。
2. 同じ固定依存で既存の抽出チェックを `checks` に追加する。保存と引用まで検証する場合は、`source` と `cite` を備える track CLI の版も揃える。
3. skill の実行例と README を更新する。現行 README の「外部依存を追加しない」は Web クリップに限定する。

Rust に移行する場合も Nix の配布入口は維持できる。
`rustPlatform.buildRustPackage` と `Cargo.lock` で crate を固定し、必要な features だけを有効にする。
純 Rust でも Cargo の推移的依存や OS の実行時ライブラリまでなくなるわけではなく、配布容量の差は実際の Nix closure で比較する。
[Nixpkgs の Rust ビルド](https://nixos.org/manual/nixpkgs/stable/#rust)

## 今回のローカル検証

対象コミットは `c93101a1b0463125813814032face4bc3205eb1c`。
[`flake.lock`](../../flake.lock) が固定する Nixpkgs は `83199d0d373dd3ac2b9a1996b1d0263f76ab7a4c` だった。

| 検証 | 結果 |
| --- | --- |
| 固定 Nixpkgs の aarch64-darwin 依存 | Python 3.14.7、Poppler 26.06.0 を評価し、Nix の一時環境で供給できた |
| その依存で既存の抽出回帰チェックを実行 | `extract_pdf: all checks passed` |
| aarch64-linux / x86_64-linux | Poppler の derivation 評価は成功。ビルドと実行は未検証 |
| x86_64-darwin | 固定 Nixpkgs がサポート終了を理由に評価を拒否 |
| PDF 保存と引用の結合チェック | インストール済み track が `unknown command "source"` を返して失敗。抽出テストの成功と区別する |

抽出チェックは既存のスクリプトを変更せず、固定 Nixpkgs の `python3` と `poppler-utils` を `nix shell` で供給して実行した。
結合チェックは一時 vault と一時 cache を使い、通常の vault は変更していない。
実装、flake、lockfile の変更は行っていない。

Intel Mac の扱いは PDF ライブラリとは独立した判断になる。
現行 flake の対象一覧には `x86_64-darwin` が残るため、Nix 化の際にサポート対象を整理する必要がある。
維持が必要なら 26.05 系への固定を検討するが、公式のサポート期間は 2026 年末までである。
[Nixpkgs のプラットフォーム変更](https://nixos.org/manual/nixpkgs/unstable/release-notes)

## 今の実装で維持するもの

[`extract_pdf.py`](../../plugins/note/skills/track-clip/scripts/extract_pdf.py) と [回帰チェック](../../plugins/note/skills/track-clip/tests/test_extract_pdf.py) を確認した。
同等性の基準は次のとおり。

- `pdfinfo` の物理ページ数と、`pdftotext` のページ境界数が一致する。
- 途中・末尾の空ページを消さず、各ページの末尾を form feed (`\f`) で区切る。
- UTF-8 と LF に正規化し、全ページに抽出可能な文字がなければ失敗する。
- Poppler が異常終了した場合だけでなく、標準エラーに診断を出した場合も失敗する。
- 原本を一度読み取り、その同じバイト列を抽出・保存・ハッシュ計算に使う。
- 既存ファイルを上書きせず、保存途中の失敗では作成したファイルを取り除く。
- Poppler の検査と抽出を合わせて、既定 30 秒の期限を適用する。

現行テストの本文は Helvetica の単純な英文である。
日本語、複数段組、縦書き、ToUnicode の欠落・破損、Form XObject 内の文字を含む実 PDF の比較にはなっていない。
したがって現状のテスト成功だけで、日本語抽出品質の同等性は判断できない。

## 候補の比較

| 候補 | 外部 PDF エンジン | 現行契約との主な差 | 判断 |
| --- | --- | --- | --- |
| Poppler + 現行 Python | Poppler が必要 | 現行の基準。Nix の実行入口が必要 | 当面維持 |
| `pdf_oxide` | Rust の基本抽出では不要。機能選択によって C/C++ 等が追加される | 全ページ抽出 helper がページエラーを握りつぶす。診断・抽出モードの選択が必要 | Rust の第一検証候補 |
| `pdf-extract` / `lopdf` | Poppler・PDFium は不要 | CJK encoding、読み順、部分失敗・panic に注意。追加実装が必要 | 今回の直接置換には非推奨 |
| `pdfium-render` | C++ の PDFium が別途必要 | Rust はラッパー。PDFium の供給・リンクが残る | 依存削減の目的では非推奨 |

各候補の根拠は以下に記す。
表中の判断は、本リポジトリの要件と一次資料を照合した評価であり、実 PDF コーパスでのベンチマーク結果ではない。

## pdf_oxide: 検証するなら最初の候補

調査では公開タグ **v0.3.78** の `Cargo.toml` と、同版表示の docs.rs を確認した。
ライセンスは `MIT OR Apache-2.0`、宣言された最低 Rust バージョンは 1.88。
`page_count()` とページ番号を渡す `extract_text()` があり、空文字のページを保持したまま物理ページ順に処理する実装を組める。
これは API から判断した実装可能性で、空ページや壊れたページツリーの実測結果ではない。
[公開タグの Cargo.toml](https://raw.githubusercontent.com/yfedoseev/pdf_oxide/v0.3.78/Cargo.toml)、[PdfDocument API](https://docs.rs/pdf_oxide/latest/pdf_oxide/document/struct.PdfDocument.html)

文字復号では ToUnicode と、Adobe-Japan1 などの CID→Unicode fallback が提供される。
読み順の API は単段向けの抽出と、段組等に向けた処理を区別している。
ただし、対応機能があることと日本語 PDF 全般で Poppler 同等であることは同じではない。
縦書きの読み順に関する panic 修正も v0.3.73 に含まれており、この領域は実データで確認したい。
[CharacterMapper](https://docs.rs/pdf_oxide/latest/pdf_oxide/fonts/character_mapper/struct.CharacterMapper.html)、[読み順を含む抽出 API](https://docs.rs/pdf_oxide/latest/pdf_oxide/document/struct.PdfDocument.html#method.extract_text)、[v0.3.73](https://github.com/yfedoseev/pdf_oxide/releases/tag/v0.3.73)

**`extract_all_text()` をそのまま使ってはいけない。**
公開ソースでは各ページの `Err` をログに出して処理を継続し、最終的に `Ok(result)` を返している。
`extract_text_auto()` 等の自動経路も、非 security 系のページ失敗を空の結果へ変える設計が記載されている。
現行契約を維持するには、`page_count()?` で得たページ数を明示的に走査し、ページ API のエラーを伝播させる必要がある。
[document.rs の extract_all_text](https://docs.rs/pdf_oxide/latest/src/pdf_oxide/document.rs.html#7397-7409)、[自動抽出とエラーの説明](https://docs.rs/pdf_oxide/latest/pdf_oxide/document/struct.PdfDocument.html)

ページ API が成功しても、fallback や文字欠落の診断があり得る。
v0.3.78 では診断を本文へ混入させていた問題が修正され、構造化された診断を扱う API が整備された。
`warnings()` / `take_warnings()` は同版で非推奨となっている。
採用時は `structured_warnings()` 等を確認し、正常な文字なしページと、文字の脱落・読めないフォント等を区別する必要がある。
全てを無視すると不完全な抽出を保存し、全てを失敗扱いすると許容したい空ページまで拒否しかねない。
[v0.3.78 リリースノート](https://github.com/yfedoseev/pdf_oxide/releases/tag/v0.3.78)

依存を減らす目的なら、Python binding や多機能 CLI ではなく Rust crate の最小機能を選ぶ。
基本抽出用に `default-features = false` を検討し、古い暗号方式の読み取り範囲を保つなら `legacy-crypto` を明示する。
ただし同版でも `office_oxide` や画像関連 crate は必須依存であり、機能を絞っても PDF テキスト抽出専用の小さなライブラリにはならない。
`fips` は AWS-LC、`icc-lcms2` は Little CMS、`table-ml` は PDFium、`ocr` は動的 ONNX Runtime の経路を追加する。
これらは今回の用途では無効にする。
Cargo の推移的依存、実際のリンク先、Nix closure の大きさはビルドして比較する必要がある。
[v0.3.78 の dependencies / features](https://raw.githubusercontent.com/yfedoseev/pdf_oxide/v0.3.78/Cargo.toml)

2026-09-08 の v0.3.78 まで更新されている点は確認できたが、更新頻度を品質保証とは扱わない。
上流が示す速度や「100% pass rate」は上流のコーパス・判定条件の結果であり、今回独立に再現していない。
また、公式サイトの API ページと docs.rs には版の違う情報があるため、採用する版のソース・lockfile を基準にする。
[v0.3.78](https://github.com/yfedoseev/pdf_oxide/releases/tag/v0.3.78)、[上流の性能説明](https://docs.rs/crate/pdf_oxide/latest)、[公式サイト API](https://pdf.oxide.fyi/rust/docs/reference/rust-api)

## pdf-extract / lopdf: 軽さだけでは選ばない

`pdf-extract` は Rust の `lopdf` を使用する MIT ライセンスの抽出ライブラリ。
確認できた v0.12.0 タグは 2026-06-25、調査時の master の manifest は 0.12.1 だった。
以下の挙動は公開 v0.12.0 のソースでも確認した。
[タグ一覧](https://github.com/jrmuizel/pdf-extract/tags)、[v0.12.0 の依存宣言](https://raw.githubusercontent.com/jrmuizel/pdf-extract/v0.12.0/Cargo.toml)、[master の依存宣言](https://raw.githubusercontent.com/jrmuizel/pdf-extract/master/Cargo.toml)

- `extract_text_by_pages()` はページ抽出が `Ok` の間だけ処理し、最初の `Err` で終了して `Ok(Vec)` を返す。範囲外ページと途中の失敗を区別しない。
- Type0 フォントの名前付き encoding は `Identity-H` / `Identity-V` 以外だと panic する経路がある。ToUnicode が読める日本語 PDF があっても、既定 CMap を使う日本語 PDF 全般の代替とは判断できない。
- PDF 内部構造に対する `unwrap()` / `expect()` があり、`Result` だけで壊れた入力の全失敗を処理できるわけではない。

[v0.12.0 の実装](https://raw.githubusercontent.com/jrmuizel/pdf-extract/v0.12.0/src/lib.rs)

直接 `lopdf` を使えば `get_pages()` とページ単位の `extract_text(&[page])` を組み合わせられる。
しかし確認した実装の文字抽出は PDF の演算子列を順に処理しており、段組の座標配置から読み順を復元する Poppler 同等の処理を、この API 単体で得られるとはいえない。
`Do` による Form XObject の再帰的な文字抽出も、この抽出ループには見当たらない。
これはソースからの評価であり、全機能・全経路を網羅した不対応の断言ではない。
既定機能に `chrono-clock` と `rayon` があり、直接利用時は無効化を検討できる。
調査時 master は 0.45.0、MIT、最低 Rust 1.88 を宣言している。
[抽出ループ](https://raw.githubusercontent.com/J-F-Liu/lopdf/master/src/parser_aux.rs)、[Document API](https://docs.rs/lopdf/latest/lopdf/struct.Document.html)、[Cargo.toml](https://raw.githubusercontent.com/J-F-Liu/lopdf/master/Cargo.toml)

## PDFium wrapper と hayro

`pdfium-render` は MIT / Apache-2.0 の Rust wrapper であり、PDFium 本体を含まず、ビルドも行わない。
共有ライブラリの供給または静的リンクが必要で、場合によっては C++ 標準ライブラリや macOS の framework も必要になる。
Rust から使う API が欲しい場合には候補になるが、Poppler 依存を C++ PDFium 依存へ置き換えても、今回の依存削減効果は小さい。
上流 README は 0.9.4 の修正まで記載している。
[公式 README](https://github.com/ajrcarey/pdfium-render)、[wrapper のライセンス](https://raw.githubusercontent.com/ajrcarey/pdfium-render/master/LICENSE.md)

`hayro` は MIT / Apache-2.0 の純 Rust PDF interpreter / renderer で、公式 README は実験段階と位置づけ、最低 Rust 1.92 を挙げている。
`hayro-interpret::Device` で glyph や描画命令を受け取れるため独自の抽出を組む余地はあるが、読み順や空白の組み立てをこちらで実装する方向になる。
今回は汎用テキスト抽出を得るための直接置換候補から外す。
[公式 README](https://github.com/laurenzv/hayro)、[Device API](https://docs.rs/hayro-interpret/latest/hayro_interpret/trait.Device.html)

## 切り替えの判定条件

Rust の試作を行う場合も、先に多エンジン切り替え設定や独自 PDF parser は作らない。
`pdf_oxide` の固定版を使う小さな抽出実行ファイルで、次を比較すれば判断できる。

1. **現行契約:** 空ページを含む物理ページ数、末尾 `\f`、原本・本文のハッシュ、上書き拒否、失敗時に不完全な成果物を残さないことを確認する。
2. **実際の日本語資料:** 横書き・縦書き、複数段、ToUnicode あり/なし、既定 CMap、埋め込みサブセット、Form XObject、本文と画像だけのページが混在する PDF を比較する。Poppler の出力差分に加え、少数の資料は見た目と本文を突き合わせる。引用する文章や数値・単位が正しいページに残ることを基準にし、空白や改行まで Poppler と一致することは要求しない。
3. **失敗と診断:** 壊れたフォント、壊れた中間ページ、暗号化、循環参照等を、空ページや正常終了へ変換しない。構造化診断の分類も検証する。
4. **期限:** Rust のライブラリを同一プロセスで呼ぶだけでは、現在の subprocess の強制中断を置き換えられない。同一バイナリの worker subprocess 等を使い、期限を超えた抽出処理そのものを終了させる。待機 thread の timeout だけで済ませない。
5. **Nix:** 利用する OS/architecture で固定した依存からビルドでき、利用者が別途 Python・PDF エンジンを準備せず実行できることを確認する。closure、初回ビルド時間、抽出時間、ピークメモリを比べる。

文字内容・ページ境界・失敗時の挙動に回帰がなく、配布と実行時依存が実際に簡単になるなら切り替える。
差分の修復や診断の補完を大きく実装する必要があるなら、Poppler を Nix で供給する構成を維持する。
今回は候補ライブラリのビルド、実 PDF コーパスでの精度・速度比較は実施していない。
