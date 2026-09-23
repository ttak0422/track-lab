# AI 向け PDF 解析ツールの比較

調査日: 2026-09-23

AI 向けの PDF 解析には、本文抽出ライブラリより広い選択肢がある。
今回の比較対象は、ページの構造と出典位置を保持する Docling、エージェント向けの LiteParse、Rust を中心に構成する Xberg、および画像から文書を復元するモデル系ツールと商用 API である。
前回の [Rust ライブラリ調査](pdf-extraction-rust-candidates.md) は低水準の本文抽出を主に扱っており、その結論だけでは今回の選定範囲をカバーできない。

今回行ったのは公式資料と公開ソースの確認、および既存の Nixpkgs 固定版でのパッケージ評価である。
候補のビルド、モデル取得、PDF の解析実行、外部 API への文書送信は行っていない。
精度、速度、メモリ使用量について独立した実測結果はない。

## 候補の見取り図

| 候補 | 比較する価値 | ローカル実行時の主な依存 | 選定上の位置付け |
| --- | --- | --- | --- |
| Docling | 読み順、表構造、出典位置付きの文書 JSON | Python、PDF backend、レイアウトや表のモデル、選択した OCR | 構造解析の第一比較候補 |
| LiteParse | 本文、bbox、必要なページの画像をエージェントへ渡す | Rust、PDFium、Tesseract と言語データ | 軽量なエージェント利用の第一比較候補 |
| Xberg / Kreuzberg | Rust core とレイアウト、OCR、構造化出力を統合 | Rust、選択した推論 backend とモデル | Rust を優先する場合の比較候補 |
| PaddleOCR-VL | 日本語を含む画像認識、表、数式 | Python、PaddlePaddle、VLM とレイアウトモデル等 | スキャンや複雑なページの比較候補 |
| MinerU | tier ごとの解析と詳細な中間 JSON | Python、ONNX/Torch、tier に応じた VLM 等 | 構造化結果と段階的解析を重視する場合 |
| Marker | Markdown、表、数式、階層 JSON | Python、Surya、PyTorch、PDFium、VLM backend 等 | モデル利用条件と実行負荷を含めて比較 |
| olmOCR | ページ画像からの VLM 認識 | Python、NVIDIA GPU、モデル、Poppler、フォント | GPU 環境がある場合の候補 |
| PyMuPDF4LLM | ページ単位の Markdown と座標情報 | Python、MuPDF、OCR を使う場合は追加依存 | 軽い処理で足りるかを見る比較対象 |
| MarkItDown | 多形式から Markdown への簡単な変換 | Python、PDF 経路は pdfminer/pdfplumber | 変換中心の比較対象 |
| Unstructured OSS | 意味単位への分割と多形式取り込み | Python、Poppler、Tesseract、推論モデル等 | ETL やコネクタも必要なら検討 |
| LlamaParse | 構造解析、細粒度 bbox、confidence | 通常は商用 API | 外部サービスを許容する場合 |
| Reducto | 元ページ、bbox、表、confidence | 通常は商用 API | 外部サービスを許容する場合 |

この位置付けは機能と運用条件からの評価であり、認識品質のランキングではない。
各候補の一次資料と制約を以下に示す。

## 比較する機能

AI 向けという名称だけでは、LLM を使うか、実行負荷がどの程度かは決まらない。
LiteParse のように埋め込みテキストと座標から構造を組み立てるもの、Docling のようにレイアウトや表のモデルを組み合わせるもの、画像と文章を扱う VLM にページ認識を任せるものがある。
同じ製品でもモードによって変わる。
[LiteParse の構成](https://github.com/run-llama/liteparse)、[Docling の構成](https://docling-project.github.io/docling/usage/advanced_options/)

track の保存と引用に必要なのは、読みやすい Markdown に加え、元 PDF の物理ページと本文の位置へ戻れる出力である。
以下ではページ番号と bbox（ページ内の領域座標）、表構造、認識結果と生成説明の区別を重視する。

## モデルを使う文書構造解析

### Docling

標準 PDF パイプラインは、PDF の文字層にレイアウトと表構造のモデルを組み合わせる。
TableFormer の推定結果を PDF の文字セルと対応付ける設定があり、ページ全体を VLM で転記する方式に限定されない。
DoclingDocument は本文、見出し、表、文書階層、出典情報、取得できた要素の bbox を保持する。
track の引用元を保存する用途では、Markdown に加えてこの構造化 JSON を評価したい。
[公式リポジトリ](https://github.com/docling-project/docling)、[表の設定](https://docling-project.github.io/docling/usage/advanced_options/)、[DoclingDocument](https://docling-project.github.io/docling/concepts/docling_document/)

日本語 OCR はエンジンと言語モデルの選択に依存する。
公式資料には日本語指定や縦書き用 Tesseract データの説明がある一方、別経路の Granite-Docling-258M は日本語を experimental としている。
標準パイプラインと VLM パイプラインは別条件で比較する。
コードは MIT、モデルの条件は選択する重みごとに確認する。
[OCR 設定](https://docling-project.github.io/docling/concepts/OCR/)、[Granite-Docling モデルカード](https://huggingface.co/ibm-granite/granite-docling-258M)、[標準モデル束](https://huggingface.co/docling-project/docling-models)

### PaddleOCR-VL

現行 1.6 の完全なパイプラインは、ページ画像のレイアウトと読み順を推定し、各領域を VLM で認識する。
本文、表、数式、チャートを対象とし、JSON に `page_index`、`page_count`、`block_bbox`、`block_content`、`block_order` がある。
VLM 部分だけを呼ぶ方法とは機能が異なるため、比較対象は完全なパイプラインに揃える。
[公式パイプライン仕様](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html)

日本語を含む多言語対応を掲げ、コードと 1.6 モデルカードは Apache-2.0。
Apple Silicon 向けの PaddlePaddle 経路と MLX-VLM 接続手順もあるが、公式に実機確認した Apple 機は M4 とされる。
日本語の縦書きやルビを含む資料の精度は今回未測定である。
[言語対応](https://github.com/PaddlePaddle/PaddleOCR)、[1.6 モデルカード](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)、[Apple Silicon 手順](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL-Apple-Silicon.html)

### MinerU

現行 README は 4.0 を stable とする。
文字層中心の flash、小型モデルを使う basic、VLM も使う standard / advanced を選び、ModelJson / MiddleJson にページとブロックの情報を残す。
`page_index_map` で元 PDF のページへ対応付けられる。
一方、flash では数式を空の内容と画像や位置情報へ置き換える場合があるため、出力形式が同じでも tier 間の情報量を同一視しない。
[公式リポジトリ](https://github.com/opendatalab/MinerU)、[tier](https://opendatalab.github.io/MinerU/usage/tiers/)、[出力仕様](https://opendatalab.github.io/MinerU/reference/output_files/)

CPU と Apple Silicon の実行経路があり、モデルの事前取得と local 供給も用意されている。
エージェント向け `mineru parse` は初回既定が先頭 10 ページであり、全ページ取得のつもりで使わない。
コードは現在、Apache-2.0 を基に追加条件を持つ独自ライセンスで、古い AGPL の説明をそのまま使えない。
モデルは別条件であり、調査した MinerU2.5-Pro のカードは中国語と英語を掲げる。日本語品質は未確認。
[モデル供給元](https://opendatalab.github.io/MinerU/usage/model_source/)、[CLI の使い分け](https://github.com/opendatalab/MinerU)、[コードの条件](https://raw.githubusercontent.com/opendatalab/MinerU/master/LICENSE.md)、[モデルカード](https://huggingface.co/opendatalab/MinerU2.5-Pro-2604-1.2B)

### Marker

現在の fast モードは文字層を活用し、レイアウト検出と必要箇所の VLM 認識を組み合わせ、balanced は VLM をより多く使う。
Markdown のほか、ページとブロックの階層、polygon、抽出方法を含む JSON を提供する。
CPU と Apple Silicon の VLM には llama.cpp のサーバー、NVIDIA では vLLM を使う経路が案内されている。
軽量な文字抽出の置換としては依存が増えるが、表と数式を含む Markdown 化の比較対象になる。
[公式 README](https://github.com/datalab-to/marker)、[依存定義](https://raw.githubusercontent.com/datalab-to/marker/master/pyproject.toml)

調査した master の manifest は 2.0.0 でコードは Apache-2.0、モデル重みは企業規模等による条件を持つ別ライセンスである。
コードのライセンスだけで、モデルを同じ条件で再配布できると判断しない。
日本語品質とオフライン実行は未検証。
[manifest](https://raw.githubusercontent.com/datalab-to/marker/master/pyproject.toml)、[モデルの条件](https://raw.githubusercontent.com/datalab-to/marker/master/MODEL_LICENSE)

### olmOCR

olmOCR-2-7B-1025 はページ画像を読む VLM で、本文の文字範囲と物理ページを結び付ける出力がある。
標準の Dolma 出力を作る処理にはブロック bbox はなく、再試行後に `pdftotext` へフォールバックする経路もある。
位置情報の粒度と、フォールバックした結果の区別を確認する必要がある。
[モデルカード](https://huggingface.co/allenai/olmOCR-2-7B-1025)、[pipeline](https://raw.githubusercontent.com/allenai/olmocr/main/olmocr/pipeline.py)

公式の主なローカル手順は NVIDIA GPU 12 GB 以上、ディスク 30 GB 以上、Poppler とフォントを要求する。
コードと上記モデルは Apache-2.0 だが、モデルカードの言語表示は英語で、日本語品質は確認していない。
今回の Apple Silicon と Nix を中心とする候補では優先度を下げ、GPU 環境を使う場合の比較対象に残す。
[導入手順](https://github.com/allenai/olmocr)、[モデルカード](https://huggingface.co/allenai/olmOCR-2-7B-1025)

## エージェント向けの軽量抽出と Rust 系

### LiteParse

LlamaIndex のローカル文書解析ツールで、現在の主ブランチは Rust core、PDFium、Tesseract という構成である。
空間情報を保持したテキスト、Markdown、JSON、bbox、ページ画像、複雑さの判定を提供する。
通常のローカル構成で LlamaParse のクラウド契約は不要だが、C/C++ の PDFium と Tesseract への依存は残る。
コードは Apache-2.0。
[公式 README](https://github.com/run-llama/liteparse)

エージェントがまず本文を読み、必要なページだけ画像で確かめる使い方と相性がよいと評価する。
高度な数式認識やグラフの数値復元までを、この軽量経路に期待するものではない。
OCR 言語の初期値は英語であり、日本語を使う構成では言語データと設定を固定する。
事前取得した tessdata のパスを指定するオフライン利用が案内されている。
[CLI と OCR 設定](https://github.com/run-llama/liteparse#ocr-setup)

### Xberg / Kreuzberg

現行の Xberg は Kreuzberg の後継として案内されている。
Rust core に文書抽出、OCR、レイアウト、表認識、構造化出力、CLI、MCP をまとめており、単体 PDF ライブラリより今回の用途に近い候補である。
コードは MIT。
[公式 README](https://github.com/xberg-io/xberg)

調査時の主ブランチでは `pdf` feature は native PDF engine を選び、PDFium backend は別 feature である。
一方、通常の `layout-detection` は ONNX Runtime とモデル取得を伴い、OCR も backend によって依存が変わる。
Rust だけの推論経路も用意されるが、同じモデルと全機能を利用できるとは限らない。
「Rust 製だから全機能が外部エンジン不要」と判断せず、採用する固定版と features を確認する必要がある。
[feature 定義](https://raw.githubusercontent.com/xberg-io/xberg/main/crates/xberg/Cargo.toml)、[native PDF engine の依存](https://raw.githubusercontent.com/xberg-io/xberg/main/crates/xberg-native-pdf/Cargo.toml)

ページ別出力とレイアウト認識を有効にすると、ページごとの領域種別、confidence、bbox を返す。
この出力は引用元の追跡に使えるが、認識の正しさや空ページの保持は実資料で検証が必要である。
今回は公開 docs と main の構成確認までで、固定リリースの最小構成ビルドは行っていない。
[レイアウト出力](https://docs.xberg.io/guides/layout-detection/)、[型定義](https://docs.xberg.io/reference/types/)

### PyMuPDF4LLM と MarkItDown

PyMuPDF4LLM は既存 PDF の Markdown 化とページ別出力を比較する基準として残す。
`page_chunks=True` でページ番号付きの出力を得られ、表や語の座標も設定に応じて取得できる。
Python と MuPDF を使い、OCR は別エンジンと言語データに依存する。
コードのライセンスは AGPL 系で、商用ライセンスも提供されている。
[API](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html)、[公式ライセンス説明](https://pymupdf.io/blog/open-source-all-the-way-down-pymupdf4llm-goes-fully-agpl)

MarkItDown は Microsoft の汎用 Markdown 変換ツールで、今回確認した PDF 経路は pdfminer と pdfplumber が中心である。
基本の変換と、LLM を使う OCR plugin や外部サービス連携は区別する。
複雑な PDF のモデル解析を選ぶ本命というより、簡単な変換で足りるかを見る比較対象になる。
コードは MIT。
[公式 README](https://github.com/microsoft/markitdown)、[PDF converter](https://raw.githubusercontent.com/microsoft/markitdown/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py)

## 商用 API と取り込み基盤

| 候補 | 主な機能と出典情報 | 実行上の位置付け |
| --- | --- | --- |
| LlamaParse | 段組、OCR、表、数式等。モードにより Markdown/JSON、ページ情報、語や行や表セルの bbox、confidence | 通常は商用 API。構造解析と位置情報を含む比較候補 |
| Reducto | 表、OCR、レイアウト、chunk。block bbox、元ページの `original_page`、confidence | 商用 API。引用元の追跡を重視する比較候補 |
| Unstructured OSS | PDF を意味単位に分割。ページ番号、座標、表 HTML。fast / hi_res / ocr_only | Python、Poppler、Tesseract、推論モデル等を使うローカル基盤 |
| Unstructured commercial | Fast / High Res / VLM の振り分けと enrichment | 商用独自モデルを含み、OSS と同じ機能集合ではない |

LlamaParse は語、行、表セルの bbox を追加できるが、署名 URL の JSONL sidecar も取得して保持する必要がある。
Enterprise の BYOC でも外部 LLM API を呼ぶ構成が説明されており、自己ホストを完全オフラインと同一視できない。
[Parse の概要](https://developers.llamaindex.ai/llamaparse/parse/)、[細粒度 bbox](https://developers.llamaindex.ai/llamaparse/parse/examples/parse_granular_bboxes/)、[BYOC](https://developers.llamaindex.ai/llamaparse/self_hosting/)

Reducto では部分ページの解析後に `page` が振り直される場合があるため、引用には `original_page` を使う。
調査時の新しい r-1 preview と legacy Parse では、OCR 設定やセル bbox の対応が異なる。
Enterprise の VPC/on-prem 配備もあるが、一般的な OSS ライブラリの導入とは別の選択である。
[出力仕様](https://docs.reducto.ai/parse/response-format)、[r-1 の互換性](https://docs.reducto.ai/configs/parse/r-1-configuration-compatibility)、[配備形態](https://docs.reducto.ai/onprem/enterprise_deployment_options)

Unstructured OSS は Apache-2.0 で、最新の独自 VLM や調整済み OCR を含まない。
商用機能の品質評価を OSS にそのまま当てはめることはできない。
多形式の ETL やコネクタも必要なら候補になるが、PDF クリップだけへの導入は範囲が広いと評価する。
[OSS の範囲](https://docs.unstructured.io/open-source/introduction/overview)、[OSS の分割処理](https://docs.unstructured.io/open-source/core-functionality/partitioning)、[要素のメタデータ](https://docs.unstructured.io/open-source/concepts/document-elements)

商用 API のクライアントを Nix で配布しても、API 契約、通信、従量課金、提供側のモデル更新への依存は残る。
料金は解析モードと追加出力でも変わるため、比較時は同じ資料と同じ機能で見積もる。
[LlamaParse の課金単位](https://developers.llamaindex.ai/llamaparse/general/pricing/)、[Reducto の提供プラン](https://reducto.ai/pricing)

## 現在の Nix 固定版で確認できたこと

[`flake.lock`](../../flake.lock) の Nixpkgs revision `83199d0d373dd3ac2b9a1996b1d0263f76ab7a4c` を、`config = {}` で読み込んだ。
`aarch64-darwin` と `x86_64-linux` の各 package の `drvPath` を評価した結果は以下である。
評価成功はビルド成功や解析品質の確認を意味しない。

| 固定版の package | バージョン | Apple Silicon macOS | x86_64 Linux |
| --- | --- | --- | --- |
| `docling` | 2.118.0 | 評価失敗: docling-core のテスト依存 saxonche が unfree 判定 | 同じ理由で評価失敗 |
| `liteparse` | 2.13.0 | package の対象 platform 外 | 評価成功 |
| `python3Packages.paddleocr` | 3.7.0 | 評価失敗: PaddlePaddle 3.3.0 が Python 3.14 非対応 | 同じ理由で評価失敗 |
| `markitdown` | 0.1.7 | 評価成功 | 評価成功 |
| `python3Packages.pymupdf4llm` | 0.3.4 | 評価成功 | 評価成功 |
| `python3Packages.unstructured` | 0.18.31 | 評価成功 | 評価成功 |

上流資料に書かれた現行機能と、表の Nix 収録版の機能は一致するとは限らない。
採用する場合は、対象バージョンの出力仕様とモデル構成を再確認する。

Docling の失敗は、この固定版の Nix パッケージが持つテスト依存による。
Docling 自体のコードライセンスや、PDF 実行時に saxonche が必要だという意味ではない。
上流ツールの macOS 対応と、Nixpkgs の特定 revision の対応も分けて判断する。
[docling-core の Nix 定義](https://github.com/NixOS/nixpkgs/blob/83199d0d373dd3ac2b9a1996b1d0263f76ab7a4c/pkgs/development/python-modules/docling-core/default.nix)、[LiteParse の Nix 定義](https://github.com/NixOS/nixpkgs/blob/83199d0d373dd3ac2b9a1996b1d0263f76ab7a4c/pkgs/by-name/li/liteparse/package.nix)

この revision のファイル検索では Xberg/Kreuzberg、MinerU、olmOCR、Datalab Marker の専用定義は見つからなかった。
`pkgs.marker` は名前が同じ別製品の Markdown エディタである。
専用定義が見つからないことは Nix 化できないことを意味しないが、追加のパッケージ作業を見込む必要がある。
[別製品の marker 定義](https://github.com/NixOS/nixpkgs/blob/83199d0d373dd3ac2b9a1996b1d0263f76ab7a4c/pkgs/by-name/ma/marker/package.nix)

モデルを使う構成では、実行ファイルだけでなくモデルの revision とハッシュ、OCR 言語データ、推論 runtime も固定対象になる。
例えば Docling はモデルの事前取得と `artifacts_path` によるオフライン実行を案内している。
Nix の package が存在するだけでは、初回実行時のモデル取得まで固定済みとは判断できない。
[Docling のモデル事前取得](https://docling-project.github.io/docling/usage/advanced_options/#model-prefetching-and-offline-usage)

## 調査後の方針: Xberg を多形式の共通抽出器として優先

ユーザーは PDF に加えて他形式にも利用し、将来の依存管理を軽くする観点から Xberg を支持した。
以後は Xberg を第一候補とし、最小構成で Nix に収められるかを先に確認する。
これは複数の変換ツールを個別に管理する負担を減らすための方針であり、実行速度、メモリ、配布容量が最小だと実測した結論ではない。

Xberg は PDF、Office、HTML、メール等に対応し、core crate は `pdf`、`office`、`excel`、`html` 等の feature を選べる。
一方、標準 CLI の default features は OCR、レイアウト、埋め込み、VLM 等も含む。
軽量な導入では既定構成をそのまま採らず、固定版で必要な feature の依存を確認してビルドする。
[対応形式](https://github.com/xberg-io/xberg)、[core の feature 定義](https://raw.githubusercontent.com/xberg-io/xberg/main/crates/xberg/Cargo.toml)、[CLI の既定構成](https://raw.githubusercontent.com/xberg-io/xberg/main/crates/xberg-cli/Cargo.toml)

このリポジトリでは PDF 抽出が `extract_pdf.py` にまとまっており、Web 取得は別バイナリの `track-fetch-web` を呼んでいる。
最初の導入対象を現在利用中の PDF 抽出に絞り、既存の原本確保、ハッシュ、物理ページ、失敗時の出力破棄という契約を検証する。
DOCX、XLSX、PPTX 等は、利用が必要になった時点で同じ抽出器へ追加する。
位置情報は PDF のページ、表計算のシート、プレゼンテーションのスライドなど、各形式の単位を保持する。
Web 取得の置換は別判断とし、Xberg の HTML 対応だけを理由に既存の取得処理まで変更しない。

後続で確認する順序は、固定版の必要最小限のビルド、Nix による実行環境の固定、既存 PDF 契約と日本語資料の検証とする。
OCR やレイアウトモデルは必要性が確認された時点で追加し、その際に重みと言語データも固定する。
この方針を記録した段階では、実装や依存設定は変更していない。

## 後続の検証条件

比較候補を絞る段階では、構造解析の Docling、軽量なエージェント利用の LiteParse、Rust を優先する Xberg を基本候補とした。
スキャンや表や数式が中心なら PaddleOCR-VL と MinerU を追加し、外部 API を許容するなら LlamaParse または Reducto を比較対象に加える。
上記の方針を受け、まず Xberg の適合性を検証し、品質や機能に不足があれば他候補との比較へ戻る。

原本 PDF、構造化された解析結果、読みやすい Markdown は、それぞれ保持する情報が違う。
ツールを比較するときは原本のハッシュ、エンジンとモデルの版、元ページ、bbox、エラーや警告を残せるかを確認する。
数値を含む資料では、生成された説明と原文の認識結果を混ぜない。
例えば Unstructured の table description enrichment は、要素の text を生成要約に置き換える仕様である。
[table description の仕様](https://docs.unstructured.io/concepts/enriching/table-descriptions)

後続で実行比較を選ぶ場合は、日本語の横書きと縦書き、複数段、表、数式、画像 PDF、空ページを含む同じ資料を使う。
本文の引用一致、数値と単位、表のセル対応、読み順、物理ページの一致、欠落の検知、処理時間、メモリ、取得容量を別々に評価する。
confidence はレビュー箇所を選ぶ手掛かりであり、原文との一致を検証した結果の代わりにはしない。

公開ベンチマークには OmniDocBench などがあり、本文、表、数式、読み順の評価に利用できる。
ただし、異なる資料、モデル、ハードウェア、指標のスコアを一つの順位にまとめない。
今回、日本語の実資料で優劣を確認した候補はない。
[OmniDocBench の評価対象と指標](https://github.com/opendatalab/OmniDocBench)
