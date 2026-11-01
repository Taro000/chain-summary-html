# quality-summary-html

English | [日本語](README.ja.md)

An agent skill that turns the outputs the four [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) skills write to `docs/quality/` into one HTML page, `docs/quality/summary.html`. Instead of reading four reports and one YAML file per item, you can follow each CUJ to the requirements and SLOs that serve it (CUJ → QIU → FR → QR → NFR / SLI) on a single page.

## What the page shows

| Section | Contents |
|---|---|
| Traceability | A diagram of item counts per stage, then one table that follows each CUJ through its QIUs, FRs and QRs to NFRs and SLIs, grouped by user. Requirements that do not come from users (laws, standards, security risk analysis, development policies) form the last group. |
| Stage 1 | Business requirements, users, CUJs, quality-in-use requirements, failure scenarios and measures, what is not targeted, and each formula counted two ways (quality-in-use measure and KPI) |
| Stage 2 | Functional requirements, functions considered and not added |
| Stage 3 | An impact × likelihood chart, product quality and data quality matrices (characteristic × CUJ), the priority table, handling by CUJ, internal quality derived from external quality, quality requirements, requirements that do not come from users |
| Stage 4 | SLO cards, SLOs, SLIs, error budget policies, burn-rate alerts, deadline SLOs, other non-functional requirements |

Only the traceability table is open; every other table sits in a closed toggle. Each ID links to its row and shows the item's title on hover. Stages not run yet are left out, and a note at the bottom of the page says which.

To stay quick to read, the page leaves out, among other things, the basis of most items, the rationale for SLO numbers, measurement points and blind spots. Read those in the YAML and the reports. Light mode only.

## Install

```sh
# into the current project (asks which agents to install for)
npx skills add Taro000/quality-summary-html

# for Claude Code only, available in every project, without prompts
npx skills add Taro000/quality-summary-html -a claude-code -g -y
```

The skill runs a Python script, so it needs Python 3.9 or later and PyYAML. With [uv](https://docs.astral.sh/uv/), `uv run --with pyyaml` brings PyYAML along.

`evals/` (test outputs, about 1.7 MB) is installed with the skill. Delete it if you only use the skill.

## Use

1. Run the cuj-to-slo skills, at least stage 1, so that `docs/quality/context.yaml` exists.
2. "Summarize docs/quality as an HTML page."
3. After re-running a stage: "Rebuild summary.html."

The skill runs the bundled script, which builds every table from the YAML items, so every project and every re-run gets the same layout. It then tells you what the page could not show: inconsistencies between the outputs (a report table that disagrees with the YAML, a reference to a retired item), each with the stage whose re-run fixes it, and the report-only tables it could not find. When SLO targets are provisional or quality requirements are still drafts, it says that the page shows proposals, not agreed targets.

The page follows the language of the outputs: Japanese for Japanese outputs, English for any other language. Only the labels change; the content stays as written. You can also ask for the labels in the other language, another title or another output path.

## Output

```
docs/quality/
├── context.yaml  qiu/ … ebp/              YAML items: the source of every table
├── 1-quality-in-use.md … 4-nfr-slo.md     reports: stage titles and the few tables only they have
└── summary.html                           the page this skill writes
```

The page's header shows the git commit of the docs it was built from, and marks uncommitted changes. Every run overwrites `summary.html`; commit it together with the docs it was built from.

## What the skill will not do

- Write or patch the page by hand. A hand edit drifts from the YAML and is lost on the next run. To change the page, change the script and `assets/`; the change applies to every project that uses the skill.
- Edit the YAML or the reports to clear an inconsistency. The page reports the chain's state; fixing it belongs to the stage that owns the item.
- Prefer a report over the YAML. The YAML items are the source of truth, as cuj-to-slo's artifacts.md says. A report-only table whose heading is not found is left out, and the skill says so.
- Build a page from other documents when the chain has not been run. Without `context.yaml`, it points you to `cuj-to-quality-in-use` instead.
- Commit, unless you ask.

## Maintaining

```
skills/quality-summary-html/
├── SKILL.md                   instructions for the agent
├── scripts/build_summary.py   the generator
├── assets/                    summary.css, summary.js, and the wording per language (lang/ja.json, lang/en.json)
├── references/page-spec.md    every table with its columns and sources, what is left out and why, how to change the page
└── evals/                     four test cases
scripts/check-chain.py         checks for drift from the cuj-to-slo glossary and artifacts.md
tests/                         automated tests, and the script that builds the fictional service's outputs
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

## License

MIT
