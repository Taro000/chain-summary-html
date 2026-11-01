# quality-summary-html

[日本語](README.ja.md)

A Claude skill that builds one quality summary page in HTML (`docs/quality/summary.html`) from the outputs that the four [cuj-to-slo](https://github.com/Taro000/cuj-to-slo) skills write to `docs/quality/`.

The page exists so that people can understand a system's quality efficiently. It opens with a CUJ-by-CUJ traceability table (CUJ → QIU → FR → QR → NFR / SLI), followed by the tables of stages 1 to 4 in toggles. IDs in the tables link to their rows, and the page adds an impact × likelihood chart, product quality and data quality matrices, and SLO cards.

A bundled script renders the page from the YAML items, so every project, and every re-run of a stage, gets a page with the same layout. The page itself is in Japanese.

## Requirements

- `docs/quality/` written by the cuj-to-slo skills (at least stage 1). If stages 2 to 4 are missing, the page leaves them out.
- Python 3.9 or later and PyYAML. With uv, `uv run --with pyyaml` brings PyYAML along.

## Installation

Install with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
# Into the current project (asks which agents to install for)
npx skills add Taro000/quality-summary-html
# For all your projects, Claude Code only, without prompts
npx skills add Taro000/quality-summary-html -g -a claude-code -y
```

Or place `skills/quality-summary-html/` in Claude Code's skills directory yourself:

```bash
# For all your projects
cp -R skills/quality-summary-html ~/.claude/skills/
# To use it while editing this repository, link instead of copying
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html
```

Either way, `evals/` comes along. It holds test outputs (about 1.4 MB) and can be deleted if you only use the skill.

## Usage

Ask Claude something like "summarize the outputs in docs/quality as HTML", and it uses this skill. You can also run the script directly:

```bash
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality
# Change the output path and the title
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py docs/quality --out /tmp/summary.html --title 配車アプリの品質
```

Besides writing the page, the script prints to standard output the inconsistencies between the outputs (report tables that differ from the YAML, references to retired items, and so on), the report-only tables it could not find and left out, and the report tables it could not find and so did not compare with the YAML.

## Layout

```
skills/quality-summary-html/
├── SKILL.md                    instructions for Claude
├── scripts/build_summary.py    the generator (builds the tables with the YAML as the source of truth)
├── assets/                     look (summary.css, summary.js) and the term table (terms.ja.json)
├── references/page-spec.md     page specification: tables and columns, sources, what is left out, how to change it
└── evals/                      three test cases (ride-hailing app; a fictional homework submission service, all stages and up to stage 2)
scripts/check-chain.py          checks for drift from the cuj-to-slo glossary and artifacts.md
tests/                          automated tests, and a script that builds the fictional project's outputs
```

## Checking

```bash
# Automated tests
uv run --with pyyaml python3 -m unittest discover -s tests -v
# Whether the cuj-to-slo glossary and artifacts.md still have what this skill relies on
# (defaults to quality-kpi-skills next to this repository)
python3 scripts/check-chain.py [the cuj-to-slo repository, or an installed skill's directory]
# Rebuild the fictional project's outputs
uv run --with pyyaml python3 tests/make_homework_fixture.py
```

If the cuj-to-slo terms or YAML shapes change, `check-chain.py` reports the drift. Then update `assets/terms.ja.json` and the generator to match.

## Decisions

- Tables are built from the YAML (cuj-to-slo's artifacts.md). Report headings and column names are written by the model on every run, so only the tables that exist only in the reports (not targeted, functions considered and not added, and so on) are looked up in the reports, and they are left out when not found.
- The page is in Japanese and light mode only.
- Do not edit the generated page by hand. To change it, edit the script and `assets/`, then rebuild.
- `evals/ride-hailing-full` is a copy of `docs/quality` in ride-hailing-app-demo (commit ba28153).

## License

MIT. See [LICENSE](LICENSE).
