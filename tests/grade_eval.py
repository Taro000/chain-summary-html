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


def visible(n):
    """The text a reader sees: scripts and styles left out"""
    if n.tag in ('script', 'style'):
        return ''
    return ''.join(k if isinstance(k, str) else visible(k) for k in n.kids)


def cells_of(row):
    return [c for c in row.kids if isinstance(c, Node) and c.tag in ('td', 'th')]


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
        # The language the case's outputs are written in, which the page should follow
        self.lang = bs.detect_lang(p.read_text(encoding='utf-8') for p in sorted(self.docs.rglob('*')) if p.suffix in ('.yaml', '.md'))

    # One check per grader statement. Each returns (passed, evidence)
    def page_written(self):
        return bool(self.src and self.tables), 'summary.html %d 字、表 %d 個' % (len(self.src), len(self.tables))

    # Column heads may be abbreviations, Japanese (「機能要件」 is FR, 「利用時の品質要求」 is QIU) or English
    COLS = {
        'CUJ': lambda h: 'CUJ' in h,
        'QIU': lambda h: 'QIU' in h or '利用時の品質' in h or 'QUALITY IN USE' in h or 'QUALITY-IN-USE' in h,
        'FR': lambda h: bool(re.search(r'(?<![A-Z])FR(?![A-Z])', h)) or bool(re.search(r'(?<!非)機能', h)) or h.startswith('FUNCTION'),
        'QR': lambda h: bool(re.search(r'(?<![A-Z])QR', h)) or ('品質要求' in h and '利用時の品質要求' not in h) or h.startswith('QUALITY REQ'),
        'NFR': lambda h: 'NFR' in h or '非機能要件' in h or 'SLO' in h or 'SLI' in h or 'NON-FUNCTIONAL' in h,
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
            if any(c.text().strip().startswith('根拠') or c.text().strip().lower().startswith('basis') for c in header_cells(t)):
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

    def english_page(self):
        # Text a reader sees (scripts and styles left out) has no Japanese, and the page says it is English
        text = visible(self.tree)
        ja = re.findall(r'[　-ヿ㐀-鿿＀-￯]', text)
        html_ = next((n for n in self.tree.walk() if n.tag == 'html'), None)
        lang = (html_.attrs.get('lang') or '') if html_ else ''
        ok = bool(self.tables) and not ja and lang.lower().startswith('en')
        return ok, 'html の lang: %s、日本語の文字: %d 個（%s）' % (lang or 'なし', len(ja), ''.join(ja[:20]))

    def priority_sort(self):
        def is_score(n):
            return n.startswith('点') or n.lower().startswith('score')
        for t in self.tables:
            cells = header_cells(t)
            names = [c.text().strip() for c in cells]
            if any(is_score(n) for n in names) and any('影響' in n or 'impact' in n.lower() for n in names):
                def sortable(c):
                    return any(n.tag == 'button' for n in c.walk()) or any(k in c.attrs for k in ('onclick', 'data-sort', 'data-key', 'aria-sort'))
                qr = [c for c, n in zip(cells, names) if n.upper().startswith('QR')]
                pt = [c for c, n in zip(cells, names) if is_score(n)]
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

    # ---------- Checks for the shapes cuj-to-slo 0.3.0 brought ----------
    # The glossary's terms for target statuses. English terms are capitalized as the page writes its other terms, so a raw
    # YAML value (lower case) does not pass for the term
    STATUS_TERMS = {'ja': {'confirmed': '確認済み', 'provisional': '仮', 'undecided': '未定'},
                    'en': {'confirmed': 'Confirmed', 'provisional': 'Provisional', 'undecided': 'Undecided'}}

    def slo_status_terms(self):
        # Each SLO's row (with its ID and target) carries the term for its target status, and a Japanese page shows no raw value
        terms = self.STATUS_TERMS[self.lang]
        rows = [r.text() for t in self.tables for r in body_rows(t)]
        miss = []
        for p in sorted((self.docs / 'nfr').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            if d.get('kind') == 'slo' and d.get('status') != 'retired':
                slo = d.get('slo') or {}
                st, target = str(slo.get('target_status')), str(slo.get('target'))
                term = terms.get(st, st)
                if not any(d['id'] in r and target in r and term in r for r in rows):
                    miss.append('%s（%s → %s）' % (d['id'], st, term))
        raw = []
        if self.lang == 'ja':
            text = visible(self.tree)
            raw = [w for w in terms if re.search(r'(?<![A-Za-z_-])%s(?![A-Za-z_-])' % w, text)]
        return not miss and not raw, '目標値の状態の語が行にない SLO: %s。ページに出ている YAML の値: %s' % (miss[:10] or 'なし', raw or 'なし')

    def data_producers(self):
        # The list that follows the label 「データを作る人」 / "Data producers" names every external system with creates_data: true
        ctx = yaml.safe_load((self.docs / 'context.yaml').read_text(encoding='utf-8')) or {}
        exts = [e for e in ctx.get('external_systems') or [] if isinstance(e, dict) and e.get('creates_data') and e.get('status') != 'retired']
        lists = []
        for n in self.tree.walk():
            own = ''.join(k for k in n.kids if isinstance(k, str)).strip().rstrip(':：').lower()
            if own in ('データを作る人', 'data producers') and n.parent is not None:
                sib = [k for k in n.parent.kids if isinstance(k, Node)]
                i = sib.index(n)
                if i + 1 < len(sib):
                    lists.append(sib[i + 1].text())
        if not lists:
            return False, '「データを作る人」の一覧がない'
        txt = ' '.join(lists)
        miss = [str(e.get('id')) for e in exts
                if str(e.get('id')) not in txt and re.split(r'[（(]', str(e.get('role')))[0].strip() not in txt]
        return not miss, '一覧: %s。載っていない外部のシステム: %s' % (re.sub(r'\s+', ' ', txt)[:150], miss or 'なし')

    def sli_no_empty_column(self):
        # The SLI table is the one whose first column holds every live SLI; no column of it is empty in every row
        want, empty_words = set(live_ids(self.docs, 'sli')), {'', '—', '–', '-', 'なし', 'none', 'n/a'}
        for t in self.tables:
            rows = [cells_of(r) for r in body_rows(t)]
            firsts = [bs.ids_in(cs[0].text(), 'SLI')[:1] if cs else [] for cs in rows]
            if not rows or not all(firsts) or {f[0] for f in firsts} != want:
                continue
            heads = [c.text().strip() for c in header_cells(t)]
            width = max(len(cs) for cs in rows)
            empty = [heads[j] if j < len(heads) else str(j) for j in range(1, width)
                     if all(j >= len(cs) or cs[j].text().strip().lower() in empty_words for cs in rows)]
            return not empty, 'SLI の表の見出し: %s。すべての行が空の列: %s' % (heads, empty or 'なし')
        return False, 'SLI の表（1 列目にすべての SLI がある表）がない'

    def no_false_coverage(self):
        # QIUs that the stage 2 report covers in more than one row, whose rows together list the FRs the YAML traces to them.
        # A check that compares row by row reports them falsely. No line of the final report names one of them as a
        # disagreement, even as a false alarm: the statement is about the skill's check, which the report relays
        sec = bs.section((self.docs / '2-functional-requirements.md').read_text(encoding='utf-8'), bs.EXTRA['coverage'][1])
        got = next(((h, rs) for h, rs in bs.md_tables(sec or '') if len(h) >= 3), None)
        if got is None:
            return False, '第 2 段階の報告書に利用時の品質要求の対応の表がない（ケースの入力を確かめる）'
        head, rows = got
        fc = bs.col(head, ('fr', 'frs', '機能要件', 'functional requirements'), 2)
        union, count = {}, {}
        for r in rows:
            for q in bs.ids_in(r[0], 'QIU'):
                union.setdefault(q, set()).update(bs.ids_in(r[fc], 'FR'))
                count[q] = count.get(q, 0) + 1
        traced = {}
        for p in sorted((self.docs / 'fr').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            if d.get('status') != 'retired':
                for t in d.get('traces_to') or []:
                    traced.setdefault(str(t), set()).add(str(d['id']))
        safe = sorted((q for q in union if count[q] > 1 and union[q] == traced.get(q, set())), key=bs.id_key)
        # A line relays the check when it names the stage 2 table, calls the line a false alarm, or counts repeated lines
        # (「QIU-01 ×2」), which only a row-by-row comparison produces. Other mentions of these QIUs (an assumption, the
        # stage 3 coverage checklist) do not count
        words = re.compile(r'(利用時の品質要求の対応|quality-in-use coverage|false (?:alarm|positive)|誤検知|誤報|\bfalse\b\s*[:：]|×\s*\d)', re.I)
        bad = [ln.strip()[:100] for ln in self.report.splitlines() if words.search(ln) and set(bs.ids_in(ln, 'QIU')) & set(safe)]
        return not bad, '複数の行で対応する QIU: %s。それを食い違いとして挙げた行: %s' % (safe or 'なし', bad[:3] or 'なし')

    def tables_found(self):
        # No line of the final report says a report table was not found or not compared, unless it says there was none.
        # The list of the kinds of data (「主なデータ」 / "Main data") is not in the 0.3.0 templates, so any mention of it
        # means the skill still looked for it
        nf = re.compile(r'(見つから|not found|突き合わせ(?:なかった|られなかった|ていない)|not compared|could not (?:be )?(?:found|compared))', re.I)
        nothing = re.compile(r'(なし|ありません|0\s*件|\bnone\b|\bno tables?\b)', re.I)
        kinds = re.compile(r'(データの種類|主なデータ|kinds of data|main data)', re.I)
        bad = [ln.strip()[:120] for ln in self.report.splitlines() if (nf.search(ln) and not nothing.search(ln)) or kinds.search(ln)]
        return not bad, '表が見つからない、突き合わせなかった、0.3.0 にない表を求めると言う行: %s' % (bad[:3] or 'なし')

    def entry_column(self):
        # In the product quality matrix (the table with a 副特性 / sub-characteristic column), each entry-point QR
        # appears in the entry column (入口 / entry point) on the row of its sub-characteristic, named in the page's language
        terms = bs.LANG_DATA[self.lang]['terms']['characteristic']
        want = []
        for p in sorted((self.docs / 'qr').glob('*.yaml')):
            d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            key = bs.char_key(d.get('characteristic'))
            if d.get('status') != 'retired' and d.get('entry_point') and d.get('model') == 'product' and d.get('layer') != 'internal' and len(key) == 2:
                want.append((str(d['id']), terms.get(key[1], key[1])))
        for t in self.tables:
            names = [c.text().strip() for c in header_cells(t)]
            if not any('副特性' in n or 'sub-characteristic' in n.lower() for n in names):
                continue
            ent = [j for j, n in enumerate(names) if '入口' in n or '経由しない' in n or 'entry' in n.lower() or 'not through users' in n.lower()]
            if not ent:
                return False, '製品の品質のマトリクスに入口の列がない（見出し: %s）' % names[:5]
            k, miss = len(names) - ent[0], []  # the characteristic column uses rowspan, so count column positions from the right
            for q, sub in want:
                row = next((r for r in body_rows(t) if any(isinstance(c, Node) and c.tag == 'th' and c.text().strip().lower() == sub.lower()
                                                           for c in r.kids)), None)
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
