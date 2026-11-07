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

ROOT = pathlib.Path(__file__).resolve().parent.parent
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
        self.assertIn('設計の決定（第 2 段階）: YAML にあって報告書にない DEC-06', out)
        self.assertIn('通し確認: CUJ-03 提出の失敗の調査（報告書に表がない）', out)
        self.assertIn('遅延の予算: NFR-02（報告書に表がない）', out)
        self.assertIn('履歴の注記を削った文: 25 件', out)

    def test_yaml_over_the_report(self):
        dec = toggle(self.page, 't-dec')
        self.assertIn('DEC-06', dec)
        self.assertIn('先送り', dec)                                  # a deferred decision has no chosen option
        self.assertNotIn('DRV-10', toggle(self.page, 't-constraint'))  # retired
        self.assertIn('個人情報（生徒の答案）', toggle(self.page, 't-data'))

    def test_report_prose_is_left_out(self):
        self.assertNotIn('t-structure', self.page)
        self.assertNotIn('依存の規則', self.page)
        self.assertNotIn('区間の表にするほどの区間はない', self.page)

    def test_budget_chart_and_threat_links(self):
        b = toggle(self.page, 't-budget')
        self.assertIn('id="b-NFR-06"', b)
        self.assertIn('class="bud"', b)
        self.assertIn('和 1.5 秒、余り 1.5 秒', b)
        self.assertNotIn('b-NFR-02', b)
        threat = toggle(self.page, 't-threat')
        self.assertIn('data-links="flow"', threat)
        self.assertEqual(re.findall(r'id="(flow-F\d)"', threat), ['flow-F1', 'flow-F2', 'flow-F3', 'flow-F4', 'flow-F5'])

    def test_shared_error_contracts_shown_once(self):
        err = toggle(self.page, 't-err')
        self.assertEqual(err.count('401 UNAUTHENTICATED'), 1)
        self.assertIn('共通 2', err)


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
        self.assertIn('Decisions (stage 2): in the YAML but not in the report: DEC-06', out)
        self.assertIn('Texts with revision notes removed: 25', out)

    def test_english_terms_and_ids(self):
        self.assertIn('Technology constraint: External service', toggle(self.page, 't-premise'))
        self.assertIn('Non-negotiable', toggle(self.page, 't-constraint'))
        self.assertIn('All operations', toggle(self.page, 't-err'))
        # 「FR-01、02、06」 is written "FR-01, 02, 06" and 02 still links to FR-02's tooltip
        self.assertRegex(toggle(self.page, 't-elm'), r'FR-01</span>, <span class="id dead" data-ref="FR-02">02')


class HomeworkStage2(Case):
    case = 'homework-service-stage2'

    def test_only_stages_1_and_2(self):
        self.assertIn('id="sec-2"', self.page)
        self.assertNotIn('id="sec-3"', self.page)
        self.assertIn('第 3 段階（概要設計）の成果物はまだない', toggle(self.page, 't-notes'))


@unittest.skipUnless(design_of('ride-hailing-full').is_dir(), '配車アプリの成果物がない')
class RideHailing(Case):
    case = 'ride-hailing-full'

    def test_real_project(self):
        out = self.run1.stdout
        self.assertIn('項目: DRV 32 · DEC 55（第 2 段階 37 · 第 3 段階 18） · ELM 23 · IFC 29 · DAT 29', out)
        self.assertIn('技術的負債と先送りした決定: 報告書にあって YAML にない DEC-21、DEC-30', out)
        self.assertIn('突き合わせなかった表: なし', out)
        self.assertEqual(self.page.count('<figure class="mmd"'), 50)
        self.assertIn('<title>配車アプリの設計</title>', self.page)
        self.assertIn('id="b-NFR-02"', self.page)
        self.assertNotIn('FND-', visible(self.page))


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
        self.assertIn('Texts with revision notes removed: 25', r.stdout)

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
        built = {'k_' + k for k in bd.REPORT_KINDS} | {f'stage_title_{n}' for n in (1, 2, 3)} | {'lang_detected', 'lang_given'}
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


if __name__ == '__main__':
    unittest.main()
