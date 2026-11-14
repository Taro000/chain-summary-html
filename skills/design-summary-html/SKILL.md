---
name: design-summary-html
description: Builds docs/design/summary.html, one light-mode page for grasping the direction of the design quickly from the outputs of the req-to-design 0.3.0 chain (requirements-to-architecture-drivers → architecture-drivers-to-architecture → architecture-to-technical-policy → architecture-to-high-level-design), in quality-summary-html's layout with its own orange theme. As in quality-summary-html, a bundled script renders the page from the YAML items (drivers, design context, elements, decisions with their options and consequences, technical policies, interfaces, error contracts, SLI bindings, data entities, design parameters, debt, open hand-offs), takes the Mermaid diagrams and the tables no item holds from the reports, leaves the reports' prose out, cuts every text, table cell and diagram label to its gist (the first sentence, without bracketed asides; the YAML and the reports keep the rest), and reports where a report disagrees with the YAML, so every project and every re-run gets the same page with no hand-written text. The page and the report are written in the language of the outputs (Japanese, or English for any other language). Use it whenever someone wants to summarize, visualize, share, review or present docs/design, asks for an HTML overview of the architecture or the high-level design, or wants summary.html rebuilt after a design stage was re-run, even if they never name this skill, including Japanese requests such as 「設計の成果物を HTML にまとめて」「docs/design の要約を作り直して」.
---

# Design summary HTML

Renders `docs/design/summary.html` from the design chain's outputs so that a person can grasp the direction of the design quickly: the ranked architecture drivers, the elements and views, every decision with its options and consequences, the threat model, the walkthroughs, the technical policy (the stack, repositories, test layers, pipeline and specs), the high-level design's interfaces, error contracts, SLI bindings, end-to-end flows, latency budgets, screens, data and states, and what each stage handed off and has not been decided yet. The page is not for the full picture: it shows the gist of every text, and whoever needs the whole of one reads the YAML item (the source of truth) or the report.

The page design and the set of tables are fixed, and `scripts/build_design_summary.py` does all of the rendering, from the outputs alone: nothing on the page is written by hand. The layout is quality-summary-html's (`assets/base.css` and `assets/base.js` are copies of its `summary.css` and `summary.js`); `assets/design.css` gives the page an orange theme and the parts the design page needs, and `assets/design.js` draws the diagrams. The page uses as little color as quality-summary-html: one orange from this skill's icon where quality-summary-html uses its blue, and neutrals everywhere else, diagrams included (Theme in `references/page-spec.md`). Your job is to run the script, read what it reports, check the result, and tell the user plainly what the page shows and what it cannot.

## Sources

req-to-design's `artifacts.md` says the YAML items are the source of truth and the reports explain them. The page follows that rule, the way quality-summary-html does:

- **From the YAML items**: the ranking table, the design context, scenarios, constraints, functional/observability/security drivers, principles and conflicts (`drv/`, `design-context.yaml`); elements, the decisions table, one card per stage 2 decision with its question, options, chosen and rejected options, rationale, gains, costs, sensitive points, trade-offs, assumptions and debt, the design parameters and the technical debt (`elm/`, `dec/`); one item per technical policy with the table of its scope (`pol/`); interfaces, error contracts, SLI bindings and data entities (`ifc/`, `dat/`); the open hand-offs of each stage (`hnd/`); every count on the route at the top.
- **From the reports**: the Mermaid diagrams (views, threat model, the technical policy's repositories and pipeline, end-to-end flows, screens, the ER diagram, data quality flows, states), and the tables that no item holds: concerns, feasibility, the tables beside the views, design concerns, the threat table, walkthroughs, cost and team, shared conventions, latency budgets, data quality. A latency budget whose hop table gives seconds is drawn as a chart against its threshold. The tables that req-to-design's `scripts/tables.py` writes from the items (between `<!-- generated: … -->` markers) are found by their markers and only compared with the items.
- **As a gist**: every text, table cell and diagram label shows its first sentence without bracketed asides (a bracket that holds only a quantity, such as 「（5 秒）」, stays). IDs, terms, numbers, titles and names are shown whole. The rule is in `references/page-spec.md` (Gist).
- **Left out**: the reports' prose; a section that has neither a table nor a diagram (the overall structure, a CUJ walkthrough written as prose, a latency budget without a table), which the script lists; what only justifies or traces a text (the reasons for the ranking levels, the sources of the drivers and design inputs, the basis of a design parameter's value, the gate and audit bindings, the acceptance-criteria trace, what was already decided); details (the timeouts, the rules of each policy, which are only counted, the directory tree, the kinds of interface); the chain's process (findings, decided hand-offs, open assumptions and requests to the quality chain, which the script only counts, questions and answers, placeholders); stage 4, the detailed design; and what another table on the page already shows (a card's design parameters and the reasons of its debt).

When a report table restates items (ranking, design context, drivers, elements, decisions of each stage, policies, interfaces, data, and the debt table that the stage 2 report writes by hand) and lists other IDs or another order, the page follows the YAML and the script reports the difference.

## Language

The page and the script's report are written in the language of the outputs, so that the labels match the content around them:

- Outputs written in Japanese give a Japanese page and a Japanese report.
- Outputs in any other language give an English page and an English report. Only Japanese and English are bundled (`assets/lang/ja.json`, `assets/lang/en.json`).

The script decides from the YAML free text and the reports (Japanese when kana make up a tenth or more of the letters) and prints its decision on the second line of the report: `言語: ja（資料から判定）` or `Language: en (detected from the outputs)`. `--lang ja` or `--lang en` overrides it; use that only when the user asks for a page in the other language. The labels then change, but the content stays in the language it was written in.

The reports are found by their headings in Japanese (req-to-design's glossary and reports) or English (its report templates), and the generated tables by their markers. When the outputs are in a language other than Japanese or English, tell the user before or with the result: the page's labels are English, the content stays in the original language, and the report-only tables are usually not found, so the script lists them as missing. Revision notes are removed by rules for Japanese and English only.

The report labels below are given in both languages; match on the exact strings.

## Inputs

```
docs/design/
├── drv/ dec/ elm/ pol/ ifc/ dat/ hnd/, design-context.yaml   the items: every table that has items
├── 1-architecture-drivers.md, 2-architecture.md,             diagrams and report-only tables
│   2b-technical-policy.md, 3-high-level-design.md
├── fnd/ das/ qcr/ mod/                                       titles for tooltips; open assumptions and requests are counted
└── 4-detailed-design*, quality-chain-requests.md, reviews/   not read
docs/quality/   titles of FR, QR, NFR, SLI, CUJ… and the anchors of summary.html (quality IDs link to the quality summary)
```

A stage is shown when its items or its report exist (stage 2b: `pol/` or technical-policy decisions). A stage with items but no report loses only its diagrams and report-only tables; a stage with a report but no items shows only those. If the project keeps the outputs elsewhere, pass that directory.

The script reads the layout of req-to-design 0.3.0. Outputs of 0.1.0 or 0.2.0 still carry `changelog`, `version`, `needs_agreement`, the statuses `draft` and `agreed`, and deferred decisions, and have no stage 2b and no hand-offs: the script lists them under `旧い形式` / `Older outputs`, and the page then misses the technical policy and the hand-offs and reports the old reports' sections as not found. req-to-design's release notes say to re-run the stages in order, running architecture-to-technical-policy after stage 2, to bring such outputs to 0.3.0. Tell the user so instead of working around it.

## Steps

1. **Find the outputs.** Look for `docs/design/drv/` or `docs/design/1-architecture-drivers.md`. Without either, the design chain has not run: point to requirements-to-architecture-drivers instead of building a page from other documents.

2. **Run the script.** It needs Python 3.9 or later and PyYAML; with uv, PyYAML comes along:

   ```bash
   uv run --with pyyaml python3 <this skill's directory>/scripts/build_design_summary.py docs/design
   ```

   Options: `--out PATH`, `--quality-dir DIR` (default: `quality` next to the design directory), `--lang ja|en` (see Language), `--show-cleaning` (every text whose revision notes were removed, before and after). The script overwrites the output.

3. **Read the report.** Exit code 0: written, even with warnings. 1: written, but the page failed its own check (duplicate ids or links without a target); that is a bug in the script, so fix the script, never the page. 2: nothing to read (no items and no reports). Act on these lines:
   - `言語` / `Language`: the language of the page and the report, and how it was chosen. If it does not match the outputs, say so and rerun with `--lang`.
   - `ページに載せない項目` / `Not on the page`: the open assumptions (`das/`) and the requests to the quality chain that wait for or have an answer (`quality-chain-requests.md`). The page leaves them out; say how many there are, since the design rests on the assumptions until they are confirmed.
   - `旧い形式` / `Older outputs`: items in the layout of req-to-design before 0.3.0 (see Inputs). Say which stages to re-run; do not edit the items.
   - `食い違い` / `Mismatches`: a report table that restates items lists other IDs, or another ranking order. The page follows the YAML. Do not edit either to make it go away; name the stage whose re-run would fix it (usually the report is stale, or it records something the YAML has no field for, such as an accepted risk).
   - `突き合わせなかった表` / `Not found in the reports, not compared`: a report table that should be compared was not found, so that comparison did not run. Say so; otherwise 「食い違い: なし」 reads as a full check.
   - `報告書` / `Reports`: a stage whose report is missing (its diagrams and report-only tables are left out), a stage that has no outputs yet (or none although a later stage has), or a report that is still a draft or waits for answers, whose stage is not settled.
   - `YAML`: an item file that could not be read, a missing `priority.rank`, a `chosen` that matches no option, or a stage that has a report but no items.
   - `節` / `Sections not found`, `表` / `Tables not found`: a heading or table the page expects in a report was not found. If a stage renamed it, update the script's lookup (`H` at the top).
   - `用語集にない値` / `Values not in the glossary`: an enum value the language files do not know (a new kind or classification). It appears as written; if the chain's glossary changed, add the term to `assets/lang/ja.json` and `en.json`.
   - `表も図もなく省いたもの` / `Left out (no table or diagram)`: sections written only as prose, such as a CUJ walkthrough or a latency budget without a table. Tell the user they are not on the page.
   - `使わないファイル` / `Files no longer used`: a `summary-text.yaml` from the version of this skill that kept hand-written texts. The page no longer reads it. Tell the user it can be deleted; do not delete it yourself, since it may hold their notes.
   - `履歴の注記を削った文` / `Texts with revision notes removed`: the number of texts cleaned (YAML values and report cells). After a re-run, skim `--show-cleaning` for wrong removals and fix the rules in the script if one removed something meaningful.

4. **Check the page** in a browser: the top (route and ranking table), a decision card, the technical policy, the threat model diagram, one Mermaid diagram and one budget chart. Diagrams render when they first come into view and need network access (Mermaid from jsDelivr, fonts from Google Fonts).

5. **Report to the user**: the path, the language, every warning (older outputs and mismatches first), and what the page leaves out (the reports' prose, the sections listed as left out, every sentence after the first and the bracketed asides of each text, the reasons for the ranking levels, the sources and most basis columns, the rules of the technical policies, the gate and audit bindings, the timeouts, the acceptance-criteria trace, findings, decided hand-offs, the open assumptions and requests to the quality chain with their counts, questions and answers, open gaps, the option-comparison tables inside each decision section of the report, and stage 4, the detailed design). Say that the page shows gists, so that the YAML and the reports are read for the whole of a text. When a report is a draft or waits for answers, say that its stage is not settled, so that nobody reads the page as a settled design.

## Rules

- **Never write or hand-edit summary.html.** A hand-written or patched page drifts from the YAML, and the next run silently overwrites the edits. If the user wants something different, change the script, `assets/` and `references/page-spec.md`, rebuild, and point out that the change applies to every project that uses this skill.
- **Do not change the reports or the YAML items to suit the page.** The page reports the design chain's state; wording belongs to the stage that owns it.
- **Do not prefer a report to the YAML.** When they disagree, the page shows the YAML and the report line says where.
- **Do not work around a poor gist.** A text whose first sentence does not carry its point (one that starts with a label, such as 「規模。デモは…」) shows only that sentence. If you notice one, name the item and the stage that wrote it; the fix is to lead with the point in that stage's output, not to special-case the page.
- **Commit only when asked.** `summary.html` is generated, so it is reasonable to suggest committing it together with the docs it was built from; the page shows the commit it was built at.

Read `references/page-spec.md` for the page structure, every table and its source, the cleaning rules, and how to change the page.
