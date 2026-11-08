#!/usr/bin/env python3
"""Grade design-summary-html's eval runs against each test case's grader statements and write grading.json for every run.

  uv run --with pyyaml python3 tests/grade_design_eval.py <workspace>/iteration-N

This is the "Grade each run" step of the skill-creator workflow, as tests/grade_eval.py is for quality-summary-html.
A run is <case>/<config>/outputs/ holding summary.html (the page it built) and report.md (its final report to the
user). The grader statements live in skills/design-summary-html/evals/<case>/graders/, and the second half of each
file name (page-written and so on) selects the check. Runs without the skill build the page differently, so the
checks look at the property a statement describes, not at markup details.
"""
import importlib.util
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from grade_eval import Node, Tree, body_rows, header_cells  # noqa: E402  (the same HTML reading as quality-summary-html's grader)

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS = ROOT / 'skills' / 'design-summary-html' / 'evals'
spec = importlib.util.spec_from_file_location('build_design_summary', ROOT / 'skills' / 'design-summary-html' / 'scripts' / 'build_design_summary.py')
bd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bd          # its dataclasses look the module up while it loads
spec.loader.exec_module(bd)
JAPANESE = re.compile(r'[　-ヿ㐀-鿿＀-￯]')
ID_RE = re.compile(r'\b(?:DRV|DEC|ELM|IFC|DAT)-\d{2,}\b')
# Revision notes that must not reach the page, in both languages
NOTES = [r'FND-\d', r'[A-Z]{2,4}-\d{2}\s*版\s*\d', r'[A-Z]{2,4}-\d{2} version \d', r'前の版は', r'previous version',
         r'再実行', r'\bre-?run\b']


def items(docs, kind):
    out = {}
    for p in sorted((docs / kind).glob('*.yaml')):
        d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        if d.get('id'):
            out[str(d['id'])] = d
    return out


def visible(n):
    """The text a reader sees: scripts, styles and diagram sources left out"""
    if not isinstance(n, Node):
        return n
    if n.tag in ('script', 'style') or (n.tag == 'pre' and 'mmd-src' in (n.attrs.get('class') or '')):
        return ''
    return ''.join(visible(k) for k in n.kids)


class Run:
    def __init__(self, run_dir, case):
        self.dir, self.case = run_dir, case
        self.docs = EVALS / case / 'files' / 'docs' / 'design'
        page = run_dir / 'outputs' / 'summary.html'
        self.src = page.read_text(encoding='utf-8', errors='replace') if page.is_file() else ''
        rep = run_dir / 'outputs' / 'report.md'
        self.report = rep.read_text(encoding='utf-8', errors='replace') if rep.is_file() else ''
        self.tree = Tree(self.src).root
        self.nodes = list(self.tree.walk())
        self.texts = {}
        self._text(self.tree)
        self.tables = [n for n in self.nodes if n.tag == 'table']
        self.ids = {n.attrs.get('id') for n in self.nodes if n.attrs.get('id')}
        self.text = visible(self.tree)
        self.drv, self.dec = items(self.docs, 'drv'), items(self.docs, 'dec')
        self.elm, self.ifc, self.dat = items(self.docs, 'elm'), items(self.docs, 'ifc'), items(self.docs, 'dat')
        # texts are compared after the build script's own removal of revision notes, in the outputs' language
        texts = [s for coll in (self.drv, self.dec, self.elm) for v in coll.values() for s in bd.strings(v)]
        texts += [p.read_text(encoding='utf-8') for p in sorted(self.docs.glob('*.md'))]
        bd.SRC['lang'] = bd.detect_lang(texts)

    def _text(self, n):
        """Every node's text, computed once (the pages are large)"""
        t = ''.join(k if isinstance(k, str) else self._text(k) for k in n.kids)
        self.texts[id(n)] = t
        return t

    @staticmethod
    def live(coll):
        return {k: v for k, v in coll.items() if v.get('status') != 'retired'}

    def clean(self, s):
        return bd.clean_text(str(s or '').strip())[0]

    @staticmethod
    def squeeze(s):
        return re.sub(r'\s+', '', s or '')

    def forms(self, s):
        """A YAML text as a page may show it: whole (without revision notes) or as its gist, spaces left out"""
        full = self.clean(s)
        return {self.squeeze(x) for x in (full, bd.gist(full)) if x}

    def shows(self, s, text):
        return any(f in text for f in self.forms(s))

    def decs(self, stage):
        return {k: v for k, v in self.live(self.dec).items() if v.get('stage') == stage}

    def holder(self, *needles):
        """The smallest details, section, article or div whose text holds every needle: a string, or a YAML text that
        may be shown whole or as its gist (a set of forms; spaces are left out for those)"""
        best, best_len = None, 0
        for n in self.nodes:
            if n.tag not in ('details', 'section', 'article', 'div', 'li'):
                continue
            t = self.texts[id(n)]
            sq = None
            ok = True
            for x in needles:
                if isinstance(x, set):
                    sq = sq if sq is not None else self.squeeze(t)
                    ok = any(f in sq for f in x)
                else:
                    ok = x in t
                if not ok:
                    break
            if ok and (best is None or len(t) < best_len):
                best, best_len = n, len(t)
        return best

    # One check per grader statement. Each returns (passed, evidence)
    def page_written(self):
        return bool(self.src and self.tables), 'summary.html %d 字、表 %d 個' % (len(self.src), len(self.tables))

    def rank_first(self):
        if not self.tables:
            return False, '表がない'
        t = self.tables[0]
        heads = [c.text().strip() for c in header_cells(t)]
        got = []
        for r in body_rows(t):
            # the node that holds only the ID (the name may follow it with no space: 「DRV-06」「2 人で…」)
            own = next((self.texts[id(n)].strip() for n in r.walk() if re.fullmatch(r'DRV-\d{2,}', self.texts[id(n)].strip())), None)
            m = own or (re.search(r'DRV-\d{2}(?!\d)', r.text()) or [None])[0]
            if m:
                got.append(m)
        want = [v['id'] for v in sorted((v for v in self.live(self.drv).values() if v.get('kind') != 'principle'),
                                        key=lambda v: (int((v.get('priority') or {}).get('rank') or 999), v['id']))]
        retired = [k for k, v in self.drv.items() if v.get('status') == 'retired']
        closed = any(a.tag == 'details' and 'open' not in a.attrs for a in t.ancestors())
        ok = got == want and not closed and not set(retired) & set(got)
        return ok, '最初の表の見出し: %s。順: %s。YAML の順位: %s。閉じたトグルの中: %s' % (
            heads[:7], ' '.join(got[:12]), ' '.join(want[:12]), closed)

    def id_links(self):
        """Every item has a row that links can reach; an item mentioned outside its own row is linked; no link is broken"""
        anchors = [a for a in self.nodes if a.tag == 'a' and a.attrs.get('href', '').startswith('#') and len(a.attrs.get('href', '')) > 1]
        broken = sorted({a.attrs['href'][1:] for a in anchors if a.attrs['href'][1:] not in self.ids})
        # a link to the item's row or to another block of its own (its card 「d-DEC-05」, its rank 「rank-DRV-01」)
        targets = {t for a in anchors for t in [a.attrs['href'][1:]] for t in (t, t.split('-', 1)[-1])}
        want = set(self.live(self.drv)) | set(self.live(self.elm)) | set(self.live(self.ifc)) | set(self.live(self.dat))
        want |= set(self.decs('architecture')) | set(self.decs('high-level-design'))
        rows = {n.attrs['id']: n for n in self.nodes if n.attrs.get('id') in want}
        no_row = sorted(want - set(rows), key=bd.id_key)
        unlinked = []
        for x in sorted(want & set(rows), key=bd.id_key):
            total = len(re.findall(re.escape(x) + r'(?!\d)', self.text))
            own = sum(len(re.findall(re.escape(x) + r'(?!\d)', visible(n))) for n in self.nodes
                      if n.attrs.get('id') == x or (n.attrs.get('id') or '').endswith('-' + x))
            if total > own and x not in targets:
                unlinked.append(x)
        ok = not broken and not no_row and not unlinked
        return ok, 'ページ内のリンク %d 件。行き先のないリンク: %s。行のない項目: %s。ほかで触れているのにリンクのない項目: %s' % (
            len(anchors), broken[:8] or 'なし', no_row[:10] or 'なし', unlinked[:10] or 'なし')

    def toggles(self):
        rest = self.tables[1:]
        bad = [t for t in rest if not any(a.tag == 'details' and 'open' not in a.attrs for a in t.ancestors())]
        return bool(rest) and not bad, '順位表のほかの表 %d 個のうち、閉じたトグルに入っていないもの %d 個' % (len(rest), len(bad))

    def light_only(self):
        hits = [p for p in ('prefers-color-scheme: dark', 'prefers-color-scheme:dark', 'data-theme="dark"', 'color-scheme: dark',
                            'color-scheme:dark') if p in self.src]
        return not hits, 'ダークモードの記述: %s' % (hits or 'なし')

    def decision_cards(self):
        bad = []
        decs = self.decs('architecture')
        for k, v in decs.items():
            first = [self.forms(o.get('name')) for o in v.get('options') or []][:1]
            card = self.holder(k, self.forms(v.get('question')), *first)
            if card is None:
                bad.append('%s（問いがない）' % k)
                continue
            t = self.texts[id(card)]
            sq = self.squeeze(t)
            miss = [o['name'] for o in v.get('options') or [] if not self.shows(o.get('name'), sq)]
            miss += [r['reason'] for r in v.get('rejected') or [] if not self.shows(r.get('reason'), sq)]
            marked = re.search(r'選んだ|採用|Chosen|chosen|Selected|selected', t)
            if miss or (v.get('chosen') and not marked):
                bad.append('%s（%s）' % (k, '案か理由がない' if miss else '選んだ案の印がない'))
        return bool(decs) and not bad, '第 2 段階の決定 %d 件のうち、足りないもの: %s' % (len(decs), bad[:6] or 'なし')

    def follows_yaml_dec06(self):
        v = self.dec.get('DEC-06') or {}
        q = self.shows(v.get('question'), self.squeeze(self.text))
        return 'DEC-06' in self.text and q, 'ページに DEC-06: %s、その問い: %s' % ('DEC-06' in self.text, q)

    def report_cells(self):
        """Every cell of every table in the reports"""
        out = []
        for p in sorted(self.docs.glob('*.md')):
            stack = [bd.parse_md(p.read_text(encoding='utf-8'), p.name)]
            while stack:
                s = stack.pop()
                out += [c for b in s.blocks if b.kind == 'table' for r in b.rows for c in r]
                stack += s.children
        return out

    def gist_only(self):
        """No sentence after the first of a YAML item's text is on the page: every text is cut to its gist. A later
        sentence that is also part of a title or name (shown whole) or of the gist of another text (a YAML text,
        design-context.yaml, a report table cell) is on the page by right and does not count"""
        whole = ('changelog', 'basis_note', 'title', 'name', 'entity')      # not texts, or shown whole
        items = [v for coll in (self.drv, self.elm, self.ifc, self.dat, self.dec) for v in self.live(coll).values()]
        texts = [s for v in items for k, x in v.items() if k not in whole for s in bd.strings(x)]
        dc = self.docs / 'design-context.yaml'
        others = list(bd.strings(yaml.safe_load(dc.read_text(encoding='utf-8')) or {})) if dc.is_file() else []
        gists = '\n'.join([self.squeeze(bd.gist(self.clean(s))) for s in texts + others + self.report_cells()]
                          + [self.squeeze(self.clean(v.get(k))) for v in items for k in ('title', 'name', 'entity') if v.get(k)])
        page = self.squeeze(self.text)
        later, checked = [], 0
        for s in texts:
            rest = self.clean(s)
            sents = []
            while rest:
                head = bd.first_sentence(rest)
                sents.append(head)
                rest = rest[len(head):].lstrip('。. ')
            for sent in sents[1:]:
                forms = {self.squeeze(x) for x in (sent, bd.drop_asides(sent))}
                if max(len(f) for f in forms) < 12:
                    continue
                checked += 1
                if any(f in page and f not in gists for f in forms if len(f) >= 12):
                    later.append(sent.strip()[:40])
        return checked > 0 and not later, '2 文目より後の文 %d 個のうち、ページに出ているもの: %s' % (checked, later[:5] or 'なし')

    def follows_yaml_debt(self):
        want = sorted(k for k, v in self.decs('architecture').items()
                      if (isinstance(v.get('debt'), dict) and v['debt'].get('what')) or v.get('deferred'))
        for t in self.tables:
            heads = ' '.join(c.text() for c in header_cells(t))
            if re.search(r'負債か先送り|[Dd]ebt or deferral|負債|[Dd]ebt', heads):
                got = sorted({m.group(0) for r in body_rows(t) for m in [re.search(r'DEC-\d{2,}', r.text())] if m})
                return got == want, '負債の表の DEC: %s。YAML: %s' % (' '.join(got), ' '.join(want))
        return False, '負債の表がない'

    def near(self, ids, words):
        """The final report names every ID in ids, and one of words, within the same line or the next two"""
        lines = self.report.splitlines()
        for i in range(len(lines)):
            w = ' '.join(lines[i:i + 3])
            if all(x in w for x in ids) and re.search(words, w, re.I):
                return w.strip()
        return None

    def reports_dec06(self):
        hit = self.near(['DEC-06'], r'報告書|report|表|table')
        return hit is not None, '報告書の決定の表に DEC-06 がないことに触れた行: %s' % (hit[:120] if hit else 'なし')

    def reports_dec21_dec30(self):
        hit = self.near(['DEC-21', 'DEC-30'], r'負債|危険|debt|risk')
        return hit is not None, '負債の表の DEC-21・DEC-30 に触れた行: %s' % (hit[:120] if hit else 'なし')

    def no_revision_notes(self):
        hits = {p: len(re.findall(p, self.text, re.I)) for p in NOTES}
        hits = {p: n for p, n in hits.items() if n}
        return bool(self.src) and not hits, '見える文に残った改訂の注記: %s' % (hits or 'なし')

    def diagrams(self):
        want = sum(len(re.findall(r'^```mermaid', p.read_text(encoding='utf-8'), re.M)) for p in sorted(self.docs.glob('*.md')))
        got = len([n for n in self.nodes if (n.tag == 'pre' and 'mmd-src' in (n.attrs.get('class') or ''))
                   or 'mermaid' in (n.attrs.get('class') or '').split()])
        got = got or len([n for n in self.nodes if n.tag == 'svg'])
        return got >= want > 0, '報告書の mermaid の図 %d 個、ページの図 %d 個' % (want, got)

    def threat_links(self):
        rows = sorted({i for i in self.ids if re.fullmatch(r'(?:flow-)?F\d+', i or '')}, key=lambda x: int(re.sub(r'\D', '', x)))
        anchors = {a.attrs.get('href', '')[1:] for a in self.nodes if a.tag == 'a' and a.attrs.get('href', '').startswith('#')}
        by_script = 'data-links="flow"' in self.src
        linked = [r for r in rows if r in anchors]
        ok = bool(rows) and (by_script or len(linked) == len(rows))
        return ok, '流れの行 %d 個（%s）。リンクのある行 %d 個。図の F 番号をリンクにする印: %s' % (
            len(rows), ' '.join(rows[:6]), len(linked), by_script)

    def budget_chart(self):
        nfr = 'NFR-02' if self.case == 'ride-hailing-full' else 'NFR-06'
        box = None
        for n in self.nodes:
            if n.tag in ('details', 'section', 'article', 'div') and (n.attrs.get('id') or '').endswith(nfr):
                box = n
                break
        box = box or self.holder(nfr, '0.5' if nfr == 'NFR-06' else '2.0')
        if box is None:
            return False, '%s の予算がページにない' % nfr
        chart = [n for n in box.walk() if n.tag in ('svg', 'canvas') or (n.tag == 'figure' and re.search(r'bud|chart', n.attrs.get('class') or ''))
                 or 'width:' in (n.attrs.get('style') or '')]
        return bool(chart), '%s の予算の図の部品: %d 個' % (nfr, len(chart))

    def english_page(self):
        ja = JAPANESE.findall(self.text)
        html_ = next((n for n in self.nodes if n.tag == 'html'), None)
        lang = (html_.attrs.get('lang') or '') if html_ else ''
        ok = bool(self.tables) and not ja and lang.lower().startswith('en')
        return ok, 'html の lang: %s、日本語の文字: %d 個（%s）' % (lang or 'なし', len(ja), ''.join(ja[:20]))

    def missing_stage(self):
        txt = self.report + '\n' + self.text
        says3 = re.search(r'第\s*3\s*段階|stage\s*3|概要設計|high-level design', txt, re.I)
        says_missing = re.search(r'まだ|ない|未|ありません|missing|not yet|no outputs|absent|left out', txt, re.I)
        no_ifc = not any(re.search(r'IFC-\d', t.text()) for t in self.tables)
        ok = bool(self.src and self.tables and says3 and says_missing and no_ifc)
        return ok, '第 3 段階に触れている: %s、ないことを言う語: %s、インタフェースの表がない: %s' % (bool(says3), bool(says_missing), no_ifc)


def grade(run_dir, case):
    r = Run(run_dir, case)
    exps = []
    for g in sorted((EVALS / case / 'graders').glob('*.md')):
        text = re.split(r'^---\s*$', g.read_text(encoding='utf-8'), maxsplit=2, flags=re.M)[2].strip()
        slug = g.stem.split('-', 1)[1].replace('-', '_')
        try:
            ok, ev = getattr(r, slug)()
        except Exception as e:  # a check that crashes counts as a failed statement
            ok, ev = False, '採点できなかった: %r' % e
        exps.append({'text': text, 'passed': bool(ok), 'evidence': ev})
    passed = sum(e['passed'] for e in exps)
    timing = {}
    tj = run_dir / 'timing.json'
    if tj.is_file():
        timing = json.loads(tj.read_text(encoding='utf-8'))
    out = {'expectations': exps,
           'summary': {'passed': passed, 'failed': len(exps) - passed, 'total': len(exps), 'pass_rate': round(passed / len(exps), 2) if exps else 0.0},
           'timing': {'total_duration_seconds': timing.get('total_duration_seconds')}}
    (run_dir / 'grading.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    return passed, len(exps)


def main():
    it = pathlib.Path(sys.argv[1])
    for case_dir in sorted(p for p in it.iterdir() if (p / 'eval_metadata.json').is_file()):
        for cfg in sorted(p for p in case_dir.iterdir() if (p / 'outputs').is_dir()):
            if not (cfg / 'outputs' / 'summary.html').is_file() and not (cfg / 'outputs' / 'report.md').is_file():
                print('%s/%s: まだ結果がない' % (case_dir.name, cfg.name))
                continue
            p, n = grade(cfg, case_dir.name)
            print('%s/%s: %d / %d' % (case_dir.name, cfg.name, p, n))


if __name__ == '__main__':
    main()
