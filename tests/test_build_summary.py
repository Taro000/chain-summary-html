"""Tests for the build script. They need PyYAML; run them from the repository root like this:

  uv run --with pyyaml python3 -m unittest discover -s tests -v
"""
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills' / 'quality-summary-html'
SCRIPT = SKILL / 'scripts' / 'build_summary.py'
EVALS = SKILL / 'evals'
CHAIN = ROOT.parent / 'quality-kpi-skills'

spec = importlib.util.spec_from_file_location('build_summary', SCRIPT)
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)


def docs_of(case):
    return EVALS / case / 'files' / 'docs' / 'quality'


def build(docs, out, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(docs), '--out', str(out)] + list(extra),
                          capture_output=True, text=True, timeout=120)


def toggle(page, tid):
    m = re.search(r'<details class="tbl" id="%s"[^>]*>.*?</details>' % tid, page, re.S)
    return m.group(0) if m else ''


def heads(block):
    return re.findall(r'<th scope="col"[^>]*>(?:<button[^>]*>)?([^<]+)', block)


def entry_cell(page, tid, sub):
    """QRs in the matrix's 「入口」 (entry) column, on the row whose sub-characteristic
    (characteristic, for data quality) is sub"""
    for row in re.findall(r'<tr>(.*?)</tr>', toggle(page, tid), re.S):
        if 'class="mx-sub">%s<' % sub in row:
            m = re.search(r'<td class="mx-c mx-ent">(.*?)</td>', row, re.S)
            return re.findall(r'>(QR-\d+)<', m.group(1)) if m else None
    return None


class Ids(unittest.TestCase):
    def test_range_and_list(self):
        self.assertEqual(bs.ids_in('QR-36〜42・47・48'), ['QR-%02d' % i for i in (36, 37, 38, 39, 40, 41, 42, 47, 48)])

    def test_range_with_prefix(self):
        self.assertEqual(bs.ids_in('QR-01〜QR-03'), ['QR-01', 'QR-02', 'QR-03'])

    def test_three_digits(self):
        self.assertEqual(bs.ids_in('QR-100、101 と QR-99'), ['QR-100', 'QR-101', 'QR-99'])

    def test_no_false_continuation(self):
        self.assertEqual(bs.ids_in('QR-01、2026 年。FR-01, 2 件'), ['QR-01', 'FR-01'])

    def test_prefix_and_boundary(self):
        self.assertEqual(bs.ids_in('QIU-01、KPI-01', 'KPI'), ['KPI-01'])
        self.assertEqual(bs.ids_in('NFR-01 と XQR-02'), ['NFR-01'])


class Markdown(unittest.TestCase):
    TEXT = '''# 機能要件: 例

## 検討して加えなかった機能（参考）

| 候補 | 対象 | 理由 |
|---|---|---|
| A \\| B | QIU-01 | なし |

## 次へ
主なデータ: 記録、ファイル（添付）、レポート。
'''

    def test_section_and_table(self):
        sec = bs.section(self.TEXT, ('検討して加えなかった機能',))
        head, rows = bs.md_tables(sec)[0]
        self.assertEqual(head, ['候補', '対象', '理由'])
        self.assertEqual(rows, [['A | B', 'QIU-01', 'なし']])
        self.assertIsNone(bs.section(self.TEXT, ('対象にしない',)))

    def test_line_value(self):
        line = bs.line_value(self.TEXT, ('主なデータ',))
        self.assertEqual(bs.split_top(bs.first_sentence(line)), ['記録', 'ファイル（添付）', 'レポート'])

    def test_window(self):
        self.assertEqual(bs.window_ja('28-day rolling'), '直近 28 日')
        self.assertEqual(bs.exhaust(bs.window_days('28-day rolling'), 14.4), '1.9 日')
        self.assertEqual(bs.exhaust(28, 1), '28 日')


class Page(unittest.TestCase):
    """The fictional project (stages 1 to 4)"""
    case = 'homework-service-full'

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.run1 = build(docs_of(cls.case), cls.tmp / 'a.html')
        cls.run2 = build(docs_of(cls.case), cls.tmp / 'b.html')
        cls.page = (cls.tmp / 'a.html').read_text(encoding='utf-8') if cls.run1.returncode == 0 else ''

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_builds_and_is_deterministic(self):
        self.assertEqual(self.run1.returncode, 0, self.run1.stderr + self.run1.stdout)
        self.assertEqual((self.tmp / 'a.html').read_bytes(), (self.tmp / 'b.html').read_bytes())

    def test_links_resolve(self):
        self.assertEqual(bs.self_check(self.page), [])

    def test_traceability_first_and_open(self):
        main = self.page.split('<main>', 1)[1]
        self.assertTrue(main.lstrip().startswith('<section id="sec-trace"'))
        trace = toggle(self.page, 't-trace')
        self.assertIn(' open>', trace.split('<summary>')[0])
        self.assertEqual(heads(trace), ['CUJ', 'QIU', 'FR', 'QR', 'NFR / SLI'])
        for q in ('QIU-01', 'QIU-02', 'QIU-03', 'QIU-04', 'QIU-05'):
            self.assertIn('href="#%s"' % q, trace)
        self.assertNotIn('QIU-06', trace)  # retired

    def test_every_other_table_is_closed(self):
        tids = re.findall(r'<details class="tbl" id="([^"]+)"([^>]*)>', self.page)
        self.assertGreater(len(tids), 15)
        self.assertEqual([t for t, a in tids if 'open' in a], ['t-trace'])
        self.assertEqual(tids[-1][0], 't-req')

    def test_basis_only_for_users_and_cujs(self):
        with_basis = [t for t in re.findall(r'<details class="tbl" id="([^"]+)"', self.page) if '根拠' in heads(toggle(self.page, t))]
        self.assertEqual(with_basis, ['t-users', 't-cuj'])

    def test_excluded_columns(self):
        self.assertNotIn('既存', heads(toggle(self.page, 't-fr')))
        self.assertNotIn('持ち込んだ人', toggle(self.page, 't-ext'))
        self.assertNotIn('重なり', heads(toggle(self.page, 't-formula')))
        for h in ('測定点', '見えないもの'):
            self.assertNotIn(h, heads(toggle(self.page, 't-sli')))

    def test_sortable_priority_table(self):
        prio = toggle(self.page, 't-prio')
        self.assertIn('data-key="qr"', prio)
        self.assertIn('data-key="score"', prio)

    def test_light_mode_only_and_self_contained(self):
        self.assertNotIn('prefers-color-scheme', self.page)
        self.assertNotRegex(self.page, r'<script[^>]+src=')
        self.assertEqual(re.findall(r'<link rel="stylesheet" href="([^"]+)"', self.page)[0][:31], 'https://fonts.googleapis.com/cs')

    def test_reports_the_planted_inconsistency(self):
        self.assertIn('QIU-03', self.run1.stdout)
        self.assertRegex(self.run1.stdout, r'YAML だけ: FR-08')

    def test_reports_tables_it_could_not_compare(self):
        self.assertIn('報告書に見つからず突き合わせなかった表: CUJ の手順ごとの機能（2-functional-requirements.md）', self.run1.stdout)

    def test_entry_column_before_cujs(self):
        pq = toggle(self.page, 't-pq')
        self.assertIn('mx-ent', re.findall(r'<th scope="col" class="(mx-h[^"]*)"', pq)[0])
        self.assertIn('入口 1', pq.split('</summary>')[0])
        self.assertEqual(entry_cell(self.page, 't-pq', '機密性'), ['QR-09'])
        self.assertEqual(entry_cell(self.page, 't-pq', '可用性'), [])
        self.assertEqual(entry_cell(self.page, 't-dq', '回復性'), ['QR-13'])

    def test_stage4_parts(self):
        self.assertIn('id="EBP-01"', self.page)
        self.assertIn('id="EBP-02"', self.page)
        self.assertIn('1.9 日', toggle(self.page, 't-burn'))
        self.assertIn('NFR-02', toggle(self.page, 't-dl'))
        self.assertIn('99.5%', self.page)


class PartialChain(unittest.TestCase):
    def test_stage2_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(docs_of('homework-service-stage2'), pathlib.Path(d) / 'p.html')
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertNotIn('id="sec-3"', page)
        self.assertNotIn('id="sec-4"', page)
        self.assertEqual(heads(toggle(page, 't-trace')), ['CUJ', 'QIU', 'FR'])
        self.assertIn('この版にない段階', page)
        self.assertEqual(bs.self_check(page), [])


class MissingInputs(unittest.TestCase):
    def test_no_context(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(pathlib.Path(d), pathlib.Path(d) / 'p.html')
        self.assertEqual(r.returncode, 2)
        self.assertIn('context.yaml', r.stderr)

    def test_report_only_table_missing(self):
        with tempfile.TemporaryDirectory() as d:
            docs = pathlib.Path(d) / 'docs' / 'quality'
            shutil.copytree(docs_of('homework-service-full'), docs)
            r1 = docs / '1-quality-in-use.md'
            r1.write_text(r1.read_text(encoding='utf-8').replace('### 対象にしない', '### 対象外の特性'), encoding='utf-8')
            r = build(docs, docs / 'summary.html')
            page = (docs / 'summary.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('id="t-excl"', page)
        self.assertIn('報告書に見つからず省いたもの: 対象にしない', r.stdout)
        self.assertIn('この版の注記', page)


class StepTable(unittest.TestCase):
    """Compares stage 2's 「CUJ の手順ごとの機能」 (functions by CUJ step) with each FR's cuj and cuj_step"""
    TABLE = '''
## CUJ の手順ごとの機能

| CUJ | 手順 | FR | 注記 |
|---|---|---|---|
| CUJ-01 課題の提出 | 課題を開く | （なし） | |
| | ファイルを 添付する | FR-06 | CUJ の欄が空なら上の行の CUJ。空白の違いは見ない |
| CUJ-01 | 提出する | FR-01 | FR-02 が抜けている |
| CUJ-02 採点と返却 | 提出を開く | FR-07 | 廃止した FR |
| CUJ-02 | 返却する | FR-03 | FR-08 が抜けている |
| CUJ-03 提出の失敗の調査 | ログを調べる | FR-04 | context.yaml にない手順 |
| CUJ-04 月次の提出状況の確認 | 未提出の生徒を確かめる | FR-05 | YAML では「レポートを開く」 |
| （どの CUJ にもない） | | FR-01 | CUJ のない行は比べない |
'''

    def test_positions(self):
        with tempfile.TemporaryDirectory() as d:
            docs = pathlib.Path(d) / 'docs' / 'quality'
            shutil.copytree(docs_of('homework-service-full'), docs)
            r2 = docs / '2-functional-requirements.md'
            r2.write_text(r2.read_text(encoding='utf-8') + self.TABLE, encoding='utf-8')
            r = build(docs, docs / 'summary.html')
        self.assertEqual(r.returncode, 0, r.stderr)
        got = [ln for ln in r.stdout.splitlines() if '「CUJ の手順ごとの機能」' in ln]
        want = [
            'FR-07: 2-functional-requirements.md の「CUJ の手順ごとの機能」に載っているが、YAML では廃止',
            '手順「ログを調べる」が、CUJ-03 の手順（context.yaml）にない',
            'FR-02: 2-functional-requirements.md の「CUJ の手順ごとの機能」の位置と、FR の YAML の cuj と cuj_step が違う（報告書: 載っていない、YAML: CUJ-01「提出する」）',
            'FR-05: 2-functional-requirements.md の「CUJ の手順ごとの機能」の位置と、FR の YAML の cuj と cuj_step が違う（報告書: CUJ-04「未提出の生徒を確かめる」、YAML: CUJ-04「レポートを開く」）',
            'FR-08: 2-functional-requirements.md の「CUJ の手順ごとの機能」の位置と、FR の YAML の cuj と cuj_step が違う（報告書: 載っていない、YAML: CUJ-02「返却する」）',
        ]
        for w in want:
            self.assertTrue(any(w in ln for ln in got), '%s がない:\n%s' % (w, '\n'.join(got)))
        self.assertEqual(len(got), len(want), '\n'.join(got))
        self.assertIn('YAML と突き合わせた報告書の表: 利用時の品質要求の対応、CUJ の手順ごとの機能', r.stdout)


@unittest.skipUnless(docs_of('ride-hailing-full').is_dir(), '配車アプリの成果物がない')
class RideHailing(unittest.TestCase):
    def test_full_chain(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(docs_of('ride-hailing-full'), pathlib.Path(d) / 'p.html')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('トレーサビリティ: QIU の行 28、入口 9', r.stdout)
        self.assertEqual(len(re.findall(r'YAML だけ: FR-52', r.stdout)), 4)
        # In the step table only FR-52 disagrees. The pickup row, the CUJ-11 to 13 rows and FRs without a CUJ are not reported
        steps = [ln for ln in r.stdout.splitlines() if '「CUJ の手順ごとの機能」' in ln]
        self.assertEqual(len(steps), 1, '\n'.join(steps))
        self.assertIn('FR-52: ', steps[0])
        self.assertIn('（報告書: 載っていない、YAML: CUJ-06「配車依頼を選ぶ」）', steps[0])
        self.assertIn('報告書に見つからず突き合わせなかった表: なし', r.stdout)
        self.assertEqual(entry_cell(page, 't-pq', '機密性'), ['QR-38', 'QR-41'])
        self.assertEqual(entry_cell(page, 't-pq', 'インテグリティ'), ['QR-47'])
        self.assertEqual(entry_cell(page, 't-dq', '機密性'), ['QR-39'])
        self.assertEqual(bs.self_check(page), [])
        self.assertIn('<title>配車アプリの品質</title>', page)


@unittest.skipUnless((CHAIN / 'shared' / 'glossary.md').is_file(), 'cuj-to-slo がない')
class ChainCheck(unittest.TestCase):
    def run_check(self, base):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check-chain.py'), str(base)], capture_output=True, text=True)

    def test_current_chain_matches(self):
        r = self.run_check(CHAIN)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_detects_a_renamed_term(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(CHAIN / 'shared', pathlib.Path(d) / 'shared')
            g = pathlib.Path(d) / 'shared' / 'glossary.md'
            g.write_text(g.read_text(encoding='utf-8').replace('最低限守る線', '最低限の線'), encoding='utf-8')
            r = self.run_check(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn('最低限守る線', r.stdout)


if __name__ == '__main__':
    unittest.main()
