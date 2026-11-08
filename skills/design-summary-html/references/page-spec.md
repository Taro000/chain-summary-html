# Page specification

What `scripts/build_design_summary.py` puts on `docs/design/summary.html`, where each part comes from, and how to change it. Labels are quoted in Japanese and English as the two pages show them (`assets/lang/ja.json`, `assets/lang/en.json`).

## Contents
- Sources
- Gist
- Language
- Page structure
- Stage 1, Stage 2, Stage 3
- Comparing the reports with the items
- Revision notes
- Links and tooltips
- Diagrams
- Latency budget charts
- Theme
- Checks
- Evals
- Changing the page

## Sources

The YAML items are the source of truth (req-to-design's `artifacts.md`), as in quality-summary-html: every table that has items is built from them. The reports are read for the Mermaid diagrams, for the stage titles (H1 before the colon), and for the tables that no item holds. The reports' prose is never shown: a section with neither a table nor a diagram is left out and listed in the report. Nothing on the page is written by hand; there is no file of condensed texts (a `summary-text.yaml` from an earlier version of this skill is reported as no longer used). Enum values become the req-to-design glossary's terms in the page's language (`terms` in the language files). Every text is shown as its gist (next section).

## Gist

The page is for grasping the design's direction quickly; the YAML items and the reports hold the whole text. So every text on the page is cut to its gist by one rule, with no hand-written text (`gist`, `drop_asides` and `first_sentence` in the script):

1. Bracketed asides go: every （…）, and every (…) that does not follow a Latin letter or digit (`f(x)` and `watchPosition()` stay). A bracket that holds only a quantity stays, because the number is the point: 「T_deliver（5 秒）以内」, "a signed URL (15 min)". Code in backticks is left alone. A Latin word that the removal leaves against the next word gets its space back (「DRV-05（…）と」 → 「DRV-05 と」).
2. Only the first sentence stays: up to the first 「。」, or a full stop followed by a space or the end (not after e.g., i.e., etc., vs., cf.), outside brackets, quotes and code. A question or exclamation mark stays; the full stop goes.
3. A text that is all aside (「（未定）」) keeps its first sentence as written.

The rule applies to every YAML text, every report table cell and header, the section titles that become item titles (views, flows, screens, states, the walkthroughs' CUJ labels, the data quality flows' captions) and diagram labels (see Diagrams). Shown whole: IDs, enum terms, numbers, and titles and names, which are short already (items' titles, element, interface and design parameter names, data entities).

What only justifies or traces a text is left out: the ranking table's reasons for the levels, the sources of design inputs, constraints, principles and the other drivers, and the basis of a design parameter's value. So is what another table on the page shows: a decision card's design parameters (in 設計上の値 / Design parameters), why its debt was accepted and when it is repaid (in the debt table), and the decisions table's addresses (in each card). A scenario shows its stimulus, environment and response measure: the source and the artifact are mostly implied by the stimulus, and the response is the measure in words.

The gist is only as good as the first sentence. A text that starts with a label (「規模。デモは…」) shows only the label; the fix belongs to the stage that wrote it (lead with the point), not to this page.

## Language

The page and the report follow the language of the outputs: Japanese when kana make up a tenth or more of the letters (kana and Latin) in the YAML free text and the reports, English otherwise. `--lang ja|en` sets the page's labels; the content stays as written. Report sections are found by their Japanese heading (the glossary's term) or English heading (the report template's), so a Japanese report and an English one are read the same way (`H` at the top of the script). Revision notes are removed by the rules of the outputs' language, not the page's. English pages use IBM Plex Sans; Japanese pages use BIZ UDPGothic and Zen Kaku Gothic New.

## Page structure

1. Header: repository · docs path, the title 「<system name>の設計」 / "<system name> design" (system name from docs/quality/context.yaml without its trailing bracket, else the report's H1), stages covered (「第 1〜3 段階の成果物の要点」 / "Gist of the stage 1–3 outputs"), latest update date (newest `changelog` date of the items, or a 「再実行（日付」 / "Re-run on <date>" heading), git commit of docs/design with 「（未コミットの変更あり）」 / "(uncommitted changes)" when the folder differs from it (summary.html itself is ignored). 「すべて開く」「すべて閉じる」 / "Open all" "Close all" open or close every toggle, nested ones included.
2. Table of contents on the left (a strip under 1100 px).
3. 「成果物のつながり」 / "How the outputs connect": a route of up to seven stops with counts from the items: drivers (primary and kinds), stage-2 decisions (debt and deferred), elements (kinds), stage-3 decisions (shared conventions from the report, and the others), interfaces (kinds), end-to-end flows (diagrams in the report: CUJ and driver flows), data entities (owners). A stop whose toggle is not on the page is left out.
4. One section per stage, titled with the report's H1 before the colon (or the language file's stage title), with its sources beside the title. Every table is in a closed `details.tbl` toggle with a count, except the ranking table, which is open.
5. 「この版の注記」 / "Notes on this version", only when there are mismatches, missing reports, items or later stages, or missing sections or tables.

A stage is on the page when its items (stage 1: `drv/`; stage 2: `elm/` or architecture decisions; stage 3: `ifc/`, `dat/` or high-level-design decisions) or its report exist.

## Stage 1

| Toggle | Source | Notes |
|---|---|---|
| 順位表 / Ranking table (first, open) | YAML `drv/`: `priority.rank`, `business`, `difficulty`, `primary` | principles and retired drivers are not ranked; a driver without a rank goes last and is reported; priority and difficulty as badges, 高 / High outlined in the accent and the other levels in ink; primary as a filled chip; the reasons for the levels are left out |
| 設計の前提と利害関係者 / Design inputs and stakeholders | YAML `design-context.yaml`: `technology_constraints`, `project_constraints`, `teams`, `anticipated_changes`, `stakeholders` | kind from `kind`; a team as 「name: owns」, a stakeholder as 「role: concerns」; the basis column is kept (these are the inputs), the source is left out |
| 関心事の一覧 / Concern inventory | report table | the column of what each became (なったもの / Became) dropped |
| 品質と変更のシナリオ / Quality and change scenarios | YAML kinds quality and change: `scenario.stimulus`, `environment`, `measure` | the kind as a tag beside the ID |
| 制約 / Constraints | YAML kind constraint: `statement`, `negotiable` | |
| 機能・観測・セキュリティの要求 / Functional, observability and security drivers | YAML kinds function, observability, security: `kind`, `statement`; the scenarios of those that have one | both tables in one toggle |
| 全体の原則 / Principles | YAML kind principle: `statement`, `derived_from` | |
| 競合 / Conflicts | YAML `conflicts` | one row per pair of drivers; both drivers record the conflict, and the side with more notes is shown |
| 実現できるか / Feasibility | report table | |

## Stage 2

| Toggle | Source | Notes |
|---|---|---|
| 要素 / Elements (first) | YAML `elm/`: `kind`, `name`, `responsibility`, `functions`, `drivers`, `team`, `as_is` | ID lists as ranges (「FR-01〜14、24」 / "FR-01–14, 24") |
| ビュー / Views (second) | report, each subsection of the views section | one nested item per view: its diagram and the tables beside it |
| 設計の決定 / Decisions | YAML `dec/` of stage architecture: `question`, `chosen` (「先送り」 / "Deferred" for a deferred decision without one), `rejected` (option and reason) | each DEC links to its card, which has what it addresses |
| 決定の中身 / Decision details | YAML `dec/` | one card per DEC: the question; the options (`options`: name, effect, cost) with the chosen one marked (a filled mark, its name in bold) and each rejected one's reason; then the rationale, gains, costs, sensitive points, trade-offs, assumptions, technical debt (what it is), deferral, addresses and dependencies. Findings in `addresses` are left out (review history). The design parameters and why the debt was accepted and when it is repaid are in the stage's tables, not in the card. The reports' option-comparison tables inside each decision section are not used |
| 設計の観点 / Design concerns | report table | as a definition list |
| 脅威のモデル / Threat model | report: the first Mermaid diagram and the table | the flow numbers on the diagram's arrows (F1…) link to the table's rows, which get the ids `flow-F1`…; pointing at one highlights the arrows that carry it |
| 通し確認（CUJ） / Walkthroughs (CUJs) | report: one table per CUJ, under a bold label or its own heading | all merged into one table with a header row per CUJ; a CUJ written as prose is left out and listed |
| 通し確認（設計を動かす要求） / Walkthroughs (primary drivers) | report tables | both tables, if there are two |
| 設計上の値 / Design parameters | YAML `parameters` of the stage's decisions | parameter, value, decision; the basis of the value is left out |
| 技術的負債と先送りした決定 / Debt and deferred decisions | YAML `debt` (what, why_accepted, repay_when) and `deferred` (question, rationale, revisit_when) | the schema has no field for an accepted risk; one written only in the report is reported as a mismatch |
| 走る費用 / Running cost | report: the running-cost subsection of cost and team, or its first table | |

## Stage 3

| Toggle | Source | Notes |
|---|---|---|
| 共通の約束事 / Shared conventions | report table | |
| 設計の決定 / Decisions | YAML `dec/` of stage high-level-design | as in stage 2, without cards; detailed-design decisions are not on the page |
| インタフェース / Interfaces | YAML `ifc/`: `kind`, `name`, `provider`, `consumers`, `operations`, `functions`, `spec` | operations: up to three names (every message of an event interface), else 「N 件（最初 ほか）」 / "N (first and others)"; spec: the file name |
| エラーの決まり / Error contracts | YAML `errors` (`case`, `signal`, `caller_does`) | a case written 「操作: 場合」 / "Operation: case" gives the operation; rows for all operations (「共通」 / "Common") that are the same in several interfaces are shown once at the top (「IFC-01〜07」); IFC and operation merged into row groups |
| 端から端の流れ / End-to-end flows | report: each subsection with a diagram | one nested item per diagram, with an index |
| 遅延の予算 / Latency budgets | report: each NFR subsection | titled with the NFR's title from docs/quality (the heading's bracket only restates it); a hop table becomes a chart (see below); another table is shown as it is; a subsection without a table is left out and listed |
| 失敗したときの流れとエラーバジェット / Failure paths and error budgets | report table | |
| 画面 / Screens | report: each subsection with a diagram | one item per diagram |
| データ / Data | report: the ER diagram; YAML `dat/`: `entity`, `owner`, `store`, `consistency`, `retention`, `classification` | entity names added to the ER boxes; a classification with a note after it (「personal（IP アドレス）」) keeps the note |
| データの品質の流れ / Data quality flows | report: the diagrams (a short paragraph ending in a colon before one is its caption) and the table | |
| 要素をまたぐ状態 / States across elements | report: each subsection with a diagram | one item per diagram |
| 測定点 / Measurement points | report tables | duplicate rows in the second table (same NFR) merged, keeping the fuller one |
| 受け入れ基準のトレース / Acceptance criteria trace | report table | columns reordered to FR, IFC, criterion, flow and grouped by FR; revision notes are not removed (the criteria are quotations), but the criteria are cut to their gist |
| 設計上の値 / Design parameters | YAML `parameters` of the stage's decisions | |
| 技術的負債と先送りした決定 / Debt and deferred decisions | YAML, as in stage 2 | only when a stage-3 decision has debt or is deferred |

## Comparing the reports with the items

These report tables restate items, so their first column (or the named ID column) is compared with the items' IDs: ranking table (also the order), design inputs and stakeholders, quality and change scenarios, constraints, functional/observability/security drivers, principles, elements, decisions (both stages), debt and deferred decisions, interfaces, data. Retired rows (「（廃止）」 / "(retired)") are skipped. A difference is reported as a mismatch and listed in the notes on the page; a table that was not found is reported as not compared. Cell contents are not compared. A hop table whose hops and margin do not add up to its total is also reported as a mismatch.

## Revision notes

YAML texts, report table cells and diagram labels lose revision notes; their meaning does not change. The rules follow the language the outputs are written in.

Japanese:

- A sentence (split at 「。」 outside brackets) is dropped when it contains 前回, 前々回, 「N 回目の再実行」, 再実行, 「課題 N は決着」, 「版 N」 not attached to an ID, an FND number used in a sentence, or 「前の版」 meaning a document revision (followed by は, （, 。, ）, では, が挙, の欠け, の誤り, の負債, or the end). 「前の版に戻す」「前の版の動き」「一つ前の版」「本番は前の版のまま」「戻せる前の版がない」 mean product versions and are kept.
- Inside brackets the same rule applies per sentence; a bracket left with only process references (課題, 質問, 回答の設計) after a removal goes too, and an empty bracket disappears.
- 「XX-NN 版 N」 becomes 「XX-NN」. An FND number that is one item of a list (「質問 11・14、FND-27」「（FND-02）」) is removed alone.

English (the same kinds of note; wordings that can also describe the product are kept, such as a job that is re-run or an image rolled back to the previous version):

- A sentence (split at a full stop followed by a space, outside brackets, not after e.g., i.e., etc., vs., cf.) is dropped when it contains an FND number, an ordinal re-run ("the second re-run"), "re-run on <date>", "re-run of (this) stage", "in/since/after/before the re-run", "the previous version/revision/draft" followed by a verb that reports the document (said, showed, had, was, listed, assumed, missed…) or "of this report/item/decision…", "the previous run", a sentence starting with "Previously", "issue N is settled", or "version N" followed by such a verb.
- Inside brackets the same rule applies; a bracket left with only process references (issues, questions, answer designs) after a removal goes too, and an empty bracket disappears.
- "XX-NN version N" becomes "XX-NN". An FND number that is one item of a list ("question 11, FND-27", "(FND-02)") is removed alone.

Both: diagrams lose only bracketed notes, and lines are never dropped. Findings are also left out of a decision's `addresses`.

## Links and tooltips

Design IDs (DRV, DEC, ELM, IFC, DAT, TC, PC, TEAM, CHG, STK) link to their rows; quality IDs (FR, QR, NFR, SLI, CUJ, QIU, USR…) link to `docs/quality/summary.html` when that page has the anchor (dotted underline). 「DRV-01、02」 and "DRV-01, 02" link 02 to DRV-02, 「FR-01〜14」 and "FR-01–14" link both ends; numbers followed by units are not IDs. IDs without a row (FND, FRP, retired items, detailed-design decisions) are plain text. Tooltip texts are stored once in a JSON block (`#id-tips`) and attached on hover by design.js; the messages design.js shows are in another JSON block (`#ui-text`, the `js_` keys of the language files).

## Diagrams

- Mermaid 11.17.2 from jsDelivr, imported only when the first diagram scrolls into view; each diagram renders when it becomes visible. Diagrams are drawn in the page's neutrals and fonts, taken from the CSS tokens: white boxes outlined in `--ink-3`, groups and notes in `--paper`, lines in `--ink-3`. The accent appears in a diagram only as a link (the threat model's flow numbers) and the arrows it highlights. Sequence diagrams measure and draw text with the same font so labels do not overlap arrows.
- Labels are cut to their gist (see Gist), and only labels, never syntax (`gist_mermaid`): in a sequence diagram the text of messages, notes, blocks (alt, else, opt, loop…) and participants; elsewhere the quoted labels, a flowchart's edge labels, a state or ER diagram's label after the colon, and any （…）, which Mermaid never uses. Lines whose parentheses and colons are syntax (style, classDef, class, linkStyle, click, direction, rect, box, and %% comments and directives) are left alone. The threat model's flow numbers stay, since the reports write them first in the label.
- Sequence diagram text is pre-wrapped at punctuation and spaces (messages 24 full-width characters, notes 30, block labels 40), because Mermaid only breaks at spaces and hyphenates long words. Participant aliases break after the ELM/USR id.
- Flowchart boxes whose label is only an ELM id (also once its aside is gone: 「ELM-06（…）」) get the element's name.
- Direction: a flowchart or ER diagram wider than the column is also drawn the other way (LR ↔ TB, the ER diagram's `direction`), and the drawing that shows larger when fitted to the column is kept, if it is at least 15% larger; very tall drawings count as smaller. The diagram's content does not change.
- 「幅に合わせる」 / "Fit to width" scales a diagram to the column; it is on by default only when the scale stays at 0.75 or more. 「全画面」 / "Full screen" shows the diagram at natural size in an overlay (Esc closes).

## Latency budget charts

A hop table (first column 区間 / Hop, second column starting 予算 / Budget, values in 秒, s, ms, 分 or min, rows 余り / Margin and 合計 / Total) becomes a horizontal stacked bar: one segment per hop in the accent (`--route`), a light track up to the threshold (the margin, `--rule-soft`), and a line at the threshold (the total, or the hops plus the margin). Values of ten minutes or more are shown in minutes. Labels inside segments are hidden when they do not fit; every value is in the tooltip and in the 「数値の表」 / "Values" toggle under each chart. The kinds of hop (own processing, external services, waits) are not in the table, so the chart does not color them.

## Theme

The layout is quality-summary-html's, and so is the amount of color; only the hue differs. One accent, the orange of this skill's icon, goes where quality-summary-html uses its blue, and everything else is neutral. The accent marks:

- links and IDs, the numbers in the table of contents and the stage numbers, hover and focus;
- the route at the top;
- one state per table, filled: a primary driver in the ranking table, the chosen option in a decision card (as quality-summary-html fills only the emphasized QRs);
- the highest level, outlined: 高 / High priority and difficulty in the ranking table, so that a long ranking can be scanned for it (as quality-summary-html outlines only the NFRs that are SLOs);
- the one data series of a chart: the hops of a latency budget.

Everything else is neutral: the other levels (中 and 低 / Medium and Low, told apart by the darkness of the ink), rejected options (a dashed mark), the indexes inside toggles (links in neutral boxes), and the diagrams (see Diagrams). Nothing is colored for decoration, and there is no second hue; the flash on a jump (`--pickup`) is the only other color, as in quality-summary-html.

`assets/design.css` redefines base.css's tokens at the top: warm neutrals (`--paper`, `--head`, `--ink`…), `--route` #c9461a (the icon's #e2531b darkened so that white text on chips and bars keeps 4.8:1), `--route-ink` #a8320e for links and IDs (5.9:1 on `--route-soft`), `--route-soft` and `--route-line` as tints, and `--pickup` from the icon's yellow. design.css and design.js define no token of their own and write no color outside the tokens; `tests/test_build_design_summary.py` checks this. Change colors there, never in base.css. A new part of the page is neutral unless the list above names it: do not give a kind of element a color of its own.

## Checks

The script reports mismatches between the reports and the items, report tables it could not compare, missing reports, items and later stages, unreadable items, enum values without a term, sections left out for having neither a table nor a diagram, files no longer used, missing sections and tables, and the number of cleaned texts. The page itself is checked for duplicate ids and links without targets (links to IDs that have no row are turned into plain text first). The output is deterministic: no clock, sorted keys.

## Evals

`evals/` holds four cases in the skill-creator format (`case.yaml`, `prompt.md`, `place-files.sh`, `graders/`):

| Case | Input | What it tests |
|---|---|---|
| homework-service-full | the fictional homework submission service, stages 1 to 3, Japanese | YAML over the report (DEC-06 is missing from the stage 2 report's decisions table), revision notes, texts cut to their gist (DEC-02's rationale, ELM-01's responsibility, DAT-02's consistency have a second sentence), a prose-only walkthrough and budget, shared error contracts, a hop-table chart, threat links |
| homework-service-full-en | the same in English | the same, and an English page with no Japanese |
| homework-service-stage2 | the same up to stage 2, Japanese | a missing later stage |
| ride-hailing-full | a copy of ride-hailing-app-demo's docs/design and docs/quality (commit b63c7a1; without summary.html, summary-text.yaml, reviews/ and the OpenAPI specs) | a real project: 37 decisions, 326 error contracts, 50 diagrams, an accepted risk only in the report (DEC-21, DEC-30), and texts written in long paragraphs |

`tests/make_homework_design_fixture.py` writes the three fictional cases (on top of quality-summary-html's homework-service outputs). `tests/grade_design_eval.py` grades runs of the skill-creator workflow against the grader statements, one deterministic check per statement; the gist statement (`gist-only`) fails a page that shows any sentence after the first of a YAML text, unless that sentence is also part of a title or of another text's gist. `tests/test_build_design_summary.py` builds every case with the script, grades the result, and checks that the grader fails pages that miss what a statement asks for.

## Changing the page

- Table set and columns: the `stage1` … `stage3` methods; decisions: `dec_table`, `dec_card`, `values_toggle`, `debt_rows`; error contracts: `error_rows`; comparisons: `compare`; route: `route`; budget charts: `hop_chart`, `budget_chart`; report headings: `H`.
- How much of a text is shown: `gist` (with `drop_asides`, `first_sentence` and the quantities kept, `QTY_RE`), `Builder.g` for YAML texts, `Table` for report cells, `gist_mermaid` for diagrams. A YAML text shown whole uses `Builder.t` instead; keep that for titles and names.
- Wording and terms: `assets/lang/ja.json` and `en.json` (same keys and placeholders; the tests check this).
- Look: `assets/design.css` (tokens at the top; color only as in Theme). `assets/base.css` and `assets/base.js` are copies of `skills/quality-summary-html/assets/summary.css` and `summary.js` in this repository, so that each skill installs on its own. When those change, copy them here unchanged and check the page; the theme survives because design.css comes after base.css.
- Behavior: `assets/design.js` (tooltips, nested toggles, Mermaid and its direction, threat-diagram links, full screen, chart labels).
- After a change, rerun `tests/make_homework_design_fixture.py` if the fixture changed, and the tests.
