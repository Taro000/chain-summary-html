---
name: quality-summary-html
description: Builds docs/quality/summary.html, one self-contained light-mode page that summarizes the outputs of the cuj-to-slo quality chain (cuj-to-quality-in-use → quality-in-use-to-functional-requirements → functional-requirements-to-product-quality → product-quality-to-slo) so people can grasp a system's quality quickly. It puts a CUJ-by-CUJ traceability table first (CUJ → QIU → FR → QR → NFR/SLI), then every stage's tables in toggles, with ID links, an impact × likelihood chart, quality matrices and SLO cards. A bundled script renders the page from the YAML items, so every project and every re-run gets the same design. Use it whenever someone wants to summarize, visualize, share, review or present docs/quality, asks for an HTML overview or one-pager of quality requirements, KPIs, NFRs or SLOs, wants to see traceability from CUJs to SLOs, or wants summary.html rebuilt after a stage was re-run, even if they never name this skill, including Japanese requests such as 「品質の成果物を HTML にまとめて」「docs/quality の要約」「トレーサビリティを一覧で見たい」.
---

# Quality summary HTML

Renders `docs/quality/summary.html` from the outputs of the four-stage quality chain. The page exists so that a person can understand the system's quality efficiently: what users need (CUJs and quality-in-use requirements), which functions serve them, which quality requirements matter most, and how each one is held by an SLO, a gate, an audit or a monitor.

The page is written in Japanese. The script's report and the page use the Japanese labels quoted below, so match on those exact strings; the English glosses are for you.

The page design and the set of tables are fixed, and `scripts/build_summary.py` does all of the rendering. That is the point of this skill: the user approved this exact layout, and every project, and every re-run of a stage, should produce the same page from the same data. Your job is to run the script, read what it reports, check the result, and tell the user plainly what the page shows and what it cannot.

## Inputs

The chain writes its outputs in the layout of its `artifacts.md`:

```
docs/quality/
├── context.yaml            stage 1: system, KGIs, outcomes, users, CUJs   (required)
├── qiu/ kpi/               stage 1                                         (required)
├── fr/ frp/                stage 2
├── qr/                     stage 3
├── nfr/ sli/ ebp/          stage 4
└── 1-quality-in-use.md … 4-nfr-slo.md   the four reports
```

The YAML items are the source of truth (artifacts.md says so), and the script builds every table from them. It reads the Markdown reports only for each stage's title and for the few tables that exist only there: not targeted, functions considered and not added, how each internal QR supports the external ones, the kinds of data and their producers, and out-of-scope notes. It also compares four report tables with the YAML to catch stale reports: the quality-in-use coverage and the functions by CUJ step (stage 2), the internal-quality pairs (stage 3) and the allocation (stage 4). The report headings are written in the working language by whichever model ran the stage, so the script matches them loosely; when it cannot find a table, it leaves the table out of the page or skips the comparison, and says so.

Stages 2 to 4 are optional. If the chain has only reached stage 2, the page covers stages 1 and 2 and says the rest is missing. If the project keeps the outputs somewhere other than `docs/quality`, which artifacts.md allows, use that directory.

## Steps

1. **Find the outputs directory.** Look for `context.yaml` under `docs/quality/`, or wherever the project's reports say the chain wrote. If there is no `context.yaml`, the chain has not been run; say so and point to the cuj-to-quality-in-use skill rather than writing a page from other documents.

2. **Run the script.** It needs Python 3.9 or later and PyYAML. With uv, PyYAML comes along for the run:

   ```bash
   uv run --with pyyaml python3 <this skill's directory>/scripts/build_summary.py docs/quality
   ```

   Without uv, install PyYAML first (`python3 -m pip install --user pyyaml`) and run `python3 <…>/build_summary.py docs/quality`. Options: `--out PATH` to write somewhere other than `docs/quality/summary.html`, and `--title TEXT` to replace the default title, which is the `system.name` from context.yaml (without a trailing parenthetical) followed by 「の品質」 ("quality of"). The script overwrites the output file. If `summary.html` already exists and is not tracked by git, mention that it will be replaced before running.

3. **Read the report the script prints.** Exit code 0 means the page was written, even when there are inconsistencies. Exit code 2 means the input could not be read (no context.yaml, no PyYAML). Exit code 1 means the page was written but failed its own check (a duplicate id or a link with no target), which is a bug in the script or data it did not expect; tell the user and do not patch the HTML by hand. The lines to act on:
   - `食い違い` (inconsistencies): references to items that do not exist or are retired, and places where a report table disagrees with the YAML. The page follows the YAML. Do not edit the YAML or the reports to make these go away; that belongs to the stage that owns the item. Report each one and name the stage whose re-run would fix it. When a report table disagrees with the YAML, the report is usually stale.
   - `報告書に見つからず省いたもの` (not found in the reports, left out): report-only tables that were not found and so are missing from the page. Tell the user which ones. If the heading exists under a different name, it is fine to suggest renaming it in the report, but do not edit reports without being asked.
   - `報告書に見つからず突き合わせなかった表` (not found in the reports, not compared): report tables the script compares with the YAML but could not find, so that comparison did not run. Tell the user; otherwise 「食い違い: 0 件」 (0 inconsistencies) reads as if the reports had been checked in full.
   - `用語集にない値` (values not in the glossary): YAML enum values the term table does not know (for example a new characteristic name). They appear in English on the page. If the chain's glossary changed, `assets/terms.ja.json` needs the new term.
   - `リンクにしていない ID` (IDs not linked): IDs mentioned on the page that have no row of their own, usually retired items and function proposals (FRP). This is expected and needs no action.

4. **Check the page.** If a browser is available, open the file or take a headless screenshot and look at the top (the route diagram and the traceability table) and one opened table. The script checks ids and links itself; the visual check is for layout surprises with unusual data, such as very long titles or many CUJs.

5. **Report to the user.** Give the path, the stages and item counts, every inconsistency, and every table left out. Then say what the page hides, because the page is meant to be quick to read and so drops columns: the basis of most items (most are `inferred`), the overlap column, the rationale for SLO numbers, measurement points and blind spots. If SLO targets are `provisional` or quality requirements are still `draft`, say that the page presents proposals, not agreed commitments, so nobody mistakes the cards for operating targets.

## Rules

- **Never write or hand-edit the page.** A hand-written or patched page drifts from the YAML and from the design the user approved, and the next run silently overwrites the edits. If the user wants something different, change the script, `assets/` and `references/page-spec.md`, rebuild, and point out that the change applies to every project that uses this skill.
- **Do not change the docs to suit the page.** The page reports the chain's state; it does not repair it.
- **Commit only when the user asks.** `summary.html` is generated, so it is reasonable to suggest committing it together with the docs it was built from; the page shows the commit it was built at.

## What the page contains

The order is fixed: a header with the commit and the latest update date; the traceability section (a route diagram of item counts per stage, then the CUJ-by-CUJ table, open by default); one section per stage with its tables in closed toggles; and a closed toggle at the bottom, 「HTML作成時の要件」 (requirements for building the HTML), that records the purpose, the requirements and the rules the page was built by. IDs link to their rows, opening the toggle they are in; hovering shows the item's title. The priority table sorts by QR and by score.

Read `references/page-spec.md` when you need the details: every table with its columns and YAML sources, the figures, what is deliberately left out and why, and how to change the design.
