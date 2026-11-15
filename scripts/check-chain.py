#!/usr/bin/env python3
"""Check that the two chains' glossaries, artifacts.md and report templates still contain what the skills rely on.

  python3 scripts/check-chain.py [CUJ_TO_SLO] [--req-to-design REQ_TO_DESIGN] [--only cuj-to-slo|req-to-design]

CUJ_TO_SLO is the cuj-to-slo repository or an installed skill directory (with the glossary under references/). It
defaults to the CUJ_TO_SLO environment variable, or else cuj-to-slo next to this repository (where `git clone` puts it).
REQ_TO_DESIGN is the req-to-design repository, or an installed skill directory (whose own report template is then the
only one read). It defaults to the REQ_TO_DESIGN environment variable, or else req-to-design next to this repository.
tests/test_build_summary.py and tests/test_build_design_summary.py look in the same places.

What it checks, for quality-summary-html against cuj-to-slo:
  - the Japanese terms in assets/lang/ja.json and the English characteristic names are in the glossary (glossary.md)
  - the English terms in assets/lang/en.json are in the glossary (ignoring case and hyphens; the few the glossary has no
    entry for, in artifacts.md)
  - the YAML keys build_summary.py reads and the English values it translates are in artifacts.md
and for design-summary-html against req-to-design:
  - the Japanese and English terms in its assets/lang/*.json are in the glossary, and the values they translate are in
    artifacts.md
  - the YAML keys build_design_summary.py reads are in artifacts.md (as a key of a schema, or a field named in a table)
  - the English report headings it looks for (H in the script) are headings of the report templates
Each chain is checked when it is found. A chain that is not found is reported as not checked, and the exit status is
then 1, as it is when anything disagrees. After a chain changes, run this first, then update assets/lang/*.json and
the build script to match.
"""
import argparse
import ast
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANG = ROOT / 'skills' / 'quality-summary-html' / 'assets' / 'lang'
DLANG = ROOT / 'skills' / 'design-summary-html' / 'assets' / 'lang'
DSCRIPT = ROOT / 'skills' / 'design-summary-html' / 'scripts' / 'build_design_summary.py'
# Keys build_summary.py reads. When the script reads a new key, add it here too
KEYS = '''system name external_systems role creates_data kgis measure target outcomes statement verb users category data_role
considered exclusion_reason basis basis_note cujs user_goal steps id title status user cuj context_of_use characteristic
failure_scenario numerator denominator narrowed_to observable kpi outcome overlaps_with origin cuj_step traces_to proposal
extends acceptance_criteria model layer applies_to entry_point type source score impact likelihood handling handling_reason
implies_internal conflicts with from kind slo sli target_status window error_budget error_budget_volume policy alerts notify
long_window short_window burn_rate budget_spent_at_alert bad_run_budget_share progress_alert after_miss gate where check audit
mechanism cadence_or_deadline monitor signal notifies function refs vantage elements definition applies_to rules when action'''.split()
# English terms the glossary has no entry for. They are checked against artifacts.md instead
ARTIFACTS_ONLY = set()
# Keys build_design_summary.py reads. When the script reads a new key, add it here too
DKEYS = '''id title status kind statement scenario stimulus environment measure negotiable derived_from priority rank
business difficulty primary conflicts with note technology_constraints project_constraints teams anticipated_changes
stakeholders name owns change expected role concerns basis responsibility functions drivers team as_is stage question
options effect cost chosen rejected option reason rationale gains costs sensitive_points trade_offs assumptions debt what
why_accepted repay_when addresses depends_on parameters value provider consumers operations errors case signal caller_does
spec sli_bindings sli events method entity owner store consistency retention classification scope rules stack elements
language runtime framework libraries repositories holds layers layer covers replaces runs pipeline step when blocks specs
interfaces made how from to trigger'''.split()
# Terms of design-summary-html that the req-to-design glossary has no entry for, as (group, value). They are checked
# against artifacts.md only: classification `other` is a value with a note after it (other: <what it is>)
DESIGN_ARTIFACTS_ONLY = {('classification', 'other')}


def find(base):
    for sub in ('shared', 'references'):
        g, a = base / sub / 'glossary.md', base / sub / 'artifacts.md'
        if g.is_file() and a.is_file():
            return g, a
    return None


def flat(t):
    return re.sub(r'[\s-]+', ' ', t.lower())


def check_quality(gpath, apath):
    glossary, artifacts = gpath.read_text(encoding='utf-8'), apath.read_text(encoding='utf-8')
    ja = json.loads((LANG / 'ja.json').read_text(encoding='utf-8'))['terms']
    en = json.loads((LANG / 'en.json').read_text(encoding='utf-8'))['terms']
    bad = []
    for key, term in ja['characteristic'].items():
        if key not in glossary.lower():
            bad.append('用語集に特性の英語の名前がない: %s' % key)
        if term not in glossary:
            bad.append('用語集に特性の日本語がない: %s → %s' % (key, term))
    for group, table in ja.items():
        if group == 'characteristic':
            continue
        for key, term in table.items():
            if term not in glossary:
                bad.append('用語集に日本語がない: %s.%s → %s' % (group, key, term))
            if not re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(key), artifacts):
                bad.append('artifacts.md に値がない: %s.%s' % (group, key))
    for group, table in en.items():
        for key, term in table.items():
            where = (artifacts, 'artifacts.md') if (group, key) in ARTIFACTS_ONLY else (glossary, '用語集')
            if flat(term) not in flat(where[0]):
                bad.append('%sに英語がない: %s.%s → %s' % (where[1], group, key, term))
    for key in sorted(set(KEYS)):
        if not re.search(r'(?<![\w-])%s:' % re.escape(key), artifacts):
            bad.append('artifacts.md にキーがない: %s' % key)
    return bad


def headings_of(base):
    """The report templates of req-to-design: every skill's in a repository, or the one of an installed skill"""
    paths = sorted(base.glob('skills/*/references/report-template.md')) or sorted(base.glob('references/report-template.md'))
    return paths, '\n'.join(p.read_text(encoding='utf-8') for p in paths)


def design_headings():
    """H of build_design_summary.py: the report headings it looks for, Japanese first, then English"""
    src = DSCRIPT.read_text(encoding='utf-8')
    m = re.search(r'^H = (\{.*?^\})', src, re.S | re.M)
    if not m:
        sys.exit('build_design_summary.py に H が見つからない')
    return ast.literal_eval(m.group(1))


def check_design(gpath, apath, base):
    glossary, artifacts = gpath.read_text(encoding='utf-8'), apath.read_text(encoding='utf-8')
    ja = json.loads((DLANG / 'ja.json').read_text(encoding='utf-8'))['terms']
    en = json.loads((DLANG / 'en.json').read_text(encoding='utf-8'))['terms']
    bad, notes = [], []
    for group, table in ja.items():
        for key, term in table.items():
            if (group, key) not in DESIGN_ARTIFACTS_ONLY and term not in glossary:
                bad.append('用語集に日本語がない: %s.%s → %s' % (group, key, term))
            if not re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(key), artifacts):
                bad.append('artifacts.md に値がない: %s.%s' % (group, key))
    for group, table in en.items():
        for key, term in table.items():
            if (group, key) in DESIGN_ARTIFACTS_ONLY:
                continue
            if flat(term) not in flat(glossary):
                bad.append('用語集に英語がない: %s.%s → %s' % (group, key, term))
    for key in sorted(set(DKEYS)):
        # a key of a schema (key:), or a field named in a table or a comment (`key`, {a, key, b})
        if not re.search(r'(?<![\w-])%s(?=\s*:|`|\s*[,}])' % re.escape(key), artifacts):
            bad.append('artifacts.md にキーがない: %s' % key)
    paths, templates = headings_of(base)
    if not paths:
        notes.append('報告書のテンプレートが見つからないので、見出しは確かめなかった')
    else:
        for key, names in design_headings().items():
            en_names = names[1:]
            if not any(re.search(r'^#{1,4}\s+%s\s*(?:$|[(（:])' % re.escape(n), templates, re.M) for n in en_names):
                bad.append('報告書のテンプレートに見出しがない: %s → %s' % (key, ' / '.join(en_names)))
    return bad, notes


def main():
    ap = argparse.ArgumentParser(description='Check the chains against what the two skills rely on.')
    ap.add_argument('cuj_to_slo', nargs='?', default=os.environ.get('CUJ_TO_SLO', str(ROOT.parent / 'cuj-to-slo')))
    ap.add_argument('--req-to-design', default=os.environ.get('REQ_TO_DESIGN', str(ROOT.parent / 'req-to-design')))
    ap.add_argument('--only', choices=('cuj-to-slo', 'req-to-design'))
    a = ap.parse_args()
    failed = False
    if a.only in (None, 'cuj-to-slo'):
        base = pathlib.Path(a.cuj_to_slo).expanduser()
        found = find(base)
        print('== quality-summary-html と cuj-to-slo')
        if not found:
            print('確かめなかった: 用語集と artifacts.md が %s に見つからない（shared/ か references/ の下を探した）。'
                  'cuj-to-slo の場所を、引数か環境変数 CUJ_TO_SLO で渡す' % base)
            failed = True
        else:
            bad = check_quality(*found)
            print('確かめた先: %s、%s' % found)
            failed |= report(bad)
    if a.only in (None, 'req-to-design'):
        base = pathlib.Path(a.req_to_design).expanduser()
        found = find(base)
        print('== design-summary-html と req-to-design')
        if not found:
            print('確かめなかった: 用語集と artifacts.md が %s に見つからない（shared/ か references/ の下を探した）。'
                  'req-to-design の場所を、--req-to-design か環境変数 REQ_TO_DESIGN で渡す' % base)
            failed = True
        else:
            bad, notes = check_design(*found, base)
            print('確かめた先: %s、%s' % found)
            for n in notes:
                print('注: ' + n)
            failed |= report(bad)
    return 1 if failed else 0


def report(bad):
    if bad:
        print('食い違い: %d 件' % len(bad))
        for b in bad:
            print(' - ' + b)
        return True
    print('食い違い: なし')
    return False


if __name__ == '__main__':
    sys.exit(main())
