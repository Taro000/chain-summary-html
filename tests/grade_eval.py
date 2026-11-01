#!/usr/bin/env python3
"""Grade eval runs against each test case's grader statements and write grading.json for every run.

  uv run --with pyyaml python3 tests/grade_eval.py <workspace>/iteration-N

This is the "Grade each run" step of the skill-creator workflow. A run is <case>/<config>/outputs/
holding summary.html (the page it built) and report.md (its final report to the user). The grader
statements live in skills/quality-summary-html/evals/<case>/graders/, and the second half of each file
name (page-written and so on) selects the check. Runs without the skill build the page differently,
so the checks look at the property a statement describes, not at markup details.
"""
import html.parser
import importlib.util
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS = ROOT / 'skills' / 'quality-summary-html' / 'evals'
spec = importlib.util.spec_from_file_location('build_summary', ROOT / 'skills' / 'quality-summary-html' / 'scripts' / 'build_summary.py')
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs), parent, []

    def text(self):
        return ''.join(k if isinstance(k, str) else k.text() for k in self.kids)

    def walk(self):
        for k in self.kids:
            if isinstance(k, Node):
                yield k
                yield from k.walk()

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent


class Tree(html.parser.HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node('#root', [], None)
        self.feed(src)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        for a in [self.cur] + list(self.cur.ancestors()):
            if a.tag == tag:
                self.cur = a.parent or self.root
                return

    def handle_data(self, data):
        self.cur.kids.append(data)


def header_cells(table):
    rows = [n for n in table.walk() if n.tag == 'tr']
    thead = [n for n in table.walk() if n.tag == 'thead']
    first = [n for n in thead[0].walk() if n.tag == 'tr'][:1] if thead else rows[:1]
    return [c for r in first for c in r.kids if isinstance(c, Node) and c.tag in ('th', 'td')]


def body_rows(table):
    return [n for n in table.walk() if n.tag == 'tr' and not any(a.tag == 'thead' for a in n.ancestors())]


def live_ids(docs, kind):
    out = []
    for p in sorted((docs / kind).glob('*.yaml')):
        d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        if d.get('status') != 'retired':
            out.append(str(d['id']))
    return out


def retired_ids(docs, kind):
    return [p.stem for p in sorted((docs / kind).glob('*.yaml'))
            if (yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('status') == 'retired']


class Run:
    def __init__(self, run_dir, case):
        self.dir, self.case = run_dir, case
        self.docs = EVALS / case / 'files' / 'docs' / 'quality'
        page = run_dir / 'outputs' / 'summary.html'
        self.src = page.read_text(encoding='utf-8', errors='replace') if page.is_file() else ''
        rep = run_dir / 'outputs' / 'report.md'
        self.report = rep.read_text(encoding='utf-8', errors='replace') if rep.is_file() else ''
        self.tree = Tree(self.src).root
        self.tables = [n for n in self.tree.walk() if n.tag == 'table']
        self.ids = {n.attrs.get('id') for n in self.tree.walk() if n.attrs.get('id')}
        self.full = (self.docs / 'nfr').is_dir()

    # One check per grader statement. Each returns (passed, evidence)
    def page_written(self):
        return bool(self.src and self.tables), 'summary.html %d 字、表 %d 個' % (len(self.src), len(self.tables))

    # Column heads may be abbreviations or Japanese (「機能要件」 is FR, 「利用時の品質要求」 is QIU)
    COLS = {
        'CUJ': lambda h: 'CUJ' in h,
        'QIU': lambda h: 'QIU' in h or '利用時の品質' in h,
        'FR': lambda h: bool(re.search(r'(?<![A-Z])FR(?![A-Z])', h)) or bool(re.search(r'(?<!非)機能', h)),
        'QR': lambda h: bool(re.search(r'(?<![A-Z])QR', h)) or ('品質要求' in h and '利用時の品質要求' not in h),
        'NFR': lambda h: 'NFR' in h or '非機能要件' in h or 'SLO' in h or 'SLI' in h,
    }

    def trace_first(self):
        if not self.tables:
            return False, '表がない'
        t = self.tables[0]
        txt = t.text()
        cells = [c.text().strip().upper() for c in header_cells(t)]
        heads = ' | '.join(cells)
        need = ['CUJ', 'QIU', 'FR'] + (['QR', 'NFR'] if self.full else [])
        miss_cols = [c for c in need if not any(self.COLS[c](h) for h in cells)]
        live, gone = live_ids(self.docs, 'qiu'), retired_ids(self.docs, 'qiu')
        miss = [q for q in live if q not in txt]
        extra = [q for q in gone if re.search(r'%s(?!\d)' % q, txt)]
        ok = not miss_cols and not miss and not extra
        return ok, '最初の表の列: %s。足りない列: %s。載っていない QIU: %s。載っている廃止の QIU: %s' % (
            heads[:120], miss_cols or 'なし', miss or 'なし', extra or 'なし')

    def id_links(self):
        hrefs = [(a.attrs.get('href', '')[1:], a.text().strip()) for a in self.tree.walk()
                 if a.tag == 'a' and a.attrs.get('href', '').startswith('#') and len(a.attrs.get('href', '')) > 1]
        broken = sorted({h for h, _ in hrefs if h not in self.ids})
        linked = {i for h, t in hrefs if h in self.ids for i in bs.ids_in(t)}
        want = live_ids(self.docs, 'qiu') + (live_ids(self.docs, 'qr') if (self.docs / 'qr').is_dir() else [])
        miss = [i for i in want if i not in linked]
        return not broken and not miss, 'ページ内のリンク %d 件、行き先のないリンク: %s。リンクになっていない QR・QIU: %s' % (
            len(hrefs), broken[:10] or 'なし', miss[:10] or 'なし')

    def toggles(self):
        rest = self.tables[1:]
        bad = [t for t in rest if not any(a.tag == 'details' and 'open' not in a.attrs for a in t.ancestors())]
        return bool(rest) and not bad, 'トレーサビリティのほかの表 %d 個のうち、閉じたトグルに入っていないもの %d 個' % (len(rest), len(bad))

    def basis_columns(self):
        kinds = []
        for t in self.tables:
            if any(c.text().strip().startswith('根拠') for c in header_cells(t)):
                firsts = set()
                for r in body_rows(t):
                    cells = [c for c in r.kids if isinstance(c, Node) and c.tag in ('td', 'th')]
                    got = bs.ids_in(cells[0].text()) if cells else []
                    if got:
                        firsts.add(got[0].split('-')[0])
                kinds.append('/'.join(sorted(firsts)) or '?')
        ok = sorted(kinds) == ['CUJ', 'USR']
        return ok, '「根拠」の列がある表（1 列目の ID の種類）: %s' % (kinds or 'なし')

    def light_only(self):
        hits = [p for p in ('prefers-color-scheme: dark', 'prefers-color-scheme:dark', 'data-theme="dark"', 'color-scheme: dark', 'color-scheme:dark')
                if p in self.src]
        return not hits, 'ダークモードの記述: %s' % (hits or 'なし')

    def requirements_toggle(self):
        ds = [d for d in self.tree.walk() if d.tag == 'details']
        target = [d for d in ds if any(k.tag == 'summary' and 'HTML作成時の要件' in k.text() for k in d.kids if isinstance(k, Node))]
        if not target:
            return False, '「HTML作成時の要件」のトグルがない'
        d = target[-1]
        inside = set(id(n) for n in d.walk())
        after = False
        later_tables = 0
        for n in self.tree.walk():
            if n is d:
                after = True
            elif after and n.tag == 'table' and id(n) not in inside:
                later_tables += 1
        ok = 'open' not in d.attrs and '目的' in d.text() and '要件' in d.text() and later_tables == 0
        return ok, '閉じている: %s、目的と要件: %s、後ろにある表: %d' % ('open' not in d.attrs, '目的' in d.text(), later_tables)

    def priority_sort(self):
        for t in self.tables:
            cells = header_cells(t)
            names = [c.text().strip() for c in cells]
            if any(n.startswith('点') for n in names) and any('影響' in n for n in names):
                def sortable(c):
                    return any(n.tag == 'button' for n in c.walk()) or any(k in c.attrs for k in ('onclick', 'data-sort', 'data-key', 'aria-sort'))
                qr = [c for c, n in zip(cells, names) if n.upper().startswith('QR')]
                pt = [c for c, n in zip(cells, names) if n.startswith('点')]
                js = 'sort' in ''.join(n.text() for n in self.tree.walk() if n.tag == 'script')
                ok = bool(qr and pt and sortable(qr[0]) and sortable(pt[0]) and js)
                return ok, '優先度の表の見出し: %s。QR と点の見出しが操作できる: %s、並べ替えの処理: %s' % (
                    names, bool(qr and pt and sortable(qr[0]) and sortable(pt[0])), js)
        return False, '優先度の表（点と影響の列を持つ表）がない'

    def slo_targets(self):
        miss = []
        rows = [r.text() for t in self.tables for r in body_rows(t)]
        for p in sorted((self.docs / 'nfr').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            if d.get('kind') == 'slo' and d.get('status') != 'retired':
                target = str((d.get('slo') or {}).get('target'))
                if not any(d['id'] in r and target in r for r in rows):
                    miss.append('%s %s' % (d['id'], target))
        return not miss, '目標値が NFR と同じ行にない SLO: %s' % (miss or 'なし')

    def both_ebps(self):
        txt = self.tree.text()
        miss = []
        for p in sorted((self.docs / 'ebp').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            rule = (d.get('rules') or [{}])[0].get('when', '')
            if d['id'] not in txt or rule not in txt:
                miss.append(d['id'])
        return not miss, '載っていない EBP（ID か最初の条件）: %s' % (miss or 'なし')

    def reports_fr52(self):
        qs = set(bs.ids_in(self.report, 'QIU')) & {'QIU-04', 'QIU-11', 'QIU-15', 'QIU-17'}
        ok = 'FR-52' in self.report and len(qs) >= 3
        return ok, '報告に FR-52: %s、挙げた QIU: %s' % ('FR-52' in self.report, sorted(qs) or 'なし')

    def reports_fr52_step(self):
        # FR-52, the step table (手順 or "step", since the report may be in English), and CUJ-06 or 「配車依頼を選ぶ」
        # appear close together (that line and the next two)
        lines = self.report.splitlines()

        def near(i):
            w = ' '.join(lines[i:i + 3])
            return ('手順' in w or re.search(r'\bsteps?\b', w, re.I)) and ('CUJ-06' in w or '配車依頼を選ぶ' in w)
        hit = next((ln for i, ln in enumerate(lines) if 'FR-52' in ln and near(i)), None)
        return hit is not None, '手順の表の FR-52 に触れた行: %s' % (hit.strip()[:120] if hit else 'なし')

    def entry_column(self):
        # In the product quality matrix (the table with a 副特性 / sub-characteristic column), each entry-point QR
        # appears in the entry column (入口) on the row of its sub-characteristic
        want = []
        for p in sorted((self.docs / 'qr').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            key = bs.char_key(d.get('characteristic'))
            if d.get('status') != 'retired' and d.get('entry_point') and d.get('model') == 'product' and d.get('layer') != 'internal' and len(key) == 2:
                want.append((str(d['id']), bs.term('characteristic', key[1], strict=False)))
        for t in self.tables:
            names = [c.text().strip() for c in header_cells(t)]
            if not any('副特性' in n for n in names):
                continue
            ent = [j for j, n in enumerate(names) if '入口' in n or '経由しない' in n]
            if not ent:
                return False, '製品の品質のマトリクスに入口の列がない（見出し: %s）' % names[:5]
            k, miss = len(names) - ent[0], []  # the characteristic column uses rowspan, so count column positions from the right
            for q, sub in want:
                row = next((r for r in body_rows(t) if any(isinstance(c, Node) and c.tag == 'th' and c.text().strip() == sub for c in r.kids)), None)
                cells = [c for c in row.kids if isinstance(c, Node) and c.tag in ('td', 'th')] if row else []
                if len(cells) < k or q not in cells[-k].text():
                    miss.append('%s（%s）' % (q, sub))
            return not miss, '入口の列: %s。入口の列の正しい行にない QR: %s' % (names[ent[0]], miss or 'なし')
        return False, '製品の品質のマトリクス（副特性の列を持つ表）がない'

    def reports_fr08(self):
        ok = 'FR-08' in self.report and 'QIU-03' in bs.ids_in(self.report, 'QIU')
        return ok, '報告に FR-08: %s、QIU-03: %s' % ('FR-08' in self.report, 'QIU-03' in self.report)

    def missing_stages(self):
        txt = self.report + '\n' + self.tree.text()
        # Japanese or English, since the page is Japanese and the report may be in either
        says3 = re.search(r'(第\s*3|3\s*[・、〜~と]\s*(第\s*)?4|stages?\s*3)', txt, re.I)
        says_missing = re.search(r'(まだ|ない|未|ありません|含まれていません|省|missing|not yet|absent|left out|not (?:been )?run)', txt, re.I)
        ok = bool(self.src and self.tables and says3 and says_missing)
        return ok, '第 3・4 段階に触れている: %s、ないことを言う語: %s' % (bool(says3), bool(says_missing))


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
