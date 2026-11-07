---
name: design-summary-html
description: Builds docs/design/summary.html, one light-mode page that explains the current outputs of the req-to-design chain (requirements-to-architecture-drivers → architecture-drivers-to-architecture → architecture-to-high-level-design) in the same layout and look as quality-summary-html. Tables and Mermaid diagrams are taken from the three reports on every run; the condensed prose (each decision, the overall structure, design concerns, the threat model, latency budgets) lives in docs/design/summary-text.yaml, which records a hash of each source section so that a stale summary is reported. Japanese outputs only. Use it when someone wants to summarize, visualize, share or review docs/design, asks for an HTML overview of the architecture or the high-level design, or wants summary.html rebuilt after a design stage was re-run, including Japanese requests such as 「設計の成果物を HTML にまとめて」「docs/design の要約を作り直して」.
---

# Design summary HTML

Renders `docs/design/summary.html` from the design chain's reports so that a person can grasp the design quickly: the ranked architecture drivers, the elements and views, every decision with its options and consequences, the threat model, the walkthroughs, and the high-level design's interfaces, error contracts, end-to-end flows, latency budgets, screens, data and states.

The layout and look are fixed and shared with quality-summary-html: `assets/base.css` and `assets/base.js` are copies of its `summary.css` and `summary.js`, and `assets/design.css` and `assets/design.js` add what the design page needs. `scripts/build_design_summary.py` does all the rendering. Your job is to run it, keep the condensed texts current, read its report, check the result, and tell the user what the page shows and what it cannot.

## Language

The page and the report are Japanese. The script finds the reports' sections by their Japanese headings (「順位表」「設計の決定」「端から端の流れ」…), as the req-to-design glossary names them. When the design chain wrote its outputs in another language, the sections are not found: tell the user that this skill supports Japanese outputs only, rather than running it.

## Inputs

```
docs/design/
├── 1-architecture-drivers.md, 2-architecture.md, 3-high-level-design.md   tables and diagrams, read on every run
├── drv/ dec/ elm/ ifc/ dat/ fnd/, design-context.yaml                      counts and titles (tooltips)
└── summary-text.yaml                                                       condensed texts, figure layout, chart data, fixes, hashes
docs/quality/   titles of FR, QR, NFR, SLI, CUJ… and the anchors of summary.html (quality IDs link to the quality summary)
```

Stage 1 is required; stages 2 and 3 are shown when their reports exist. If the project keeps the outputs elsewhere, pass that directory.

## Steps

1. **Find the outputs.** Look for `docs/design/1-architecture-drivers.md`. Without it, the design chain has not run: point to requirements-to-architecture-drivers instead of building a page from other documents.

2. **Run the script.** It needs Python 3.9 or later and PyYAML; with uv, PyYAML comes along:

   ```bash
   uv run --with pyyaml python3 <this skill's directory>/scripts/build_design_summary.py docs/design
   ```

   Options: `--out PATH`, `--quality-dir DIR` (default: `quality` next to the design directory), `--text PATH` (default: `summary-text.yaml` in the design directory), `--show-cleaning` (every table cell whose revision notes were removed, before and after), `--hashes` (the current hash of every condensed source), `--write-hashes` (rewrite the `hashes:` block at the end of summary-text.yaml). The script overwrites the output.

3. **Read the report.** Exit code 0: written, even with warnings. 1: written, but the page failed its own check (duplicate ids or links without a target); that is a bug in the script, so fix the script, never the page. 2: the inputs could not be read. Act on these lines:
   - `添削文がない` (no condensed text): on a first run every condensed section is listed, and the page shows stand-ins (the decision's tables without points, the report's own threat diagram and budget tables, 「（添削文なし）」). Write the missing entries in summary-text.yaml (format in `references/page-spec.md`), then run with `--write-hashes`. Later runs list only new sections, typically a new decision or budget.
   - `添削文のもとが変わった` (source changed): a stage re-run changed the section a condensed text was written from. Read that section, rewrite the entry, then `--write-hashes`. Never refresh a hash without re-reading the source: the page would present outdated text as current.
   - `節` / `表` / `列`: a heading, table or column the page expects was not found. If a stage renamed it, update the script's lookup.
   - `手直し`: a `fixes` entry no longer matches the report text, or a `diagram_direction` key names no section with a diagram. Remove or update it.
   - `履歴の注記を削ったセル`: the number of cells cleaned. After a re-run, skim `--show-cleaning` for wrong removals and correct them with a `fixes` entry rather than loosening the rules.

4. **Check the page** in a browser: the top (route and ranking table), a decision card, the threat model figure, one Mermaid diagram and one budget chart. Diagrams render when they first come into view and need network access (Mermaid from jsDelivr, fonts from Google Fonts).

5. **Report to the user**: the path, every warning, which condensed texts you wrote or rewrote, and what the page leaves out (paragraphs around tables, the reports' summaries, findings, items needing agreement, questions and answers, open gaps, the basis columns). The design items are drafts; say so, so that nobody reads the page as an approved design.

## Writing condensed texts

Shorten and merge; never add a claim the report does not make. Keep the reports' plain wording and terms, write short sentences, and drop revision history (「前の版は…」「N 回目の再実行で…」, finding numbers). For a decision, keep what decides it: how it works, what it gains and loses, the points the response depends on, accepted risks, deferrals. The threat-model figure's layout (boxes, zones, arrows, chips) is drawn by hand in `threat.diagram`; until it exists, the report's diagram is shown.

## Rules

- **Never write or hand-edit summary.html.** Change the script, the assets or summary-text.yaml, and rebuild.
- **Do not change the reports or the YAML items to suit the page.** The page reports the design chain's state; wording belongs to the stage that owns it. `fixes` is only for revision notes and pointers the cleaner cannot see.
- **Commit only when asked.** If you commit, include summary-text.yaml with summary.html.

Read `references/page-spec.md` for the page structure, every table and its source, the cleaning rules, the summary-text.yaml format, and how to change the page.
