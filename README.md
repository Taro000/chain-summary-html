# chain-summary-html

English | [日本語](README.ja.md)

Two agent skills that each turn a skill chain's outputs into one HTML page, with the same layout:

| Skill | Reads | Writes |
|---|---|---|
| [quality-summary-html](#quality-summary-html) | [cuj-to-slo](https://github.com/Taro000/cuj-to-slo)'s `docs/quality/` | `docs/quality/summary.html` |
| [design-summary-html](#design-summary-html) | [req-to-design](https://github.com/Taro000/req-to-design)'s `docs/design/` (stages 1 to 3) | `docs/design/summary.html` |

## Install

```sh
npx skills add Taro000/chain-summary-html                          # asks which skills and agents
npx skills add Taro000/chain-summary-html -a claude-code -g -y     # both, Claude Code, global, no prompts
npx skills add Taro000/chain-summary-html -s design-summary-html   # one skill
```

Requires Python 3.9+ and PyYAML (`uv run --with pyyaml` works). Each skill's `evals/` (1.7 MB and 4.5 MB) can be deleted if you only use the skills.

## Common behavior

- A bundled script builds the whole page from the outputs; nothing is written by hand, so every run gives the same layout. To change the page, change the script and `assets/`.
- The YAML items are the source of truth. When a report disagrees with them, the page follows the YAML and the skill reports where.
- After building, the skill reports what the page could not show: inconsistencies (with the stage whose re-run fixes them) and report sections it could not find.
- The labels follow the outputs' language: Japanese if kana make up a tenth or more of the letters, otherwise English. `--lang ja|en` overrides the labels only.
- Light mode only. Every run overwrites `summary.html`; commit it with the docs it was built from.
- The skills never edit the YAML or the reports, and never commit unless asked.

Full details (every table, its columns and sources, what is left out and why) are in each skill's `references/page-spec.md`.

## quality-summary-html

Follow each CUJ to the requirements and SLOs that serve it (CUJ → QIU → FR → QR → NFR / SLI) on one page instead of four reports and a YAML file per item.

| Section | Contents |
|---|---|
| Traceability | Item counts per stage, and one table from each CUJ to its NFRs and SLIs, grouped by user (requirements not from users last) |
| Stage 1 | Business requirements, users, CUJs, quality-in-use requirements, failure scenarios, non-targets, formulas |
| Stage 2 | Functional requirements, functions not added |
| Stage 3 | Impact × likelihood chart, quality matrices (characteristic × CUJ), priorities, quality requirements |
| Stage 4 | SLOs, SLIs, error budget policies, burn-rate alerts, other NFRs |

Only the traceability table is open; the rest sit in closed toggles. IDs link to their rows and show titles on hover. Stages not yet run are left out. Rationale, measurement points and blind spots stay in the YAML and the reports. The header shows the docs' git commit and marks uncommitted changes. When SLO targets are provisional, the skill says the page shows proposals.

**Use:** run cuj-to-slo at least through stage 1 (`docs/quality/context.yaml` must exist), then ask "Summarize docs/quality as an HTML page" or, after a re-run, "Rebuild summary.html". Without `context.yaml`, the skill points you to `cuj-to-quality-in-use`.

## design-summary-html

Go from the ranked architecture drivers to the elements, decisions, flows and data on one page instead of three long reports. Same layout as quality-summary-html, orange theme.

| Section | Contents |
|---|---|
| Route | Item counts by stage, drivers to data entities |
| Stage 1 | Driver ranking (open), inputs, stakeholders, scenarios, constraints, principles, conflicts, feasibility |
| Stage 2 | Elements, the five views, one card per decision, threat model, walkthroughs, debt, running cost |
| Stage 3 | Conventions, interfaces, error contracts, sequence diagrams, latency budgets, failure paths, ER diagram, measurement points, acceptance-criteria trace |

The page is for grasping the design quickly:

- Tables with items come from the YAML; the reports are read only for Mermaid diagrams and the tables no item holds. Report prose is not shown, and a section with neither table nor diagram is left out (the skill says so).
- Every text is cut to its first sentence without bracketed asides, and columns that only justify or trace a text are dropped. Revision-history notes are removed.
- Mermaid loads from a CDN, so viewing needs network access.

**Use:** run req-to-design at least through stage 1 (`docs/design/drv/` must exist), then ask "Summarize docs/design as an HTML page" or "Rebuild the design summary".

## Maintaining

```
skills/<skill>/
├── SKILL.md                 instructions for the agent
├── scripts/                 the generator
├── assets/                  CSS, JS, labels per language (lang/ja.json, lang/en.json)
├── references/page-spec.md  page specification
└── evals/                   four test cases
scripts/check-chain.py       checks for drift from cuj-to-slo's glossary and artifacts.md
tests/                       automated tests, fixture builders, eval graders
```

```sh
# run a generator directly (--out, --title, --lang are optional)
uv run --with pyyaml python3 skills/quality-summary-html/scripts/build_summary.py path/to/docs/quality
uv run --with pyyaml python3 skills/design-summary-html/scripts/build_design_summary.py path/to/docs/design

# tests (including byte-identical output for identical input)
uv run --with pyyaml python3 -m unittest discover -s tests -v

# rebuild the fictional homework service's eval outputs
uv run --with pyyaml python3 tests/make_homework_fixture.py
uv run --with pyyaml python3 tests/make_homework_design_fixture.py

# grade design-summary-html eval runs from the skill-creator workflow
uv run --with pyyaml python3 tests/grade_design_eval.py skills/design-summary-html-workspace/iteration-1

# after cuj-to-slo changes (default path: $CUJ_TO_SLO, else ../cuj-to-slo)
python3 scripts/check-chain.py [path/to/cuj-to-slo]

# use your working copy as an installed skill
ln -s "$PWD/skills/quality-summary-html" ~/.claude/skills/quality-summary-html
```

Generator exit codes: 0 page written (even with inconsistencies), 1 written but failed its own check (duplicate ids or broken links), 2 outputs unreadable.

- When `check-chain.py` reports drift, update `assets/lang/*.json` and the generator.
- When quality-summary-html's `summary.css` or `summary.js` changes, copy it unchanged to design-summary-html's `assets/base.css` / `base.js`. The orange theme lives in `design.css`.
- `ride-hailing-full` evals are copies from ride-hailing-app-demo: `docs/quality` at ba28153, `docs/design` and `docs/quality` at b63c7a1 (without files the skill does not read).

## License

MIT
