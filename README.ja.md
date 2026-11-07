# quality-summary-html

[English](README.md) | 日本語

スキルの連鎖が書いた成果物を、それぞれ 1 枚の HTML のページにまとめる二つのエージェントスキルです。ページの形と見た目は同じです。

| スキル | 読むもの | 書くもの |
|---|---|---|
| [quality-summary-html](#quality-summary-html) | [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の 4 つのスキルが `docs/quality/` に書いた成果物 | `docs/quality/summary.html` |
| [design-summary-html](#design-summary-html) | [req-to-design](https://github.com/Taro000/req-to-design) のスキルが `docs/design/` に書いた成果物（第 1〜3 段階） | `docs/design/summary.html` |

## インストール

```sh
# 今のプロジェクトに入れる（どのスキルを、どのエージェントに入れるかを聞かれる）
npx skills add Taro000/quality-summary-html

# 二つとも、Claude Code にだけ、すべてのプロジェクトで使えるように、確認なしで入れる
npx skills add Taro000/quality-summary-html -a claude-code -g -y

# 一つだけ入れる
npx skills add Taro000/quality-summary-html -s design-summary-html
```

スキルは Python のスクリプトを動かすので、Python 3.9 以降と PyYAML が要ります。[uv](https://docs.astral.sh/uv/) があれば、`uv run --with pyyaml` で PyYAML ごと動きます。

quality-summary-html の `evals/`（試験用の成果物、約 1.7 MB）も一緒に入ります。使うだけなら消してかまいません。

## quality-summary-html

[cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の 4 つのスキルが `docs/quality/` に書いた成果物を、1 枚の HTML のページ（`docs/quality/summary.html`）にまとめるエージェントスキルです。4 つの報告書と項目ごとの YAML ファイルを読まなくても、各 CUJ から、それを支える要求と SLO までを 1 枚のページでたどれます（CUJ → QIU → FR → QR → NFR / SLI）。

### ページの中身

| 部分 | 中身 |
|---|---|
| トレーサビリティ | 段階ごとの項目の数を並べた図と、各 CUJ から QIU、FR、QR を経て NFR と SLI までをたどる表。表は利用者ごとにまとめ、利用者を経由しない要求（法令、標準・指針、セキュリティのリスク分析、開発方針）を最後のまとまりにする。 |
| 第 1 段階 | 「事業の要求」「利用者」「CUJ」「利用時の品質要求」「失敗のシナリオと測定量」「対象にしない」「一つの式、二つの数え方」（利用時の品質の測定量と KPI） |
| 第 2 段階 | 「機能要件」「検討して加えなかった機能」 |
| 第 3 段階 | 「QR の影響 × 起こりやすさ」の図、「製品の品質」と「データの品質」のマトリクス（特性 × CUJ）、「優先度の表」「CUJ ごとの扱い」「外部品質から導いた内部品質」「品質要求」「利用者を経由しない要求」 |
| 第 4 段階 | SLO のカード、「SLO」「SLI」「エラーバジェット方針」「バーンレートのアラート」「締め切りの SLO」「そのほかの非機能要件」 |

開いているのはトレーサビリティの表だけで、ほかの表はすべて閉じたトグルに入っています。ID は行へのリンクで、マウスを重ねると項目の表題が出ます。まだ実行していない段階は省き、ページの最後の注記にそう書きます。

すばやく読めるように、ページは、ほとんどの項目の根拠、SLO の数値の理由、測定点、見えないもの（測定の制約）などを省いています。これらは YAML と報告書で読んでください。ライトモードだけです。

### 使い方

1. cuj-to-slo のスキルを少なくとも第 1 段階まで実行し、`docs/quality/context.yaml` を作る。
2. 「docs/quality の成果物を HTML にまとめてください。」
3. 段階を再実行したあとで: 「summary.html を作り直してください。」

スキルは同梱のスクリプトを動かします。スクリプトはどの表も YAML の項目から作るので、どのプロジェクトでも、段階を再実行したあとでも、同じ形のページになります。そのあとスキルは、ページで示せなかったことを伝えます。成果物どうしの食い違い（YAML と違う報告書の表、廃止した項目への参照など）には、どの段階を再実行すれば直るかを添えます。報告書に見つからなかった表も伝えます。SLO の目標値が仮のものや、品質要求が下書きのものがあれば、ページが示すのは合意済みの目標ではなく提案だと伝えます。

ページは成果物の言語で書きます。日本語の成果物なら日本語、それ以外の言語なら英語です。変わるのはラベルだけで、中身は書かれた言語のままです。ラベルをもう一方の言語にすることや、表題や書き出す先を変えることも頼めます。

### 出力

```
docs/quality/
├── context.yaml  qiu/ … ebp/              YAML の項目: どの表もここから作る
├── 1-quality-in-use.md … 4-nfr-slo.md     報告書: 段階の表題と、報告書にしかない少数の表を読む
└── summary.html                           このスキルが書くページ
```

ページの見出しには、もとにした docs の git のコミットを出し、コミットしていない変更があればそう示します。`summary.html` は実行のたびに上書きされるので、もとにした docs と一緒にコミットしてください。

### スキルがしないこと

- ページを手で書いたり直したりすること。手で直したページは YAML とずれ、次の実行で消えます。ページを変えたいときは、スクリプトと `assets/` を直します。その変更は、このスキルを使うすべてのプロジェクトに及びます。
- 食い違いを消すために YAML や報告書を直すこと。ページはチェーンの状態を伝えるだけです。直すのは、その項目を持つ段階の仕事です。
- 報告書を YAML より優先すること。cuj-to-slo の artifacts.md のとおり、YAML の項目を正とします。報告書にしかない表は見出しで探し、見つからなければページから省いて、そう伝えます。
- チェーンを実行していないのに、ほかの文書からページを作ること。`context.yaml` がなければ、代わりに `cuj-to-quality-in-use` を案内します。
- 頼まれていないのにコミットすること。

## design-summary-html

[req-to-design](https://github.com/Taro000/req-to-design) のスキルが `docs/design/` に書いた成果物（第 1 段階の設計を動かす要求、第 2 段階のアーキテクチャ、第 3 段階の概要設計）を、quality-summary-html と同じ形で、オレンジの配色の 1 枚の HTML のページ（`docs/design/summary.html`）にまとめるエージェントスキルです。長い報告書を 3 つ読まなくても、順位の付いた要求から、要素、決定、流れ、データまでを 1 枚のページでたどれます。今は日本語の成果物だけを読みます。

### ページの中身

| 部分 | 中身 |
|---|---|
| 成果物のつながり | 設計を動かす要求からデータの実体までの、段階ごとの項目の数 |
| 第 1 段階 | 「順位表」（いちばん上で、開いておく）、「設計の前提と利害関係者」「関心事の一覧」「品質と変更のシナリオ」「制約」「機能・観測・セキュリティの要求」「全体の原則」「競合」「実現できるか」 |
| 第 2 段階 | 「要素」（いちばん上）、五つの「ビュー」（図と表）、「全体の構造」、「設計の決定」と決定ごとのカード（問い、案と退けた理由、得るもの、失うもの、応答を左右する点、引き換え、前提、設計上の値、負債）、「設計の観点」、「脅威のモデル」（信頼の境界と流れの図と、脅威の表）、「通し確認」、「設計上の値」「技術的負債と先送りした決定」「走る費用」 |
| 第 3 段階 | 「共通の約束事」「設計の決定」「インタフェース」「エラーの決まり」、「端から端の流れ」（シーケンス図）、グラフにした「遅延の予算」、「失敗したときの流れとエラーバジェット」、「画面」の図、「データ」（ER 図と実体の表）、「データの品質の流れ」「要素をまたぐ状態」「測定点と監視の NFR の出どころ」「受け入れ基準のトレース」「設計上の値」 |

quality-summary-html と同じく、YAML の項目を正とします。項目のある表（設計を動かす要求、設計の前提、要素、設計の決定、設計上の値、負債、インタフェース、エラーの決まり、データの実体）は、実行のたびに YAML から作ります。報告書から読むのは、mermaid の図と、どの項目にもない節（関心事の一覧、実現できるか、ビュー、脅威のモデル、通し確認、走る費用、共通の約束事、遅延の予算、測定点、受け入れ基準のトレース）だけです。項目を書き写した報告書の表は YAML と突き合わせ、食い違えばそう伝えます。ページは YAML に従います。YAML の文と表のセルからは、改訂の履歴の注記（「前の版は…」や指摘の番号）を削ります。報告書にしかない節の文章はエージェントが添削して `docs/design/summary-text.yaml` に置き、そのもとの節の hash も記録します。段階を再実行したあとは、もとが変わった添削文をスキルが伝え、エージェントがそれだけを書き直します。mermaid は最初の図が見える所に来たときに CDN から読むので、ページを見るにはネットが要ります。ライトモードだけです。

### 使い方

1. req-to-design のスキルを少なくとも第 1 段階まで実行し、`docs/design/drv/` を作る。
2. 「docs/design の成果物を HTML にまとめてください。」最初の実行では、エージェントが `summary-text.yaml`（全体の構造、設計の観点、脅威のモデル、遅延の予算の添削文）も書きます。それができるまでは、その場所に報告書の表や図を出します。YAML から作る部分は、最初の実行から揃います。
3. 段階を再実行したあとで: 「設計の要約を作り直してください。」

### 出力

```
docs/design/
├── drv/ dec/ elm/ ifc/ dat/、design-context.yaml       YAML の項目: 項目のある表はすべてここから作る
├── 1-architecture-drivers.md … 3-high-level-design.md   報告書: 図と、どの項目にもない節
├── summary-text.yaml                                    添削文と、そのもとの hash
└── summary.html                                         このスキルが書くページ
```

`summary-text.yaml` と `summary.html` は、もとにした docs と一緒にコミットしてください。

### スキルがしないこと

- ページを手で書いたり直したりすること。理由は quality-summary-html と同じです。
- ページに合わせて報告書や YAML の項目を直すこと。`summary-text.yaml` の置き換えは、報告書の中で削る規則に掛からない改訂の注記を消すためだけに使います。
- 報告書を YAML より優先すること。食い違えば、ページは YAML を示し、スキルがどこで食い違ったかを伝えます。
- 報告書が言っていないことを添削文に書くこと。
- 英語で書かれた設計の成果物を読むこと。報告書の節は日本語の見出しで探します。
- 頼まれていないのにコミットすること。

## メンテナンス

```
skills/quality-summary-html/
├── SKILL.md                   エージェントへの指示
├── scripts/build_summary.py   生成スクリプト
├── assets/                    summary.css、summary.js と、言語ごとの文言（lang/ja.json、lang/en.json）
├── references/page-spec.md    表ごとの列と出どころ、省いたものとその理由、ページの変え方
└── evals/                     試験の 4 件
skills/design-summary-html/
├── SKILL.md                          エージェントへの指示
├── scripts/build_design_summary.py   生成スクリプト
├── assets/                           base.css と base.js（quality-summary-html の summary.css と summary.js の写し）、design.css（オレンジの配色と設計のページの部品）、design.js
└── references/page-spec.md           表ごとの出どころ、履歴の注記を削る規則、summary-text.yaml の形、ページの変え方
scripts/check-chain.py         cuj-to-slo の用語集と artifacts.md との食い違いを確かめる
tests/                         二つのスキルの自動テストと、架空のサービスの成果物を作るスクリプト
```

エージェントを通さずに生成スクリプトを動かすときは、このリポジトリを clone して使います。

```sh
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality

# 書き出す先と表題を変える
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title 配車アプリの品質

# 日本語の成果物から、英語のラベルのページを作る
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --lang en
```

スクリプトは、ページと同じ言語で報告を標準出力に出します。終了コードが 0 ならページを書いています（食い違いがあっても 0 です）。1 はページを書いたものの自己点検（id の重なり、リンク先のないリンク）に失敗したこと、2 は成果物を読めなかったことを表します。

```sh
# 手元のコピーを、Claude Code に入れたスキルとして使う
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html

# 自動テスト（同じ入力から同じバイト列のページができることも確かめる）
uv run --with pyyaml python3 -m unittest discover -s tests -v

# evals/ にある、架空の課題提出サービスの成果物を作り直す
uv run --with pyyaml python3 tests/make_homework_fixture.py

# cuj-to-slo が変わったら: このスキルが頼るものが、用語集と artifacts.md にまだあるかを確かめる
python3 scripts/check-chain.py [path/to/cuj-to-slo]
```

`check-chain.py` が食い違いを出したら、`assets/lang/ja.json`、`assets/lang/en.json` と生成スクリプトを合わせてください。引数を省くと、環境変数 `CUJ_TO_SLO` のパスを読み、それもなければ `../cuj-to-slo`（このリポジトリの隣に `git clone` したときの場所）を見ます。入れたスキルのディレクトリを渡すこともできます。自動テストも同じ場所で同じ確認をし、cuj-to-slo のリポジトリがなければその確認を飛ばします。

`evals/ride-hailing-full` は ride-hailing-app-demo の `docs/quality`（コミット ba28153）の写しです。

design-summary-html も同じように動かします。報告は日本語で、終了コードの意味も同じです。

```sh
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design

# summary-text.yaml の添削文を書き直したあと: もとの hash を記録する
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design --write-hashes

# 手元のコピーを、Claude Code に入れたスキルとして使う
ln -s "$PWD/skills/design-summary-html" ~/.claude/skills/design-summary-html
```

quality-summary-html の `summary.css` か `summary.js` を変えたら、design-summary-html の `assets/base.css` か `assets/base.js` にそのまま写し、二つのページの形をそろえてください。オレンジの配色は `design.css` にあり、`base.css` の後で色のトークンを定め直します。design-summary-html の自動テストは `tests/test_build_design_summary.py` です（評価ケースはまだありません）。実際のプロジェクトの `summary-text.yaml` の例は、ride-hailing-app-demo の `docs/design/summary-text.yaml` です。

## ライセンス

MIT
