# quality-summary-html

[English](README.md)

[cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の 4 つの skill が `docs/quality/` に書いた成果物から、品質の要約の HTML（`docs/quality/summary.html`）を 1 枚作る Claude の skill です。

ページの目的は、人がそのシステムの品質を効率よく理解することです。先頭に CUJ ごとのトレーサビリティの表（CUJ → QIU → FR → QR → NFR / SLI）を置き、第 1〜4 段階の表をトグルで続けます。表の中の ID は行へのリンクで、影響 × 起こりやすさの図、製品の品質とデータの品質のマトリクス、SLO のカードを添えます。

ページは同梱のスクリプトが YAML の項目から作るので、どの PJ でも、段階を再実行したあとでも、同じ形のページになります。

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

どちらの入れ方でも `evals/` が一緒に入ります。試験用の成果物（約 1.4 MB）なので、使うだけなら消してかまいません。

## 使い方

Claude に「docs/quality の成果物を HTML にまとめて」のように頼むと、この skill を使います。スクリプトを直接動かすこともできます。

```bash
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality
# 書き出す先と表題を変える
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title 配車アプリの品質
```

スクリプトは、書き出したページのほかに、成果物どうしの食い違い（報告書の表と YAML の違い、廃止した項目への参照など）、報告書に見つからず省いた表、見つからず YAML と突き合わせなかった表を標準出力に出します。

## 構成

```
skills/quality-summary-html/
├── SKILL.md                    Claude への指示
├── scripts/build_summary.py    生成スクリプト（YAML を正にして表を作る）
├── assets/                     見た目（summary.css、summary.js）と用語の対応表（terms.ja.json）
├── references/page-spec.md     ページの仕様: 表と列、出どころ、省いたもの、直し方
└── evals/                      試験の 3 件（配車アプリ、架空の課題提出サービスの全段階と第 2 段階まで）
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

cuj-to-slo の用語や YAML の形が変わったら、`check-chain.py` が食い違いを出します。そのときは `assets/terms.ja.json` と生成スクリプトを合わせてください。

## 決めていること

- 表は YAML（cuj-to-slo の artifacts.md）から作る。報告書の見出しや列名は実行のたびにモデルが書くので、報告書にしかない表（対象にしない、検討して加えなかった機能など）だけを報告書から探し、見つからなければ省く。
- ページは日本語で、ライトモードだけ。
- 生成したページは手で直さない。変えたいときは、スクリプトと `assets/` を直して作り直す。
- `evals/ride-hailing-full` は ride-hailing-app-demo の `docs/quality`（コミット ba28153）の写し。

## ライセンス

MIT。[LICENSE](LICENSE) を見てください。
