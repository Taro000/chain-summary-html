"""Tests for the build script. They need PyYAML; run them from the repository root like this:

  uv run --with pyyaml python3 -m unittest discover -s tests -v
"""
import importlib.util
import os
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
# The cuj-to-slo repository, found the same way scripts/check-chain.py finds it
CHAIN = pathlib.Path(os.environ.get('CUJ_TO_SLO', ROOT.parent / 'cuj-to-slo')).expanduser()

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


def toggle_ids(page):
    return re.findall(r'<details class="tbl" id="([^"]+)"', page)


# Japanese script: kana, kanji, and full-width punctuation and forms
JAPANESE = re.compile(r'[　-ヿ㐀-鿿＀-￯]')


class EnglishTerms:
    """Switches the imported script to English for a block, and back to Japanese after it"""
    def __enter__(self):
        bs.set_lang('en')

    def __exit__(self, *exc):
        bs.set_lang('ja')


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
'''

    def test_section_and_table(self):
        sec = bs.section(self.TEXT, ('検討して加えなかった機能',))
        head, rows = bs.md_tables(sec)[0]
        self.assertEqual(head, ['候補', '対象', '理由'])
        self.assertEqual(rows, [['A | B', 'QIU-01', 'なし']])
        self.assertIsNone(bs.section(self.TEXT, ('対象にしない',)))

    def test_english_sentences(self):
        self.assertEqual(bs.first_sentence('Comes from a law, e.g. the APPI. So it stays.'), 'Comes from a law, e.g. the APPI')
        self.assertEqual(bs.first_sentence('Keeps 99.5% (see v1.2). Next.'), 'Keeps 99.5% (see v1.2)')
        self.assertEqual(bs.split_who('External storage (keeps the submitted files)'), ('External storage', 'keeps the submitted files'))
        self.assertEqual(bs.split_who('外部の決済サービス（支払いと返金を処理する）'), ('外部の決済サービス', '支払いと返金を処理する'))
        self.assertEqual(bs.ids_in('CUJ-01–03 and QR-07–QR-09'), ['CUJ-01', 'CUJ-02', 'CUJ-03', 'QR-07', 'QR-08', 'QR-09'])

    def test_window(self):
        self.assertEqual(bs.window_text('28-day rolling'), '直近 28 日')
        self.assertEqual(bs.exhaust(bs.window_days('28-day rolling'), 14.4), '1.9 日')
        self.assertEqual(bs.exhaust(28, 1), '28 日')
        with EnglishTerms():
            self.assertEqual(bs.window_text('rolling 30 days'), '30-day rolling')
            self.assertEqual(bs.exhaust(28, 14.4), '1.9 days')
            self.assertEqual(bs.exhaust(28, 28), '1 day')


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

    def test_no_build_requirements_and_no_notes(self):
        # The requirements for building the HTML are not on the page. Nothing is missing, so there are no notes either
        self.assertNotIn('HTML作成時の要件', self.page)
        self.assertNotIn('t-req', self.page)
        self.assertNotIn('t-notes', self.page)

    def test_japanese_page(self):
        self.assertIn('<html lang="ja">', self.page)
        self.assertIn('BIZ+UDPGothic', self.page)
        self.assertIn('言語: ja（資料から判定）', self.run1.stdout)

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
        self.assertIn('食い違い: 1 件', self.run1.stdout)
        self.assertRegex(self.run1.stdout, r'QIU-03: .*YAML だけ: FR-08')
        # QIU-01, 04 and 05 are covered in two rows each, which together list the FRs the YAML traces to them
        issues = [ln for ln in self.run1.stdout.splitlines() if '「利用時の品質要求の対応」' in ln]
        self.assertEqual([bs.ids_in(ln, 'QIU') for ln in issues], [['QIU-03']])

    def test_compares_every_report_table(self):
        self.assertIn('YAML と突き合わせた報告書の表: 利用時の品質要求の対応、CUJ の手順ごとの機能、外部品質から導いた内部品質、割り当て',
                      self.run1.stdout)
        self.assertIn('報告書に見つからず省いたもの: なし', self.run1.stdout)
        self.assertIn('報告書に見つからず突き合わせなかった表: なし', self.run1.stdout)
        self.assertNotIn('用語集にない値', self.run1.stdout)

    def test_data_producers(self):
        # Users who produce data, and the external systems with creates_data: true, named by their role
        dq = toggle(self.page, 't-dq')
        self.assertEqual(re.findall(r'<span class="who">([^<]+)</span>', dq), ['生徒', '講師', '外部のストレージ'])
        self.assertIn('外部のシステム（EXT-01）', dq)

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
        self.assertIn('99.5%（確認済み）', toggle(self.page, 't-slo'))
        self.assertIn('99%（仮）', toggle(self.page, 't-slo'))
        self.assertEqual(re.findall(r'<span class="slo-state">([^<]+)</span>', self.page), ['確認済み', '仮'])
        sli = toggle(self.page, 't-sli')
        self.assertEqual(heads(sli), ['SLI', '良いイベント ÷ 有効なイベント', '見る位置'])
        self.assertIn('システムの境界', sli)
        self.assertIn('データ', sli)


class PartialChain(unittest.TestCase):
    def test_stage2_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(docs_of('homework-service-stage2'), pathlib.Path(d) / 'p.html')
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertNotIn('id="sec-3"', page)
        self.assertNotIn('id="sec-4"', page)
        self.assertEqual(heads(toggle(page, 't-trace')), ['CUJ', 'QIU', 'FR'])
        self.assertEqual(bs.self_check(page), [])
        # The notes are the last toggle, closed, and say which stages are missing
        tids = re.findall(r'<details class="tbl" id="([^"]+)"([^>]*)>', page)
        self.assertEqual(tids[-1], ('t-notes', ''))
        self.assertIn('この版の注記', toggle(page, 't-notes'))
        self.assertIn('この版にない段階: 第 3 段階、第 4 段階', toggle(page, 't-notes'))
        self.assertIn('href="#t-notes"', page.split('</nav>')[0])


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

    def test_compared_table_missing(self):
        # A table that is only compared is not on the page, so its absence goes to the report, not to the notes
        with tempfile.TemporaryDirectory() as d:
            docs = pathlib.Path(d) / 'docs' / 'quality'
            shutil.copytree(docs_of('homework-service-full'), docs)
            r2 = docs / '2-functional-requirements.md'
            r2.write_text(r2.read_text(encoding='utf-8').replace('## CUJ の手順ごとの機能', '## 手順の一覧'), encoding='utf-8')
            r = build(docs, docs / 'summary.html')
            page = (docs / 'summary.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('報告書に見つからず突き合わせなかった表: CUJ の手順ごとの機能（2-functional-requirements.md）', r.stdout)
        self.assertNotIn('この版の注記', page)

    def test_allocation_heading_variants(self):
        # The stage 4 template's "Allocation" is written 「割り当て」 or 「配分」
        with tempfile.TemporaryDirectory() as d:
            docs = pathlib.Path(d) / 'docs' / 'quality'
            shutil.copytree(docs_of('homework-service-full'), docs)
            r4 = docs / '4-nfr-slo.md'
            r4.write_text(r4.read_text(encoding='utf-8').replace('## 割り当て', '## 配分'), encoding='utf-8')
            r = build(docs, docs / 'summary.html')
            page = (docs / 'summary.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('報告書に見つからず突き合わせなかった表: なし', r.stdout)
        self.assertIn('ストレージの事業者の障害そのもの', toggle(page, 't-trace'))


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
            text = r2.read_text(encoding='utf-8')
            # Replace the project's own table (up to the next heading) with this one
            text, n = re.subn(r'## CUJ の手順ごとの機能\n.*?(?=\n## )', self.TABLE.strip() + '\n', text, flags=re.S)
            self.assertEqual(n, 1)
            r2.write_text(text, encoding='utf-8')
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


class EnglishPage(unittest.TestCase):
    """The same fictional project written in English. The page and the report follow the language of the outputs"""
    case = 'homework-service-full-en'

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.run1 = build(docs_of(cls.case), cls.tmp / 'a.html')
        cls.run2 = build(docs_of(cls.case), cls.tmp / 'b.html')
        cls.page = (cls.tmp / 'a.html').read_text(encoding='utf-8') if cls.run1.returncode == 0 else ''
        cls.ja = build(docs_of('homework-service-full'), cls.tmp / 'ja.html')
        cls.ja_page = (cls.tmp / 'ja.html').read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_builds_and_is_deterministic(self):
        self.assertEqual(self.run1.returncode, 0, self.run1.stderr + self.run1.stdout)
        self.assertEqual((self.tmp / 'a.html').read_bytes(), (self.tmp / 'b.html').read_bytes())
        self.assertEqual(bs.self_check(self.page), [])

    def test_english_throughout(self):
        self.assertIn('<html lang="en">', self.page)
        self.assertIn('<title>Homework submission service quality</title>', self.page)
        self.assertEqual(JAPANESE.findall(self.page), [])
        self.assertIn('IBM+Plex+Sans', self.page)
        self.assertNotIn('BIZ+UDPGothic', self.page)

    def test_same_tables_as_the_japanese_page(self):
        self.assertEqual(toggle_ids(self.page), toggle_ids(self.ja_page))
        self.assertEqual(self.page.count('<tr'), self.ja_page.count('<tr'))
        self.assertEqual(sorted(re.findall(r'href="#([^"]+)"', self.page)), sorted(re.findall(r'href="#([^"]+)"', self.ja_page)))

    def test_headings(self):
        self.assertEqual(heads(toggle(self.page, 't-trace')), ['CUJ', 'QIU', 'FR', 'QR', 'NFR / SLI'])
        with_basis = [t for t in toggle_ids(self.page) if 'Basis' in heads(toggle(self.page, t))]
        self.assertEqual(with_basis, ['t-users', 't-cuj'])
        self.assertIn('Score', heads(toggle(self.page, 't-prio')))
        self.assertIn('Traceability by CUJ', toggle(self.page, 't-trace'))

    def test_report_in_english(self):
        out = self.run1.stdout
        self.assertEqual(JAPANESE.findall(out), [])
        self.assertIn('Language: en (detected from the outputs)', out)
        self.assertIn('Inconsistencies: 1', out)
        self.assertRegex(out, r'QIU-03: .*YAML only: FR-08')
        self.assertIn('Not found in the reports, not compared: none', out)

    def test_reads_the_english_reports(self):
        # In 「CUJ-01–03」 (an en dash), 03 is read as CUJ-03, as in 「CUJ-01〜03」
        self.assertEqual(re.findall(r'href="#(CUJ-\d+)"', toggle(self.page, 't-excl')), ['CUJ-01', 'CUJ-03', 'CUJ-04'])
        dq = toggle(self.page, 't-dq')
        self.assertEqual(re.findall(r'<span class="who">([^<]+)</span>', dq), ['Student', 'Teacher', 'External storage'])
        self.assertIn('External system (EXT-01)', dq)
        # The first sentence of an entry point's source, and a handling reason without its leading handling name
        self.assertIn('<span class="ent-src">Act on the Protection of Personal Information</span>', self.page)
        self.assertIn('<span class="note">teachers write the notification text themselves</span>', toggle(self.page, 't-prio'))

    def test_entry_column(self):
        self.assertEqual(entry_cell(self.page, 't-pq', 'Confidentiality'), ['QR-09'])
        self.assertEqual(entry_cell(self.page, 't-dq', 'Recoverability'), ['QR-13'])

    def test_stage4_parts(self):
        self.assertIn('1.9 days', toggle(self.page, 't-burn'))
        self.assertIn('99.5% (Confirmed)', toggle(self.page, 't-slo'))
        self.assertIn('99% (Provisional)', toggle(self.page, 't-slo'))
        self.assertIn('28-day rolling', toggle(self.page, 't-slo'))
        self.assertEqual(heads(toggle(self.page, 't-sli'))[-1], 'Vantage')
        self.assertIn('System boundary', toggle(self.page, 't-sli'))


class LanguageChoice(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(bs.detect_lang(['生徒は期限までに提出できる', 'QIU-01', 'inferred', 'satisfaction > trust']), 'ja')
        self.assertEqual(bs.detect_lang(['Students can submit by the deadline', 'QIU-01', '生徒']), 'en')
        # Outputs in another language get the English page; Chinese has no kana
        self.assertEqual(bs.detect_lang(['学生可以在截止日期前提交作业']), 'en')
        self.assertEqual(bs.detect_lang(['Los estudiantes entregan la tarea a tiempo']), 'en')

    def test_lang_option_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(docs_of('homework-service-full'), pathlib.Path(d) / 'p.html', '--lang', 'en')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('<html lang="en">', page)
        self.assertIn('Language: en (set with --lang)', r.stdout)
        self.assertIn('Inconsistencies: 1', r.stdout)
        # Labels are English; the content stays in the language it was written in
        self.assertIn('Traceability by CUJ', page)
        self.assertIn('期限までに提出が終わる', page)

    def test_input_error_before_the_language_is_known(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(pathlib.Path(d), pathlib.Path(d) / 'p.html')
        self.assertEqual(r.returncode, 2)
        self.assertIn('No context.yaml', r.stderr)
        self.assertIn('context.yaml がない', r.stderr)


class LanguageFiles(unittest.TestCase):
    def test_same_keys_and_placeholders(self):
        ja, en = bs.LANG_DATA['ja'], bs.LANG_DATA['en']
        self.assertEqual(set(ja), set(en))
        self.assertEqual(set(ja['terms']), set(en['terms']))
        for g in ja['terms']:
            self.assertEqual(set(ja['terms'][g]), set(en['terms'][g]), g)
        self.assertEqual(set(ja['text']), set(en['text']))

        def ph(t):
            return sorted(set(re.findall(r'\{(\w+)\}', t)))
        for k in ja['text']:
            self.assertEqual(ph(ja['text'][k]), ph(en['text'][k]), k)

    def test_every_key_is_used_and_exists(self):
        src = SCRIPT.read_text(encoding='utf-8')
        used = set(re.findall(r"\b(?:T|die_t)\(\s*'(\w+)'", src)) | set(re.findall(r"pending\.append\(\('(\w+)'", src))
        # Keys the script builds at run time
        built = {'stage_title_1', 'stage_title_2', 'stage_title_3', 'stage_title_4', 'note_unplaced_product', 'note_unplaced_data',
                 'lang_detected', 'lang_given', 'days'}
        keys = set(bs.LANG_DATA['en']['text'])
        self.assertEqual((used | built) - keys, set(), 'used but not in the language files')
        self.assertEqual(keys - used - built, set(), 'in the language files but never used')


@unittest.skipUnless(docs_of('ride-hailing-full').is_dir(), '配車アプリの成果物がない')
class RideHailing(unittest.TestCase):
    def test_full_chain(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(docs_of('ride-hailing-full'), pathlib.Path(d) / 'p.html')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('トレーサビリティ: QIU の行 32、入口 8', r.stdout)
        # The outputs of a replay with cuj-to-slo 0.3.0. The stage 2 report names FR-42 under the coverage table and FR-45
        # and FR-53 in its notes, not in the FR column, so those QIUs disagree. The QIUs covered in several rows do not
        coverage = [bs.ids_in(ln, 'QIU')[0] for ln in r.stdout.splitlines() if '「利用時の品質要求の対応」' in ln]
        self.assertEqual(coverage, ['QIU-%02d' % i for i in list(range(1, 7)) + list(range(8, 21)) + [33]])
        self.assertNotIn('「CUJ の手順ごとの機能」', r.stdout)
        # The stage 4 allocation table is headed 「配分」, and its out-of-scope notes reach the traceability table
        self.assertIn('報告書に見つからず突き合わせなかった表: なし', r.stdout)
        self.assertNotIn('用語集にない値', r.stdout)
        self.assertEqual(set(re.findall(r'<span class="nfr-item none" data-tip="([^"]+)">範囲外</span>', toggle(page, 't-trace'))),
                         {'登録した内容が実際と一致すること', '定めの中身を読んで確かめること'})  # QR-20 and QR-62
        self.assertEqual(entry_cell(page, 't-pq', '機密性'), ['QR-57', 'QR-60'])
        self.assertEqual(entry_cell(page, 't-pq', '機能正確性'), ['QR-61', 'QR-63'])
        self.assertEqual(entry_cell(page, 't-dq', '標準適合性'), ['QR-59', 'QR-62'])
        dq = toggle(page, 't-dq')
        self.assertIn('<span class="who">外部の決済サービス</span>', dq)
        self.assertIn('<span class="who">外部の地図のサービス</span>', dq)
        self.assertEqual(bs.self_check(page), [])
        self.assertIn('<title>配車サービスの品質</title>', page)


@unittest.skipUnless((CHAIN / 'shared' / 'glossary.md').is_file(), 'cuj-to-slo がない: %s（環境変数 CUJ_TO_SLO で場所を渡せる）' % CHAIN)
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

    def test_detects_a_renamed_english_term(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(CHAIN / 'shared', pathlib.Path(d) / 'shared')
            g = pathlib.Path(d) / 'shared' / 'glossary.md'
            g.write_text(g.read_text(encoding='utf-8').replace('minimum line', 'minimum bar'), encoding='utf-8')
            r = self.run_check(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Minimum line', r.stdout)


if __name__ == '__main__':
    unittest.main()
