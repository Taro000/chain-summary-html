---
name: design-summary-html
description: Builds docs/design/summary.html, one light-mode page that explains the current outputs of the req-to-design chain (requirements-to-architecture-drivers → architecture-drivers-to-architecture → architecture-to-high-level-design) in quality-summary-html's layout with its own orange theme. As in quality-summary-html, the YAML items are the source of truth and every table that has items is built from them (drivers, premises, elements, decisions with their options and consequences, interfaces, error contracts, data entities, design parameters, debt); the reports are read only for the Mermaid diagrams and for the sections no item holds, and report tables that restate items are compared with the YAML so a stale report is reported. The condensed prose of report-only sections (overall structure, design concerns, the threat model, latency budgets) lives in docs/design/summary-text.yaml with a hash of each source section. Japanese outputs only. Use it when someone wants to summarize, visualize, share or review docs/design, asks for an HTML overview of the architecture or the high-level design, or wants summary.html rebuilt after a design stage was re-run, including Japanese requests such as 「設計の成果物を HTML にまとめて」「docs/design の要約を作り直して」.
---

# Design summary HTML

Renders `docs/design/summary.html` from the design chain's outputs so that a person can grasp the design quickly: the ranked architecture drivers, the elements and views, every decision with its options and consequences, the threat model, the walkthroughs, and the high-level design's interfaces, error contracts, end-to-end flows, latency budgets, screens, data and states.

The layout is fixed and shared with quality-summary-html: `assets/base.css` and `assets/base.js` are copies of its `summary.css` and `summary.js`. `assets/design.css` redefines the color tokens for an orange theme (the colors of this skill's icon) and adds what the design page needs; `assets/design.js` adds the behavior. `scripts/build_design_summary.py` does all the rendering. Your job is to run it, keep the condensed texts current, read its report, check the result, and tell the user what the page shows and what it cannot.

## Sources

req-to-design's `artifacts.md` says the YAML items are the source of truth and the reports explain them. The page follows that rule, the way quality-summary-html does:

- **From the YAML items**: the ranking table, premises and stakeholders, scenarios, constraints, functional/observability/security drivers, principles and conflicts (`drv/`, `design-context.yaml`); elements, the decisions table, one card per decision with its question, options, chosen and rejected options, rationale, gains, costs, sensitive points, trade-offs, assumptions, parameters and debt, the design parameters, and debt and deferred decisions (`elm/`, `dec/`); interfaces, error contracts and data entities (`ifc/`, `dat/`); every count on the route at the top.
- **From the reports**: the Mermaid diagrams (views, threat model before its hand-laid figure exists, end-to-end flows, screens, the ER diagram, data quality flows, states), and the sections that no item holds: concerns, feasibility, the tables beside the views, overall structure, design concerns, the threat table, walkthroughs, running cost, shared conventions, latency budgets, failure paths and error budgets, measurement points, the acceptance-criteria trace.

When a report table restates items (ranking, scenarios, constraints, principles, premises, elements, decisions, debt, interfaces, data) and lists other IDs or another order, the page follows the YAML and the script reports the difference.

## Language

The page and the report are Japanese. The script finds the reports' sections by their Japanese headings (「順位表」「脅威のモデル」「端から端の流れ」…), as the req-to-design glossary names them, and turns the YAML's enum values into the glossary's Japanese terms. When the design chain wrote its outputs in another language, tell the user that this skill supports Japanese outputs only, rather than running it.

## Inputs

```
docs/design/
├── drv/ dec/ elm/ ifc/ dat/, design-context.yaml                           the items: every table that has items
├── 1-architecture-drivers.md, 2-architecture.md, 3-high-level-design.md   diagrams and report-only sections
├── fnd/                                                                    titles of findings (tooltips)
└── summary-text.yaml                                                       condensed texts of report-only sections, figure layout, chart data, fixes, hashes
docs/quality/   titles of FR, QR, NFR, SLI, CUJ… and the anchors of summary.html (quality IDs link to the quality summary)
```

A stage is shown when its items or its report exist. A stage with items but no report loses only its diagrams and report-only sections; a stage with a report but no items (a draft before the answers were applied) shows only those. If the project keeps the outputs elsewhere, pass that directory.

## Steps

1. **Find the outputs.** Look for `docs/design/drv/` or `docs/design/1-architecture-drivers.md`. Without either, the design chain has not run: point to requirements-to-architecture-drivers instead of building a page from other documents.

2. **Run the script.** It needs Python 3.9 or later and PyYAML; with uv, PyYAML comes along:

   ```bash
   uv run --with pyyaml python3 <this skill's directory>/scripts/build_design_summary.py docs/design
   ```

   Options: `--out PATH`, `--quality-dir DIR` (default: `quality` next to the design directory), `--text PATH` (default: `summary-text.yaml` in the design directory), `--show-cleaning` (every text whose revision notes were removed, before and after, from the YAML and the reports), `--hashes` (the current hash of every condensed source), `--write-hashes` (rewrite the `hashes:` block at the end of summary-text.yaml). The script overwrites the output.

3. **Read the report.** Exit code 0: written, even with warnings. 1: written, but the page failed its own check (duplicate ids or links without a target); that is a bug in the script, so fix the script, never the page. 2: nothing to read (no items and no reports). Act on these lines:
   - `食い違い` (mismatch): a report table that restates items lists other IDs, or another ranking order. The page follows the YAML. Do not edit either to make it go away; name the stage whose re-run would fix it (usually the report is stale, or the report records something the YAML has no field for, such as an accepted risk).
   - `突き合わせなかった表`: a report table that should be compared was not found, so that comparison did not run. Say so; otherwise 「食い違い: なし」 reads as a full check.
   - `添削文がない` (no condensed text): on a first run every condensed section is listed, and the page shows stand-ins (the report's own threat diagram and budget tables, 「（添削文なし）」). Write the missing entries in summary-text.yaml (format in `references/page-spec.md`), then run with `--write-hashes`. Later runs list only new sections, typically a new latency budget.
   - `添削文のもとが変わった` (source changed): a stage re-run changed the section a condensed text was written from. Read that section, rewrite the entry, then `--write-hashes`. Never refresh a hash without re-reading the source: the page would present outdated text as current.
   - `YAML`: an item file that could not be read, a missing `priority.rank`, a `chosen` that matches no option, or a stage that has a report but no items.
   - `用語集にない値`: an enum value the script does not know (a new kind or classification). It appears as written; if the chain's glossary changed, add the term to the `T_…` tables in the script.
   - `使わないキー`: a key of summary-text.yaml the page no longer uses, such as `decisions` from before the decision cards were built from `dec/*.yaml`. Remove it.
   - `節` / `表` / `列`: a heading, table or column the page expects in a report was not found. If a stage renamed it, update the script's lookup.
   - `手直し`: a `fixes` entry no longer matches the report text, or a `diagram_direction` key names no section with a diagram. Remove or update it.
   - `履歴の注記を削った文`: the number of texts cleaned (YAML values and report cells). After a re-run, skim `--show-cleaning` for wrong removals; correct a report's text with a `fixes` entry rather than loosening the rules.

4. **Check the page** in a browser: the top (route and ranking table), a decision card, the threat model figure, one Mermaid diagram and one budget chart. Diagrams render when they first come into view and need network access (Mermaid from jsDelivr, fonts from Google Fonts).

5. **Report to the user**: the path, every warning (mismatches first), which condensed texts you wrote or rewrote, and what the page leaves out (paragraphs around tables, the reports' summaries, findings, items needing agreement, questions and answers, open gaps, the basis columns, the reports' option-comparison tables inside each decision section). The design items are drafts; say so, so that nobody reads the page as an approved design.

## Writing condensed texts

Only report-only sections are condensed: the overall structure, design concerns, the threat model's assets and kinds, latency budgets, notes on state diagrams, walkthrough rows for CUJs the report describes in prose, and the dependency rules. Shorten and merge; never add a claim the report does not make. Keep the reports' plain wording and terms, write short sentences, and drop revision history (「前の版は…」「N 回目の再実行で…」, finding numbers). The threat-model figure's layout (boxes, zones, arrows, chips) is drawn by hand in `threat.diagram`; until it exists, the report's diagram is shown. Decisions are not condensed: their cards come from `dec/*.yaml` as written, minus revision notes.

## Rules

- **Never write or hand-edit summary.html.** Change the script, the assets or summary-text.yaml, and rebuild.
- **Do not change the reports or the YAML items to suit the page.** The page reports the design chain's state; wording belongs to the stage that owns it. `fixes` is only for revision notes and pointers the cleaner cannot see in the reports.
- **Do not prefer a report to the YAML.** When they disagree, the page shows the YAML and the report line says where.
- **Commit only when asked.** If you commit, include summary-text.yaml with summary.html.

Read `references/page-spec.md` for the page structure, every table and its source, the cleaning rules, the summary-text.yaml format, and how to change the page.
