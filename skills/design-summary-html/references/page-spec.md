# Page specification

What `scripts/build_design_summary.py` puts on `docs/design/summary.html`, where each part comes from, and how to change it. The page is Japanese; labels are quoted as the page shows them. The requirements that shaped the page can be kept in summary-text.yaml (`requirements`, `answers`); they are shown in the closed toggle 「このページの要件」 at the bottom of the page. A complete summary-text.yaml for a real project is `docs/design/summary-text.yaml` in ride-hailing-app-demo (its `decisions` block predates the YAML-built decision cards and is no longer used).

## Contents
- Sources
- Page structure
- Stage 1, Stage 2, Stage 3
- Comparing the reports with the items
- Stand-ins before the condensed texts exist
- Revision history in texts
- Links and tooltips
- Diagrams
- Latency budget charts
- Theme
- summary-text.yaml
- Checks
- Changing the page

## Sources

The YAML items are the source of truth (req-to-design's `artifacts.md`), as in quality-summary-html: every table that has items is built from them. The reports are read for the Mermaid diagrams, for the stage titles (H1 before the colon), and for the sections that no item holds. Enum values become the req-to-design glossary's Japanese terms (`T_…` tables in the script). In the tables below, "YAML" names the fields and "report" names the section.

## Page structure

1. Header: repository · docs path, title 「<system name>の設計」 (system name from docs/quality/context.yaml, else the report's H1), stages covered, latest update date (newest `changelog` date of the items or 「再実行（日付」 heading), git commit of docs/design with 「未コミットの変更あり」 when the folder differs from it (summary.html itself is ignored). A band of the icon's five colors runs under the header. 「すべて開く」「すべて閉じる」 open or close every toggle, nested ones included.
2. Table of contents on the left (a strip under 1100 px).
3. 「成果物のつながり」: a route of seven stops with counts from the items: drivers (primary and kinds), stage-2 decisions (debts and deferrals), elements (kinds), stage-3 decisions (shared conventions from the report, and the others), interfaces (kinds), end-to-end flows (diagrams in the report: CUJ and driver flows), data entities (owners). A stop whose toggle is not on the page is left out.
4. One section per stage, titled with the report's H1 before the colon (or 設計を動かす要求 / アーキテクチャ / 概要設計), with its sources beside the title. Every table is in a closed `details.tbl` toggle with a count, except the ranking table, which is open.
5. 「この版の注記」 only when there are mismatches, missing reports or items, missing sections, or stale or missing condensed texts.
6. 「このページの要件」: the user's requirements and the answers to the clarifying questions.

A stage is on the page when its items (stage 1: `drv/`; stage 2: `elm/` or architecture decisions; stage 3: `ifc/`, `dat/` or high-level-design decisions) or its report exist.

## Stage 1

| Toggle | Source | Notes |
|---|---|---|
| 順位表 (first, open) | YAML `drv/`: `priority.rank`, `business`, `business_reason`, `difficulty`, `difficulty_reason`, `primary` | principles and retired drivers are not ranked; a driver without a rank goes last and is reported; priority and difficulty as badges, 主 as a chip |
| 設計の前提と利害関係者 | YAML `design-context.yaml`: `technology_constraints`, `project_constraints`, `teams`, `anticipated_changes`, `stakeholders` | 種類 from `kind`; 根拠 is the basis (入力 / 推定 / 確認済み) |
| 関心事の一覧 | report 関心事の一覧 | なったもの dropped |
| 品質と変更のシナリオ | YAML `drv/` of kind quality and change: `scenario` | the kind as a tag beside the ID |
| 制約 | YAML kind constraint: `statement`, `negotiable`, `sources` | |
| 機能・観測・セキュリティの要求 | YAML kinds function, observability, security: `kind`, `statement`, `sources`; the scenarios of those that have one | both tables in one toggle |
| 全体の原則 | YAML kind principle: `statement`, `derived_from` (`sources` in brackets) | |
| 競合 | YAML `conflicts` | one row per pair of drivers; both drivers record the conflict, and the side with more notes is shown |
| 実現できるか | report 実現できるか | |

## Stage 2

| Toggle | Source | Notes |
|---|---|---|
| 要素 (first) | YAML `elm/`: `kind`, `name`, `responsibility`, `functions`, `drivers`, `team`, `as_is` | ID lists as ranges (「FR-01〜14、24」) |
| ビュー (second) | report ビュー > each H3 | one nested item per view: the diagram and the view's tables; for コードの分け方, the dependency rules as a table (`code_rules`) |
| 全体の構造 | report 全体の構造 | condensed bullets (`structure`) |
| 設計の決定 | YAML `dec/` of stage architecture: `question`, `chosen`, `addresses`, `rejected` (option and reason) | each DEC links to its card |
| 決定の中身 | YAML `dec/` | one card per DEC: 問い; the options (`options`: name, effect, cost) with the chosen one highlighted and each rejected one's reason; then 選んだ理由 (`rationale`), 得るもの, 失うもの, 応答を左右する点, 引き換え, 前提, 設計上の値, 技術的負債, 先送り, 対象, 依存する決定. The reports' option-comparison tables inside each DEC section are not used |
| 設計の観点 | report 設計の観点 | condensed text per viewpoint (`viewpoints`), as a definition list |
| 脅威のモデル | report 脅威のモデル | assets and the six threats as bullets (`threat`), a hand-laid SVG of trust boundaries and flows (`threat.diagram`; chips link to the table rows), the table |
| 通し確認（CUJ） | report 通し確認 > CUJ | all CUJ tables merged into one table with a header row per CUJ; CUJs written as prose come from `walk_extra` |
| 通し確認（設計を動かす要求） | report 通し確認 > 主な設計を動かす要求 | both tables |
| 設計上の値 | YAML `parameters` of the stage's decisions | 値, 仮の値, もと (`basis`), 決定 |
| 技術的負債と先送りした決定 | YAML `debt` (what, why_accepted, repay_when) and `deferred` (question, rationale, revisit_when) | the schema has no field for an accepted risk; one written only in the report is reported as a mismatch |
| 走る費用 | report 費用と体制 > 走る費用 | |

## Stage 3

| Toggle | Source | Notes |
|---|---|---|
| 共通の約束事 | report 共通の約束事 | |
| 設計の決定 | YAML `dec/` of stage high-level-design | as in stage 2, without cards; detailed-design decisions are not on the page |
| インタフェース | YAML `ifc/`: `kind`, `name`, `provider`, `consumers`, `operations`, `functions`, `spec` | 操作 lists up to three operations (every message of an event interface), else 「N 件（最初 ほか）」; 仕様 is the file name |
| エラーの決まり | YAML `errors` (`case`, `signal`, `caller_does`) | a case written 「操作: 場合」 gives the 操作 column; rows for 「共通」 that are the same in several interfaces are shown once at the top (「IFC-01〜07」); IFC and 操作 merged into row groups |
| 端から端の流れ | report 端から端の流れ > each H3 with a diagram | one nested item per diagram, with an index |
| 遅延の予算 | report 遅延の予算 > NFR-xx and スクリプトの出力 | one item per NFR: a chart and condensed text (`budgets`) |
| 失敗したときの流れとエラーバジェット | report 遅延の予算 > 失敗したときの流れとエラーバジェット | |
| 画面 | report 画面 > each H3 | one item per diagram |
| データ | report データ (ER diagram); YAML `dat/`: `entity`, `owner`, `store`, `consistency`, `retention`, `classification` | entity names added to the ER boxes |
| データの品質の流れ | report データ > データの品質の流れ | the diagrams (captioned by the paragraph before each) and 「ほかのデータの品質」 |
| 要素をまたぐ状態 | report 要素をまたぐ状態 > each H3 | one item per diagram, plus a short note only where the diagram cannot be read alone (`states`) |
| 測定点と監視の NFR の出どころ | report 測定点 (both tables) | duplicate rows in the second table (same NFR) merged, keeping the fuller one |
| 受け入れ基準のトレース | report 受け入れ基準のトレース | columns reordered to FR, IFC, 基準, 流れ and grouped by FR; not cleaned (the criteria are quotations) |
| 設計上の値 | YAML `parameters` of the stage's decisions | |
| 技術的負債と先送りした決定 | YAML, as in stage 2 | only when a stage-3 decision has debt or is deferred |

Paragraphs around tables are left out on purpose (the requirements ask for no explanations around tables).

## Comparing the reports with the items

These report tables restate items, so their first column is compared with the items' IDs: 順位表 (also the order), 設計の前提と利害関係者, 品質と変更のシナリオ, 制約, 機能・観測・セキュリティの要求, 全体の原則, 要素, 設計の決定 (both stages), 技術的負債と先送りした決定, インタフェース, データ. Retired rows (「（廃止）」) are skipped. A difference is reported under 「食い違い」 and listed in 「この版の注記」; a table that was not found is reported under 「突き合わせなかった表」. Cell contents are not compared.

## Stand-ins before the condensed texts exist

On a first run there is no summary-text.yaml, every condensed section is reported under 「添削文がない」, and the page still builds:

- 全体の構造 and 設計の観点 show 「（添削文なし）」;
- the threat model shows the report's own Mermaid diagram instead of the hand-laid figure, and the table;
- each latency budget without an entry shows the tables of its subsection;
- state diagrams have no notes, and prose-only CUJs have no rows in the walkthrough table.

Every table built from the items is complete on the first run.

## Revision history in texts

YAML texts, report table cells and diagram labels lose revision notes; their meaning does not change.

- A sentence (split at 「。」 outside brackets) is dropped when it contains 前回, 前々回, 「N 回目の再実行」, 再実行, 「課題 N は決着」, 「版 N」 not attached to an ID, an FND number used in a sentence, or 「前の版」 meaning a document revision (followed by は, （, 。, ）, では, が挙, の欠け, の誤り, の負債, or the end). 「前の版に戻す」「前の版の動き」「一つ前の版」「本番は前の版のまま」「戻せる前の版がない」 mean product versions and are kept.
- Inside brackets the same rule applies per sentence; a bracket left with only process references (課題, 質問, 回答の設計) after a removal goes too, and an empty bracket disappears.
- 「XX-NN 版 N」 becomes 「XX-NN」. An FND number that is one item of a list (「質問 11・14、FND-27」「（FND-02）」) is removed alone.
- Diagrams: only bracketed notes are cleaned; lines are never dropped.
- What the rules cannot see in a report goes in `fixes` (exact text replacements in the report text before parsing). YAML texts have no fixes; their wording belongs to the stage.

## Links and tooltips

Design IDs (DRV, DEC, ELM, IFC, DAT, TC, PC, TEAM, CHG, STK) link to their rows; quality IDs (FR, QR, NFR, SLI, CUJ, QIU, USR…) link to `docs/quality/summary.html` when that page has the anchor (dotted underline). 「DRV-01、02」 links 02 to DRV-02; numbers followed by units are not IDs. IDs without a row (FND, FRP, retired items, detailed-design decisions) are plain text. Tooltip texts are stored once in a JSON block (`#id-tips`) and attached on hover by design.js.

## Diagrams

- Mermaid 11.17.2 from jsDelivr, imported only when the first diagram scrolls into view; each diagram renders when it becomes visible. Theme colors and fonts come from the page's CSS tokens (notes use `--note-bg` and `--note-line`); sequence diagrams measure and draw text with the same font so labels do not overlap arrows.
- Sequence diagram text is pre-wrapped at Japanese punctuation (messages 24 full-width characters, notes 30, block labels 40), because Mermaid only breaks at spaces and hyphenates long words. Participant aliases break after the ELM/USR id.
- Flowchart boxes whose label is only an ELM id get the element's name.
- `diagram_direction` in summary-text.yaml changes a diagram's direction (flowchart LR/TB, ER `direction`) where that makes it fit; the diagram's content is unchanged. Current choices were measured: 外部との関係 TB, 配置 LR, 情報 TB, ER LR, データの品質の流れ TB.
- 「幅に合わせる」 scales a diagram to the column; it is on by default only when the scale stays at 0.75 or more. 「全画面」 shows the diagram at natural size in an overlay (Esc closes).

## Latency budget charts

Horizontal stacked bars on one shared axis per NFR (`budgets[].chart`): segments colored by kind (自分の処理 #e2531b, the theme's color; 外部サービスと回線 #1d5fae; 待ち #1baf7a; validated with the dataviz palette validator, light mode, all pairs, on #ffffff, worst CVD ΔE 9.9), a light track up to the threshold (余り), threshold lines, optional worst-case markers, a rejected option dimmed, status colors for NFR-03. Labels inside segments are hidden when they do not fit; every value is in the tooltip and in the 「数値の表」 toggle under each chart. Axis `clock` turns minutes into times (NFR-06).

## Theme

The layout is quality-summary-html's; the colors are this skill's icon (#fccb52, #f9a330, #f37b20, #e2531b, #b8360f). `assets/design.css` redefines base.css's tokens at the top: warm neutrals (`--paper`, `--head`, `--ink`…), `--route` #c9461a (darkened from #e2531b so that white text on chips and badges keeps 4.8:1), `--route-ink` #a8320e for links and IDs (5.9:1 on `--route-soft`), `--route-soft` and `--route-line` as tints, `--pickup` (the flash on a jump) from the yellow, and `--brand-1`…`--brand-5` for the band under the header. Change colors there, never in base.css.

## summary-text.yaml

| Key | Content |
|---|---|
| `requirements`, `answers` | the page's requirements, shown at the bottom |
| `fixes` | `{file, find, replace}` exact replacements applied to a report before parsing |
| `structure.bullets` | 全体の構造 |
| `code_rules` | dependency rules table under コードの分け方 |
| `viewpoints.items` | [viewpoint, text] |
| `threat` | `assets`, `kinds`, `diagram` (`width`, `height`, `zones`, `nodes` with `kind` comp/store/ext/person, `flows` with `points`, `chips`, `at`, optional `arrow: false`) |
| `budgets[]` | `id`, `source` (heading prefix under 遅延の予算), `title`, `chart`, `text` |
| `states.<name>` | `note` for a state diagram (name = heading without its bracket) |
| `walk_extra.groups` | rows for CUJs that the report describes in prose (`after` = start of that CUJ's label) |
| `diagram_direction` | section path → direction |
| `hashes` | key → hash of the source section(s); written by `--write-hashes` |

Any other key is reported under 「使わないキー」. Text may use `` `code` `` and `**bold**`; IDs are linked automatically.

## Checks

The script reports mismatches between the reports and the items, report tables it could not compare, unreadable items, enum values without a term, unused keys, missing sections, tables and columns, unmatched `fixes`, unused `diagram_direction` keys, stale or missing condensed texts, and the number of cleaned texts. The page itself is checked for duplicate ids and links without targets (links to IDs that have no row are turned into plain text first). The output is deterministic: no clock, sorted keys. `tests/test_build_design_summary.py` builds a small made-up design and checks the sources, the comparisons and the build without reports.

## Changing the page

- Table set and columns: the `stage1` … `stage3` methods; decisions: `dec_table`, `dec_card`, `values_table`, `debt_rows`; error contracts: `error_rows`; comparisons: `compare`; route: `route`; charts: `budget_chart`; threat figure: `threat_svg`; terms: the `T_…` tables.
- Look: `assets/design.css` (tokens at the top). `assets/base.css` and `assets/base.js` are copies of `skills/quality-summary-html/assets/summary.css` and `summary.js` in this repository, so that each skill installs on its own. When those change, copy them here unchanged and check the page; the theme survives because design.css comes after base.css.
- Behavior: `assets/design.js` (tooltips, nested toggles, Mermaid, full screen, chart labels, threat-figure highlight).
