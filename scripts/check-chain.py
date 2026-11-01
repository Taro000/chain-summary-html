#!/usr/bin/env python3
"""Check that the cuj-to-slo glossary and artifacts.md still contain what this skill relies on.

  python3 scripts/check-chain.py [CUJ_TO_SLO]

CUJ_TO_SLO is the cuj-to-slo repository or an installed skill directory (with the glossary under references/).
It defaults to the CUJ_TO_SLO environment variable, or else quality-kpi-skills next to this repository.
What it checks:
  - the Japanese terms in assets/terms.ja.json and the English characteristic names are in the glossary (glossary.md)
  - the YAML keys build_summary.py reads and the English values it translates are in artifacts.md
If anything disagrees, it lists the problems and exits with 1. After cuj-to-slo changes, run this first,
then update terms.ja.json and the build script to match.
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TERMS = ROOT / 'skills' / 'quality-summary-html' / 'assets' / 'terms.ja.json'
# Keys build_summary.py reads. When the script reads a new key, add it here too
KEYS = '''system name data_producers kgis measure target outcomes statement verb users category data_role considered
exclusion_reason basis basis_note cujs user_goal steps id title status changelog date user cuj context_of_use characteristic
failure_scenario numerator denominator narrowed_to observable kpi outcome overlaps_with origin cuj_step traces_to proposal
extends acceptance_criteria model layer applies_to entry_point type source score impact likelihood handling handling_reason
implies_internal conflicts with from kind slo sli target_status window error_budget error_budget_volume policy alerts notify
long_window short_window burn_rate budget_spent_at_alert bad_run_budget_share progress_alert after_miss gate where check audit
mechanism cadence_or_deadline monitor signal notifies function refs method elements definition applies_to rules when action'''.split()
# Term tables whose English keys are not checked (their keys are not YAML values)
NOT_ENUM = {'_about', 'characteristic', 'product_model', 'data_model'}


def find(base):
    for sub in ('shared', 'references'):
        g, a = base / sub / 'glossary.md', base / sub / 'artifacts.md'
        if g.is_file() and a.is_file():
            return g, a
    sys.exit('用語集と artifacts.md が見つからない: %s（shared/ か references/ の下を探した）' % base)


def main():
    base = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('CUJ_TO_SLO', ROOT.parent / 'quality-kpi-skills')).expanduser()
    gpath, apath = find(base)
    glossary, artifacts = gpath.read_text(encoding='utf-8'), apath.read_text(encoding='utf-8')
    terms = json.loads(TERMS.read_text(encoding='utf-8'))
    bad = []
    for en, ja in terms['characteristic'].items():
        if en not in glossary.lower():
            bad.append('用語集に特性の英語の名前がない: %s' % en)
        if ja not in glossary:
            bad.append('用語集に特性の日本語がない: %s → %s' % (en, ja))
    for group, table in terms.items():
        if group in NOT_ENUM:
            continue
        for en, ja in table.items():
            if ja not in glossary:
                bad.append('用語集に日本語がない: %s.%s → %s' % (group, en, ja))
            if not re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(en), artifacts):
                bad.append('artifacts.md に値がない: %s.%s' % (group, en))
    for key in sorted(set(KEYS)):
        if not re.search(r'(?<![\w-])%s:' % re.escape(key), artifacts):
            bad.append('artifacts.md にキーがない: %s' % key)
    print('確かめた先: %s、%s' % (gpath, apath))
    if bad:
        print('食い違い: %d 件' % len(bad))
        for b in bad:
            print(' - ' + b)
        return 1
    print('食い違い: なし')
    return 0


if __name__ == '__main__':
    sys.exit(main())
