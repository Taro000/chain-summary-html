"""Tests for design-summary-html's build script and its eval grader. They need PyYAML; run them from the repository root:

  uv run --with pyyaml python3 -m unittest discover -s tests -v

The inputs are the eval cases in skills/design-summary-html/evals/: the fictional homework submission service (written
by tests/make_homework_design_fixture.py, in Japanese and English) and a copy of ride-hailing-app-demo's outputs.
"""
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import os

ROOT = pathlib.Path(__file__).resolve().parent.parent
# req-to-design, for scripts/check-chain.py: REQ_TO_DESIGN, else next to this repository
CHAIN = pathlib.Path(os.environ.get('REQ_TO_DESIGN', ROOT.parent / 'req-to-design')).expanduser()
SKILL = ROOT / 'skills' / 'design-summary-html'
SCRIPT = SKILL / 'scripts' / 'build_design_summary.py'
EVALS = SKILL / 'evals'
JAPANESE = re.compile(r'[　-ヿ㐀-鿿＀-￯]')
sys.path.insert(0, str(ROOT / 'tests'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m          # dataclasses look the module up while it loads
    spec.loader.exec_module(m)
    return m


bd = load('build_design_summary', SCRIPT)
gd = load('grade_design_eval', ROOT / 'tests' / 'grade_design_eval.py')


def design_of(case):
    return EVALS / case / 'files' / 'docs' / 'design'


def build(design, out, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(design), '--out', str(out)] + list(extra),
                          capture_output=True, text=True, timeout=180)


def toggle(page, tid):
    m = re.search(r'<details class="tbl" id="%s"[^>]*>.*?</details>(?=<details class="tbl"|</section>|\s*</main>)' % tid, page, re.S)
    return m.group(0) if m else ''


def toggle_ids(page):
    return re.findall(r'<details class="tbl" id="([^"]+)"', page)


def visible(page):
    return re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>|<pre class="mmd-src".*?</pre>', '', page, flags=re.S))


class Case(unittest.TestCase):
    """Builds one eval case twice, and grades the first page as a run (the script's report stands in for the final report)"""
    case = None

    @classmethod
    def setUpClass(cls):
        if cls.case is None:
            raise unittest.SkipTest('base class')
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        out = cls.tmp / 'iteration' / cls.case / 'script' / 'outputs'
        out.mkdir(parents=True)
        cls.run1 = build(design_of(cls.case), out / 'summary.html')
        cls.run2 = build(design_of(cls.case), cls.tmp / 'b.html')
        cls.page = (out / 'summary.html').read_text(encoding='utf-8') if cls.run1.returncode == 0 else ''
        (out / 'report.md').write_text(cls.run1.stdout, encoding='utf-8')
        cls.passed, cls.total = gd.grade(out.parent, cls.case)
        cls.grading = json.loads((out.parent / 'grading.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_builds_and_is_deterministic(self):
        self.assertEqual(self.run1.returncode, 0, self.run1.stderr + self.run1.stdout)
        self.assertEqual((self.tmp / 'iteration' / self.case / 'script' / 'outputs' / 'summary.html').read_bytes(),
                         (self.tmp / 'b.html').read_bytes())

    def test_passes_every_grader(self):
        failed = [(e['text'][:60], e['evidence']) for e in self.grading['expectations'] if not e['passed']]
        self.assertEqual(failed, [])


class HomeworkFull(Case):
    case = 'homework-service-full'

    def test_japanese_page(self):
        self.assertIn('<html lang="ja">', self.page)
        self.assertIn('<title>課題提出サービスの設計</title>', self.page)
        self.assertIn('言語: ja（資料から判定）', self.run1.stdout)

    def test_reports_the_planted_mismatch_and_what_it_left_out(self):
        out = self.run1.stdout
        self.assertIn('食い違い: 1 件', out)
        self.assertIn('技術的負債: YAML にあって報告書にない DEC-06', out)
        self.assertIn('通し確認: CUJ-03 提出の失敗の調査（報告書に表がない）', out)
        self.assertIn('遅延の予算: NFR-02（報告書に表がない）', out)
        self.assertIn('履歴の注記を削った文: 7 件', out)
        self.assertIn('ページに載せない項目: 未確認の仮定 1 件、品質チェーンへの要求 未回答 1 件・回答済み 0 件', out)
        self.assertIn('旧い形式: なし', out)

    def test_yaml_over_the_report(self):
        self.assertIn('保護者の画面と生徒の画面が一つのアプリにまとまる', toggle(self.page, 't-debt2'))   # DEC-06's debt
        self.assertNotIn('DRV-10', toggle(self.page, 't-constraint'))  # retired
        self.assertIn('個人情報（生徒の答案）', toggle(self.page, 't-data'))

    def test_report_prose_is_left_out(self):
        self.assertNotIn('t-structure', self.page)
        self.assertNotIn('apps/server/', self.page)                  # the directory tree
        self.assertNotIn('ホップの表にするほどのホップはない', self.page)
        self.assertNotIn('呼ぶ側が待つ最悪', self.page)               # the timeouts
        self.assertNotIn('generated:', visible(self.page))

    def test_budget_chart_and_threat_links(self):
        b = toggle(self.page, 't-budget')
        self.assertIn('id="b-NFR-06"', b)
        self.assertIn('class="bud"', b)
        self.assertIn('和 1.5 秒、余り 1.5 秒', b)                    # the report's 「余裕」 and 「計」 rows
        self.assertNotIn('b-NFR-02', b)
        threat = toggle(self.page, 't-threat')
        self.assertIn('data-links="flow"', threat)
        # F5 shares its row with F4, and gets an anchor of its own; the count is of the flows, not the rows
        self.assertEqual(re.findall(r'id="(flow-F\d)"', threat), ['flow-F1', 'flow-F2', 'flow-F3', 'flow-F4', 'flow-F5', 'flow-F6'])
        self.assertIn('<span class="t-count">流れ 6</span>', threat)

    def test_walkthroughs_labelled_with_a_colon(self):
        walk = toggle(self.page, 't-walk')
        self.assertEqual(re.findall(r'<tr class="grp" id="([^"]+)"', walk), ['w-CUJ-01', 'w-CUJ-02', 'w-CUJ-04'])

    def test_shared_error_contracts_shown_once(self):
        err = toggle(self.page, 't-err')
        self.assertEqual(err.count('401 UNAUTHENTICATED'), 1)
        self.assertIn('共通 2', err)

    def test_technical_policy(self):
        self.assertIn('id="sec-2b"', self.page)
        pol = toggle(self.page, 't-pol')
        self.assertEqual(re.findall(r'<details class="item" id="(POL-\d+)"', pol), ['POL-01', 'POL-02', 'POL-03', 'POL-04', 'POL-05', 'POL-06'])
        self.assertIn('ランタイム', pol)
        self.assertIn('Hono', pol)
        self.assertIn('テスト戦略とゲート', pol)                      # the scope's glossary term
        self.assertEqual(pol.count('<figure class="mmd"'), 2)         # the repositories and the pipeline
        self.assertNotIn('互いに import しない', pol)                 # the rules are counted, not shown
        self.assertEqual(re.findall(r'<tr id="(DEC-\d+)"', toggle(self.page, 't-dec2b')), ['DEC-07', 'DEC-08'])

    def test_open_hand_offs_only(self):
        self.assertEqual(re.findall(r'<tr id="(HND-\d+)"', toggle(self.page, 't-hnd2')), ['HND-02'])
        self.assertEqual(re.findall(r'<tr id="(HND-\d+)"', toggle(self.page, 't-hnd2b')), ['HND-04'])
        self.assertEqual(re.findall(r'<tr id="(HND-\d+)"', toggle(self.page, 't-hnd3')), ['HND-03'])
        self.assertNotIn('<tr id="HND-01"', self.page)                # decided
        self.assertIn('実装', toggle(self.page, 't-hnd3'))

    def test_sli_bindings_and_header(self):
        sli = toggle(self.page, 't-sli')
        self.assertEqual(re.findall(r'<tr[^>]*><th scope="row"[^>]*>.*?(SLI-\d+)', sli), ['SLI-01', 'SLI-02'])
        self.assertIn('更新 2026-09-25', self.page)                  # the newest 「更新」 of the reports
        self.assertNotIn('>仕様<', toggle(self.page, 't-ifc'))        # no spec written by hand: no column

    def test_texts_cut_to_their_gist(self):
        """Every text shows its first sentence without asides, and what only justifies or traces it is left out"""
        self.assertEqual(len(re.findall(r'<th scope="col"', toggle(self.page, 't-rank'))), 5)   # no reasons for the levels
        self.assertNotIn('出どころ', toggle(self.page, 't-premise'))
        self.assertNotIn('出どころ', toggle(self.page, 't-constraint'))
        decd = toggle(self.page, 't-decd')
        self.assertIn('締め切り前の集中で、サーバーがファイルを受けると詰まる', decd)            # DEC-02's rationale
        self.assertNotIn('署名付き URL なら', decd)
        self.assertNotIn('設計上の値', decd)                     # in the design parameters' table, not in the cards
        self.assertNotIn('提出の画面を開いてから送るまでの時間', self.page)   # the basis of a value
        data = toggle(self.page, 't-data')
        self.assertIn('提出の記録と受領を一つのトランザクションで書く', data)
        self.assertNotIn('受領の番号', data)
        self.assertNotIn('下書きを保存し', toggle(self.page, 't-elm'))

    def test_diagram_labels_cut_to_their_gist(self):
        src = ''.join(re.findall(r'<pre class="mmd-src" hidden>(.*?)</pre>', self.page, re.S))
        self.assertIn('A-&gt;&gt;P: POST /api/v1/submissions\n', src)
        self.assertIn('署名付き URL（15 分）', src)                # a bracket that holds a quantity stays
        self.assertIn('s[&quot;提出&quot;] --&gt; r[&quot;夜間のバッチ&quot;]', src)
        self.assertIn('draft --&gt; submitted: 提出\n', src)


class HomeworkEnglish(Case):
    case = 'homework-service-full-en'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ja = build(design_of('homework-service-full'), cls.tmp / 'ja.html')
        cls.ja_page = (cls.tmp / 'ja.html').read_text(encoding='utf-8')

    def test_english_throughout(self):
        self.assertIn('<html lang="en">', self.page)
        self.assertIn('<title>Homework submission service design</title>', self.page)
        self.assertEqual(JAPANESE.findall(visible(self.page)), [])
        self.assertEqual(JAPANESE.findall(self.page), [])
        self.assertIn('IBM+Plex+Sans', self.page)

    def test_same_page_as_the_japanese_one(self):
        self.assertEqual(toggle_ids(self.page), toggle_ids(self.ja_page))
        self.assertEqual(self.page.count('<tr'), self.ja_page.count('<tr'))
        self.assertEqual(sorted(re.findall(r'href="#([^"]+)"', self.page)), sorted(re.findall(r'href="#([^"]+)"', self.ja_page)))

    def test_report_in_english(self):
        out = self.run1.stdout
        self.assertEqual(JAPANESE.findall(out), [])
        self.assertIn('Language: en (detected from the outputs)', out)
        # the questions and answers under "## Decisions" are not the decisions table: one mismatch, the planted one
        self.assertIn('Mismatches: 1\n  - Technical debt: in the YAML but not in the report: DEC-06\n', out)
        self.assertIn('Texts with revision notes removed: 7', out)

    def test_english_terms_and_ids(self):
        self.assertIn('Technology constraint: External service', toggle(self.page, 't-premise'))
        self.assertIn('Non-negotiable', toggle(self.page, 't-constraint'))
        self.assertIn('All operations', toggle(self.page, 't-err'))
        self.assertIn('Testing', toggle(self.page, 't-pol'))
        self.assertIn('Implementation', toggle(self.page, 't-hnd3'))
        # 「FR-01、02、06」 is written "FR-01, 02, 06" and 02 still links to FR-02's tooltip
        self.assertRegex(toggle(self.page, 't-elm'), r'FR-01</span>, <span class="id dead" data-ref="FR-02">02')


class HomeworkStage2(Case):
    case = 'homework-service-stage2'

    def test_only_stages_1_and_2(self):
        self.assertIn('id="sec-2"', self.page)
        self.assertNotIn('id="sec-2b"', self.page)
        self.assertNotIn('id="sec-3"', self.page)
        notes = toggle(self.page, 't-notes')
        self.assertIn('第 2b 段階（技術方針）の成果物はまだない', notes)
        self.assertIn('第 3 段階（概略設計）の成果物はまだない', notes)
        self.assertEqual(re.findall(r'<tr id="(HND-\d+)"', toggle(self.page, 't-hnd1')), ['HND-01'])   # open until stage 3 runs


@unittest.skipUnless(design_of('ride-hailing-full').is_dir(), '配車アプリの成果物がない')
class RideHailing(Case):
    case = 'ride-hailing-full'

    def test_real_project(self):
        out = self.run1.stdout
        self.assertIn('項目: DRV 35 · DEC 46（第 2 段階 27 · 第 2b 段階 7 · 第 3 段階 12） · ELM 12 · POL 6 · IFC 25 · DAT 27 · 未決定の申し送り 3', out)
        self.assertIn('食い違い: なし', out)
        self.assertIn('突き合わせなかった表: なし', out)
        self.assertIn('節: なし', out)
        self.assertIn('表: なし', out)
        self.assertIn('用語集にない値: なし', out)
        self.assertIn('旧い形式: なし', out)
        self.assertEqual(self.page.count('<figure class="mmd"'), 67)
        self.assertIn('<title>配車サービスの設計</title>', self.page)
        self.assertIn('id="b-NFR-07"', self.page)
        self.assertNotIn('FND-', visible(self.page))
        # stage 4 (the detailed design of two components) is not on the page
        self.assertNotIn('<tr id="DEC-47"', self.page)
        self.assertNotRegex(self.page, r'<tr id="MOD-')

    def test_grader_catches_a_false_mismatch(self):
        run = self.tmp / 'iteration' / self.case / 'false' / 'outputs'
        run.mkdir(parents=True)
        shutil.copyfile(self.tmp / 'iteration' / self.case / 'script' / 'outputs' / 'summary.html', run / 'summary.html')
        for report, ok in (('食い違い: 2 件\n  - 設計の決定（第 2 段階）: YAML にあって報告書にない DEC-01、DEC-02\n', False),
                           ('**Warnings, mismatches first**\n- Mismatches: none\n', True)):
            (run / 'report.md').write_text(report, encoding='utf-8')
            gd.grade(run.parent, self.case)
            g = json.loads((run.parent / 'grading.json').read_text(encoding='utf-8'))
            e = next(e for e in g['expectations'] if 'claims no disagreement' in e['text'])
            self.assertEqual(e['passed'], ok, report)

    def test_choices_of_the_real_reports(self):
        """The real 0.3.0 reports label the CUJ walkthroughs with plain lines, name the hops ホップ / 余裕 / 計, share
        a threat row between F9 and F10, and write no operation in the error cases"""
        self.assertEqual(len(re.findall(r'<tr class="grp"', toggle(self.page, 't-walk'))), 18)
        self.assertIn('id="flow-F10"', toggle(self.page, 't-threat'))
        self.assertEqual(toggle(self.page, 't-budget').count('class="bud"'), 2)
        self.assertNotIn('>操作<', toggle(self.page, 't-err'))
        self.assertIn('DEC-02', toggle(self.page, 't-dec'))
        self.assertIn('iOS 16.4 以降の iPhone', toggle(self.page, 't-dec'))   # 「18.4 より前の版」 is a product version


class Graders(unittest.TestCase):
    """The grader fails pages and reports that miss what a statement asks for"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.good = cls.tmp / 'good.html'
        r = build(design_of('homework-service-full'), cls.good)
        cls.report = r.stdout

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def grade(self, page, report=None, case='homework-service-full'):
        d = self.tmp / 'run' / case / 'x'
        if d.parent.parent.exists():
            shutil.rmtree(d.parent.parent)
        (d / 'outputs').mkdir(parents=True)
        (d / 'outputs' / 'summary.html').write_text(page, encoding='utf-8')
        (d / 'outputs' / 'report.md').write_text(self.report if report is None else report, encoding='utf-8')
        gd.grade(d, case)
        g = json.loads((d / 'grading.json').read_text(encoding='utf-8'))
        return {pathlib.Path(n).stem.split('-', 1)[1] for n, e in zip(sorted((EVALS / case / 'graders').glob('*.md')), g['expectations'])
                if not e['passed']}

    def test_good_page_passes(self):
        self.assertEqual(self.grade(self.good.read_text(encoding='utf-8')), set())

    def test_failures_are_caught(self):
        page = self.good.read_text(encoding='utf-8')
        self.assertIn('reports-dec06', self.grade(page, report='Done. The page is at docs/design/summary.html.'))
        self.assertIn('no-revision-notes', self.grade(page.replace('</td>', ' FND-01</td>', 1)))
        self.assertIn('threat-links', self.grade(page.replace('data-links="flow"', '').replace('id="flow-F', 'id="row-F')))
        self.assertIn('toggles', self.grade(page.replace('<details class="tbl" id="t-premise"', '<details class="tbl" id="t-premise" open')))
        rows = re.findall(r'<tr id="rank-[^"]+">.*?</tr>', page, re.S)
        swapped = page.replace(rows[1], '\0').replace(rows[2], rows[1]).replace('\0', rows[2])
        self.assertIn('rank-first', self.grade(swapped))
        self.assertIn('budget-chart', self.grade(page.replace('class="bud"', 'class="x"').replace('<svg', '<g').replace('width:', 'w:')))
        self.assertIn('decision-cards', self.grade(page.replace('選んだ', '○')))
        self.assertIn('gist-only', self.grade(page.replace('</td>', ' 署名付き URL なら、ファイルはサーバーを通らない</td>', 1)))
        debt = re.search(r'<details class="tbl" id="t-debt2".*?</details>', page, re.S).group(0)
        self.assertIn('follows-yaml-dec06', self.grade(page.replace(debt, '')))
        self.assertIn('technical-policy', self.grade(page.replace('POL-0', 'XOL-0')))
        self.assertIn('hand-offs', self.grade(page.replace('HND-03', 'HND-99')))
        walk = re.search(r'<details class="tbl" id="t-walk".*?</details>', page, re.S).group(0)
        self.assertIn('walkthrough-rows', self.grade(page.replace(walk, '')))
        self.assertIn('header-date', self.grade(page.replace('更新 2026-09-25', '')))
        self.assertIn('markers-hidden', self.grade(page.replace('</td>', ' &lt;!-- generated: decisions --&gt;</td>', 1)))

    def test_english_page_check(self):
        en = build(design_of('homework-service-full-en'), self.tmp / 'en.html')
        page = (self.tmp / 'en.html').read_text(encoding='utf-8')
        self.assertEqual(self.grade(page, en.stdout, 'homework-service-full-en'), set())
        self.assertIn('english-page', self.grade(page.replace('Ranking table', '順位表'), en.stdout, 'homework-service-full-en'))


class LanguageChoice(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(bd.detect_lang(['提出を確定する', 'DRV-01', 'inferred']), 'ja')
        self.assertEqual(bd.detect_lang(['Confirm the submission', 'DRV-01', '提出']), 'en')
        self.assertEqual(bd.detect_lang(['确认提交作业']), 'en')        # Chinese has no kana: English labels

    def test_lang_option_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(design_of('homework-service-full'), pathlib.Path(d) / 'p.html', '--lang', 'en')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Language: en (set with --lang)', r.stdout)
        self.assertIn('<html lang="en">', page)
        self.assertIn('Ranking table', page)
        # labels are English; the content stays Japanese, and its revision notes are removed by the Japanese rules
        self.assertIn('締め切り前の集中でも提出を受け付け続ける', page)
        self.assertIn('Texts with revision notes removed: 7', r.stdout)

    def test_input_errors_in_both_languages(self):
        with tempfile.TemporaryDirectory() as d:
            r = build(pathlib.Path(d), pathlib.Path(d) / 'p.html')
        self.assertEqual(r.returncode, 2)
        self.assertIn('No design outputs', r.stderr)
        self.assertIn('設計の成果物がない', r.stderr)


class LanguageFiles(unittest.TestCase):
    def test_same_keys_and_placeholders(self):
        ja, en = bd.LANG_DATA['ja'], bd.LANG_DATA['en']
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
        used = set(re.findall(r"""\b(?:T|die_t)\(\s*['"](\w+)['"](?!\s*\+)""", src))   # not 「T('k_' + kind)」
        built = ({'k_' + k for k in bd.REPORT_KINDS} | {f'stage_title_{n}' for n in bd.STAGES} | {'lang_detected', 'lang_given'}
                 | {'w_report_draft', 'w_report_waiting', 'w_later_missing', 'finding', 'assumption', 'request', 'module'}
                 | {h for _, cols in bd.POL_TABLES.values() for _, h in cols})
        js = {k for k in bd.LANG_DATA['en']['text'] if k.startswith('js_')}
        design_js = (SKILL / 'assets' / 'design.js').read_text(encoding='utf-8')
        for k in js:
            self.assertIn('UI.' + k[3:], design_js, k)
        keys = set(bd.LANG_DATA['en']['text'])
        self.assertEqual((used | built) - keys, set(), 'used but not in the language files')
        self.assertEqual(keys - used - built - js, set(), 'in the language files but never used')


class Cleaning(unittest.TestCase):
    def ja(self, s):
        bd.SRC['lang'] = 'ja'
        return bd.clean_text(s)[0]

    def en(self, s):
        bd.SRC['lang'] = 'en'
        return bd.clean_text(s)[0]

    def test_japanese(self):
        self.assertEqual(self.ja('原則 DRV-09 に従う。前の版は、受領を先に示していた（FND-01）。'), '原則 DRV-09 に従う。')
        self.assertEqual(self.ja('記録が欠けうる（DRV-03 版 2）'), '記録が欠けうる（DRV-03）')
        self.assertEqual(self.ja('ブラウザの失敗がつながらない（質問 4、FND-02）'), 'ブラウザの失敗がつながらない（質問 4）')
        self.assertEqual(self.ja('失敗したら前の版に戻す。'), '失敗したら前の版に戻す。')       # a product version is kept
        self.assertEqual(self.ja('18.4 より前の版では自動ロックを切る'), '18.4 より前の版では自動ロックを切る')
        self.assertEqual(self.ja('押さえを解く（FND-13）。'), '押さえを解く。')

    def test_english(self):
        self.assertEqual(self.en('It follows principle DRV-09. The previous version showed the receipt first (FND-01).'),
                         'It follows principle DRV-09.')
        self.assertEqual(self.en('Records can go missing (DRV-03 version 2)'), 'Records can go missing (DRV-03)')
        self.assertEqual(self.en('Browser failures are not linked (question 4, FND-02)'), 'Browser failures are not linked (question 4)')
        self.assertEqual(self.en('Added in the second re-run. A CUJ-03 investigation starts from one ID.'),
                         'A CUJ-03 investigation starts from one ID.')
        # product wordings are kept: a job is re-run, an image is rolled back to the previous version
        for s in ('The nightly job is re-run for every unfinished day.', 'On failure, roll back to the previous version.',
                  'Use e.g. a signed URL. It expires in 15 minutes.', 'Node.js version 20 is used.'):
            self.assertEqual(self.en(s), s)

    def tearDown(self):
        bd.SRC['lang'] = 'ja'


class Gist(unittest.TestCase):
    """Every text on the page is its gist: the first sentence, without bracketed asides (a quantity stays) and without
    the full stop. Diagrams lose only label text, never syntax"""

    def test_japanese(self):
        g = bd.gist
        self.assertEqual(g('上位の DRV-01 はどの案でも満たせ、DRV-06（2 人と費用）で一つのサーバーの案が勝つ。'),
                         '上位の DRV-01 はどの案でも満たせ、DRV-06 で一つのサーバーの案が勝つ')
        self.assertEqual(g('状態の変化を T_deliver（5 秒）以内に届ける。追いかけは 1 秒ごと'), '状態の変化を T_deliver（5 秒）以内に届ける')
        self.assertEqual(g('TC-07（デモの回だけ）は「配備する」と決める'), 'TC-07 は「配備する」と決める')   # the space comes back
        self.assertEqual(g('「確かめています。」と示す（DEC-52）。取り消せる'), '「確かめています。」と示す')
        self.assertEqual(g('サーバー(Cloud Run)で動かす'), 'サーバーで動かす')
        self.assertEqual(g('`f(a)` を呼ぶ（DEC-01）。'), '`f(a)` を呼ぶ')
        self.assertEqual(g('（未定）'), '（未定）')                                   # all aside: kept as written

    def test_english(self):
        g = bd.gist
        self.assertEqual(g('In the rush (DRV-01), a server would choke. With signed URLs, files never pass through it.'),
                         'In the rush, a server would choke')
        self.assertEqual(g('Use e.g. a signed URL (15 min). It expires.'), 'Use e.g. a signed URL (15 min)')
        self.assertEqual(g('Call watchPosition() and f(x) as before'), 'Call watchPosition() and f(x) as before')
        self.assertEqual(g('Timeout is 0.5 s. Then retry.'), 'Timeout is 0.5 s')
        self.assertEqual(g('Is it idempotent? Yes.'), 'Is it idempotent?')

    def test_diagrams(self):
        seq = '\n'.join(['sequenceDiagram', '  participant S as ELM-04 サーバー（Cloud Run）', '  rect rgb(240, 240, 240)',
                         '  S->>D: 書く（DAT-06）。二度目は弾く', '  alt 押さえた（200）', '  Note over S: 待つ（30 秒）', '  end', '  end'])
        self.assertEqual(bd.gist_mermaid(seq, 'sequenceDiagram').split('\n'),
                         ['sequenceDiagram', '  participant S as ELM-04 サーバー', '  rect rgb(240, 240, 240)', '  S->>D: 書く',
                          '  alt 押さえた', '  Note over S: 待つ（30 秒）', '  end', '  end'])
        flow = '\n'.join(['flowchart LR', '  db[("ELM-07 データベース（Turso）")]', '  a -->|"F1 操作（HTTPS）"| b',
                          '  c -->|読む（毎日）| d', '  style a fill:#fff,stroke:#333', '  e[箱（補足）] --> f(("丸 (round)"))'])
        self.assertEqual(bd.gist_mermaid(flow, 'flowchart').split('\n'),
                         ['flowchart LR', '  db[("ELM-07 データベース")]', '  a -->|"F1 操作"| b', '  c -->|読む| d',
                          '  style a fill:#fff,stroke:#333', '  e[箱] --> f(("丸"))'])
        state = '\n'.join(['stateDiagram-v2', '  state "手配の処理中（booking）" as booking', '  a --> b: 許諾（30 秒）。後で見直す',
                           '  b --> c : 取り消し（無料）'])
        self.assertEqual(bd.gist_mermaid(state, 'stateDiagram-v2').split('\n'),
                         ['stateDiagram-v2', '  state "手配の処理中" as booking', '  a --> b: 許諾（30 秒）', '  b --> c : 取り消し'])
        er = '\n'.join(['erDiagram', '  A ||--o{ B : "持つ（複数）"', '  A }|..|{ C : 使う（毎日）', '    string id PK "ID（ULID）"'])
        self.assertEqual(bd.gist_mermaid(er, 'erDiagram').split('\n'),
                         ['erDiagram', '  A ||--o{ B : "持つ"', '  A }|..|{ C : 使う', '    string id PK "ID"'])


class Ids(unittest.TestCase):
    def test_lists_and_ranges(self):
        bd.set_lang('ja')
        self.assertEqual(bd.ids_text(['FR-01', 'FR-02', 'FR-03', 'FR-05', 'DRV-01']), 'FR-01〜03、05、DRV-01')
        self.assertEqual(bd.ids_text(['DRV-33', 'DRV-04', 'DRV-21'], sort=False), 'DRV-33、04、21')
        bd.set_lang('en')
        self.assertEqual(bd.ids_text(['FR-01', 'FR-02', 'FR-03', 'FR-05', 'DRV-01']), 'FR-01–03, 05, DRV-01')
        bd.set_lang('ja')

    def test_links_in_both_languages(self):
        ctx = bd.Ctx()
        ctx.own = {'DRV-01', 'DRV-02', 'DRV-14'}
        for s in ('DRV-01、02', 'DRV-01, 02', 'DRV-01〜14', 'DRV-01–14'):
            self.assertEqual(len(re.findall(r'href="#DRV-', bd.link_ids(s, ctx))), 2, s)
        self.assertNotIn('DRV-10', bd.link_ids('DRV-01, 10 seconds', ctx))


class Inputs(unittest.TestCase):
    def test_yaml_alone_and_an_old_text_file(self):
        with tempfile.TemporaryDirectory() as d:
            design = pathlib.Path(d) / 'docs' / 'design'
            shutil.copytree(design_of('homework-service-full'), design)
            for md in design.glob('*.md'):
                md.unlink()
            (design / 'summary-text.yaml').write_text('structure: {}\n', encoding='utf-8')
            r = build(design, pathlib.Path(d) / 'p.html')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('1-architecture-drivers.md がない', r.stdout)
        self.assertIn('summary-text.yaml はもう使わない（消してよい）', r.stdout)
        for tid in ('t-rank', 't-decd', 't-ifc', 't-err', 't-data'):
            self.assertIn(f'id="{tid}"', page)
        self.assertNotIn('id="t-views"', page)


class Reports(unittest.TestCase):
    """How the reports of req-to-design 0.3.0 are read"""

    def test_generated_tables_and_comments(self):
        md = '\n'.join(['# 概略設計: X', '', '## 設計の決定', '<!-- generated: decisions -->', '| DEC | 名前 |', '|---|---|',
                         '| DEC-01 | A |', '<!-- /generated -->', '', '<!-- a note', 'over two lines -->', 'DEC-01 案の比べ:',
                         '| 要求 | 案 |', '|---|---|', '| DRV-01 | 満たす |'])
        root = bd.parse_md(md, 'r.md')
        sec = root.children[0].find(bd.H['decisions'])
        self.assertEqual([(b.kind, b.gen) for b in sec.blocks], [('table', 'decisions'), ('label', ''), ('table', '')])
        self.assertEqual(sec.blocks[1].text, 'DEC-01 案の比べ')
        self.assertIs(root.generated('decisions')[1], sec.blocks[0])

    def test_a_colon_line_before_prose_is_a_paragraph(self):
        root = bd.parse_md('## A\n\nCUJ-03 調べ:\n\n文だけで書く。\n', 'r.md')
        self.assertEqual([b.kind for b in root.children[0].blocks], ['para', 'para'])

    def test_heading_prefix(self):
        self.assertTrue(bd.heading_is('遅延の予算とタイムアウト', '遅延の予算…'))
        self.assertTrue(bd.heading_is('Design decisions', 'Design decisions'))
        self.assertFalse(bd.heading_is('Decisions', 'Design decisions'))
        self.assertFalse(bd.heading_is('設計の決定の理由', '設計の決定'))

    def test_status_line(self):
        self.assertEqual(bd.report_status('# A: B\n\n状態: 質問待ち · 更新: 2026-11-13 · 入力の基準: なし · 第 2 段階（全 4 段階）\n'),
                         ('waiting', '2026-11-13'))
        self.assertEqual(bd.report_status('# A\n\nStatus: answers applied · Updated: 2026-01-02 · Stage 1 of 4\n'), ('applied', '2026-01-02'))
        self.assertEqual(bd.report_status('# A\n\nno status\n'), ('', ''))

    def test_hop_table_words(self):
        rows = [['ホップ（送ってから示すまで）', '予算（99 パーセンタイル）', 'もと'], ['送る', '0.30 秒', ''], ['返す', '0.70 秒', ''],
                ['余裕', '1.00 秒', ''], ['計', '2.00 秒', '']]
        sp = bd.hop_chart(bd.Block('table', rows=rows), bd.Ctx(), 'x')
        self.assertEqual((len(sp['hops']), sp['threshold']), (2, 2.0))

    def test_flows_of_a_threat_row(self):
        self.assertEqual(bd.flows_of('F9、F10'), ['F9', 'F10'])
        self.assertEqual(bd.flows_of('F1 操作（ELM-01 → ELM-03）'), ['F1'])
        self.assertEqual(bd.flows_of('F4, F5'), ['F4', 'F5'])
        self.assertEqual(bd.flows_of('流れ'), [])


class Warnings(unittest.TestCase):
    """Older outputs, and reports that are not settled, are reported"""

    def build_changed(self, change):
        with tempfile.TemporaryDirectory() as d:
            design = pathlib.Path(d) / 'docs' / 'design'
            shutil.copytree(design_of('homework-service-full'), design)
            change(design)
            r = build(design, pathlib.Path(d) / 'p.html')
            page = (pathlib.Path(d) / 'p.html').read_text(encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout, page

    def test_older_outputs(self):
        def legacy(design):
            p = design / 'drv' / 'DRV-01.yaml'
            p.write_text(p.read_text(encoding='utf-8') + 'version: 2\nchangelog: []\n', encoding='utf-8')
            p = design / 'dec' / 'DEC-01.yaml'
            p.write_text(p.read_text(encoding='utf-8').replace('status: active', 'status: draft'), encoding='utf-8')
        out, page = self.build_changed(legacy)
        self.assertIn('旧い形式: 1 件', out)
        self.assertIn('changelog（1 件）、status: draft（1 件）、version（1 件）', out)
        self.assertIn('旧い形式', toggle(page, 't-notes'))

    def test_report_waiting_for_answers(self):
        def waiting(design):
            p = design / '3-high-level-design.md'
            p.write_text(p.read_text(encoding='utf-8').replace('状態: 回答反映済み', '状態: 質問待ち'), encoding='utf-8')
        out, page = self.build_changed(waiting)
        self.assertIn('3-high-level-design.md は質問待ち', out)



class Palette(unittest.TestCase):
    """Color is used as in quality-summary-html (references/page-spec.md, Theme): design.css only redefines base.css's
    tokens, neither design.css nor design.js writes a color of its own, and the diagrams are drawn without the accent"""
    base = (SKILL / 'assets' / 'base.css').read_text(encoding='utf-8')
    css = (SKILL / 'assets' / 'design.css').read_text(encoding='utf-8')
    js = (SKILL / 'assets' / 'design.js').read_text(encoding='utf-8')
    COLOR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl|hwb|lab|lch|oklab|oklch)a?\(')

    @staticmethod
    def root(css):
        return re.search(r':root\{(.*?)\}', css, re.S).group(1)

    def tokens(self, css):
        return set(re.findall(r'(--[\w-]+)\s*:', self.root(css)))

    def test_no_token_of_its_own(self):
        self.assertEqual(self.tokens(self.css) - self.tokens(self.base), set())
        self.assertEqual(set(re.findall(r"""v\(['"](--[\w-]+)['"]\)""", self.js)) - self.tokens(self.base), set())

    def test_no_color_outside_the_tokens(self):
        rest = re.sub(r'/\*.*?\*/', '', self.css.replace(self.root(self.css), ''), flags=re.S)
        for decl in re.split(r'[;{}]', rest):
            if self.COLOR.search(decl):
                self.assertTrue(decl.strip().startswith('box-shadow'), decl.strip())   # a shadow is a shade of ink
        self.assertIsNone(self.COLOR.search(re.sub(r'//[^\n]*', '', self.js)))

    def test_diagrams_without_the_accent(self):
        theme = re.search(r'themeVariables:\s*\{(.*?)\}', self.js, re.S).group(1)
        self.assertNotIn('--route', theme)

    def test_only_the_highest_level_outlined(self):
        """高 is outlined in the accent exactly as base.css outlines the SLO type; 中 and 低 stay in ink"""
        def decls(css, sel):
            return set(re.search(re.escape(sel) + r'\{([^}]*)\}', css).group(1).split(';')) - {''}
        self.assertEqual(decls(self.css, '.lvl-h'), decls(self.base, '.ntype.is-slo'))
        for sel in ('.lvl-m', '.lvl-l'):
            self.assertFalse([d for d in decls(self.css, sel) if '--route' in d], sel)


@unittest.skipUnless((CHAIN / 'shared' / 'glossary.md').is_file(), 'req-to-design がない: %s（環境変数 REQ_TO_DESIGN で場所を渡せる）' % CHAIN)
class ChainCheck(unittest.TestCase):
    def run_check(self, base):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check-chain.py'), '--only', 'req-to-design',
                               '--req-to-design', str(base)], capture_output=True, text=True)

    def test_current_chain_matches(self):
        r = self.run_check(CHAIN)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_detects_a_renamed_term_and_heading(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(CHAIN / 'shared', pathlib.Path(d) / 'shared')
            shutil.copytree(CHAIN / 'skills', pathlib.Path(d) / 'skills', ignore=shutil.ignore_patterns('scripts', '__pycache__'))
            g = pathlib.Path(d) / 'shared' / 'glossary.md'
            g.write_text(g.read_text(encoding='utf-8').replace('外部のシステム', '外部システム'), encoding='utf-8')
            t = pathlib.Path(d) / 'skills' / 'architecture-to-technical-policy' / 'references' / 'report-template.md'
            t.write_text(t.read_text(encoding='utf-8').replace('## Technical policies', '## Policies'), encoding='utf-8')
            r = self.run_check(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn('外部のシステム', r.stdout)
        self.assertIn('Technical policies', r.stdout)

    def test_a_missing_chain_is_not_skipped_silently(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_check(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn('確かめなかった', r.stdout)


if __name__ == '__main__':
    unittest.main()
