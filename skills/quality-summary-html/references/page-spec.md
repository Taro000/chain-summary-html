# Page specification

What `scripts/build_summary.py` puts on the page, where each value comes from, and how to change it. Read this before changing the design or the table set, or when a user asks why the page shows or omits something.

## Contents
- Purpose and requirements
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

## Purpose and requirements

Purpose: people understand the system's quality efficiently. The requirements came from the user who approved the design, and they are printed at the bottom of every page in the closed toggle 「HTML作成時の要件」 (the `PURPOSE`, `REQS` and `RULES` lists in the script). In short: the tables listed below and nothing around them; IDs link to their rows; every table folds; figures where they help; traceability first, gathered into one CUJ-by-CUJ table; light mode.

## Page structure

1. Header: an eyebrow with the repository name and the docs path, the title (「<system name>の品質」), and a meta line with the stages covered, the latest update date (the newest `changelog` date or report 「更新:」 date) and the git commit of the docs, marked 「未コミットの変更あり」 when the docs differ from it. Buttons open and close every toggle.
2. A table of contents on the left (a horizontal strip below 1100 px), listing each stage's toggles.
3. The traceability section (`#sec-trace`).
4. One section per stage that has YAML items (`#sec-1` … `#sec-4`), titled with the report's H1 before the colon.
5. The closed toggle 「HTML作成時の要件」 (`#t-req`), plus 「この版の注記」 when stages or report-only tables are missing.

Every table sits in a `<details class="tbl">` toggle with a count, closed by default; only the traceability table is open. Inside, the table scrolls within a box up to 78vh high with a sticky header.

## Traceability

The route diagram (`.route`) shows one stop per available item type, with counts: 事業の要求 (KGIs, with outcomes and KPIs), 利用者 (considered / all), CUJ (per first user), QIU (per top-level characteristic), FR (per origin), QR (per handling, with a small bar), NFR (per kind). Bands under the stops name the stage each stop belongs to. Each stop links to its table.

「CUJ ごとの対応」 is one table. Rows are grouped by the CUJ's first user, in context.yaml order; within a group, one block per CUJ (rowspan) and one row per live QIU of that CUJ. Columns appear only for the stages that exist:

| Column | Source |
|---|---|
| CUJ | CUJ id, name, and its outcomes |
| QIU | QIU id, the KPIs that count the same formula (`kpi` and KPI `overlaps_with`), title |
| FR | FRs whose `traces_to` names the QIU (numbers only) |
| QR | QRs whose `traces_to` names the QIU, one sub-row each, sorted by handling, then external before internal, then id; chips are colored by handling; 「内部」 marks internal QRs |
| NFR / SLI | NFRs whose `from` names the QR, with their kind, and the SLI of each SLO; 「範囲外」 when the stage 4 allocation table has an out-of-scope note for the QR |

A CUJ with no QIU gets one row of dashes. QRs with an `entry_point` (laws, standards, security risk analysis, policies) have no CUJ, so they form a last group, 「利用者を経由しない要求」, where the QIU column shows the entry type and the first sentence of its source and the FR column shows `applies_to`.

## Stage 1 tables

| Toggle | Columns (source) |
|---|---|
| 事業の要求 | KGI table: ID, KGI (`name`), 測定量 (`measure`), 目標値 (`target`). Outcome table: ID, 中間成果 (`statement`), 動詞 (`verb`), KGI (`kgis`). |
| 利用者 | ID, 利用者, 区分 (`category`), データの役割 (`data_role`), 考慮 (`considered`), 考慮しない理由 (`exclusion_reason`), 根拠 (`basis` + `basis_note`) |
| CUJ | ID, CUJ, 利用者 (`users`), 利用者の目的 (`user_goal`), 手順 (`steps`, numbered), 中間成果 (`outcomes`), 根拠 |
| 利用時の品質要求 | ID, 利用者, CUJ, 利用状況 (`context_of_use` values joined), 特性, 要求 (title in bold, then `statement`) |
| 失敗のシナリオと測定量 | ID with title, 失敗のシナリオ, 分子 ÷ 分母 (`measure.numerator` over `measure.denominator`), 絞り込み (`measure.narrowed_to`), 見えるか (`measure.observable`) |
| 対象にしない | report-only (see below) |
| 一つの式、二つの数え方 | One row per live KPI (outcome, formula, the narrowed QIUs with their `narrowed_to`, the KPI); one row per QIU that has outcomes but no KPI; one row gathering the QIUs with neither. |

Left out on purpose: the basis of every table except users and CUJs, and the overlap column.

## Stage 2 tables

| Toggle | Columns (source) |
|---|---|
| 機能要件 | ID, 機能 (title in bold, then `statement`), 受け入れ基準 (`acceptance_criteria`, bulleted), 出どころ (`origin`, with the FRP for proposals), たどれる先 (`traces_to`) |
| 検討して加えなかった機能 | report-only |

Left out on purpose: 既存 (`existing`) and the basis.

## Stage 3 tables and figures

- 「QR の影響 × 起こりやすさ」: a 5 × 5 grid of every QR with a `score`, colored by impact × likelihood, chips colored by handling.
- 製品の品質: a matrix of the 31 product sub-characteristics (glossary order) by CUJ. A cell lists the external QRs with that characteristic that trace to a QIU of that CUJ. Internal QRs are left out, as in the stage 3 coverage checklist; they appear in 「外部品質から導いた内部品質」. CUJ names are written vertically in the column heads.
- データの品質: the same matrix for the 15 data characteristics, with 「データの種類」 above it (report-only) and 「データを作る人」 below it (from the report line 「データを作る人:」, or else from users whose `data_role` is producer or both and `system.data_producers`).
- 優先度の表: QR (id and title), 特性, 失敗のシナリオ, 影響, 起こりやすさ, 点 (impact × likelihood), 扱い (handling badge and the first sentence of `handling_reason`), CUJ (derived through `traces_to`). Sortable by QR and by 点.
- CUJ ごとの扱い: per CUJ, the external QRs tracing to it, split into 重視 / 最低限守る線 / 今期は対象外, and the count of emphasized ones.
- 外部品質から導いた内部品質: one row per internal QR, with the external QRs whose `implies_internal` names it and 「どう支えるか」 from the report. Without the report table, the third column is the internal QR's `statement`, headed 「内部の QR の要求」.
- 品質要求: ID, モデル / 層, 特性, 要求 (title in bold, then `statement`), 対象の機能 (`applies_to`), たどれる先 (`traces_to`, or 「入口: <type>」).
- 利用者を経由しない要求: QR, 種類 (`entry_point.type`), 出どころ (`entry_point.source`), 扱い, 要求.

Left out on purpose: the 「—」 reasons of the coverage checklist, the basis, and `entry_point.brought_by` (持ち込んだ人).

## Stage 4 tables and cards

- SLO cards: target, its status (仮 / 合意済み), the SLI title, and NFR · CUJ · window. Each card links to its SLO row.
- SLO: NFR, CUJ, SLI, 目標値（状態）, ウィンドウ (「28-day rolling」 becomes 「直近 28 日」), エラーバジェット, 許容される失敗の件数 (`error_budget_volume`), 方針 (`policy`).
- SLI: SLI, 良いイベント ÷ 有効なイベント (the element definitions chosen by `function`, such as `OK ÷ VALID`), 測定方法 (`method`).
- エラーバジェット方針: one table per EBP (`rules`: when / action), captioned with its target NFRs when there is more than one.
- バーンレートのアラート: the `alerts` of each SLO; 使い切るまで = window days ÷ burn rate.
- 締め切りの SLO: SLOs with `bad_run_budget_share`, `progress_alert` or `after_miss`.
- そのほかの非機能要件: NFR, 種類, 出どころ（扱い）, 要件 (`statement`), 確かめる場所 (gate: where and check; audit: mechanism and cadence; monitor: signal and who is notified).

Left out on purpose: measurement points, blind spots, and the rationale for the numbers.

## Report-only tables

These exist only in the Markdown reports. The script looks for the heading (any level) by the glossary's Japanese term or the template's English heading, takes the first table under it, and reads its columns by position, so renamed columns do not matter but reordered ones do.

| Content | Report | Headings looked for | Columns used |
|---|---|---|---|
| 対象にしない | 1 | 対象にしない, Not targeted | CUJ, characteristic, reason |
| 検討して加えなかった機能 | 2 | 検討して加えなかった機能, Functions considered and not added | candidate, for, reason |
| 利用時の品質要求の対応 (checked, not shown) | 2 | 利用時の品質要求の対応, Quality-in-use coverage | QIU, the column named FR |
| 外部品質から導いた内部品質 | 3 | 外部品質から導いた内部品質, Internal quality derived from external quality | external, internal, how |
| データの種類 / データを作る人 | 3 | lines starting 「主なデータ:」 or 「データの種類:」, and 「データを作る人:」 | split on 「、」 |
| 割り当て (out-of-scope notes, checked) | 4 | 割り当て, Allocation | QR, the NFR column, the out-of-scope column |

A missing table is left out of the page, listed in 「この版の注記」, and printed in the report.

## Interactions

- Every ID in a table links to the row that defines it. Clicking opens the toggles around the target, scrolls to it, flashes the row, and pushes the hash so the back button returns. IDs without a row on the page (retired items, FRPs) are plain text with a tooltip.
- Hovering or focusing an ID shows a tooltip with its title; for QRs also the handling and 「内部品質」, for NFRs the kind.
- 「すべて開く」 / 「すべて閉じる」 toggle every table.
- Sorting in the priority table: the first click sorts QR ascending or 点 descending, the second reverses, the third restores the original order.

## Design

Light mode only, by the user's choice. Colors are tokens on `:root` in `assets/summary.css`: a cool paper background, white surfaces, one blue route color for links, emphasized chips and the route line, and amber for risk. Chips encode handling: filled blue (重視), pale blue (最低限守る線), dashed outline (今期は対象外). Fonts come from Google Fonts with system fallbacks: Zen Kaku Gothic New for headings, BIZ UDPGothic for text, IBM Plex Mono for IDs and counts. Wide tables scroll inside their box; the page itself never scrolls sideways, down to phone width, where the route diagram turns vertical.

## Checks the script runs

- References between items: every ID a field names must exist and must not be retired (`kgis`, `users`, `outcomes`, `cuj`, `kpi`, `overlaps_with`, `traces_to`, `proposal`, `extends`, `applies_to`, `implies_internal`, `conflicts.with`, `from`, `slo.sli`, `slo.policy`, `refs`, `applies_to` of EBPs), and `cuj_step` must be one of the CUJ's steps.
- Enum values: `handling` and `kind` must be known values; other unknown values are listed under 用語集にない値.
- Both sides of the KPI overlap: a QIU's `kpi` must list the QIU in that KPI's `overlaps_with`.
- Report against YAML: the stage 2 coverage table's FRs per QIU, the stage 3 internal-quality pairs, and the stage 4 allocation's NFRs per QR.
- IDs that appear in reports but not in the YAML are listed as notes (often removed CUJs that a report still mentions).
- The page itself: no duplicate ids, and every `href="#…"` has a target.

## Changing the page

The page is generated, so change the generator, never the output:

- Table columns and order: the `stage1` … `stage4` methods; the traceability table: `trace`; figures: `route`, `risk_chart`, `matrix`, `slo_cards`.
- Look: `assets/summary.css` (tokens at the top) and `assets/summary.js` (links, tooltips, sorting).
- Terms: `assets/terms.ja.json` maps the YAML's English values to the glossary's Japanese terms. The repository's `scripts/check-chain.py` compares it, and the YAML keys the script reads, with the cuj-to-slo glossary and artifacts.md.
- Requirements text at the bottom of the page: `PURPOSE`, `REQS` and `RULES` in the script; keep them in step with this file.

Keep the output deterministic: no current time, sorted sets, no randomness. The same inputs must give the same bytes, which the tests check.
