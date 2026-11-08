# quality-summary-html

English | [日本語](README.ja.md)

Two agent skills that each turn a skill chain's outputs into one HTML page, with the same layout and look:

| Skill | Reads | Writes |
|---|---|---|
| [quality-summary-html](#quality-summary-html) | what the four [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) skills write to `docs/quality/` | `docs/quality/summary.html` |
| [design-summary-html](#design-summary-html) | what the [req-to-design](https://github.com/Taro000/req-to-design) skills write to `docs/design/` (stages 1 to 3) | `docs/design/summary.html` |

## Install

```sh
# into the current project (asks which skills and which agents to install for)
npx skills add Taro000/quality-summary-html

# both skills, for Claude Code only, available in every project, without prompts
npx skills add Taro000/quality-summary-html -a claude-code -g -y

# one skill only
npx skills add Taro000/quality-summary-html -s design-summary-html
```

The skills run Python scripts, so they need Python 3.9 or later and PyYAML. With [uv](https://docs.astral.sh/uv/), `uv run --with pyyaml` brings PyYAML along.

Each skill's `evals/` (test outputs: about 1.7 MB for quality-summary-html, about 4.5 MB for design-summary-html) is installed with it. Delete them if you only use the skills.

## quality-summary-html

An agent skill that turns the outputs the four [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) skills write to `docs/quality/` into one HTML page, `docs/quality/summary.html`. Instead of reading four reports and one YAML file per item, you can follow each CUJ to the requirements and SLOs that serve it (CUJ → QIU → FR → QR → NFR / SLI) on a single page.

### What the page shows

| Section | Contents |
|---|---|
| Traceability | A diagram of item counts per stage, then one table that follows each CUJ through its QIUs, FRs and QRs to NFRs and SLIs, grouped by user. Requirements that do not come from users (laws, standards, security risk analysis, development policies) form the last group. |
| Stage 1 | Business requirements, users, CUJs, quality-in-use requirements, failure scenarios and measures, what is not targeted, and each formula counted two ways (quality-in-use measure and KPI) |
| Stage 2 | Functional requirements, functions considered and not added |
| Stage 3 | An impact × likelihood chart, product quality and data quality matrices (characteristic × CUJ), the priority table, handling by CUJ, internal quality derived from external quality, quality requirements, requirements that do not come from users |
| Stage 4 | SLO cards, SLOs, SLIs, error budget policies, burn-rate alerts, deadline SLOs, other non-functional requirements |

Only the traceability table is open; every other table sits in a closed toggle. Each ID links to its row and shows the item's title on hover. Stages not run yet are left out, and a note at the bottom of the page says which.

To stay quick to read, the page leaves out, among other things, the basis of most items, the rationale for SLO numbers, measurement points and blind spots. Read those in the YAML and the reports. Light mode only.

### Use

1. Run the cuj-to-slo skills, at least stage 1, so that `docs/quality/context.yaml` exists.
2. "Summarize docs/quality as an HTML page."
3. After re-running a stage: "Rebuild summary.html."

The skill runs the bundled script, which builds every table from the YAML items, so every project and every re-run gets the same layout. It then tells you what the page could not show: inconsistencies between the outputs (a report table that disagrees with the YAML, a reference to a retired item), each with the stage whose re-run fixes it, and the report-only tables it could not find. When SLO targets are provisional or quality requirements are still drafts, it says that the page shows proposals, not agreed targets.

The page follows the language of the outputs: Japanese for Japanese outputs, English for any other language. Only the labels change; the content stays as written. You can also ask for the labels in the other language, another title or another output path.

### Output

```
docs/quality/
├── context.yaml  qiu/ … ebp/              YAML items: the source of every table
├── 1-quality-in-use.md … 4-nfr-slo.md     reports: stage titles and the few tables only they have
└── summary.html                           the page this skill writes
```

The page's header shows the git commit of the docs it was built from, and marks uncommitted changes. Every run overwrites `summary.html`; commit it together with the docs it was built from.

### What the skill will not do

- Write or patch the page by hand. A hand edit drifts from the YAML and is lost on the next run. To change the page, change the script and `assets/`; the change applies to every project that uses the skill.
- Edit the YAML or the reports to clear an inconsistency. The page reports the chain's state; fixing it belongs to the stage that owns the item.
- Prefer a report over the YAML. The YAML items are the source of truth, as cuj-to-slo's artifacts.md says. A report-only table whose heading is not found is left out, and the skill says so.
- Build a page from other documents when the chain has not been run. Without `context.yaml`, it points you to `cuj-to-quality-in-use` instead.
- Commit, unless you ask.

## design-summary-html

An agent skill that turns the outputs the [req-to-design](https://github.com/Taro000/req-to-design) skills write to `docs/design/` (stage 1 architecture drivers, stage 2 architecture, stage 3 high-level design) into one HTML page, `docs/design/summary.html`, in quality-summary-html's layout with its own orange theme. Instead of reading three long reports, you can go from the ranked drivers to the elements, decisions, flows and data on a single page. The page is for grasping the design's direction quickly, so it shows the gist of every text (its first sentence, without bracketed asides); the YAML items and the reports keep the whole. The page is written in the language of the outputs (Japanese, or English for any other language).

### What the page shows

| Section | Contents |
|---|---|
| Route | Item counts by stage, from architecture drivers to data entities |
| Stage 1 | The ranking table (first and open), design inputs and stakeholders, concerns, quality and change scenarios, constraints, functional, observability and security drivers, principles, conflicts, feasibility |
| Stage 2 | Elements first, then the five views (diagrams and tables), the decisions with one card each (the question, the options with the rejected ones' reasons, rationale, gains, costs, sensitive points, trade-offs, assumptions and debt), design concerns, the threat model (a diagram whose flow numbers link to the threat table, and the table), walkthroughs, design parameters, debt and deferred decisions, running cost |
| Stage 3 | Shared conventions, decisions, interfaces, error contracts, end-to-end flows (sequence diagrams), latency budgets (a hop table becomes a chart), failure paths and error budgets, screen flows, data (ER diagram and entities), data quality flows, states across elements, measurement points, the acceptance-criteria trace, design parameters |

As in quality-summary-html, the YAML items are the source of truth, and a script builds the page from the outputs alone: nothing on it is written by hand. Every table that has items (drivers, design inputs, elements, decisions, design parameters, debt, interfaces, error contracts, data entities) is built from them. The reports are read only for their Mermaid diagrams and for the tables that no item holds (concerns, feasibility, the views' tables, design concerns, the threat table, walkthroughs, running cost, shared conventions, latency budgets, measurement points, the acceptance-criteria trace); their prose is not shown. A section with neither a table nor a diagram (the overall structure, a CUJ walkthrough written as prose, a latency budget without a table) is left out, and the skill says so. Report tables that restate items are compared with them, and a stale report is reported; the page follows the YAML. Every text, table cell and diagram label is cut to its gist: its first sentence, without bracketed asides (a bracket that holds only a quantity, such as "(5 s)", stays). Columns that only justify or trace a text, such as the reasons for the ranking levels, the sources of the drivers and the basis of a design parameter's value, are left out. Revision-history notes (「前の版は…」, "the previous version…", finding numbers) are removed from YAML texts and table cells by the rules of the outputs' language. Mermaid is loaded from a CDN when the first diagram comes into view, so viewing the page needs network access. Light mode only.

### Language

The same as quality-summary-html: outputs (YAML free text and reports) in which kana make up a tenth or more of the letters give a Japanese page and report, anything else an English one. Report sections are found by their Japanese (req-to-design's glossary) or English (its report templates) headings. `--lang ja` or `--lang en` switches only the labels (the content stays as written). For outputs in other languages, the labels are English and the report-only tables are usually not found, and the skill says so.

### Use

1. Run the req-to-design skills, at least stage 1, so that `docs/design/drv/` exists.
2. "Summarize docs/design as an HTML page."
3. After re-running a stage: "Rebuild the design summary."

`docs/design/summary-text.yaml` (condensed texts), which an earlier version used, is no longer read; if one is left, the skill says it can be deleted.

### Output

```
docs/design/
├── drv/ dec/ elm/ ifc/ dat/, design-context.yaml        YAML items: every table that has items
├── 1-architecture-drivers.md … 3-high-level-design.md   reports: diagrams and the tables no item holds
└── summary.html                                         the page this skill writes
```

Commit `summary.html` together with the docs it was built from.

### What the skill will not do

- Write or patch the page by hand, for the same reasons as quality-summary-html.
- Edit the reports or the YAML items to suit the page.
- Prefer a report to the YAML. When they disagree, the page shows the YAML and the skill says where.
- Show the reports' prose. Sections with neither a table nor a diagram are left out, and the skill says so.
- Commit, unless you ask.

## Maintaining

```
skills/quality-summary-html/
├── SKILL.md                   instructions for the agent
├── scripts/build_summary.py   the generator
├── assets/                    summary.css, summary.js, and the wording per language (lang/ja.json, lang/en.json)
├── references/page-spec.md    every table with its columns and sources, what is left out and why, how to change the page
└── evals/                     four test cases
skills/design-summary-html/
├── SKILL.md                          instructions for the agent
├── scripts/build_design_summary.py   the generator
├── assets/                           base.css and base.js (copies of quality-summary-html's summary.css and summary.js), design.css (the orange theme and the design page's parts), design.js, and the wording per language (lang/ja.json, lang/en.json)
├── references/page-spec.md           every table with its source, the language, the cleaning rules, how to change the page
└── evals/                            four test cases
scripts/check-chain.py         checks for drift from the cuj-to-slo glossary and artifacts.md
tests/                         automated tests of both skills, the scripts that build the fictional service's outputs, and the eval graders
```

To run the generator without an agent, use a clone of this repository:

```sh
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality

# another output path and title
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title "Ride-hailing app quality"

# English labels for Japanese outputs
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --lang en
```

It prints its report to standard output, in the page's language. Exit code 0 means the page was written, even with inconsistencies; 1 means it was written but failed its own check (duplicate ids or links without a target); 2 means the outputs could not be read.

```sh
# use your working copy as Claude Code's installed skill
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html

# automated tests (they also check that the same inputs give the same bytes)
uv run --with pyyaml python3 -m unittest discover -s tests -v

# rebuild the fictional homework submission service's outputs in evals/
uv run --with pyyaml python3 tests/make_homework_fixture.py

# after cuj-to-slo changes: check that its glossary and artifacts.md still have what this skill relies on
python3 scripts/check-chain.py [path/to/cuj-to-slo]
```

When `check-chain.py` reports drift, update `assets/lang/ja.json`, `assets/lang/en.json` and the generator to match. Without an argument, it reads the path from the `CUJ_TO_SLO` environment variable, or else uses `../cuj-to-slo`, where `git clone` puts cuj-to-slo next to this repository. It also accepts an installed skill's directory. The automated tests run the same check against the same place, and skip it when the cuj-to-slo repository is not there.

`evals/ride-hailing-full` is a copy of `docs/quality` in ride-hailing-app-demo (commit ba28153).

design-summary-html runs the same way; it reports in the page's language, with the same exit codes:

```sh
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design

# a page with English labels from Japanese outputs
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design --lang en

# rebuild the fictional homework submission service's design outputs in evals/ (on top of quality-summary-html's eval outputs)
uv run --with pyyaml python3 tests/make_homework_design_fixture.py

# after running the evals with the skill-creator workflow: grade every run and write grading.json
uv run --with pyyaml python3 tests/grade_design_eval.py skills/design-summary-html-workspace/iteration-1

# use your working copy as Claude Code's installed skill
ln -s "$PWD/skills/design-summary-html" ~/.claude/skills/design-summary-html
```

When quality-summary-html's `summary.css` or `summary.js` changes, copy it unchanged to design-summary-html's `assets/base.css` or `assets/base.js`, so that both pages keep the same layout; the orange theme lives in `design.css`, which redefines the color tokens after `base.css`.

design-summary-html's `evals/` holds four cases: the fictional homework submission service's design (stages 1 to 3 in Japanese, the same in English, and stages 1 and 2 in Japanese), and `ride-hailing-full`, a copy of `docs/design` and `docs/quality` in ride-hailing-app-demo (commit b63c7a1) without the files the skill does not read (`summary.html`, `summary-text.yaml`, `reviews/`, the OpenAPI specs). The tests (`tests/test_build_design_summary.py`) build all four with the script, grade the pages with the eval grader, and check that the grader fails pages that miss what a statement asks for.

## License

MIT
