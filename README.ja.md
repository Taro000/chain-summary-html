<p align="center">
  <img src="assets/logo.png" alt="chain-summary-html logo" width="589">
</p>

# chain-summary-html

[English](README.md) | 日本語

スキルの連鎖が書いた成果物を、それぞれ 1 枚の HTML のページにまとめる二つのエージェントスキルです。ページの形は同じです。

| スキル | 読むもの | 書くもの | 例 |
|---|---|---|---|
| [quality-summary-html](#quality-summary-html) | [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の `docs/quality/` | `docs/quality/summary.html` | [日本語](https://taro000.github.io/chain-summary-html/ride-hailing-full/docs/quality/summary.html) · [英語](https://taro000.github.io/chain-summary-html/homework-service-full-en/docs/quality/summary.html) |
| [design-summary-html](#design-summary-html) | [req-to-design](https://github.com/Taro000/req-to-design) の `docs/design/`（第 1〜3 段階と 2b） | `docs/design/summary.html` | [日本語](https://taro000.github.io/chain-summary-html/ride-hailing-full/docs/design/summary.html) · [英語](https://taro000.github.io/chain-summary-html/homework-service-full-en/docs/design/summary.html) |

## インストール

```sh
npx skills add Taro000/chain-summary-html                          # どのスキルを、どのエージェントに入れるかを聞かれる
npx skills add Taro000/chain-summary-html -a claude-code -g -y     # 二つとも、Claude Code に、全プロジェクト向けに、確認なしで
npx skills add Taro000/chain-summary-html -s design-summary-html   # 一つだけ
```

Python 3.9 以降と PyYAML が要ります（`uv run --with pyyaml` でも動きます）。それぞれの `evals/`（2.2 MB と 5.8 MB）は、使うだけなら消してかまいません。

## 共通の動き

- 同梱のスクリプトが成果物だけからページ全体を作ります。手で書く部分はないので、何度実行しても同じ形になります。ページを変えたいときは、スクリプトと `assets/` を直します。
- YAML の項目を正とします。報告書が YAML と食い違えば、ページは YAML に従い、スキルがどこで食い違ったかを伝えます。
- ページを作ったあと、スキルはページで示せなかったことを伝えます。成果物どうしの食い違い（どの段階を再実行すれば直るかを添える）と、報告書に見つからなかった節です。
- ラベルは成果物の言語に合わせます。仮名が文字の 1 割以上なら日本語、それ以外は英語です。`--lang ja|en` でラベルだけを切り替えられます。
- ライトモードだけです。`summary.html` は実行のたびに上書きされるので、もとにした docs と一緒にコミットしてください。
- スキルは YAML も報告書も直しません。頼まれない限りコミットもしません。

各表の列と出どころ、省いたものとその理由は、各スキルの `references/page-spec.md` にあります。

## quality-summary-html

4 つの報告書と項目ごとの YAML を読まなくても、各 CUJ から、それを支える要求と SLO までを 1 枚でたどれます（CUJ → QIU → FR → QR → NFR / SLI）。

| 部分 | 中身 |
|---|---|
| トレーサビリティ | 段階ごとの項目の数と、各 CUJ から NFR と SLI までをたどる表。利用者ごとにまとめ、利用者を経由しない要求を最後に置く |
| 第 1 段階 | 事業の要求、利用者、CUJ、利用時の品質要求、失敗のシナリオ、対象にしないもの、式 |
| 第 2 段階 | 機能要件、加えなかった機能 |
| 第 3 段階 | 影響 × 起こりやすさの図、品質のマトリクス（特性 × CUJ）、優先度、品質要求 |
| 第 4 段階 | SLO、SLI、エラーバジェット方針、バーンレートのアラート、そのほかの非機能要件 |

開いているのはトレーサビリティの表だけで、ほかは閉じたトグルに入っています。ID は行へのリンクで、マウスを重ねると表題が出ます。まだ実行していない段階は省きます。根拠、測定点、見えないものは YAML と報告書で読みます。見出しには docs の git のコミットを出し、コミットしていない変更があればそう示します。SLO の目標値が仮なら、ページが示すのは提案だとスキルが伝えます。

**使い方:** cuj-to-slo を少なくとも第 1 段階まで実行し（`docs/quality/context.yaml` が要る）、「docs/quality の成果物を HTML にまとめてください」と頼みます。再実行したあとは「summary.html を作り直してください」。`context.yaml` がなければ、スキルは `cuj-to-quality-in-use` を案内します。読むのは cuj-to-slo 0.3.0 の形式です。それより前の成果物は、cuj-to-slo のリリースノートのとおり、先に各段階を再実行してください。

## design-summary-html

長い報告書を 3 つ読まなくても、順位の付いた設計を動かす要求から、要素、決定、流れ、データまでを 1 枚でたどれます。形は quality-summary-html と同じで、配色はオレンジです。

| 部分 | 中身 |
|---|---|
| 成果物のつながり | 設計を動かす要求からデータの実体までの、段階ごとの項目の数 |
| 第 1 段階 | 順位表（開いておく）、設計の与件、シナリオ、制約、原則、競合、実現できるか |
| 第 2 段階 | 要素、四つのビュー、決定ごとのカード、脅威のモデル、通し確認、費用と体制、負債 |
| 第 2b 段階 | 技術方針（技術の組み合わせ、リポジトリ、テストの層、パイプライン、仕様書の作り方）とその図、決定 |
| 第 3 段階 | 共通の約束事、インタフェース、エラーの決まり、SLI の出どころ、シーケンス図、遅延の予算、画面、ER 図、状態 |

どの段階も、最後にまだ決まっていない申し送り（後の段階か実装に残したこと）を示します。

ページは設計の方向性をすばやくつかむためのものです。

- 項目のある表は YAML から作ります。報告書から読むのは mermaid の図と、どの項目にもない表だけです。報告書の文は載せず、表も図もない節は省いて、スキルがそう伝えます。
- どの文も、最初の文から括弧の補足を除いた要点だけを示します。文を裏付けたりたどったりするための列は省き、改訂の履歴の注記は削ります。
- mermaid は CDN から読むので、ページを見るにはネットが要ります。

**使い方:** req-to-design を少なくとも第 1 段階まで実行し（`docs/design/drv/` が要る）、「docs/design の成果物を HTML にまとめてください」と頼みます。再実行したあとは「設計の要約を作り直してください」。読むのは req-to-design 0.3.0 の形式です。それより前の成果物は、req-to-design のリリースノートのとおり、先に各段階を再実行してください（第 2 段階の後に第 2b 段階）。第 4 段階（詳細設計）はページに載せません。

## メンテナンス

```
skills/<skill>/
├── SKILL.md                 エージェントへの指示
├── scripts/                 生成スクリプト
├── assets/                  CSS、JS、言語ごとの文言（lang/ja.json、lang/en.json）
├── references/page-spec.md  ページの仕様
└── evals/                   試験の 4 件
scripts/check-chain.py       二つの連鎖の用語集、artifacts.md、報告書のテンプレートとの食い違いを確かめる
scripts/build-pages.py       例のサイトを作る（main に push するたび .github/workflows/pages.yml が公開する）
tests/                       自動テスト、試験用の成果物を作るスクリプト、eval の採点スクリプト
```

```sh
# 生成スクリプトを直接動かす（--out、--title、--lang は任意）
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design

# 自動テスト（同じ入力から同じバイト列のページができることも確かめる）
uv run --with pyyaml python3 -m unittest discover -s tests -v

# 二つの eval の成果物から、例のサイトを _site/ に作る
uv run --with pyyaml python3 scripts/build-pages.py

# 架空の課題提出サービスの eval の成果物を作り直す（設計のほうは req-to-design の tables.py と check.py を使う）
uv run --with pyyaml python3 tests/make_homework_fixture.py
uv run --with pyyaml python3 tests/make_homework_design_fixture.py [path/to/req-to-design]

# skill-creator の手順で走らせた design-summary-html の eval を採点する
uv run --with pyyaml python3 tests/grade_design_eval.py skills/design-summary-html-workspace/iteration-1

# 連鎖が変わったら（省くと $CUJ_TO_SLO、なければ ../cuj-to-slo。$REQ_TO_DESIGN、なければ ../req-to-design）
python3 scripts/check-chain.py [path/to/cuj-to-slo] [--req-to-design path/to/req-to-design] [--only cuj-to-slo|req-to-design]

# 手元のコピーを、入れたスキルとして使う
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html
```

生成スクリプトの終了コード: 0 はページを書いた（食い違いがあっても 0）、1 は書いたが自己点検（id の重なり、リンク先のないリンク）に失敗した、2 は成果物を読めなかった。

- `check-chain.py` が食い違いを出したら、`assets/lang/*.json` と生成スクリプトを合わせます。
- quality-summary-html の `summary.css` か `summary.js` を変えたら、design-summary-html の `assets/base.css` / `base.js` にそのまま写します。オレンジの配色は `design.css` にあります。
- eval の `ride-hailing-full` は ride-hailing-app-demo の写しです。quality-summary-html のものはブランチ quality/replay-0.3.0（a26000f）から、design-summary-html のものはブランチ design/trial-0.3.0（cd761e7。`docs/quality` は同じ木）から写しました（summary.html と設計のレビューは除く）。

## ライセンス

MIT
