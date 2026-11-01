# quality-summary-html

[English](README.md)

[cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の 4 つの skill が `docs/quality/` に書いた成果物から、品質の要約の HTML（`docs/quality/summary.html`）を 1 枚作る Claude の skill です。

ページの目的は、人がそのシステムの品質を効率よく理解することです。先頭に CUJ ごとのトレーサビリティの表（CUJ → QIU → FR → QR → NFR / SLI）を置き、第 1〜4 段階の表をトグルで続けます。表の中の ID は行へのリンクで、影響 × 起こりやすさの図、製品の品質とデータの品質のマトリクス、SLO のカードを添えます。

ページは同梱のスクリプトが YAML の項目から作るので、どの PJ でも、段階を再実行したあとでも、同じ形のページになります。ページは成果物の言語で書きます。日本語の成果物なら日本語、それ以外の言語なら英語です。

## 前提

- cuj-to-slo の skill で `docs/quality/` を作ってあること（少なくとも第 1 段階）。第 2〜4 段階がなければ、その段階を省いたページになる。
- Python 3.9 以降と PyYAML。uv があれば `uv run --with pyyaml` で PyYAML ごと動く。

## 入れ方

[skills CLI](https://github.com/vercel-labs/skills) で入れます。

```bash
# いまの PJ に入れる（どのエージェントに入れるかを聞かれる）
npx skills add Taro000/quality-summary-html
# 自分のすべての PJ で、Claude Code にだけ、確認なしで入れる
npx skills add Taro000/quality-summary-html -g -a claude-code -y
```

`skills/quality-summary-html/` を Claude Code の skill のディレクトリに自分で置いてもかまいません。

```bash
# 自分のすべての PJ で使う
cp -R skills/quality-summary-html ~/.claude/skills/
# このリポジトリを直しながら使うなら、コピーの代わりにリンク
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html
```

どちらの入れ方でも `evals/` が一緒に入ります。試験用の成果物（約 1.7 MB）なので、使うだけなら消してかまいません。

## 使い方

Claude に「docs/quality の成果物を HTML にまとめて」のように頼むと、この skill を使います。スクリプトを直接動かすこともできます。

```bash
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality
# 書き出す先と表題を変える
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title 配車アプリの品質
# 成果物が日本語でも、英語のページにする（変わるのはラベルだけで、中身は書かれた言語のまま）
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --lang en
```

スクリプトは、書き出したページのほかに、成果物どうしの食い違い（報告書の表と YAML の違い、廃止した項目への参照など）、報告書に見つからず省いた表、見つからず YAML と突き合わせなかった表を、ページと同じ言語で標準出力に出します。

## 構成

```
skills/quality-summary-html/
├── SKILL.md                    Claude への指示
├── scripts/build_summary.py    生成スクリプト（YAML を正にして表を作る）
├── assets/                     見た目（summary.css、summary.js）と言語ごとの文言（lang/ja.json、lang/en.json: 用語、ラベル、報告の文言）
├── references/page-spec.md     ページの仕様: 言語、表と列、出どころ、省いたもの、直し方
└── evals/                      試験の 4 件（配車アプリ、架空の課題提出サービスの全段階、第 2 段階まで、英語の全段階）
scripts/check-chain.py          cuj-to-slo の用語集と artifacts.md との食い違いを確かめる
tests/                          自動テストと、架空の PJ の成果物を作るスクリプト
```

## 確かめ方

```bash
# 自動テスト
uv run --with pyyaml python3 -m unittest discover -s tests -v
# cuj-to-slo の用語集と artifacts.md に、この skill が頼るものがまだあるか（既定は隣の quality-kpi-skills）
python3 scripts/check-chain.py [cuj-to-slo のリポジトリか、入れた skill のディレクトリ]
# 架空の PJ の成果物を作り直す
uv run --with pyyaml python3 tests/make_homework_fixture.py
```

cuj-to-slo の用語や YAML の形が変わったら、`check-chain.py` が食い違いを出します。そのときは `assets/lang/ja.json`、`assets/lang/en.json` と生成スクリプトを合わせてください。

## 決めていること

- 表は YAML（cuj-to-slo の artifacts.md）から作る。報告書の見出しや列名は実行のたびにモデルが書くので、報告書にしかない表（対象にしない、検討して加えなかった機能など）だけを報告書から探し、見つからなければ省く。
- ページとスクリプトの報告は成果物の言語に合わせる。日本語の成果物なら日本語、それ以外の言語なら英語（同梱するのはこの 2 つだけ）。`--lang` で変えられる。
- ライトモードだけ。
- 生成したページは手で直さない。変えたいときは、スクリプトと `assets/` を直して作り直す。
- `evals/ride-hailing-full` は ride-hailing-app-demo の `docs/quality`（コミット ba28153）の写し。

## ライセンス

MIT。[LICENSE](LICENSE) を見てください。
