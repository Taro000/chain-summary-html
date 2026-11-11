# Page specification

What `scripts/build_summary.py` puts on the page, where each value comes from, and how to change it. Read this before changing the design or the table set, or when a user asks why the page shows or omits something.

The page is in Japanese or English, following the outputs (see Language). Labels are quoted here as the Japanese page shows them, followed by an English gloss, which is usually the English page's label; the exact English wording is in `assets/lang/en.json`.

## Contents
- Language
- Page structure
- Traceability
- Stage 1 tables
- Stage 2 tables
- Stage 3 tables and figures
- Stage 4 tables and cards
- Report-only tables
- Interactions
- Design
- Checks the script runs
- Changing the page

## Language

The page and the script's report are written in the language of the outputs. `detect_lang` counts kana and Latin letters in every string value of the YAML items and context.yaml (keys left out) and in the reports: Japanese when kana are a tenth or more of them, English otherwise. Japanese outputs measure about 0.5 to 0.75, English outputs 0. Outputs in any other language get English, because only Japanese and English are bundled; their content stays as written, and their report-only tables are usually not found, since headings are looked up in Japanese and English. `--lang ja|en` overrides the detection. Before the language is known (no outputs directory, no context.yaml, no PyYAML), input errors are printed in both languages.

Everything the page and the report say in their own words comes from `assets/lang/<lang>.json`:

- `fonts`: the Google Fonts stylesheet the page loads. The CSS picks the faces by the `lang` attribute (see Design).
- `terms`: the YAML's English enum values in the glossary's terms. Japanese uses the glossary's Japanese column; English uses its English column in sentence case (「最低限守る線」 is "Minimum line", 「今期は対象外」 is "Excluded (this cycle)").
- `text`: labels, counts, punctuation (list separator, parentheses, quotes, CUJ steps) and report messages, with named `{placeholders}`. English labels follow the headings of the cuj-to-slo report templates ("Failure scenario", "Budget volume", "Exhausted in").

Both files have the same keys and placeholders, and every key is used by the script; the tests check this.

The parsers that read report text accept both languages whatever the page's language: a first sentence ends at 。 or at a full stop followed by a space (not after e.g., i.e., etc.), and ID ranges use 〜, ～ or an en dash (「QR-36〜42」, "QR-36–42"). The detail of an external system's role is in full- or half-width parentheses.

## Page structure

1. Header: an eyebrow with the repository name and the docs path, the title (「<system name>の品質」 or "<system name> quality"), and a meta line with the stages covered, the latest update date (the newest report 「更新:」 / "Updated:" date; the items carry no dates, since git keeps their history) and the git commit of the docs, marked 「未コミットの変更あり」 (uncommitted changes) when the docs differ from it. Buttons open and close every toggle.
2. A table of contents on the left (a horizontal strip below 1100 px), listing each stage's toggles.
3. The traceability section (`#sec-trace`).
4. One section per stage that has YAML items (`#sec-1` … `#sec-4`), titled with the report's H1 before the colon.
5. Only when stages or report-only tables are missing: the closed toggle 「この版の注記」 (notes on this version, `#t-notes`) at the bottom, listing the missing stages and the tables left out, and linked last in the table of contents.

Every table sits in a `<details class="tbl">` toggle with a count, closed by default; only the traceability table is open. Inside, the table scrolls within a box up to 78vh high with a sticky header.

## Traceability

The route diagram (`.route`) shows one stop per available item type, with counts: 事業の要求 (business requirements: KGIs, with outcomes and KPIs), 利用者 (users: considered / all), CUJ (per first user), QIU (per top-level characteristic), FR (per origin), QR (per handling, with a small bar), NFR (per kind). Bands under the stops name the stage each stop belongs to. Each stop links to its table.

「CUJ ごとの対応」 (traceability by CUJ) is one table. Rows are grouped by the CUJ's first user, in context.yaml order; within a group, one block per CUJ (rowspan) and one row per live QIU of that CUJ. Columns appear only for the stages that exist:

| Column | Source |
|---|---|
| CUJ | CUJ id, name, and its outcomes |
| QIU | QIU id, the KPIs that count the same formula (`kpi` and KPI `overlaps_with`), title |
| FR | FRs whose `traces_to` names the QIU (numbers only) |
| QR | QRs whose `traces_to` names the QIU, one sub-row each, sorted by handling, then external before internal, then id; chips are colored by handling; 「内部」 (internal) marks internal QRs |
| NFR / SLI | NFRs whose `from` names the QR, with their kind, and the SLI of each SLO; 「範囲外」 (out of scope) when the stage 4 allocation table has an out-of-scope note for the QR |

A CUJ with no QIU gets one row of dashes. QRs with an `entry_point` (laws, standards, security risk analysis, policies) have no CUJ, so they form a last group, 「利用者を経由しない要求」 (requirements that do not come through users), where the QIU column shows the entry type and the first sentence of its source and the FR column shows `applies_to`.

## Stage 1 tables

| Toggle | Columns (source) |
|---|---|
| 事業の要求 (business requirements) | KGI table: ID, KGI (`name`), 測定量 (`measure`), 目標値 (`target`). Outcome table: ID, 中間成果 (`statement`), 動詞 (`verb`), KGI (`kgis`). |
| 利用者 (users) | ID, 利用者, 区分 (`category`), データの役割 (`data_role`), 考慮 (`considered`), 考慮しない理由 (`exclusion_reason`), 根拠 (`basis` + `basis_note`) |
| CUJ | ID, CUJ, 利用者 (`users`), 利用者の目的 (`user_goal`), 手順 (`steps`, numbered), 中間成果 (`outcomes`), 根拠 |
| 利用時の品質要求 (quality-in-use requirements) | ID, 利用者, CUJ, 利用状況 (`context_of_use` values joined), 特性 (characteristic), 要求 (title in bold, then `statement`) |
| 失敗のシナリオと測定量 (failure scenarios and measures) | ID with title, 失敗のシナリオ, 分子 ÷ 分母 (`measure.numerator` over `measure.denominator`), 絞り込み (`measure.narrowed_to`), 見えるか (`measure.observable`) |
| 対象にしない (not targeted) | report-only (see below) |
| 一つの式、二つの数え方 (one formula, two counts) | One row per live KPI (outcome, formula, the narrowed QIUs with their `narrowed_to`, the KPI); one row per QIU that has outcomes but no KPI; one row gathering the QIUs with neither. |

Left out on purpose: the basis of every table except users and CUJs, the overlap column, the shared facts of context.yaml (constraints, external systems, operational facts, design inputs) and the items' `premises` that cite them, and the assumptions in `qas/`. External systems that create data appear only among the data producers (stage 3).

## Stage 2 tables

| Toggle | Columns (source) |
|---|---|
| 機能要件 (functional requirements) | ID, 機能 (title in bold, then `statement`), 受け入れ基準 (`acceptance_criteria`, bulleted), 出どころ (`origin`, with the FRP for proposals), たどれる先 (`traces_to`) |
| 検討して加えなかった機能 (functions considered and not added) | report-only |

Left out on purpose: 既存 (`existing`) and the basis.

## Stage 3 tables and figures

- 「QR の影響 × 起こりやすさ」 (QR impact × likelihood): a 5 × 5 grid of every QR with a `score`, colored by impact × likelihood, chips colored by handling.
- 製品の品質 (product quality): a matrix of the 31 product sub-characteristics (glossary order) by CUJ. A cell lists the external QRs with that characteristic that trace to a QIU of that CUJ. Internal QRs are left out, as in the stage 3 coverage checklist; they appear in 「外部品質から導いた内部品質」. CUJ names are written vertically in the column heads. Before the CUJ columns, the column 「入口」 (entry point) lists the external QRs that come from an entry point (laws, standards, security risk analysis, policies). They have no CUJ, so without this column a row such as security can look empty. It comes before the CUJs because the matrix is often wider than the screen, and a last column stays hidden until the reader scrolls sideways. Its head links to 「利用者を経由しない要求」, and each chip's tooltip names the entry type. The column is left out when no such QR has that model.
- データの品質 (data quality): the same matrix for the 15 data characteristics, with 「データを作る人」 (data producers) below it: the users whose `data_role` is producer or both, then the external systems with `creates_data: true` (`external_systems` in context.yaml), named by their role without its parenthesized detail and marked 「外部のシステム（EXT-01）」 (external system). Retired entries are left out.
- 優先度の表 (priority table): QR (id and title), 特性, 失敗のシナリオ, 影響 (impact), 起こりやすさ (likelihood), 点 (score: impact × likelihood), 扱い (handling badge and the first sentence of `handling_reason`), CUJ (derived through `traces_to`). Sortable by QR and by 点.
- CUJ ごとの扱い (handling by CUJ): per CUJ, the external QRs tracing to it, split into 重視 (emphasized) / 最低限守る線 (minimum line) / 今期は対象外 (excluded this cycle), and the count of emphasized ones.
- 外部品質から導いた内部品質 (internal quality derived from external quality): one row per internal QR, with the external QRs whose `implies_internal` names it and 「どう支えるか」 (how it supports the external one) from the report. Without the report table, the third column is the internal QR's `statement`, headed 「内部の QR の要求」 (the internal QR's requirement).
- 品質要求 (quality requirements): ID, モデル / 層 (model / layer), 特性, 要求 (title in bold, then `statement`), 対象の機能 (`applies_to`), たどれる先 (`traces_to`, or 「入口: <type>」).
- 利用者を経由しない要求: QR, 種類 (`entry_point.type`), 出どころ (`entry_point.source`), 扱い, 要求.

Left out on purpose: the 「—」 reasons of the coverage checklist, the basis, and `entry_point.brought_by` (持ち込んだ人).

## Stage 4 tables and cards

- SLO cards: target, its status (仮 provisional / 確認済み confirmed), the SLI title, and NFR · CUJ · window. Each card links to its SLO row.
- SLO: NFR, CUJ, SLI, 目標値（状態） (target and status), ウィンドウ (window; 「28-day rolling」 becomes 「直近 28 日」 on the Japanese page, and "rolling 30 days" becomes "30-day rolling" on the English one), エラーバジェット (error budget), 許容される失敗の件数 (budget volume, `error_budget_volume`), 方針 (`policy`).
- SLI: SLI, 良いイベント ÷ 有効なイベント (good events ÷ valid events; the element definitions chosen by `function`, such as `OK ÷ VALID`), 見る位置 (`vantage`: 利用者の側 user-side, システムの境界 system boundary, 模擬の利用 synthetic, データ data).
- エラーバジェット方針 (error budget policy): one table per EBP (`rules`: when / action), captioned with its target NFRs when there is more than one.
- バーンレートのアラート (burn-rate alerts): the `alerts` of each SLO; 使い切るまで (exhausted in) = window days ÷ burn rate.
- 締め切りの SLO (deadline SLOs): SLOs with `bad_run_budget_share`, `progress_alert` or `after_miss`.
- そのほかの非機能要件 (other non-functional requirements): NFR, 種類 (kind), 出どころ（扱い） (source and handling), 要件 (`statement`), 確かめる場所 (where it is checked; gate: where and check; audit: mechanism and cadence; monitor: signal and who is notified).

Left out on purpose: measurement points, blind spots, `existing_source`, and the rationale for the numbers.

## Report-only tables

These exist only in the Markdown reports. The script looks for the heading (any level) by the glossary's Japanese term or the template's English heading, whatever the page's language, takes the first table under it, and reads its columns by position, so renamed columns do not matter but reordered ones do.

| Content | Report | Headings looked for | Columns used |
|---|---|---|---|
| 対象にしない | 1 | 対象にしない, Not targeted | CUJ, characteristic, reason |
| 検討して加えなかった機能 | 2 | 検討して加えなかった機能, Functions considered and not added | candidate, for, reason |
| 利用時の品質要求の対応 (checked, not shown) | 2 | 利用時の品質要求の対応, Quality-in-use coverage | QIU, the column named FR; a QIU covered in several ways has a row for each, and a blank QIU cell repeats the QIU above |
| CUJ の手順ごとの機能 (checked, not shown) | 2 | CUJ の手順ごとの機能, 手順ごとの機能, Functions by CUJ step | CUJ, the column named 手順 or Step, the column named FR |
| 外部品質から導いた内部品質 | 3 | 外部品質から導いた内部品質, Internal quality derived from external quality | external, internal, how |
| 割り当て (out-of-scope notes, checked) | 4 | 割り当て, 配分, Allocation | QR, the NFR column, the out-of-scope column |

A missing table that the page shows is left out of the page, listed in 「この版の注記」 (notes on this version), and printed in the report. A missing table that is only compared is printed in the report under 「報告書に見つからず突き合わせなかった表」 (report tables not found and not compared), so that no inconsistencies is not mistaken for a full check.

## Interactions

- Every ID in a table links to the row that defines it. Clicking opens the toggles around the target, scrolls to it, flashes the row, and pushes the hash so the back button returns. IDs without a row on the page (retired items, FRPs) are plain text with a tooltip.
- Hovering or focusing an ID shows a tooltip with its title; for QRs also the handling and 「内部品質」 (internal quality), for NFRs the kind.
- 「すべて開く」 / 「すべて閉じる」 (open all / close all) toggle every table.
- Sorting in the priority table: the first click sorts QR ascending or 点 descending, the second reverses, the third restores the original order.

## Design

Light mode only, by the user's choice. Colors are tokens on `:root` in `assets/summary.css`: a cool paper background, white surfaces, one blue route color for links, emphasized chips and the route line, and amber for risk. Chips encode handling: filled blue (重視), pale blue (最低限守る線), dashed outline (今期は対象外). Fonts come from Google Fonts with system fallbacks, chosen by the page's language: the Japanese page uses Zen Kaku Gothic New for headings and BIZ UDPGothic for text; the English page uses IBM Plex Sans for both (`:root:lang(en)`); both use IBM Plex Mono for IDs and counts. CUJ names in the matrix heads are written vertically; on the English page the Latin text is turned 90°, with less letter spacing. Wide tables scroll inside their box; the page itself never scrolls sideways, down to phone width, where the route diagram turns vertical.

## Checks the script runs

- References between items: every ID a field names must exist and must not be retired (`kgis`, `users`, `outcomes`, `cuj`, `kpi`, `overlaps_with`, `traces_to`, `proposal`, `extends`, `applies_to`, `implies_internal`, `conflicts.with`, `from`, `slo.sli`, `slo.policy`, `refs`, `applies_to` of EBPs), and `cuj_step` must be one of the CUJ's steps.
- Enum values: `handling` and `kind` must be known values; other unknown values are listed under 用語集にない値 (values not in the glossary).
- Both sides of the KPI overlap: a QIU's `kpi` must list the QIU in that KPI's `overlaps_with`.
- Report against YAML: the stage 2 coverage table's FRs per QIU (the FR column only, merged over the QIU's rows), the stage 3 internal-quality pairs, and the stage 4 allocation's NFRs per QR. The report names the tables it compared and those it could not find.
- The stage 2 functions-by-CUJ-step table against each FR's `cuj` and `cuj_step`: an FR must be listed at its step (or, without `cuj_step`, somewhere under its CUJ). A blank CUJ cell repeats the CUJ above; steps are compared ignoring spaces and full- or half-width forms. Not compared, because the table may say more than the YAML can: rows without a CUJ id (「どの CUJ にもない」 (in no CUJ), a stretch between steps), FRs without `cuj` (an FR shared by several CUJs), and extra places an FR is listed besides its own step. A step that is not one of the CUJ's steps is reported once for its row, and a retired FR in the table is reported.
- IDs that appear in reports but not in the YAML are listed as notes (often removed CUJs that a report still mentions).
- The page itself: no duplicate ids, and every `href="#…"` has a target.

## Changing the page

The page is generated, so change the generator, never the output:

- Table columns and order: the `stage1` … `stage4` methods; the traceability table: `trace`; figures: `route`, `risk_chart`, `matrix`, `slo_cards`.
- Look: `assets/summary.css` (tokens at the top) and `assets/summary.js` (links, tooltips, sorting).
- Wording: `assets/lang/ja.json` and `assets/lang/en.json` (see Language). Change a label in both files, and add a new key to both with the same placeholders. The repository's `scripts/check-chain.py` compares the `terms` of both files, and the YAML keys the script reads, with the cuj-to-slo glossary and artifacts.md.
- The quality models (the rows of the matrices, in the glossary's order): `PRODUCT_MODEL` and `DATA_MODEL` in the script.
- Another language: add `assets/lang/<code>.json` with the same keys, add the code to `LANGS`, decide how `detect_lang` recognizes it, give its fonts in the file and in the CSS (`:root:lang(<code>)`), and add a test project in that language.

Keep the output deterministic: no current time, sorted sets, no randomness. The same inputs must give the same bytes, which the tests check.
