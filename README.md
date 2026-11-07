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

quality-summary-html's `evals/` (test outputs, about 1.7 MB) is installed with it. Delete it if you only use the skill.

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

An agent skill that turns the outputs the [req-to-design](https://github.com/Taro000/req-to-design) skills write to `docs/design/` (stage 1 architecture drivers, stage 2 architecture, stage 3 high-level design) into one HTML page, `docs/design/summary.html`, in the same layout and look as quality-summary-html. Instead of reading three long reports, you can go from the ranked drivers to the elements, decisions, flows and data on a single page. For now it reads Japanese outputs only.

### What the page shows

| Section | Contents |
|---|---|
| Route | Item counts by stage, from architecture drivers to data entities |
| Stage 1 | The ranking table (first and open), premises and stakeholders, concerns, quality and change scenarios, constraints, functional, observability and security drivers, principles, conflicts, feasibility |
| Stage 2 | Elements first, then the five views (diagrams and tables), the overall structure, the decisions with one card each (the option comparison and condensed points), design concerns, the threat model (a figure of trust boundaries and flows, and the threat table), walkthroughs, design parameters, debt and deferred decisions, running cost |
| Stage 3 | Shared conventions, decisions, interfaces, error contracts, end-to-end flows (sequence diagrams), latency budgets as charts, failure paths and error budgets, screen flows, data (ER diagram and entities), data quality flows, states across elements, measurement points, the acceptance-criteria trace, design parameters |

Tables and Mermaid diagrams are read from the reports on every run, and revision-history notes (「前の版は…」, finding numbers) are removed from table cells. The agent condenses the prose into `docs/design/summary-text.yaml`, which records a hash of each source section; after a stage re-run, the skill reports which condensed texts are stale, and the agent rewrites only those. Mermaid is loaded from a CDN when the first diagram comes into view, so viewing the page needs network access. Light mode only.

### Use

1. Run the req-to-design skills, at least stage 1, so that `docs/design/1-architecture-drivers.md` exists.
2. "Summarize docs/design as an HTML page." On the first run the agent also writes `summary-text.yaml` (the condensed decisions, overall structure, design concerns, threat model and latency budgets); until it exists, the page shows the reports' own tables and diagrams in their place.
3. After re-running a stage: "Rebuild the design summary."

### Output

```
docs/design/
├── 1-architecture-drivers.md … 3-high-level-design.md   reports: every table and diagram
├── drv/ dec/ elm/ ifc/ dat/ …                           YAML items: counts and titles
├── summary-text.yaml                                    condensed texts and the hashes of their sources
└── summary.html                                         the page this skill writes
```

Commit `summary-text.yaml` and `summary.html` together with the docs they were built from.

### What the skill will not do

- Write or patch the page by hand, for the same reasons as quality-summary-html.
- Edit the reports or the YAML items to suit the page. The exact replacements in `summary-text.yaml` only remove revision notes the cleaner cannot see.
- Say more in a condensed text than the report says.
- Read design outputs written in English. It finds the reports' sections by their Japanese headings.
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
├── assets/                           base.css and base.js (copies of quality-summary-html's summary.css and summary.js), design.css, design.js
└── references/page-spec.md           every table with its source, the cleaning rules, the summary-text.yaml format, how to change the page
scripts/check-chain.py         checks for drift from the cuj-to-slo glossary and artifacts.md
tests/                         automated tests of quality-summary-html, and the script that builds the fictional service's outputs
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

design-summary-html runs the same way, and reports in Japanese with the same exit codes:

```sh
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design

# after rewriting condensed texts in summary-text.yaml: record the hashes of their sources
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design --write-hashes

# use your working copy as Claude Code's installed skill
ln -s "$PWD/skills/design-summary-html" ~/.claude/skills/design-summary-html
```

When quality-summary-html's `summary.css` or `summary.js` changes, copy it unchanged to design-summary-html's `assets/base.css` or `assets/base.js`, so that both pages keep the same look. design-summary-html has no automated tests or evals yet. A complete `summary-text.yaml` for a real project is `docs/design/summary-text.yaml` in ride-hailing-app-demo.

## License

MIT
