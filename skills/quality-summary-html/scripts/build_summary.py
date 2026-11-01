#!/usr/bin/env python3
"""Builds one quality summary HTML page from the outputs of the four cuj-to-slo stages (docs/quality).

  uv run --with pyyaml python3 build_summary.py [DOCS] [--out PATH] [--title TITLE] [--lang ja|en]

DOCS is the outputs directory (default ./docs/quality). --out defaults to DOCS/summary.html.
The page and the report are written in the language of the outputs: Japanese when the outputs are written in
Japanese, English otherwise. --lang overrides that. --title defaults to the language's title pattern
(「<name>の品質」 or "<name> quality") with system.name from context.yaml.

Tables are built from the YAML items (artifacts.md). The Markdown reports are used only for each stage's title
and for the tables that exist only in the reports (not targeted, functions considered and not added, the explanation
of internal quality derived from external quality, kinds of data, out of scope); a table that is not found is left
out and reported. The report tables compared with the YAML (quality-in-use coverage, functions by CUJ step,
internal quality derived from external quality, allocation) are reported as not compared when they are not found.
Labels, terms and report messages are in assets/lang/<lang>.json.
The same input always produces the same HTML.
Exit codes: 0 means the page was written (0 even when there are inconsistencies), 2 means an input error,
1 means the written HTML failed its own check.
"""
import argparse
import html
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets'
LANGS = ('ja', 'en')
REPORTS = {1: '1-quality-in-use.md', 2: '2-functional-requirements.md',
           3: '3-product-quality.md', 4: '4-nfr-slo.md'}
KINDS = ('qiu', 'kpi', 'fr', 'frp', 'qr', 'nfr', 'sli', 'ebp')
STAGE_KINDS = {1: ('qiu', 'kpi'), 2: ('fr', 'frp'), 3: ('qr',), 4: ('nfr', 'sli', 'ebp')}
HANDLINGS = ('emphasized', 'minimum-line', 'excluded')
HCLS = {'emphasized': 'qr-emph', 'minimum-line': 'qr-base', 'excluded': 'qr-out'}
NFR_KINDS = ('slo', 'gate', 'audit', 'monitor')
CONTEXT_KEYS = ('device', 'network', 'user_type', 'task', 'environment', 'other')
# Report-only tables: (stage, candidate headings, minimum number of columns). Headings are the glossary's Japanese and the template's English
EXTRA = {
    'excl': (1, ('対象にしない', 'Not targeted'), 3),
    'coverage': (2, ('利用時の品質要求の対応', 'Quality-in-use coverage'), 3),
    'steps': (2, ('CUJ の手順ごとの機能', '手順ごとの機能', 'Functions by CUJ step'), 3),
    'notadd': (2, ('検討して加えなかった機能', 'Functions considered and not added'), 3),
    'derived': (3, ('外部品質から導いた内部品質', 'Internal quality derived from external quality'), 3),
    'alloc': (4, ('割り当て', 'Allocation'), 6),
}
DATA_KINDS = ('主なデータ', 'データの種類', 'Main data', 'Kinds of data')
DATA_WHO = ('データを作る人', 'Data producers')
NONE_WORDS = ('—', '–', '-', 'なし', 'none', 'n/a')
# The quality models in the glossary's order: product characteristics with their sub-characteristics, and data characteristics
PRODUCT_MODEL = [
    ('functional suitability', ('functional completeness', 'functional correctness', 'functional appropriateness')),
    ('performance efficiency', ('time behaviour', 'resource utilization', 'capacity')),
    ('compatibility', ('co-existence', 'interoperability')),
    ('usability', ('appropriateness recognizability', 'learnability', 'operability', 'user error protection',
                   'user interface aesthetics', 'accessibility')),
    ('reliability', ('maturity', 'availability', 'fault tolerance', 'recoverability')),
    ('security', ('confidentiality', 'integrity', 'non-repudiation', 'accountability', 'authenticity')),
    ('maintainability', ('modularity', 'reusability', 'analysability', 'modifiability', 'testability')),
    ('portability', ('adaptability', 'installability', 'replaceability')),
]
DATA_MODEL = ('accuracy', 'completeness', 'consistency', 'credibility', 'currentness',
              'accessibility', 'compliance', 'confidentiality', 'efficiency', 'precision', 'traceability', 'understandability',
              'availability', 'portability', 'recoverability')


def read_lang(code):
    return json.loads((ASSETS / 'lang' / ('%s.json' % code)).read_text(encoding='utf-8'))


LANG_DATA = {c: read_lang(c) for c in LANGS}
LANG = {}
UNKNOWN = Counter()


def set_lang(code):
    """Chooses the language of the page and the report. Japanese until this is called"""
    LANG.clear()
    LANG.update(LANG_DATA[code])
    LANG['code'] = code


set_lang('ja')


def T(key, **kw):
    """A label or message of the current language, with its {placeholders} filled in"""
    t = LANG['text'][key]
    return t.format(**kw) if kw else t


def paren(x):
    return T('paren', x=x)


def quote(x):
    return T('quote', x=x)


def join(xs):
    return T('sep').join(xs)


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def die_t(key, lang=None, **kw):
    """Stops on an input error. Until the language is known, the message is printed in every language"""
    die('\n'.join(LANG_DATA[c]['text'][key].format(**kw) for c in ((lang,) if lang else ('en', 'ja'))))


# ---------- Language of the outputs ----------
KANA = re.compile(r'[぀-ヿ]')
LATIN = re.compile(r'[A-Za-z]')


def strings(v):
    """Every string value in a YAML value (keys are left out)"""
    if isinstance(v, dict):
        for x in v.values():
            yield from strings(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from strings(x)
    elif isinstance(v, str):
        yield v


def detect_lang(texts):
    """ja when kana make up a tenth or more of the letters (kana and Latin), en otherwise. Japanese prose always has
    kana; IDs, enum values and English terms are Latin. Outputs in a language other than Japanese get English"""
    kana = latin = 0
    for t in texts:
        kana += len(KANA.findall(t))
        latin += len(LATIN.findall(t))
    return 'ja' if kana and kana * 10 >= kana + latin else 'en'


# ---------- Values and terms ----------
def s(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'true' if v else 'false'
    return str(v).strip()


def L(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [s(x) for x in v if s(x)]
    return [s(v)] if s(v) else []


def term(group, v, strict=True):
    """Turns an English YAML value into the term of the current language. A value not in the table is returned as is, and reported when strict"""
    if v is None or v == '':
        return ''
    got = LANG['terms'][group].get(s(v))
    if got is None:
        if strict:
            UNKNOWN['%s: %s' % (group, s(v))] += 1
        return s(v)
    return got


def char_key(v):
    t = re.sub(r'\s+', ' ', s(v)).lower()
    for a, b in (('behavior', 'behaviour'), ('analyzability', 'analysability'), ('utilisation', 'utilization')):
        t = t.replace(a, b)
    return tuple(p.strip() for p in t.split('>') if p.strip())


def char_text(v):
    return ' > '.join(term('characteristic', p) for p in char_key(v))


def window_text(v):
    w = s(v)
    m = re.fullmatch(r'(\d+)\s*-?\s*days?\s+rolling', w, re.I) or re.fullmatch(r'rolling\s+(\d+)\s*-?\s*days?', w, re.I)
    if m:
        return T('window_rolling', n=m.group(1))
    return T('window_calendar_month') if w.lower() in ('calendar month', 'calendar-month') else w


def window_days(v):
    w = s(v)
    m = re.search(r'(\d+)\s*(?:-?\s*days?\b|日|d\b)', w, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:-?\s*weeks?\b|週|w\b)', w, re.I)
    return int(m.group(1)) * 7 if m else None


def exhaust(days, rate):
    try:
        r = float(s(rate))
    except ValueError:
        return '—'
    if not days or r <= 0:
        return '—'
    x = days / r
    n = '%d' % round(x) if abs(x - round(x)) < 0.05 else '%.1f' % x
    return T('days_one' if n == '1' else 'days', n=n)


def context_text(cu):
    if isinstance(cu, dict):
        vals = [s(cu.get(k)) for k in CONTEXT_KEYS] + [s(v) for k, v in cu.items() if k not in CONTEXT_KEYS]
        return join(v for v in vals if v)
    return s(cu)


def sli_parts(x):
    """Definitions of an SLI's good events and valid events. The elements are chosen by function (such as OK ÷ VALID)"""
    el = x.get('elements') if isinstance(x.get('elements'), dict) else {}
    m = re.match(r'^\s*([A-Za-z_][\w-]*)\s*(?:÷|/)\s*([A-Za-z_][\w-]*)\s*$', s(x.get('function')))
    num, den = (m.group(1), m.group(2)) if m else (next((k for k in el if k.upper() != 'VALID'), 'GOOD'), 'VALID')

    def d(k):
        v = el.get(k)
        return s(v.get('definition')) if isinstance(v, dict) else s(v)
    return d(num), d(den)


# The parsers below read text in either language: 、 and 。 for Japanese, commas and full stops for English
ABBR = re.compile(r'(?:\b(?:e\.g|i\.e|etc|vs|cf|approx|incl)|(?<![A-Za-z])[A-Za-z])$', re.I)


def split_top(t):
    """Splits a list at its top-level separators: 、，or a comma that is not inside a number. A leading "and" is dropped"""
    out, cur, depth = [], '', 0
    for i, ch in enumerate(t):
        depth += ch in '（(「'
        depth -= ch in '）)」'
        if depth == 0 and (ch in '、，' or (ch == ',' and not (t[i - 1:i].isdigit() and t[i + 1:i + 2].isdigit()))):
            out.append(cur)
            cur = ''
        else:
            cur += ch
    return [re.sub(r'^(?:and|or)\s+', '', x.strip()) for x in out + [cur] if x.strip()]


def first_sentence(t):
    """The text up to the first 。 or full stop outside brackets, without the stop"""
    depth = 0
    for i, ch in enumerate(t):
        depth += ch in '（(「'
        depth -= ch in '）)」'
        if depth:
            continue
        if ch == '。':
            return t[:i]
        if ch == '.' and (i + 1 == len(t) or t[i + 1].isspace()) and not ABBR.search(t[:i]):
            return t[:i]
    return t


def split_who(x):
    m = re.match(r'^(.+?)\s*[（(](.+)[）)]$', x)
    return (m.group(1), m.group(2)) if m else (x, '')


# ---------- ID ----------
ID_HEAD = re.compile(r'(?<![A-Za-z0-9_\-])(FRP|KGI|OUT|USR|CUJ|QIU|KPI|FR|QR|NFR|SLI|EBP)-(\d{2,})(?!\d)')
ID_CONT = re.compile(r'(、|，|, ?|・|〜|～|–)(\d+)(?![\d.])')
RANGE_SEP = ('〜', '～', '–')


def id_runs(text):
    """Yields runs of IDs as (start, end, prefix, [(separator, number, display)]). Also reads omitted prefixes, as in 「QR-36〜42・47」 or "QR-36–42" """
    pos = 0
    while True:
        m = ID_HEAD.search(text, pos)
        if not m:
            return
        p, width = m.group(1), len(m.group(2))
        parts, end = [('', m.group(2), m.group(0))], m.end()
        while True:
            c = ID_CONT.match(text, end)
            if c and len(c.group(2)) == width:
                parts.append((c.group(1), c.group(2), c.group(2)))
                end = c.end()
                continue
            r = re.compile(r'(〜|～|–)%s-(\d{%d})(?!\d)' % (p, width)).match(text, end)
            if r:
                parts.append((r.group(1), r.group(2), '%s-%s' % (p, r.group(2))))
                end = r.end()
                continue
            break
        yield m.start(), end, p, parts
        pos = end


def ids_in(text, prefix=None):
    """Returns the IDs in a text in order of appearance, expanding ranges (〜 or –)"""
    out = []
    for _, _, p, parts in id_runs(s(text)):
        if prefix and p != prefix:
            continue
        prev = None
        for sep, n, _ in parts:
            k = int(n)
            ks = range(prev + 1, k + 1) if sep in RANGE_SEP and prev is not None and k > prev else (k,)
            for x in ks:
                i = '%s-%0*d' % (p, len(n), x)
                if i not in out:
                    out.append(i)
            prev = k
    return out


def id_key(i):
    m = re.match(r'([A-Z]+)-(\d+)$', s(i))
    return (m.group(1), int(m.group(2))) if m else (s(i), 0)


# ---------- Reports ----------
def norm(t):
    return re.sub(r'[\s　]+', ' ', s(t)).lower()


def step_key(t):
    """Key for comparing CUJ steps. Ignores full-width vs half-width forms and whitespace"""
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s(t)))


def section(text, aliases):
    """Body of the section whose heading matches one of aliases (up to the next heading at the same or a higher level). None if there is none"""
    al = {norm(x) for x in aliases}
    lines = (text or '').splitlines()
    for k, ln in enumerate(lines):
        m = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', ln)
        if not m or (norm(m.group(2)) not in al and norm(re.sub(r'[（(][^（）()]*[）)]$', '', m.group(2))) not in al):
            continue
        level, out = len(m.group(1)), []
        for ln2 in lines[k + 1:]:
            m2 = re.match(r'^(#{1,6})\s', ln2)
            if m2 and len(m2.group(1)) <= level:
                break
            out.append(ln2)
        return '\n'.join(out)
    return None


def split_row(ln):
    t = ln.strip()
    t = t[1:] if t.startswith('|') else t
    t = t[:-1] if t.endswith('|') and not t.endswith('\\|') else t
    return [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', t)]


def md_tables(text):
    """Returns the tables in a text as (header row, body rows). A row is a list of cells"""
    res, cur = [], []
    for ln in (text or '').splitlines() + ['']:
        if ln.lstrip().startswith('|'):
            cur.append(split_row(ln))
            continue
        if len(cur) >= 2 and all(re.fullmatch(r':?-+:?', c.replace(' ', '')) for c in cur[1] if c):
            res.append((cur[0], [r + [''] * (len(cur[0]) - len(r)) for r in cur[2:]]))
        cur = []
    return res


def col(head, names, default):
    """Index of the column whose heading matches one of names. default if there is none"""
    return next((j for j, h in enumerate(head) if norm(h) in names), default)


def line_value(text, labels):
    """Value of a 「label: value」 line. None if there is none"""
    al = {norm(x) for x in labels}
    for ln in (text or '').splitlines():
        m = re.match(r'^\s*(?:[-*]\s+)?(?:\*\*)?([^:：*|#]+?)(?:\*\*)?\s*[:：]\s*(.+)$', ln)
        if m and norm(m.group(1)) in al:
            return m.group(2).strip()
    return None


# ---------- HTML parts ----------
def esc(v):
    return html.escape(s(v), quote=False)


def attr(v):
    return html.escape(s(v), quote=True)


def none():
    return '<span class="none">—</span>'


def wrap(t):
    return '<div class="tbl-wrap">%s</div>' % t


def tbl(cols, rows, cls=''):
    """cols is [(heading, width class)], rows is [(row id, [cell HTML])]. An empty cell shows 「—」"""
    th = ''.join('<th scope="col" class="%s">%s</th>' % (w, esc(c)) for c, w in cols)
    body = []
    for rid, cells in rows:
        tds = ''.join('<td class="%s">%s</td>' % (w, x if x else none()) for (_, w), x in zip(cols, cells))
        body.append('<tr%s>%s</tr>' % (' id="%s"' % rid if rid else '', tds))
    return '<table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
        ' class="%s"' % cls if cls else '', th, ''.join(body))


def toggle(tid, title, count, body, open_=False):
    return ('<details class="tbl" id="%s"%s><summary><span class="t-title">%s</span><span class="t-count">%s</span>'
            '<span class="chev" aria-hidden="true"></span></summary><div class="tbl-body">%s</div></details>'
            % (tid, ' open' if open_ else '', esc(title), esc(count), body))


def badge(h):
    return '<span class="badge %s">%s</span>' % (HCLS.get(h, ''), esc(term('handling', h)))


def legend(internal=False):
    items = ''.join('<span class="lg"><span class="chip %s">QR</span>%s</span>' % (HCLS[h], esc(term('handling', h)))
                    for h in HANDLINGS)
    if internal:
        items += '<span class="lg"><span class="tag">%s</span>%s</span>' % (esc(T('internal_tag')), esc(T('internal_quality')))
    return '<div class="legend">%s</div>' % items


def observable(v):
    if v is True:
        return esc(T('observable_yes'))
    if v is False:
        return '<span class="badge blind">%s</span>' % esc(T('observable_no'))
    return ''


def dots(items):
    return ' · '.join('<span class="nb">%s</span>' % esc(x) for x in items)


def ul(items):
    return '<ul>' + ''.join('<li>%s</li>' % esc(x) for x in items) + '</ul>'


class Build:
    def __init__(self, docs, yaml_mod, out, title=None, lang=None):
        self.docs, self.yaml, self.out = docs, yaml_mod, out
        self.pending, self.notes, self.used, self.skipped = [], [], [], []
        self.checked, self.unchecked = [], []
        self.dead = Counter()
        self.toc = defaultdict(list)
        self.load(lang)
        if lang:
            self.lang, self.lang_how = lang, 'lang_given'
        else:
            texts = [t for v in [self.ctx] + [v for kind in KINDS for v in self.items[kind].values()] for t in strings(v)]
            self.lang, self.lang_how = detect_lang(texts + list(self.md.values())), 'lang_detected'
        set_lang(self.lang)
        self.issues = [T(k, **kw) for k, kw in self.pending]
        self.relate()
        self.check()
        self.title = title or self.default_title()

    # ---------- Loading ----------
    def read_yaml(self, p):
        try:
            return self.yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception as e:
            self.pending.append(('issue_yaml', {'path': p.relative_to(self.docs), 'err': s(e).splitlines()[0]}))
            return None

    def load(self, lang):
        """Reads the YAML items and the reports. Problems wait in self.pending until the language is known"""
        cp = self.docs / 'context.yaml'
        if not cp.is_file():
            die_t('die_no_context', lang, path=cp)
        ctx = self.read_yaml(cp)
        if not isinstance(ctx, dict):
            die_t('die_bad_context', lang, path=cp)
        self.ctx = ctx

        def entries(key):
            out = []
            for x in ctx.get(key) or []:
                if isinstance(x, dict) and s(x.get('id')):
                    x['id'] = s(x['id'])
                    out.append(x)
            return out
        self.system = ctx.get('system') if isinstance(ctx.get('system'), dict) else {}
        self.kgis, self.outs, self.users, self.cujs = entries('kgis'), entries('outcomes'), entries('users'), entries('cujs')
        self.items = {}
        for kind in KINDS:
            got, d = {}, self.docs / kind
            for p in (sorted(d.glob('*.yaml')) if d.is_dir() else []):
                v = self.read_yaml(p)
                if not isinstance(v, dict) or not s(v.get('id')):
                    if v is not None:
                        self.pending.append(('issue_no_id', {'path': '%s/%s' % (kind, p.name)}))
                    continue
                v['id'] = s(v['id'])
                if p.stem != v['id']:
                    self.pending.append(('issue_file_id', {'path': '%s/%s' % (kind, p.name), 'id': v['id']}))
                got[v['id']] = v
            self.items[kind] = got
        self.md = {n: (self.docs / f).read_text(encoding='utf-8') if (self.docs / f).is_file() else ''
                   for n, f in REPORTS.items()}

    def live(self, kind):
        return sorted((v for v in self.items[kind].values() if s(v.get('status')) != 'retired'), key=lambda v: id_key(v['id']))

    def extra(self, key):
        n, aliases, ncol = EXTRA[key]
        sec = section(self.md[n], aliases)
        if sec is not None:
            for head, rows in md_tables(sec):
                if len(head) >= ncol:
                    return head, rows
        return None

    def extra_rows(self, key, label):
        got = self.extra(key)
        if got is None:
            self.skipped.append(label + paren(REPORTS[EXTRA[key][0]]))
            return None
        self.used.append(label)
        return got[1]

    # ---------- Relations ----------
    def relate(self):
        self.qius, self.kpis, self.frs = self.live('qiu'), self.live('kpi'), self.live('fr')
        self.qrs, self.nfrs, self.slis, self.ebps = self.live('qr'), self.live('nfr'), self.live('sli'), self.live('ebp')
        self.has = {1: True, 2: bool(self.frs), 3: bool(self.qrs), 4: bool(self.nfrs)}
        self.user_by = {u['id']: u for u in self.users}
        self.cuj_by = {c['id']: c for c in self.cujs}
        self.qiu_by = {q['id']: q for q in self.qius}
        self.fr_by = {f['id']: f for f in self.frs}
        self.qr_by = {q['id']: q for q in self.qrs}
        self.nfr_by = {n['id']: n for n in self.nfrs}
        self.sli_by = {x['id']: x for x in self.slis}
        self.kpi_ids = {k['id'] for k in self.kpis}
        self.TITLE = {i: s(v.get('title')) for kind in KINDS for i, v in self.items[kind].items()}
        self.qiu_cuj = {q['id']: s(q.get('cuj')) for q in self.qius}
        self.fr_of_qiu = defaultdict(list)
        for f in self.frs:
            for x in L(f.get('traces_to')):
                if x.startswith('QIU-'):
                    self.fr_of_qiu[x].append(f['id'])
        self.qr_of_qiu = defaultdict(list)
        for q in self.qrs:
            for x in L(q.get('traces_to')):
                self.qr_of_qiu[x].append(q['id'])
        self.qr_cujs = {q['id']: sorted({self.qiu_cuj[x] for x in L(q.get('traces_to')) if self.qiu_cuj.get(x)}, key=id_key)
                        for q in self.qrs}
        self.handling = {q['id']: s(q.get('handling')) for q in self.qrs}
        self.internal = {q['id'] for q in self.qrs if s(q.get('layer')) == 'internal'}
        self.entry = [q['id'] for q in self.qrs if q.get('entry_point')]
        self.entry_type = {q['id']: term('entry_type', q['entry_point'].get('type'))
                           for q in self.qrs if isinstance(q.get('entry_point'), dict)}
        self.nfr_of_qr = defaultdict(list)
        for n in self.nfrs:
            for x in L(n.get('from')):
                self.nfr_of_qr[x].append(n['id'])
        self.kind = {n['id']: s(n.get('kind')) for n in self.nfrs}
        self.sli_of = {n['id']: s(self.slo(n).get('sli')) for n in self.nfrs if self.kind[n['id']] == 'slo' and s(self.slo(n).get('sli'))}
        self.kpi_of = defaultdict(list)
        for q in self.qius:
            if s(q.get('kpi')) in self.kpi_ids:
                self.kpi_of[q['id']].append(s(q.get('kpi')))
        for k in self.kpis:
            for x in L(k.get('overlaps_with')):
                if k['id'] not in self.kpi_of[x]:
                    self.kpi_of[x].append(k['id'])
        self.out_scope = {}
        alloc = self.extra('alloc')
        for r in (alloc[1] if alloc else []):
            qs, v = ids_in(r[0], 'QR'), r[5].strip()
            if qs and v and v.lower() not in NONE_WORDS:
                self.out_scope[qs[0]] = v

    @staticmethod
    def slo(n):
        return n.get('slo') if isinstance(n.get('slo'), dict) else {}

    def measure(self, qi):
        m = self.qiu_by[qi].get('measure')
        return m if isinstance(m, dict) else {}

    def score(self, q):
        sc = q.get('score')
        if not isinstance(sc, dict):
            return None
        try:
            return int(sc.get('impact')), int(sc.get('likelihood'))
        except (TypeError, ValueError):
            return None

    def qr_key(self, q):
        h = self.handling.get(q, '')
        return (HANDLINGS.index(h) if h in HANDLINGS else 3, q in self.internal, id_key(q))

    # ---------- Cross-checking the outputs ----------
    def check(self):
        known = {x['id']: 'live' for x in self.kgis + self.outs + self.users + self.cujs}
        for kind in KINDS:
            for i, v in self.items[kind].items():
                known[i] = 'retired' if s(v.get('status')) == 'retired' else 'live'
        self.known = known

        def ref(owner, field, ids):
            for i in ids:
                if known.get(i) is None:
                    self.issues.append(T('issue_ref_missing', owner=owner, field=field, id=i))
                elif known[i] == 'retired':
                    self.issues.append(T('issue_ref_retired', owner=owner, field=field, id=i))

        def fmt(xs):
            return join(sorted(xs, key=id_key)) or T('none')

        for o in self.outs:
            ref(o['id'], 'kgis', L(o.get('kgis')))
        for c in self.cujs:
            ref(c['id'], 'users', L(c.get('users')))
            ref(c['id'], 'outcomes', L(c.get('outcomes')))
        for q in self.qius:
            for f in ('user', 'cuj', 'outcomes', 'kpi'):
                ref(q['id'], f, L(q.get(f)))
        for k in self.kpis:
            ref(k['id'], 'outcome', L(k.get('outcome')))
            ref(k['id'], 'overlaps_with', L(k.get('overlaps_with')))
        steps = {c['id']: L(c.get('steps')) for c in self.cujs}
        for f in self.frs:
            for fld in ('cuj', 'traces_to', 'proposal', 'extends'):
                ref(f['id'], fld, L(f.get(fld)))
            c, st = s(f.get('cuj')), s(f.get('cuj_step'))
            if st and steps.get(c) and st not in steps[c]:
                self.issues.append(T('issue_cuj_step', fr=f['id'], step=st, cuj=c))
        for q in self.qrs:
            for fld in ('applies_to', 'traces_to', 'implies_internal'):
                ref(q['id'], fld, L(q.get(fld)))
            for cf in q.get('conflicts') or []:
                if isinstance(cf, dict):
                    ref(q['id'], 'conflicts', L(cf.get('with')))
            if not L(q.get('traces_to')) and not q.get('entry_point'):
                self.issues.append(T('issue_no_trace', id=q['id']))
            if s(q.get('handling')) not in HANDLINGS:
                self.issues.append(T('issue_handling', id=q['id'], value=s(q.get('handling'))))
        for n in self.nfrs:
            ref(n['id'], 'from', L(n.get('from')))
            ref(n['id'], 'cuj', L(n.get('cuj')))
            if self.kind[n['id']] not in NFR_KINDS:
                self.issues.append(T('issue_kind', id=n['id'], value=self.kind[n['id']]))
            if self.kind[n['id']] == 'slo':
                if not s(self.slo(n).get('sli')):
                    self.issues.append(T('issue_no_sli', id=n['id']))
                ref(n['id'], 'slo.sli', L(self.slo(n).get('sli')))
                ref(n['id'], 'slo.policy', L(self.slo(n).get('policy')))
        for x in self.slis:
            ref(x['id'], 'refs', L(x.get('refs')))
        for e in self.ebps:
            ref(e['id'], 'applies_to', L(e.get('applies_to')))
        for q in self.qius:
            k = s(q.get('kpi'))
            if k in self.kpi_ids and q['id'] not in L(self.items['kpi'][k].get('overlaps_with')):
                self.issues.append(T('issue_kpi_overlap', qiu=q['id'], kpi=k))

        # Report tables against the YAML. If the stage to compare exists but its table is not found, report that it was not compared
        def compared(key, label, needed):
            got = self.extra(key)
            if got:
                self.checked.append(label)
            elif needed:
                self.unchecked.append(label + paren(REPORTS[EXTRA[key][0]]))
            return got
        cov = compared('coverage', T('tbl_coverage'), self.has[2])
        if cov:
            head, rows = cov
            fc = col(head, ('fr', 'frs', '機能要件', 'functional requirements'), 2)
            for r in rows:
                for qi in ids_in(r[0], 'QIU'):
                    if qi in self.qiu_by:
                        listed, derived = set(ids_in(r[fc], 'FR')), set(self.fr_of_qiu.get(qi, []))
                        if listed != derived:
                            self.issues.append(T('issue_coverage', qiu=qi, file=REPORTS[2], table=quote(T('tbl_coverage')),
                                                 report=fmt(listed - derived), yaml=fmt(derived - listed)))
        st = compared('steps', T('tbl_steps'), self.has[2])
        if st:
            self.check_steps(*st)
        der = compared('derived', T('derived'), bool(self.internal))
        if der:
            rep = {(e, i) for r in der[1] for i in ids_in(r[1], 'QR') for e in ids_in(r[0], 'QR')}
            yml = {(q['id'], i) for q in self.qrs for i in L(q.get('implies_internal'))}
            if rep != yml:
                self.issues.append(T('issue_derived', file=REPORTS[3], table=quote(T('derived')),
                                     report=fmt('%s→%s' % x for x in rep - yml), yaml=fmt('%s→%s' % x for x in yml - rep)))
        alloc = compared('alloc', T('tbl_alloc'), self.has[4])
        for r in (alloc[1] if alloc else []):
            qs = ids_in(r[0], 'QR')
            if qs and qs[0] in self.qr_by:
                listed, derived = set(ids_in(r[3], 'NFR')), set(self.nfr_of_qr.get(qs[0], []))
                if listed != derived:
                    self.issues.append(T('issue_alloc', qr=qs[0], file=REPORTS[4], table=quote(T('tbl_alloc')),
                                         report=fmt(listed - derived), yaml=fmt(derived - listed)))
        only = sorted({i for n in REPORTS for i in ids_in(self.md[n]) if i not in known}, key=id_key)
        if only:
            self.notes.append(T('note_only_in_reports', ids=join(only)))

    def check_steps(self, head, rows):
        """Compares where stage 2's functions-by-CUJ-step table lists each FR with the FR's cuj and cuj_step.
        Rows without a CUJ (such as 「どの CUJ にもない」, in no CUJ) and FRs without cuj in the YAML are not compared.
        A row with an empty CUJ cell takes the CUJ of the row above"""
        fc, sc = col(head, ('fr', 'frs', '機能要件', 'functional requirements'), 2), col(head, ('手順', 'step', 'steps'), 1)
        steps = {c['id']: {step_key(x): x for x in L(c.get('steps'))} for c in self.cujs}
        table = quote(T('tbl_steps'))
        pos, cur = defaultdict(set), []
        for r in rows:
            if r[0].strip():
                cur = [c for c in ids_in(r[0], 'CUJ') if c in steps]
            if not cur:
                continue
            t, k = r[sc].strip(), ''
            if t and not t.startswith(('（', '(')) and t.lower() not in NONE_WORDS:
                k = step_key(t)
                if not any(k in steps[c] for c in cur):
                    # The position is unknown, so the FRs in this row are covered by this single report
                    self.issues.append(T('issue_step_unknown', file=REPORTS[2], table=table, step=quote(t), cujs=join(cur)))
                    k = None
            for f in ids_in(r[fc], 'FR'):
                if self.known.get(f) == 'retired':
                    self.issues.append(T('issue_step_retired', fr=f, file=REPORTS[2], table=table))
                for c in cur:
                    pos[f].add((c, k))

        def where(c, k):
            if k is None:
                return c + paren(T('step_not_in_context'))
            return T('cuj_step_at', cuj=c, step=steps[c].get(k, k)) if k else c
        for f in self.frs:
            c, k = s(f.get('cuj')), step_key(f.get('cuj_step'))
            if c not in steps:
                continue
            k = k if k in steps[c] else ''  # a cuj_step that is not one of the steps is already reported by the reference check above
            mine = {p for p in pos[f['id']] if p[0] == c}
            if (c, None) in mine or ((c, k) in mine if k else mine):
                continue
            rep = sorted(pos[f['id']], key=lambda p: (id_key(p[0]), p[1] or ''))
            self.issues.append(T('issue_step_place', fr=f['id'], file=REPORTS[2], table=table,
                                 report=join(where(*p) for p in rep) or T('not_listed'), yaml=where(c, k)))

    # ---------- Title and date ----------
    def default_title(self):
        name = re.sub(r'\s*[（(][^（）()]*[）)]\s*$', '', s(self.system.get('name')))
        return T('title', name=name or self.docs.parent.parent.name)

    def stage_title(self, n):
        for ln in self.md[n].splitlines():
            m = re.match(r'^#\s+(.+)$', ln)
            if m:
                return re.split(r'[:：]', m.group(1), 1)[0].strip() or T('stage_title_%d' % n)
        return T('stage_title_%d' % n)

    def stage_date(self, n):
        ds = re.findall(r'(?:更新|Updated)\s*[:：]\s*(\d{4}-\d{2}-\d{2})', self.md[n])
        for kind in STAGE_KINDS[n]:
            for v in self.items[kind].values():
                for c in v.get('changelog') or []:
                    if isinstance(c, dict) and re.match(r'\d{4}-\d{2}-\d{2}', s(c.get('date'))):
                        ds.append(s(c.get('date'))[:10])
        return max(ds) if ds else ''

    # ---------- Links and tooltips ----------
    def prepare_links(self):
        A = {x['id'] for x in self.kgis + self.outs + self.users + self.cujs} | set(self.qiu_by) | self.kpi_ids
        if self.has[2]:
            A |= set(self.fr_by)
        if self.has[3]:
            A |= set(self.qr_by)
        if self.has[4]:
            A |= set(self.nfr_by) | set(self.sli_by) | {e['id'] for e in self.ebps}
        self.A = A
        TIP = {}
        for k in self.kgis:
            TIP[k['id']] = '%s %s' % (k['id'], s(k.get('name')))
        for o in self.outs:
            TIP[o['id']] = '%s %s' % (o['id'], s(o.get('statement')))
        for u in self.users:
            TIP[u['id']] = '%s %s' % (u['id'], s(u.get('name'))) + paren(term('category', u.get('category')))
        for c in self.cujs:
            names = join(s(self.user_by.get(x, {}).get('name')) for x in L(c.get('users')))
            TIP[c['id']] = '%s %s' % (c['id'], s(c.get('name'))) + (paren(names) if names else '')
        for kind in KINDS:
            for i, v in self.items[kind].items():
                t = '%s %s' % (i, s(v.get('title')))
                st = s(v.get('status'))
                if st == 'retired':
                    t += paren(term('status', 'retired'))
                elif kind == 'frp':
                    t += paren(term('status', st))
                elif kind == 'qr':
                    t += '\n' + term('handling', v.get('handling')) + (paren(T('internal_quality')) if s(v.get('layer')) == 'internal' else '')
                elif kind == 'nfr':
                    t += paren(term('kind', v.get('kind')))
                TIP[i] = t
        self.TIP = TIP

    def a(self, i, label=None, chip=False, tip=None):
        lab = esc(i if label is None else label)
        cls = 'id' + (' chip ' + HCLS.get(self.handling.get(i, ''), '') if chip else '')
        t = self.TIP.get(i, '') if tip is None else tip
        ta = ' data-tip="%s"' % attr(t) if t else ''
        if i in self.A:
            return '<a class="%s" href="#%s"%s>%s</a>' % (cls.strip(), i, ta, lab)
        self.dead[i] += 1
        return '<span class="%s dead"%s>%s</span>' % (cls.strip(), ta, lab)

    def linkify(self, h, chip=False):
        out, last = [], 0
        for st, en, p, parts in id_runs(h):
            out.append(h[last:st])
            for sep, n, label in parts:
                out.append(sep + self.a('%s-%s' % (p, n), label, chip=chip and p == 'QR'))
            last = en
        out.append(h[last:])
        return ''.join(out)

    def cell(self, v, chip=False):
        t = s(v)
        for x in ('（未解決の点を参照）', '(see open gaps)'):
            t = t.replace(x, '')
        if not t:
            return ''
        h = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(t))
        return self.linkify(h, chip)

    def ids(self, ids):
        ids = [x for x in ids if x]
        return join(self.a(x) for x in ids) if ids else ''

    def nums(self, ids):
        if not ids:
            return none()
        return '<span class="nums">' + ''.join(self.a(i, i.split('-', 1)[1]) for i in ids) + '</span>'

    def defid(self, i, name=None):
        return '<span class="def-id">%s</span>' % esc(i) + ('<span class="def-name">%s</span>' % self.cell(name) if s(name) else '')

    def lead(self, i):
        t = self.TITLE.get(i, '')
        return '<strong class="lead">%s</strong>' % esc(t) if t else ''

    def with_sub(self, i, text):
        return self.a(i) + ('<span class="sub">%s</span>' % esc(text) if s(text) else '')

    def users_cell(self, ids):
        return ''.join(self.with_sub(u, s(self.user_by.get(u, {}).get('name'))) for u in ids)

    def cuj_cell(self, c):
        return self.with_sub(c, s(self.cuj_by.get(c, {}).get('name'))) if c else ''

    def frac(self, n, d):
        if not s(n) and not s(d):
            return ''
        return '<span class="frac"><span class="fr-n">%s</span><span class="fr-d">%s</span></span>' % (
            self.cell(n) or none(), self.cell(d) or none())

    def basis(self, x):
        b, n = term('basis', x.get('basis')), s(x.get('basis_note'))
        return self.cell(b + (paren(n) if n else ''))

    def listing(self, items, cls):
        return '<%s class="%s">%s</%s>' % ('ol' if cls == 'steps' else 'ul', cls, ''.join('<li>%s</li>' % self.cell(x) for x in items),
                                          'ol' if cls == 'steps' else 'ul') if items else ''

    def handling_cell(self, q):
        h, r = s(q.get('handling')), s(q.get('handling_reason'))
        # The reason may start with the handling's name, in the language it was written in
        for name in sorted(({LANG_DATA[c]['terms']['handling'].get(h, '') for c in LANGS} | {h}) - {''}):
            r = re.sub(r'^\s*%s\s*[:：]\s*' % re.escape(name), '', r)
        r = first_sentence(r)
        return badge(h) + ('<span class="note">%s</span>' % self.cell(r) if r else '')

    def tog(self, n, tid, title, count, body, open_=False):
        if n:
            self.toc[n].append((tid, title))
        return toggle(tid, title, count, body, open_)

    # ---------- Traceability ----------
    def qr_line(self, q):
        tag = '<span class="tag">%s</span>' % esc(T('internal_tag')) if q in self.internal else ''
        return '<div class="qr-line">%s<span class="qr-name">%s%s</span></div>' % (self.a(q, chip=True), esc(self.TITLE.get(q)), tag)

    def nfr_cell(self, q):
        items = []
        for n in self.nfr_of_qr.get(q, []):
            k = self.kind.get(n, '')
            h = self.a(n) + '<span class="ntype%s">%s</span>' % (' is-slo' if k == 'slo' else '', esc(term('kind', k)))
            if self.sli_of.get(n):
                h += self.a(self.sli_of[n])
            items.append('<span class="nfr-item">%s</span>' % h)
        if q in self.out_scope:
            items.append('<span class="nfr-item none" data-tip="%s">%s</span>' % (attr(self.out_scope[q]), esc(T('out_of_scope'))))
        return ''.join(items) or none()

    def trace(self):
        cols = [('CUJ', 'c-cuj'), ('QIU', 'c-qiu')] + ([('FR', 'c-fr')] if self.has[2] else []) + \
               ([('QR', 'c-qr')] if self.has[3] else []) + ([('NFR / SLI', 'c-nfr')] if self.has[4] else [])
        nc = len(cols)
        out = ['<table class="trace"><thead><tr>%s</tr></thead>' % ''.join('<th scope="col" class="%s">%s</th>' % (c, esc(h)) for h, c in cols)]
        groups = []
        for c in self.cujs:
            u = (L(c.get('users')) or [''])[0]
            g = next((g for g in groups if g[0] == u), None)
            if g:
                g[1].append(c)
            else:
                groups.append((u, [c]))
        n_rows = 0
        for u, cs in groups:
            uu = self.user_by.get(u, {})
            out.append('<tbody><tr class="grp"><th colspan="%d" scope="colgroup"><span class="grp-name">%s</span>%s<span class="grp-kind">%s</span></th></tr></tbody>'
                       % (nc, esc(uu.get('name') or T('no_user')), self.a(u) if u else '', esc(term('category', uu.get('category')))))
            for c in cs:
                qis = [q['id'] for q in self.qius if self.qiu_cuj.get(q['id']) == c['id']]
                blocks = [(qi, (sorted(self.qr_of_qiu.get(qi, []), key=self.qr_key) or [None]) if self.has[3] else [None]) for qi in qis] or [(None, [None])]
                span, rows, first = sum(len(qs) for _, qs in blocks), [], True
                for qi, qs in blocks:
                    n_rows += 1 if qi else 0
                    for j, q in enumerate(qs):
                        tds = ''
                        if first:
                            outs = ''.join(self.a(o) for o in L(c.get('outcomes')))
                            tds += ('<th scope="rowgroup" class="c-cuj" rowspan="%d">%s<span class="cuj-name">%s</span>%s</th>'
                                    % (span, self.a(c['id']), esc(c.get('name')), '<span class="cuj-out">%s</span>' % outs if outs else ''))
                            first = False
                        if j == 0:
                            if qi:
                                kpi = ''.join('<span class="kpi">%s</span>' % self.a(k) for k in self.kpi_of.get(qi, []))
                                tds += '<td class="c-qiu" rowspan="%d">%s%s<span class="qiu-name">%s</span></td>' % (len(qs), self.a(qi), kpi, esc(self.TITLE.get(qi)))
                            else:
                                tds += '<td class="c-qiu" rowspan="%d">%s</td>' % (len(qs), none())
                            if self.has[2]:
                                tds += '<td class="c-fr" rowspan="%d">%s</td>' % (len(qs), self.nums(sorted(self.fr_of_qiu.get(qi, []), key=id_key)))
                        if self.has[3]:
                            tds += '<td class="c-qr">%s</td>' % (self.qr_line(q) if q else none())
                        if self.has[4]:
                            tds += '<td class="c-nfr">%s</td>' % (self.nfr_cell(q) if q else '')
                        rows.append('<tr%s>%s</tr>' % (' class="q-start"' if j == 0 else '', tds))
                out.append('<tbody class="t-cuj">%s</tbody>' % ''.join(rows))
        if self.has[3] and self.entry:
            out.append('<tbody><tr class="grp"><th colspan="%d" scope="colgroup"><span class="grp-name">%s</span>'
                       '<span class="grp-kind">%s</span></th></tr></tbody>' % (nc, esc(T('not_through_users')), esc(T('entry_point'))))
            rows = []
            for k, q in enumerate(self.entry):
                ep = self.qr_by[q].get('entry_point') if isinstance(self.qr_by[q].get('entry_point'), dict) else {}
                tds = ''
                if k == 0:
                    tds += '<th scope="rowgroup" class="c-cuj" rowspan="%d"><span class="cuj-name">%s</span><span class="sub">%s</span></th>' % (
                        len(self.entry), esc(T('entry_point')), esc(T('no_cuj')))
                tds += '<td class="c-qiu"><span class="ent-kind">%s</span><span class="ent-src">%s</span></td>' % (
                    esc(term('entry_type', ep.get('type'))), self.cell(first_sentence(s(ep.get('source')))))
                if self.has[2]:
                    tds += '<td class="c-fr">%s</td>' % self.nums(sorted(L(self.qr_by[q].get('applies_to')), key=id_key))
                tds += '<td class="c-qr">%s</td>' % self.qr_line(q)
                if self.has[4]:
                    tds += '<td class="c-nfr">%s</td>' % self.nfr_cell(q)
                rows.append('<tr class="q-start">%s</tr>' % tds)
            out.append('<tbody class="t-cuj">%s</tbody>' % ''.join(rows))
        out.append('</table>')
        self.n_trace = n_rows
        return ''.join(out)

    # ---------- Figures ----------
    def route(self):
        unit = T('unit_items')
        stops = [
            ('t-business', 1, T('business_requirements'), len(self.kgis), 'KGI',
             dots([T('route_outcomes', n=len(self.outs)), 'KPI %d' % len(self.kpis)])),
            ('t-users', 1, T('users'), sum(1 for u in self.users if u.get('considered') is True), '/ %d' % len(self.users), T('route_considered')),
        ]
        by_user = Counter((L(c.get('users')) or [''])[0] for c in self.cujs)
        stops.append(('t-cuj', 1, 'CUJ', len(self.cujs), unit,
                      dots('%s %d' % (s(self.user_by.get(u, {}).get('name')) or '—', k) for u, k in by_user.items())))
        qc = Counter(term('characteristic', (char_key(q.get('characteristic')) or ('',))[0]) for q in self.qius)
        stops.append(('t-qiu', 1, 'QIU', len(self.qius), unit, dots('%s %d' % kv for kv in qc.most_common())))
        if self.has[2]:
            oc = Counter(term('origin', f.get('origin')) for f in self.frs)
            stops.append(('t-fr', 2, 'FR', len(self.frs), unit, dots('%s %d' % kv for kv in oc.most_common())))
        if self.has[3]:
            hc = Counter(self.handling.values())
            mini = ('<span class="mini" aria-hidden="true">' + ''.join('<span class="%s" style="flex:%d"></span>' % (HCLS[h], hc[h])
                                                                       for h in HANDLINGS if hc[h]) + '</span>')
            stops.append(('t-qr', 3, 'QR', len(self.qrs), unit, dots('%s %d' % (term('handling', h), hc[h]) for h in HANDLINGS) + mini))
        if self.has[4]:
            tc = Counter(self.kind.values())
            stops.append(('sec-4', 4, 'NFR', len(self.nfrs), unit, dots('%s %d' % (term('kind', k), tc[k]) for k in NFR_KINDS)))
        lis = ''.join('<li class="stop"><a href="#%s"><span class="dot" aria-hidden="true"></span><span class="st-body">'
                      '<span class="st-stage">%s</span><span class="st-name">%s</span>'
                      '<span class="st-num">%d<span class="st-unit">%s</span></span><span class="st-sub">%s</span></span></a></li>'
                      % (h, esc(T('stage_n', n=st)), esc(n), v, esc(unit_), sub) for h, st, n, v, unit_, sub in stops)
        counts, col_, bands = Counter(st for _, st, _, _, _, _ in stops), 1, []
        for st in sorted(counts):
            bands.append('<span class="band" style="grid-column:%d / %d"><b>%s</b>%s</span>'
                         % (col_, col_ + counts[st], esc(T('stage_n', n=st)), esc(self.stage_title(st))))
            col_ += counts[st]
        return ('<div class="route-wrap" style="--n:%d"><ol class="route" aria-label="%s">%s</ol><div class="bands">%s</div></div>'
                % (len(stops), attr(T('route_label')), lis, ''.join(bands)))

    def risk_chart(self, scored):
        cells = defaultdict(list)
        for q in scored:
            imp, lik = self.score(q)
            if 1 <= imp <= 5 and 1 <= lik <= 5:
                cells[(imp, lik)].append(q['id'])
            else:
                self.issues.append(T('issue_score_range', id=q['id'], imp=imp, lik=lik))
        g = ['<div class="ax-y" style="grid-area:1 / 1 / 6 / 2">%s</div>' % esc(T('impact'))]
        for imp in range(5, 0, -1):
            row = 6 - imp
            g.append('<div class="tick-y" style="grid-area:%d / 2">%d</div>' % (row, imp))
            for lik in range(1, 6):
                sc = imp * lik
                qs = sorted(cells.get((imp, lik), []), key=self.qr_key)
                chips = ''.join(self.a(q, chip=True, tip='%s\n%s' % (self.TIP.get(q, q), T('risk_tip', imp=imp, lik=lik, score=sc))) for q in qs)
                g.append('<div class="rc%s" style="grid-area:%d / %d;--mix:%d%%"><span class="rc-score">%d</span>%s</div>'
                         % ('' if qs else ' is-empty', row, 2 + lik, round(sc / 25 * 42), sc, chips))
        for lik in range(1, 6):
            g.append('<div class="tick-x" style="grid-area:6 / %d">%d</div>' % (2 + lik, lik))
        g.append('<div class="ax-x" style="grid-area:7 / 3 / 8 / 8">%s</div>' % esc(T('likelihood')))
        return ('<figure class="risk"><figcaption class="fig-head"><span class="fig-title">%s</span>%s</figcaption>'
                '<div class="risk-scroll"><div class="risk-grid" role="group" aria-label="%s">%s</div></div></figure>'
                % (esc(T('risk_title')), legend(), attr(T('risk_label')), ''.join(g)))

    def slo_cards(self, slos):
        items = []
        for n in slos:
            slo, sli = self.slo(n), s(self.slo(n).get('sli'))
            st = term('target_status', slo.get('target_status'))
            meta = ' · '.join(x for x in (n['id'], s(n.get('cuj')), window_text(slo.get('window'))) if x)
            items.append('<a class="slo-card" href="#%s" data-tip="%s"><span class="slo-top"><span class="slo-val">%s</span>%s</span>'
                         '<span class="slo-name">%s</span><span class="slo-meta">%s</span></a>'
                         % (n['id'], attr(self.TIP.get(n['id'])), esc(s(slo.get('target')) or '—'),
                            '<span class="slo-state">%s</span>' % esc(st) if st else '',
                            esc(self.TITLE.get(sli) or self.TITLE.get(n['id'])), esc(meta)))
        return '<div class="slo-cards">%s</div>' % ''.join(items)

    # ---------- Matrices ----------
    def matrix(self, model):
        if model == 'product':
            rows_def = [(t, sub) for t, subs in PRODUCT_MODEL for sub in subs]
        else:
            rows_def = [(t, None) for t in DATA_MODEL]
        # As in the coverage checklist, only external quality is placed. Internal quality goes in
        # the table of internal quality derived from external quality.
        # QRs from an entry point have no CUJ, so they go in the entry point column before the CUJ
        # columns (its column key is None). The matrix is often wider than the screen, and a last column
        # stays hidden until the reader scrolls sideways
        valid, cells, unplaced, ents = set(rows_def), defaultdict(list), [], []
        for q in self.qrs:
            if s(q.get('model')) != model or q['id'] in self.internal:
                continue
            key = char_key(q.get('characteristic'))
            rk = (key[0], key[1]) if model == 'product' and len(key) == 2 else ((key[-1], None) if model == 'data' and key else None)
            if rk not in valid:
                unplaced.append(q['id'])
                continue
            for c in self.qr_cujs.get(q['id'], []):
                cells[(rk, c)].append(q['id'])
            if q.get('entry_point'):
                cells[(rk, None)].append(q['id'])
                ents.append(q['id'])
        if unplaced:
            self.notes.append(T('note_unplaced_%s' % model, ids=join(unplaced)))
        cols, heads = [c['id'] for c in self.cujs], ''
        if ents:
            order = list(LANG['terms']['entry_type'].values())
            types = join(sorted({self.entry_type.get(q) or '—' for q in ents}, key=lambda t: (order.index(t) if t in order else len(order), t)))
            cols = [None] + cols
            heads = ('<th scope="col" class="mx-h mx-ent"><a class="id" href="#t-ext" data-tip="%s">%s</a>'
                     '<span class="vname">%s</span></th>' % (attr(T('not_through_users') + paren(types)), esc(T('entry_point')), esc(T('entry_col_sub'))))
        heads += ''.join('<th scope="col" class="mx-h">%s<span class="vname">%s</span></th>'
                         % (self.a(c['id'], c['id'].split('-', 1)[1]), esc(c.get('name'))) for c in self.cujs)
        th = ('<th scope="col" class="mx-k">%s</th><th scope="col" class="mx-k">%s</th>' % (esc(T('col_char')), esc(T('col_sub_char')))
              if model == 'product' else '<th scope="col" class="mx-k">%s</th>' % esc(T('col_char'))) + heads

        def chip(q, c):
            if c:
                return self.a(q, chip=True)
            return self.a(q, chip=True, tip='%s\n%s' % (self.TIP.get(q, q), T('entry_tip', type=self.entry_type.get(q) or '—')))
        span, body, prev = Counter(t for t, _ in rows_def), [], None
        for t, sub in rows_def:
            if model == 'product':
                lead_ = ''
                if t != prev:
                    lead_ = '<th scope="rowgroup" class="mx-char" rowspan="%d">%s</th>' % (span[t], esc(term('characteristic', t)))
                    prev = t
                lead_ += '<th scope="row" class="mx-sub">%s</th>' % esc(term('characteristic', sub))
            else:
                lead_ = '<th scope="row" class="mx-sub">%s</th>' % esc(term('characteristic', t))
            tds = ''.join('<td class="mx-c%s">%s</td>' % ('' if c else ' mx-ent', ' '.join(chip(q, c) for q in sorted(cells[((t, sub), c)], key=self.qr_key)) or none())
                          for c in cols)
            body.append('<tr>%s%s</tr>' % (lead_, tds))
        return '<table class="mx"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (th, ''.join(body)), len(rows_def), len(ents)

    def data_lists(self):
        top = bottom = ''
        line = line_value(self.md[3], DATA_KINDS)
        if line:
            self.used.append(T('data_kinds'))
            top = '<p class="list-label">%s</p><ul class="dq-list">%s</ul>' % (esc(T('data_kinds')), ''.join(
                '<li>%s</li>' % self.cell(k) for k in split_top(first_sentence(line).rstrip('。.'))))
        else:
            self.skipped.append(T('data_kinds') + paren(REPORTS[3]))
        line = line_value(self.md[3], DATA_WHO)
        if line:
            self.used.append(T('data_producers'))
            who = [split_who(x) for x in split_top(first_sentence(line))]
        else:
            who = [(s(u.get('name')), T('user_role', role=term('data_role', u.get('data_role'))))
                   for u in self.users if s(u.get('data_role')) in ('producer', 'both')]
            who += [split_who(x) for x in L(self.system.get('data_producers'))]
        if who:
            bottom = '<p class="list-label">%s</p><ul class="dq-list who-list">%s</ul>' % (esc(T('data_producers')), ''.join(
                '<li><span class="who">%s</span>%s</li>' % (esc(w), self.cell(d)) if d else '<li>%s</li>' % self.cell(w) for w, d in who))
        return top, bottom

    # ---------- Tables by stage ----------
    def stage1(self):
        P = []
        kg = tbl([('ID', 'w-id'), ('KGI', 'w-s'), (T('col_measure'), 'w-m'), (T('col_target'), 'w-l')],
                 [(k['id'], [self.defid(k['id']), self.cell(k.get('name')), self.cell(k.get('measure')), self.cell(k.get('target'))]) for k in self.kgis])
        ou = tbl([('ID', 'w-id'), (T('col_outcome'), 'w-l'), (T('col_verb'), 'w-id'), ('KGI', 'w-id')],
                 [(o['id'], [self.defid(o['id']), self.cell(o.get('statement')), esc(term('verb', o.get('verb'))), self.ids(L(o.get('kgis')))])
                  for o in self.outs])
        P.append(self.tog(1, 't-business', T('business_requirements'), T('count_business', k=len(self.kgis), o=len(self.outs)), wrap(kg) + wrap(ou)))
        us = tbl([('ID', 'w-id'), (T('col_user'), 'w-s'), (T('col_category'), 'w-s'), (T('col_data_role'), 'w-id'), (T('col_considered'), 'w-id'),
                  (T('col_exclusion'), 'w-l'), (T('col_basis'), 'w-xl')],
                 [(u['id'], [self.defid(u['id']), self.cell(u.get('name')), esc(term('category', u.get('category'))),
                             esc(term('data_role', u.get('data_role'))), esc(term('considered', u.get('considered'))),
                             self.cell(u.get('exclusion_reason')), self.basis(u)]) for u in self.users])
        P.append(self.tog(1, 't-users', T('users'), T('count', n=len(self.users)), wrap(us)))
        cj = tbl([('ID', 'w-id'), ('CUJ', 'w-s'), (T('col_users'), 'w-id'), (T('col_user_goal'), 'w-l'), (T('col_steps'), 'w-l'),
                  (T('col_outcomes'), 'w-id'), (T('col_basis'), 'w-l')],
                 [(c['id'], [self.defid(c['id']), self.cell(c.get('name')), self.users_cell(L(c.get('users'))), self.cell(c.get('user_goal')),
                             self.listing(L(c.get('steps')), 'steps'), self.ids(L(c.get('outcomes'))), self.basis(c)]) for c in self.cujs])
        P.append(self.tog(1, 't-cuj', T('cujs'), T('count', n=len(self.cujs)), wrap(cj)))
        qt = tbl([('ID', 'w-id'), (T('col_user'), 'w-id'), ('CUJ', 'w-s'), (T('col_context'), 'w-m'), (T('col_char'), 'w-m'), (T('col_requirement'), 'w-xl')],
                 [(q['id'], [self.defid(q['id']), self.users_cell(L(q.get('user'))), self.cuj_cell(s(q.get('cuj'))),
                             self.cell(context_text(q.get('context_of_use'))), esc(char_text(q.get('characteristic'))),
                             self.lead(q['id']) + self.cell(q.get('statement'))]) for q in self.qius])
        P.append(self.tog(1, 't-qiu', T('qius'), T('count', n=len(self.qius)), wrap(qt)))
        fl = tbl([('ID', 'w-s'), (T('col_failure'), 'w-l'), (T('col_num_den'), 'w-l'), (T('col_narrowed'), 'w-m'), (T('col_observable'), 'w-id')],
                 [(None, [self.with_sub(q['id'], self.TITLE.get(q['id'])), self.cell(q.get('failure_scenario')),
                          self.frac(self.measure(q['id']).get('numerator'), self.measure(q['id']).get('denominator')),
                          self.cell(self.measure(q['id']).get('narrowed_to')), observable(self.measure(q['id']).get('observable'))])
                  for q in self.qius])
        P.append(self.tog(1, 't-fail', T('failures'), T('count', n=len(self.qius)), wrap(fl)))
        ex = self.extra_rows('excl', T('not_targeted'))
        if ex:
            P.append(self.tog(1, 't-excl', T('not_targeted'), T('count', n=len(ex)),
                              wrap(tbl([(T('col_excl_cuj'), 'w-m'), (T('col_excl_char'), 'w-m'), (T('col_reason'), 'w-xl')],
                                       [(None, [self.cell(r[0]), self.cell(r[1]), self.cell(r[2])]) for r in ex]))))
        fm = self.formula_rows()
        P.append(self.tog(1, 't-formula', T('formula'), T('count', n=len(fm)),
                          wrap(tbl([(T('col_f_outcome'), 'w-id'), (T('col_f_formula'), 'w-l'), (T('col_f_narrowed'), 'w-m'), (T('col_f_overall'), 'w-m')], fm))))
        return P

    def formula_rows(self):
        """In this order: KPI formulas, formulas of QIUs with an intermediate outcome but no KPI, and QIUs with neither (combined into one row)"""
        rows, rest = [], []
        nothing = '<span class="none">%s</span>' % esc(T('none'))
        for k in self.kpis:
            nar = ''.join('<div class="nr">%s %s</div>' % (self.a(x), self.cell(self.measure(x).get('narrowed_to')))
                          for x in L(k.get('overlaps_with')) if x in self.qiu_by)
            rows.append((k['id'], [self.ids(L(k.get('outcome'))), self.frac(k.get('numerator'), k.get('denominator')),
                                   nar, self.with_sub(k['id'], self.TITLE.get(k['id']))]))
        for q in self.qius:
            if s(q.get('kpi')) in self.kpi_ids:
                continue
            if not L(q.get('outcomes')):
                rest.append(q['id'])
                continue
            m = self.measure(q['id'])
            rows.append((None, [self.ids(L(q.get('outcomes'))), self.frac(m.get('numerator'), m.get('denominator')),
                                '<div class="nr">%s %s</div>' % (self.a(q['id']), self.cell(m.get('narrowed_to'))), nothing]))
        if rest:
            rows.append((None, ['', esc(T('formula_rest')), self.nums(rest), nothing]))
        return rows

    def stage2(self):
        P = []
        fr = tbl([('ID', 'w-id'), (T('col_function'), 'w-xl'), (T('col_ac'), 'w-xl'), (T('col_origin'), 'w-s'), (T('col_traces'), 'w-m')],
                 [(f['id'], [self.defid(f['id']), self.lead(f['id']) + self.cell(f.get('statement')),
                             self.listing(L(f.get('acceptance_criteria')), 'ac'), self.origin(f), self.ids(L(f.get('traces_to')))])
                  for f in self.frs])
        P.append(self.tog(2, 't-fr', T('frs'), T('count', n=len(self.frs)), wrap(fr)))
        na = self.extra_rows('notadd', T('not_added'))
        if na:
            P.append(self.tog(2, 't-notadd', T('not_added'), T('count', n=len(na)),
                              wrap(tbl([(T('col_candidate'), 'w-l'), (T('col_for'), 'w-m'), (T('col_reason'), 'w-xl')],
                                       [(None, [self.cell(r[0]), self.cell(r[1]), self.cell(r[2])]) for r in na]))))
        return P

    def origin(self, f):
        p = s(f.get('proposal'))
        return esc(term('origin', f.get('origin'))) + (paren(self.a(p)) if p else '')

    def stage3(self):
        P = []
        scored = [q for q in self.qrs if self.score(q)]
        if scored:
            P.append(self.risk_chart(scored))
        pq, n_pq, e_pq = self.matrix('product')
        P.append(self.tog(3, 't-pq', T('product_quality'), T('count_pq', n=n_pq, c=len(self.cujs)) + (T('count_entry', n=e_pq) if e_pq else ''),
                          legend() + wrap(pq)))
        dq, n_dq, e_dq = self.matrix('data')
        top, bottom = self.data_lists()
        P.append(self.tog(3, 't-dq', T('data_quality'), T('count_dq', n=n_dq, c=len(self.cujs)) + (T('count_entry', n=e_dq) if e_dq else ''),
                          top + legend() + wrap(dq) + bottom))
        if scored:
            P.append(self.tog(3, 't-prio', T('priority'), T('count', n=len(scored)), wrap(self.prio_table(scored))))
        P.append(self.tog(3, 't-cujh', T('handling_by_cuj'), T('count', n=len(self.cujs)), wrap(self.cujh_table())))
        der = self.derived_table()
        if der:
            P.append(self.tog(3, 't-derived', T('derived'), T('count', n=der[1]), wrap(der[0])))
        qt = tbl([('ID', 'w-id'), (T('col_model_layer'), 'w-s'), (T('col_char'), 'w-m'), (T('col_requirement'), 'w-xl'), (T('col_applies'), 'w-m'),
                  (T('col_traces'), 'w-m')],
                 [(q['id'], [self.defid(q['id']), esc('%s / %s' % (term('model', q.get('model')), term('layer', q.get('layer')))),
                             esc(char_text(q.get('characteristic'))), self.lead(q['id']) + self.cell(q.get('statement')),
                             self.ids(L(q.get('applies_to'))), self.traces(q)]) for q in self.qrs])
        P.append(self.tog(3, 't-qr', T('qrs'), T('count', n=len(self.qrs)), wrap(qt)))
        if self.entry:
            rows = []
            for q in self.entry:
                v = self.qr_by[q]
                ep = v.get('entry_point') if isinstance(v.get('entry_point'), dict) else {}
                rows.append((None, [self.with_sub(q, self.TITLE.get(q)), esc(term('entry_type', ep.get('type'))), self.cell(ep.get('source')),
                                    self.handling_cell(v), self.cell(v.get('statement'))]))
            P.append(self.tog(3, 't-ext', T('not_through_users'), T('count', n=len(rows)),
                              wrap(tbl([('QR', 'w-m'), (T('col_type'), 'w-s'), (T('col_source'), 'w-xl'), (T('col_handling'), 'w-s'),
                                        (T('col_requirement'), 'w-l')], rows))))
        return P

    def traces(self, q):
        if L(q.get('traces_to')):
            return self.ids(L(q.get('traces_to')))
        ep = q.get('entry_point') if isinstance(q.get('entry_point'), dict) else {}
        return esc(T('entry_tip', type=term('entry_type', ep.get('type')))) if ep else ''

    def prio_table(self, scored):
        cols = [('qr', 'QR', 'w-id'), ('char', T('col_char'), 'w-m'), ('fail', T('col_failure'), 'w-xl'), ('impact', T('impact'), 'num'),
                ('lik', T('likelihood'), 'num'), ('score', T('col_score'), 'num'), ('handling', T('col_handling'), 'w-m'), ('cuj', 'CUJ', 'w-s')]
        sort = ('qr', 'score')
        th = ''.join('<th scope="col" class="%s" data-key="%s" aria-sort="none"><button type="button" class="sort">%s</button></th>' % (w, k, esc(c))
                     if k in sort else '<th scope="col" class="%s">%s</th>' % (w, esc(c)) for k, c, w in cols)
        body = []
        for i, q in enumerate(scored):
            imp, lik = self.score(q)
            tds = [self.with_sub(q['id'], self.TITLE.get(q['id'])), esc(char_text(q.get('characteristic'))), self.cell(q.get('failure_scenario')) or none(),
                   str(imp), str(lik), '<strong>%d</strong>' % (imp * lik), self.handling_cell(q), self.nums(self.qr_cujs.get(q['id'], []))]
            body.append('<tr data-i="%d" data-qr="%d" data-score="%d">%s</tr>' % (i, id_key(q['id'])[1], imp * lik,
                                                                                   ''.join('<td class="%s">%s</td>' % (w, h) for (_, _, w), h in zip(cols, tds))))
        return '<table data-sortable><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (th, ''.join(body))

    def cujh_table(self):
        rows = []
        for c in self.cujs:
            by = {h: [] for h in HANDLINGS}
            for q in self.qrs:
                if q['id'] not in self.internal and c['id'] in self.qr_cujs.get(q['id'], []) and self.handling[q['id']] in by:
                    by[self.handling[q['id']]].append(q['id'])
            rows.append((None, [self.with_sub(c['id'], c.get('name')), self.ids(by['emphasized']), self.ids(by['minimum-line']),
                                self.ids(by['excluded']), str(len(by['emphasized']))]))
        return tbl([('CUJ', 'w-m'), (term('handling', 'emphasized'), 'w-m'), (term('handling', 'minimum-line'), 'w-m'),
                    (term('handling', 'excluded'), 'w-s'), (T('col_n_emph'), 'num')], rows)

    def derived_table(self):
        ints = [q for q in self.qrs if q['id'] in self.internal]
        if not ints:
            return None
        ext_of = defaultdict(list)
        for q in self.qrs:
            for i in L(q.get('implies_internal')):
                ext_of[i].append(q['id'])
        rep = self.extra_rows('derived', T('derived_how'))
        how = {}
        for r in rep or []:
            for i in ids_in(r[1], 'QR'):
                how.setdefault(i, r[2])
        rows = [(None, [self.ids(sorted(ext_of.get(q['id'], []), key=id_key)), self.with_sub(q['id'], self.TITLE.get(q['id'])),
                        self.cell(how.get(q['id'])) if rep is not None else self.cell(q.get('statement'))]) for q in ints]
        third = T('col_how') if rep is not None else T('col_int_req')
        return tbl([(T('col_ext_qr'), 'w-m'), (T('col_int_qr'), 'w-m'), (third, 'w-xl')], rows), len(rows)

    def stage4(self):
        P = []
        slos = [n for n in self.nfrs if self.kind[n['id']] == 'slo']
        if slos:
            P.append(self.slo_cards(slos))
            rows = []
            for n in slos:
                slo, sli = self.slo(n), s(self.slo(n).get('sli'))
                st = term('target_status', slo.get('target_status'))
                rows.append((n['id'], [self.defid(n['id'], self.TITLE.get(n['id'])), self.cuj_cell(s(n.get('cuj'))),
                                       self.with_sub(sli, self.TITLE.get(sli)) if sli else '',
                                       esc(s(slo.get('target')) + (paren(st) if st else '')), esc(window_text(slo.get('window'))),
                                       self.cell(slo.get('error_budget')), self.cell(slo.get('error_budget_volume')), self.ids(L(slo.get('policy')))]))
            P.append(self.tog(4, 't-slo', T('slos'), T('count', n=len(slos)), wrap(tbl(
                [('NFR', 'w-m'), ('CUJ', 'w-s'), ('SLI', 'w-m'), (T('col_target_status'), 'w-id'), (T('col_window'), 'w-id'),
                 (T('col_budget'), 'w-l'), (T('col_budget_volume'), 'w-xl'), (T('col_policy'), 'w-id')], rows))))
        if self.slis:
            rows = [(x['id'], [self.defid(x['id'], x.get('title')), self.frac(*sli_parts(x)), self.cell(x.get('method'))]) for x in self.slis]
            P.append(self.tog(4, 't-sli', T('slis'), T('count', n=len(rows)), wrap(tbl(
                [('SLI', 'w-m'), (T('col_good_valid'), 'w-xl'), (T('col_method'), 'w-l')], rows))))
        if self.ebps:
            body, n_rules = [], 0
            for e in self.ebps:
                rules = [r for r in (e.get('rules') or []) if isinstance(r, dict)]
                n_rules += len(rules)
                t = tbl([(T('col_condition'), 'w-l'), (T('col_action'), 'w-xl')],
                        [(None, [self.cell(r.get('when')), self.cell(r.get('action'))]) for r in rules], cls='ebp')
                t = t.replace('<table class="ebp">', '<table class="ebp" id="%s">' % e['id'], 1)
                cap = '' if len(self.ebps) == 1 else '<p class="list-label">%s</p>' % T(
                    'ebp_caption', id=esc(e['id']), title=esc(e.get('title')), targets=self.ids(L(e.get('applies_to'))) or '—')
                body.append(cap + wrap(t))
            count = (self.ebps[0]['id'] if len(self.ebps) == 1 else T('count_ebps', n=len(self.ebps))) + T('count_rules', n=n_rules)
            P.append(self.tog(4, 't-ebp', T('ebp'), count, ''.join(body)))
        burn = self.burn_table(slos)
        if burn:
            P.append(self.tog(4, 't-burn', T('burn'), T('count', n=burn[1]), wrap(burn[0])))
        dl = [n for n in slos if any(s(self.slo(n).get(k)) for k in ('bad_run_budget_share', 'progress_alert', 'after_miss'))]
        if dl:
            rows = [(None, [self.a(n['id']), self.cell(self.slo(n).get('progress_alert')), self.cell(self.slo(n).get('bad_run_budget_share')),
                            esc(term('notify', self.slo(n).get('after_miss'), strict=False))]) for n in dl]
            P.append(self.tog(4, 't-dl', T('deadline'), T('count', n=len(rows)), wrap(tbl(
                [('SLO', 'w-id'), (T('col_progress'), 'w-l'), (T('col_bad_share'), 'w-xl'), (T('col_after_miss'), 'w-id')], rows))))
        others = [n for n in self.nfrs if self.kind[n['id']] != 'slo']
        if others:
            rows = [(n['id'], [self.defid(n['id'], self.TITLE.get(n['id'])), '<span class="ntype">%s</span>' % esc(term('kind', n.get('kind'))),
                               self.from_cell(n), self.cell(n.get('statement')), self.where(n)]) for n in others]
            P.append(self.tog(4, 't-nfr', T('other_nfrs'), T('count', n=len(rows)), wrap(tbl(
                [('NFR', 'w-l'), (T('col_kind'), 'w-id'), (T('col_from'), 'w-m'), (T('col_nfr_req'), 'w-xl'), (T('col_where'), 'w-m')], rows))))
        return P

    def burn_table(self, slos):
        rows = []
        for n in slos:
            alerts = [x for x in (self.slo(n).get('alerts') or []) if isinstance(x, dict)]
            days = window_days(self.slo(n).get('window'))
            for k, al in enumerate(alerts):
                tds = '<th scope="rowgroup" class="w-id" rowspan="%d">%s</th>' % (len(alerts), self.a(n['id'])) if k == 0 else ''
                vals = [('w-s', esc(term('notify', al.get('notify'), strict=False))), ('num', esc(al.get('long_window'))),
                        ('num', esc(al.get('short_window'))), ('num', esc(al.get('burn_rate'))),
                        ('num', esc(al.get('budget_spent_at_alert'))), ('num', esc(exhaust(days, al.get('burn_rate'))))]
                rows.append('<tr>%s%s</tr>' % (tds, ''.join('<td class="%s">%s</td>' % (c, v or none()) for c, v in vals)))
        if not rows:
            return None
        cols = [('SLO', 'w-id'), (T('col_notify'), 'w-s'), (T('col_long'), 'num'), (T('col_short'), 'num'), (T('col_burn_rate'), 'num'),
                (T('col_spent'), 'num'), (T('col_exhaust'), 'num')]
        th = ''.join('<th scope="col" class="%s">%s</th>' % (w, esc(c)) for c, w in cols)
        return '<table class="burn"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (th, ''.join(rows)), len(rows)

    def from_cell(self, n):
        return join(self.a(q) + (paren(esc(term('handling', self.handling[q]))) if self.handling.get(q) else '')
                    for q in L(n.get('from')))

    def where(self, n):
        k = self.kind[n['id']]
        g = n.get(k) if isinstance(n.get(k), dict) else {}

        def sub(v):
            return '<span class="sub">%s</span>' % self.cell(v) if s(v) else ''
        if k == 'gate':
            return self.cell(term('gate_where', g.get('where'), strict=False)) + sub(g.get('check'))
        if k == 'audit':
            return self.cell(g.get('mechanism')) + sub(g.get('cadence_or_deadline'))
        if k == 'monitor':
            return self.cell(g.get('signal')) + sub(g.get('notifies'))
        return ''

    # ---------- Page ----------
    def git(self, *args):
        try:
            r = subprocess.run(['git', '-C', str(self.docs)] + list(args), capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return ''
        return r.stdout.strip() if r.returncode == 0 else ''

    def render(self):
        self.prepare_links()
        stages = [n for n in (1, 2, 3, 4) if self.has[n]]
        build = {1: self.stage1, 2: self.stage2, 3: self.stage3, 4: self.stage4}
        parts = {n: build[n]() for n in stages}
        trace = self.trace()
        top = self.git('rev-parse', '--show-toplevel')
        tracked = bool(self.git('ls-files', 'context.yaml'))
        commit = self.git('rev-parse', '--short', 'HEAD') if tracked else ''
        if commit:
            pathspec = ['.'] + ([':(exclude)%s' % self.out.name] if self.out.parent == self.docs else [])
            if self.git('status', '--porcelain', '--', *pathspec):
                commit += paren(T('uncommitted'))
        if top and tracked:
            eyebrow = '%s · %s' % (pathlib.Path(top).name, self.docs.relative_to(pathlib.Path(top).resolve()).as_posix())
        else:
            eyebrow = '%s · %s/%s' % (self.docs.parent.parent.name, self.docs.parent.name, self.docs.name)
        dates = [d for d in (self.stage_date(n) for n in stages) if d]
        meta = T('meta_stages', last=stages[-1]) + (T('meta_updated', date=max(dates)) if dates else '')
        missing = [n for n in (2, 3, 4) if not self.has[n]]
        notes = []
        if missing:
            notes.append(T('note_missing_stages', stages=join(T('stage_n', n=n) for n in missing)))
        if self.skipped:
            notes.append(T('note_skipped', tables=join(self.skipped)))
        toc = ('<nav class="toc" aria-label="%s"><a class="toc-sec" href="#sec-trace">%s</a>' % (attr(T('toc')), esc(T('traceability')))
               + ''.join('<div class="toc-grp"><a class="toc-sec" href="#sec-%d"><span>%d</span>%s</a><div class="sub">%s</div></div>'
                         % (n, n, esc(self.stage_title(n)), ''.join('<a href="#%s">%s</a>' % (h, esc(t)) for h, t in self.toc[n]))
                         for n in stages)
               + ('<a class="toc-sec toc-notes" href="#t-notes">%s</a>' % esc(T('notes_title')) if notes else '') + '</nav>')
        sections = ''.join(
            '<section id="sec-%d" class="stage"><header class="stage-head"><span class="stage-no">%s</span><h2>%s</h2>'
            '<span class="src">%s</span></header>%s</section>'
            % (n, esc(T('stage_n', n=n)), esc(self.stage_title(n)),
               esc((REPORTS[n] if self.md[n] else T('yaml_only')) + (T('meta_updated', date=self.stage_date(n)) if self.stage_date(n) else '')),
               ''.join(parts[n])) for n in stages)
        notes_sec = ('\n<section id="sec-notes" class="stage">%s</section>'
                     % toggle('t-notes', T('notes_title'), T('count', n=len(notes)), '<div class="notes">%s</div>' % ul(notes)) if notes else '')
        last_kind = {1: 'QIU', 2: 'FR', 3: 'QR', 4: 'SLO'}[stages[-1]]
        trace_src = T('trace_src', file=REPORTS[stages[-1]]) if self.md[stages[-1]] else T('trace_src_yaml')
        trace_count = 'QIU %d' % len(self.qius) + (T('count_entry', n=len(self.entry)) if self.has[3] and self.entry else '')
        desc = T('description', title=self.title, last_kind=last_kind, last=stages[-1])
        css = (ASSETS / 'summary.css').read_text(encoding='utf-8')
        js = (ASSETS / 'summary.js').read_text(encoding='utf-8')
        return ''.join([
            '<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n' % LANG['code'],
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n',
            '<title>%s</title>\n' % esc(self.title),
            '<meta name="claude:viewport-fit-sides" content="cover">\n',
            '<meta name="description" content="%s">\n' % attr(desc),
            '<meta name="generator" content="quality-summary-html">\n',
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n',
            '<link rel="stylesheet" href="%s">\n' % attr(LANG['fonts']),
            '<style>\n', css, '</style>\n</head>\n<body>\n<div class="page">\n<header class="masthead">\n<div class="mast-text">\n',
            '<p class="eyebrow">%s</p>\n' % esc(eyebrow),
            '<h1>%s</h1>\n' % esc(self.title),
            '<p class="meta">%s%s</p>\n' % (esc(meta), ' · <span>%s</span>' % esc(commit) if commit else ''),
            '</div>\n<div class="tools"><button type="button" class="btn" id="open-all">%s</button>'
            '<button type="button" class="btn" id="close-all">%s</button></div>\n</header>\n' % (esc(T('open_all')), esc(T('close_all'))),
            toc, '\n<main>\n<section id="sec-trace" class="stage">\n',
            '<header class="stage-head"><span class="stage-no">CUJ → %s</span><h2>%s</h2><span class="src">%s</span></header>\n'
            % (last_kind, esc(T('traceability')), esc(trace_src)),
            self.route(), '\n',
            toggle('t-trace', T('trace_title'), trace_count, (legend(True) if self.has[3] else '') + wrap(trace), open_=True),
            '\n</section>\n', sections, notes_sec, '\n</main>\n</div>\n',
            '<script>\n', js, '</script>\n</body>\n</html>\n'])

    # ---------- Report ----------
    def report(self, out, page, problems):
        print(T('rep_written', path=out, kb=len(page.encode('utf-8')) // 1024))
        print(T('rep_lang', lang=self.lang, how=T(self.lang_how)))
        print(T('rep_stages', have=join(str(n) for n in (1, 2, 3, 4) if self.has[n]),
                missing=join(str(n) for n in (2, 3, 4) if not self.has[n]) or T('none')))
        print(T('rep_items') + ' · '.join('%s %d' % (k.upper(), len(self.live(k))) for k in KINDS))
        print(T('rep_trace', rows=self.n_trace, entry=len(self.entry) if self.has[3] else 0))
        print(T('rep_used') + (join(self.used) or T('none')))
        print(T('rep_skipped') + (join(self.skipped) or T('none')))
        print(T('rep_checked') + (join(self.checked) or T('none')))
        print(T('rep_unchecked') + (join(self.unchecked) or T('none')))
        print(T('rep_dead') + (', '.join('%s×%d' % kv for kv in sorted(self.dead.items(), key=lambda kv: id_key(kv[0]))) or T('none')))
        if UNKNOWN:
            print(T('rep_unknown') + join(k + paren(str(v)) for k, v in sorted(UNKNOWN.items())))
        print(T('rep_issues', n=len(self.issues)))
        for m in self.issues:
            print(' - ' + m)
        print(T('rep_notes', n=len(self.notes)))
        for m in self.notes:
            print(' - ' + m)
        for m in problems:
            print(T('rep_selfcheck') + m)


def self_check(page):
    ids = re.findall(r'\sid="([^"]+)"', page)
    dup = sorted(k for k, v in Counter(ids).items() if v > 1)
    miss = sorted(set(re.findall(r'href="#([^"]+)"', page)) - set(ids))
    return ([T('dup_ids') + ', '.join(dup)] if dup else []) + ([T('missing_targets') + ', '.join(miss)] if miss else [])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Builds a quality summary HTML page from the cuj-to-slo outputs')
    ap.add_argument('docs', nargs='?', default='docs/quality', help='the outputs directory (default: docs/quality)')
    ap.add_argument('--out', help='where to write the page (default: DOCS/summary.html)')
    ap.add_argument('--title', help='the page title (default: from system.name in context.yaml)')
    ap.add_argument('--lang', choices=LANGS, help='language of the page and the report (default: Japanese when the outputs are '
                                                  'written in Japanese, English otherwise)')
    args = ap.parse_args(argv)
    try:
        import yaml
    except ImportError:
        die_t('die_no_yaml', args.lang, script=pathlib.Path(__file__).name)
    docs = pathlib.Path(args.docs).resolve()
    if not docs.is_dir():
        die_t('die_no_docs', args.lang, path=docs)
    out = pathlib.Path(args.out).resolve() if args.out else docs / 'summary.html'
    b = Build(docs, yaml, out, args.title, args.lang)
    page = b.render()
    problems = self_check(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    b.report(out, page, problems)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
