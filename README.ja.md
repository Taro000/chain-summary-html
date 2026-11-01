# quality-summary-html

[English](README.md) | 日本語

[cuj-to-slo](https://github.com/Taro000/cuj-to-slo) の 4 つのスキルが `docs/quality/` に書いた成果物を、1 枚の HTML のページ（`docs/quality/summary.html`）にまとめるエージェントスキルです。4 つの報告書と項目ごとの YAML ファイルを読まなくても、各 CUJ から、それを支える要求と SLO までを 1 枚のページでたどれます（CUJ → QIU → FR → QR → NFR / SLI）。

## ページの中身

| 部分 | 中身 |
|---|---|
| トレーサビリティ | 段階ごとの項目の数を並べた図と、各 CUJ から QIU、FR、QR を経て NFR と SLI までをたどる表。表は利用者ごとにまとめ、利用者を経由しない要求（法令、標準・指針、セキュリティのリスク分析、開発方針）を最後のまとまりにする。 |
| 第 1 段階 | 「事業の要求」「利用者」「CUJ」「利用時の品質要求」「失敗のシナリオと測定量」「対象にしない」「一つの式、二つの数え方」（利用時の品質の測定量と KPI） |
| 第 2 段階 | 「機能要件」「検討して加えなかった機能」 |
| 第 3 段階 | 「QR の影響 × 起こりやすさ」の図、「製品の品質」と「データの品質」のマトリクス（特性 × CUJ）、「優先度の表」「CUJ ごとの扱い」「外部品質から導いた内部品質」「品質要求」「利用者を経由しない要求」 |
| 第 4 段階 | SLO のカード、「SLO」「SLI」「エラーバジェット方針」「バーンレートのアラート」「締め切りの SLO」「そのほかの非機能要件」 |

開いているのはトレーサビリティの表だけで、ほかの表はすべて閉じたトグルに入っています。ID は行へのリンクで、マウスを重ねると項目の表題が出ます。まだ実行していない段階は省き、ページの最後の注記にそう書きます。

すばやく読めるように、ページは、ほとんどの項目の根拠、SLO の数値の理由、測定点、見えないもの（測定の制約）などを省いています。これらは YAML と報告書で読んでください。ライトモードだけです。

## インストール

```sh
# 今のプロジェクトに入れる（どのエージェントに入れるかを聞かれる）
npx skills add Taro000/quality-summary-html

# Claude Code にだけ、すべてのプロジェクトで使えるように、確認なしで入れる
npx skills add Taro000/quality-summary-html -a claude-code -g -y
```

スキルは Python のスクリプトを動かすので、Python 3.9 以降と PyYAML が要ります。[uv](https://docs.astral.sh/uv/) があれば、`uv run --with pyyaml` で PyYAML ごと動きます。

`evals/`（試験用の成果物、約 1.7 MB）もスキルと一緒に入ります。使うだけなら消してかまいません。

## 使い方

1. cuj-to-slo のスキルを少なくとも第 1 段階まで実行し、`docs/quality/context.yaml` を作る。
2. 「docs/quality の成果物を HTML にまとめてください。」
3. 段階を再実行したあとで: 「summary.html を作り直してください。」

スキルは同梱のスクリプトを動かします。スクリプトはどの表も YAML の項目から作るので、どのプロジェクトでも、段階を再実行したあとでも、同じ形のページになります。そのあとスキルは、ページで示せなかったことを伝えます。成果物どうしの食い違い（YAML と違う報告書の表、廃止した項目への参照など）には、どの段階を再実行すれば直るかを添えます。報告書に見つからなかった表も伝えます。SLO の目標値が仮のものや、品質要求が下書きのものがあれば、ページが示すのは合意済みの目標ではなく提案だと伝えます。

ページは成果物の言語で書きます。日本語の成果物なら日本語、それ以外の言語なら英語です。変わるのはラベルだけで、中身は書かれた言語のままです。

スクリプトを直接動かすこともできます。

```sh
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality

# 書き出す先と表題を変える
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title 配車アプリの品質

# 日本語の成果物から、英語のラベルのページを作る
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --lang en
```

スクリプトは、ページと同じ言語で報告を標準出力に出します。終了コードが 0 ならページを書いています（食い違いがあっても 0 です）。1 はページを書いたものの自己点検（id の重なり、リンク先のないリンク）に失敗したこと、2 は成果物を読めなかったことを表します。

## 出力

```
docs/quality/
├── context.yaml  qiu/ … ebp/              YAML の項目: どの表もここから作る
├── 1-quality-in-use.md … 4-nfr-slo.md     報告書: 段階の表題と、報告書にしかない少数の表を読む
└── summary.html                           このスキルが書くページ
```

ページの見出しには、もとにした docs の git のコミットを出し、コミットしていない変更があればそう示します。`summary.html` は実行のたびに上書きされるので、もとにした docs と一緒にコミットしてください。

## スキルがしないこと

- ページを手で書いたり直したりすること。手で直したページは YAML とずれ、次の実行で消えます。ページを変えたいときは、スクリプトと `assets/` を直します。その変更は、このスキルを使うすべてのプロジェクトに及びます。
- 食い違いを消すために YAML や報告書を直すこと。ページはチェーンの状態を伝えるだけです。直すのは、その項目を持つ段階の仕事です。
- 報告書を YAML より優先すること。cuj-to-slo の artifacts.md のとおり、YAML の項目を正とします。報告書にしかない表は見出しで探し、見つからなければページから省いて、そう伝えます。
- チェーンを実行していないのに、ほかの文書からページを作ること。`context.yaml` がなければ、代わりに `cuj-to-quality-in-use` を案内します。
- 頼まれていないのにコミットすること。

## メンテナンス

```
skills/quality-summary-html/
├── SKILL.md                   エージェントへの指示
├── scripts/build_summary.py   生成スクリプト
├── assets/                    summary.css、summary.js と、言語ごとの文言（lang/ja.json、lang/en.json）
├── references/page-spec.md    表ごとの列と出どころ、省いたものとその理由、ページの変え方
└── evals/                     試験の 4 件
scripts/check-chain.py         cuj-to-slo の用語集と artifacts.md との食い違いを確かめる
tests/                         自動テストと、架空のサービスの成果物を作るスクリプト
```

```sh
# 手元のコピーを、Claude Code に入れたスキルとして使う
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html

# 自動テスト（同じ入力から同じバイト列のページができることも確かめる）
uv run --with pyyaml python3 -m unittest discover -s tests -v

# evals/ にある、架空の課題提出サービスの成果物を作り直す
uv run --with pyyaml python3 tests/make_homework_fixture.py

# cuj-to-slo が変わったら: このスキルが頼るものが、用語集と artifacts.md にまだあるかを確かめる
python3 scripts/check-chain.py path/to/cuj-to-slo
```

`check-chain.py` が食い違いを出したら、`assets/lang/ja.json`、`assets/lang/en.json` と生成スクリプトを合わせてください。`check-chain.py` には、入れたスキルのディレクトリを渡すこともできます。環境変数 `CUJ_TO_SLO` でパスを渡すこともできます。

`evals/ride-hailing-full` は ride-hailing-app-demo の `docs/quality`（コミット ba28153）の写しです。

## ライセンス

MIT
