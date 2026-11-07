#!/usr/bin/env python3
"""Builds docs/design/summary.html from the outputs of the design chain (stages 1 to 3, req-to-design).

  uv run --with pyyaml python3 build_design_summary.py [DESIGN_DIR] [--out PATH] [--text PATH] [--quality-dir DIR]

The YAML items are the source of truth (req-to-design's artifacts.md), so every table that has items is built from
them: drv/ and design-context.yaml (stage 1), elm/ and dec/ (stage 2), ifc/, dat/ and dec/ (stage 3). The three
reports (1-architecture-drivers.md, 2-architecture.md, 3-high-level-design.md) are read for the Mermaid diagrams and
for the sections that no item holds (concerns, feasibility, views, threat model, walkthroughs, running cost, shared
conventions, latency budgets, measurement points, the acceptance-criteria trace); report tables that restate items
are compared with them, so a stale report is reported. The condensed prose of report-only sections, the threat-model
figure's layout, the latency-budget chart data and exact text fixes come from DESIGN_DIR/summary-text.yaml, which also
records a hash of each source section, so a condensed text whose source changed is reported. The layout is
quality-summary-html's (assets/base.css and base.js are copies of its summary.css and summary.js); assets/design.css
gives it its own orange theme. The page and the report are Japanese, and the reports are read by their Japanese
headings.
The same input always produces the same HTML.
Exit codes: 0 means the page was written (0 even with warnings), 1 means it was written but failed its own check
(duplicate ids or links without a target), 2 means the inputs could not be read.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print('PyYAML が要る。uv run --with pyyaml python3 … で動かすか、python3 -m pip install --user pyyaml を入れる',
          file=sys.stderr)
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / 'assets'
REPORT_FILES = {1: '1-architecture-drivers.md', 2: '2-architecture.md', 3: '3-high-level-design.md'}
FONTS_URL = ('https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700'
             '&family=IBM+Plex+Mono:wght@500&family=Zen+Kaku+Gothic+New:wght@700&display=swap')
MERMAID_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.esm.min.mjs'
STAGE_TITLES = {1: '設計を動かす要求', 2: 'アーキテクチャ', 3: '概要設計'}
STAGE_SOURCES = {1: 'drv/ · design-context.yaml', 2: 'elm/ · dec/', 3: 'ifc/ · dat/ · dec/'}
# the keys of summary-text.yaml that the page uses
TEXT_KEYS = {'requirements', 'answers', 'fixes', 'structure', 'code_rules', 'viewpoints', 'threat', 'budgets', 'states',
             'walk_extra', 'diagram_direction', 'hashes'}
# warnings that also go into 「この版の注記」 at the bottom of the page
PAGE_NOTE_KINDS = ('食い違い', '添削文のもとが変わった', '添削文がない', '報告書', 'YAML', '節', '表')
# the report's kinds of warning, in the order they are printed
REPORT_KINDS = ('食い違い', '突き合わせなかった表', '添削文のもとが変わった', '添削文がない', '節', '表', '列', '手直し',
                '報告書', 'YAML', '用語集にない値', '添削文', '使わないキー')

# Japanese terms of the YAML values (req-to-design's glossary)
T_BASIS = {'stated': '入力', 'inferred': '推定', 'confirmed': '確認済み'}
T_LEVEL = {'high': '高', 'medium': '中', 'low': '低'}
T_NEG = {True: '交渉できる', False: '交渉できない'}
T_DRV_KIND = {'quality': '品質', 'change': '変更', 'constraint': '制約', 'function': '機能', 'observability': '観測',
              'security': 'セキュリティ', 'principle': '原則'}
T_TC_KIND = {'mandated': '使う', 'prohibited': '使わない', 'platform': '基盤', 'external-service': '外部サービス'}
T_PC_KIND = {'budget': '予算', 'deadline': '納期', 'team': '体制', 'other': 'その他'}
T_ELM_KIND = {'component': 'コンポーネント', 'data-store': 'データの置き場所', 'external-system': '外部システム', 'node': '実行環境'}
T_IFC_KIND = {'http': 'HTTP', 'event': 'イベント', 'file': 'ファイル', 'screen': '画面', 'batch': 'バッチ'}
T_AS_IS = {'keep': '残す', 'change': '変える', 'new': '新設', 'remove': '廃止'}
T_CLASS = {'public': '公開', 'internal': '社内', 'personal': '個人情報', 'payment': '決済情報', 'other': 'その他'}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- reading the reports

@dataclass
class Block:
    kind: str                      # para, label, table, code, list
    text: str = ''
    lang: str = ''
    rows: list = field(default_factory=list)   # table: [header, row, ...]
    line: int = 0


@dataclass
class Section:
    title: str
    level: int
    file: str
    parent: 'Section | None' = None
    start: int = 0                 # line of the heading (0-based)
    end: int = 0                   # line of the next heading at the same or a higher level
    blocks: list = field(default_factory=list)
    children: list = field(default_factory=list)
    lines: list = field(default_factory=list)  # all lines of the file (shared)

    def path(self) -> str:
        names = []
        s = self
        while s is not None and s.level > 1:   # the report's title (H1) is left out
            names.append(s.title)
            s = s.parent
        return ' > '.join([self.file] + list(reversed(names)))

    def raw(self) -> str:
        return '\n'.join(x.rstrip() for x in self.lines[self.start:self.end]).strip()

    def find(self, *titles: str) -> 'Section | None':
        """Follows headings down. A name ending in * matches by prefix."""
        cur = self
        for t in titles:
            nxt = None
            for c in cur.children:
                if (t.endswith('*') and c.title.startswith(t[:-1])) or c.title == t:
                    nxt = c
                    break
            if nxt is None:
                return None
            cur = nxt
        return cur

    def tables(self) -> list:
        return [b for b in self.blocks if b.kind == 'table']

    def codes(self, lang: str = 'mermaid') -> list:
        return [b for b in self.blocks if b.kind == 'code' and b.lang == lang]


HEAD_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
LIST_RE = re.compile(r'^\s*(?:[-*]|\d+\.)\s+')
SEP_CELL_RE = re.compile(r'^:?-{3,}:?$')


def split_row(line: str) -> list:
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|') and not s.endswith('\\|'):
        s = s[:-1]
    cells, cur, in_code, i = [], [], False, 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s) and s[i + 1] == '|':
            cur.append('|')
            i += 2
            continue
        if c == '`':
            in_code = not in_code
        if c == '|' and not in_code:
            cells.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    cells.append(''.join(cur).strip())
    return cells


def parse_md(text: str, name: str) -> Section:
    lines = text.split('\n')
    root = Section(name, 0, name, start=0, end=len(lines), lines=lines)
    stack = [root]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            lang = line[3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            stack[-1].blocks.append(Block('code', text='\n'.join(lines[i + 1:j]), lang=lang, line=i + 1))
            i = j + 1
            continue
        m = HEAD_RE.match(line)
        if m:
            level = len(m.group(1))
            while stack[-1].level >= level:
                stack[-1].end = i
                stack.pop()
            sec = Section(m.group(2), level, name, parent=stack[-1], start=i, end=len(lines), lines=lines)
            stack[-1].children.append(sec)
            stack.append(sec)
            i += 1
            continue
        if line.startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            rows = [split_row(x) for x in lines[i:j]]
            if len(rows) >= 2 and all(SEP_CELL_RE.match(c.replace(' ', '')) for c in rows[1] if c):
                rows = [rows[0]] + rows[2:]
            stack[-1].blocks.append(Block('table', rows=rows, line=i + 1))
            i = j
            continue
        if not line.strip():
            i += 1
            continue
        if LIST_RE.match(line):
            j = i
            while j < len(lines) and lines[j].strip() and (LIST_RE.match(lines[j]) or lines[j].startswith('  ')):
                j += 1
            stack[-1].blocks.append(Block('list', text='\n'.join(lines[i:j]), line=i + 1))
            i = j
            continue
        j = i
        while (j < len(lines) and lines[j].strip() and not lines[j].startswith(('|', '```'))
               and not HEAD_RE.match(lines[j])):
            j += 1
        para = '\n'.join(lines[i:j]).strip()
        mm = re.fullmatch(r'\*\*(.+)\*\*', para)
        stack[-1].blocks.append(Block('label' if mm else 'para', text=mm.group(1) if mm else para, line=i + 1))
        i = j
    for s in stack:
        s.end = len(lines)
    return root


def section_hash(*secs: Section) -> str:
    h = hashlib.sha256()
    for s in secs:
        h.update(s.raw().encode('utf-8'))
        h.update(b'\0')
    return h.hexdigest()[:12]


# ---------------------------------------------------------------- removing revision history

# 「前の版」 (previous version) means either a document revision or a product version (「前の版に戻す」「一つ前の版」
# 「本番は前の版のまま」). Only the wordings that mean a revision (「前の版は」「（前の版）」「前の版の欠け」…) count as history
HIST_RE = re.compile(r'前々回|前回|\d+\s*回目の再実行|再実行|FND-\d+|課題\s*\d+\s*は決着'
                     r'|(?<![一二]つ)前の版(?=は|（|。|）|では|が挙|の(?:欠け|誤り|負債|\s?[A-Z])|$)')
VER_ID_RE = re.compile(r'(\b[A-Z]{2,4}-\d{2}(?:〜\d{2})?)(?:\s*の)?\s*版\s*\d+')
# A finding number that is one item of a list loses only the number, not its sentence (「質問 11・14、FND-27」「（FND-02）」)
_FND = r'FND-\d+(?:[・、]\s*(?:FND-)?\d+)*'
FND_LIST_RES = [
    re.compile(r'[、・]\s*' + _FND + r'(?=\s*(?:[、。）」]|$))'),
    re.compile(r'(?<=[（。])\s*' + _FND + r'\s*[、・]\s*'),
    re.compile(r'(?<=[（。])\s*' + _FND + r'(?=\s*(?:[。）」]|$))'),
    re.compile(r'^\s*' + _FND + r'(?=\s*(?:[。）」]|$))'),
]
VER_ALONE_RE = re.compile(r'(?<![\w-])版\s*\d+')
PROCESS_ONLY_RE = re.compile(r'^(?:\s*(?:第\s*\d\s*段階の|この段の|品質チェーンへの回答の)?'
                             r'(?:課題|質問|回答の設計|設計)\s*[\d・〜\-、]+(?:\s*の回答)?\s*[、。]?)+$')


def _parse_parens(s: str) -> list:
    stack = [[]]
    buf = []
    for ch in s:
        if ch == '（':
            if buf:
                stack[-1].append(''.join(buf))
                buf = []
            stack.append([])
        elif ch == '）' and len(stack) > 1:
            if buf:
                stack[-1].append(''.join(buf))
                buf = []
            g = stack.pop()
            stack[-1].append(g)
        else:
            buf.append(ch)
    if buf:
        stack[-1].append(''.join(buf))
    while len(stack) > 1:          # an unclosed bracket is put back as text
        g = stack.pop()
        stack[-1].append('（' + _ser(g))
    return stack[0]


def _ser(items: list) -> str:
    return ''.join(x if isinstance(x, str) else '（' + _ser(x) + '）' for x in items)


def _sentences(items: list) -> list:
    """Splits at 「。」 outside brackets. Returns [(items, whether the sentence ended with 「。」)]."""
    out = [[[], False]]
    for x in items:
        if isinstance(x, str):
            parts = x.split('。')
            for k, p in enumerate(parts):
                if p:
                    out[-1][0].append(p)
                if k < len(parts) - 1:
                    out[-1][1] = True
                    out.append([[], False])
        else:
            out[-1][0].append(x)
    return [(a, b) for a, b in out if a]


def _is_hist(text: str) -> bool:
    return bool(HIST_RE.search(text) or VER_ALONE_RE.search(text))


def _clean_items(items: list, drop_top: bool) -> tuple:
    """Returns (items, whether anything was removed). With drop_top false, sentences at this level are kept and only
    brackets are cleaned."""
    changed = False
    inner = []
    for x in items:
        if isinstance(x, list):
            g, ch = _clean_items(x, True)
            changed |= ch
            if g:
                inner.append(g)
            else:
                changed = True
        else:
            inner.append(x)
    if not drop_top:
        return inner, changed
    kept = []
    for sent, ended in _sentences(inner):
        if _is_hist(_ser(sent)):
            changed = True
            continue
        kept.append((sent, ended))
    if changed and kept and PROCESS_ONLY_RE.match(''.join(_ser(s) for s, _ in kept)):
        kept = []
    out = []
    for k, (sent, ended) in enumerate(kept):
        out.extend(sent)
        if k < len(kept) - 1 or ended:
            out.append('。')
    # no 「。」 right before a closing bracket (not 「（a。b。）」)
    while out and out[-1] == '。':
        out.pop()
    return out, changed


def _tidy(s: str) -> str:
    s = re.sub(r'（\s*）', '', s)
    s = s.replace('（。', '（').replace('。）', '）').replace('、）', '）').replace('（、', '（')
    s = re.sub(r'。{2,}', '。', s)
    s = re.sub(r'、{2,}', '、', s)
    s = re.sub(r'\s+([。、）])', r'\1', s)
    s = re.sub(r'^[。、\s]+', '', s)
    s = re.sub(r'[、\s]+$', '', s)
    return s


def clean_text(s: str, top: bool = True) -> tuple:
    """Removes revision-history notes from a table cell or a diagram line. Returns (text, changed)."""
    if not s:
        return s, False
    orig = s
    s = VER_ID_RE.sub(r'\1', s)
    for rx in FND_LIST_RES:
        s = rx.sub('', s)
    items, _ = _clean_items(_parse_parens(s), top)
    ended = orig.rstrip().endswith('。')
    out = _tidy(_ser(items))
    if top and ended and out and not out.endswith('。'):
        out += '。'
    return out, out != orig


def clean_mermaid(src: str) -> tuple:
    out, changed = [], False
    for line in src.split('\n'):
        c, ch = clean_text(line, top=False)
        if ch:
            # keep the indentation
            indent = re.match(r'^\s*', line).group(0)
            c = indent + c.lstrip()
        out.append(c if ch else line)
        changed |= ch
    return '\n'.join(out), changed


# ---------------------------------------------------------------- IDs and links

ID_PREFIX = ('DRV|DEC|ELM|IFC|DAT|TEAM|STK|CHG|TC|PC|FND|USR|CUJ|QIU|KPI|KGI|OUT|FRP|FR|QR|NFR|SLI|EBP')
UNIT_AHEAD = r'(?!\d|\s*(?:%|件|秒|回|分|日|時間|人|年|台|本|行|倍|円|個|組|km|m\b|MiB|ms))'
ID_RE = re.compile(r'(?<![A-Za-z0-9_\-])(?P<p>' + ID_PREFIX + r')-(?P<n>\d{2})(?P<rng>〜\d{2})?'
                   r'(?P<cont>(?:[、・]\d{2}' + UNIT_AHEAD + r'(?:〜\d{2})?)*)' + r'(?![\d])')
CONT_RE = re.compile(r'([、・])(\d{2})(?:(〜)(\d{2}))?')
QUALITY_PREFIXES = {'USR', 'CUJ', 'QIU', 'KPI', 'KGI', 'OUT', 'FRP', 'FR', 'QR', 'NFR', 'SLI', 'EBP'}


class Ctx:
    def __init__(self):
        self.titles: dict = {}         # ID → tooltip text
        self.own: set = set()          # IDs that should have a row on this page
        self.quality_anchor: set = set()
        self.quality_href = ''
        self.cleaned: list = []        # (where, before, after)
        self.warnings: dict = {}       # kind → [messages]
        self.used_tips: set = set()
        self.directions: dict = {}     # section path → diagram direction (diagram_direction in summary-text.yaml)
        self.used_directions: set = set()

    def warn(self, kind: str, msg: str):
        self.warnings.setdefault(kind, []).append(msg)

    def href(self, id_: str) -> str:
        if id_ in self.own:
            return '#' + id_
        p = id_.split('-')[0]
        if p in QUALITY_PREFIXES and id_ in self.quality_anchor and self.quality_href:
            return self.quality_href + '#' + id_
        return ''

    def link(self, id_: str, text: str | None = None) -> str:
        """A link for an ID. Tooltip texts are collected once in a JSON block at the end of the page, and design.js looks
        them up."""
        shown = text if text is not None else id_
        ref = f' data-ref="{esc(id_)}"' if shown != id_ else ''
        if id_ in self.titles:
            self.used_tips.add(id_)
        h = self.href(id_)
        if h:
            cls = 'id ext' if not h.startswith('#') else 'id'
            return f'<a class="{cls}" href="{esc(h)}"{ref}>{esc(shown)}</a>'
        return f'<span class="id dead"{ref}>{esc(shown)}</span>'


def link_ids(s: str, ctx: Ctx) -> str:
    """Links the IDs in escaped text. In 「DRV-01、02」, 02 links to DRV-02."""
    def rep(m):
        p, n = m.group('p'), m.group('n')
        out = [ctx.link(f'{p}-{n}')]
        if m.group('rng'):
            out.append('〜' + ctx.link(f'{p}-{m.group("rng")[1:]}', m.group('rng')[1:]))
        for cm in CONT_RE.finditer(m.group('cont') or ''):
            out.append(cm.group(1) + ctx.link(f'{p}-{cm.group(2)}', cm.group(2)))
            if cm.group(3):
                out.append('〜' + ctx.link(f'{p}-{cm.group(4)}', cm.group(4)))
        return ''.join(out)
    return ID_RE.sub(rep, s)


def inline(s: str, ctx: Ctx) -> str:
    """Turns a table cell or a condensed sentence into HTML (`code`, **bold**, ID links)."""
    out = []
    for part in re.split(r'(`[^`]+`)', s or ''):
        if len(part) >= 2 and part.startswith('`') and part.endswith('`'):
            out.append('<code>' + esc(part[1:-1]) + '</code>')
        else:
            t = esc(part)
            t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
            out.append(link_ids(t, ctx))
    return ''.join(out)


ID_ONLY_RE = re.compile(r'^([A-Z]{2,5})-(\d{2,})$')


def ids_text(items, sort: bool = True) -> str:
    """Writes a list of IDs the way the reports do: 「FR-01〜14、24、DRV-03」. With sort, the numbers of each prefix are
    sorted and three or more in a row become a range; without it, the order is kept (the order means something, such
    as the drivers a decision addresses, most important first). Other texts are kept as they are."""
    order, nums = [], {}
    for x in items or []:
        if x is None:
            continue
        x = str(x).strip()
        m = ID_ONLY_RE.match(x)
        if not m:
            if x:
                order.append(('', x))
            continue
        p, n = m.group(1), m.group(2)
        if p not in nums:
            nums[p] = []
            order.append((p, None))
        if n not in nums[p]:
            nums[p].append(n)
    parts = []
    for p, x in order:
        if not p:
            parts.append(x)
            continue
        ns = sorted(nums[p], key=int) if sort else nums[p]
        runs: list = []
        for n in ns:
            if sort and runs and int(n) == int(runs[-1][-1]) + 1 and len(n) == len(runs[-1][-1]):
                runs[-1].append(n)
            else:
                runs.append([n])
        segs = []
        for r in runs:
            segs += [f'{r[0]}〜{r[-1]}'] if len(r) >= 3 else r
        parts.append(f'{p}-' + '、'.join(segs))
    return '、'.join(parts)


# ---------------------------------------------------------------- tables

def width_class(values: list) -> str:
    if not values:
        return ''
    avg = sum(len(v) for v in values) / len(values)
    mx = max(len(v) for v in values)
    if mx <= 9:
        return 'w-id'
    if avg < 14:
        return 'w-s'
    if avg < 45:
        return 'w-m'
    if avg < 110:
        return 'w-l'
    return 'w-xl'


class Table:
    """A table from a report, with columns dropped by name and revision notes removed from its cells."""

    def __init__(self, block: Block, where: str, ctx: Ctx, drop=(), clean=True):
        self.where = where
        head = block.rows[0]
        keep = [k for k, h in enumerate(head) if h not in drop]
        missing = [d for d in drop if d not in head]
        if missing:
            ctx.warn('列', f'{where}: 外す列 {"、".join(missing)} が見つからない')
        self.head = [clean_text(head[k])[0] if clean else head[k] for k in keep]
        self.rows = []
        for r in block.rows[1:]:
            r = r + [''] * (len(head) - len(r))
            row = []
            for k in keep:
                cell = r[k]
                if clean:
                    c, ch = clean_text(cell)
                    if ch:
                        ctx.cleaned.append((where, cell, c))
                    cell = c
                row.append(cell)
            self.rows.append(row)

    def col(self, name: str) -> int:
        return self.head.index(name)


def col_classes(head, rows, col_cls) -> list:
    """Width classes of the columns. col_cls is either the whole list or a dict that overrides some columns."""
    if isinstance(col_cls, list):
        return col_cls
    out = [width_class([r[k] for r in rows if k < len(r)]) for k in range(len(head))]
    for k, v in (col_cls or {}).items():
        if k < len(out):
            out[k] = v
    return out


def render_table(head, rows, ctx: Ctx, *, cls='', row_ids=None, cell=None, col_cls=None, groups=None, row_cls=None) -> str:
    """cell(r, c, text) returns a cell's HTML. groups is [(row index, heading HTML, id)]. row_cls is a class per row."""
    col_cls = col_classes(head, rows, col_cls)
    ths = ''.join(f'<th scope="col" class="{col_cls[k]}">{esc(h)}</th>' for k, h in enumerate(head))
    gmap = {g[0]: g for g in (groups or [])}
    trs = []
    for i, r in enumerate(rows):
        if i in gmap:
            _, label, gid = gmap[i]
            gid_attr = f' id="{esc(gid)}"' if gid else ''
            trs.append(f'<tr class="grp"{gid_attr}><th colspan="{len(head)}" scope="colgroup">{label}</th></tr>')
        rid = row_ids[i] if row_ids and i < len(row_ids) and row_ids[i] else ''
        rid_attr = f' id="{esc(rid)}"' if rid else ''
        if row_cls and i < len(row_cls) and row_cls[i]:
            rid_attr += f' class="{esc(row_cls[i])}"'
        tds = []
        for k, h in enumerate(head):
            text = r[k] if k < len(r) else ''
            content = cell(i, k, text) if cell else inline(text, ctx)
            tag = 'th scope="row"' if k == 0 else 'td'
            tds.append(f'<{tag} class="{col_cls[k]}">{content}</{tag.split()[0]}>')
        trs.append(f'<tr{rid_attr}>{"".join(tds)}</tr>')
    return (f'<div class="tbl-wrap"><table class="{cls}"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def render_grouped(head, rows, ctx: Ctx, key_cols, *, cls='', col_cls=None, row_ids=None) -> str:
    """Merges consecutive rows with the same values in the leading columns (key_cols) into one cell (rowspan)."""
    col_cls = col_classes(head, rows, col_cls)
    ths = ''.join(f'<th scope="col" class="{col_cls[k]}">{esc(h)}</th>' for k, h in enumerate(head))
    spans = [[1] * len(head) for _ in rows]
    for k in key_cols:
        i = 0
        while i < len(rows):
            j = i + 1
            while (j < len(rows) and rows[j][k] == rows[i][k]
                   and all(rows[j][kk] == rows[i][kk] for kk in key_cols if kk < k)):
                j += 1
            spans[i][k] = j - i
            for t in range(i + 1, j):
                spans[t][k] = 0
            i = j
    trs = []
    for i, r in enumerate(rows):
        tds = []
        for k in range(len(head)):
            if spans[i][k] == 0:
                continue
            rs = f' rowspan="{spans[i][k]}"' if spans[i][k] > 1 else ''
            tag = 'th scope="rowgroup"' if k in key_cols else 'td'
            tds.append(f'<{tag} class="{col_cls[k]}"{rs}>{inline(r[k], ctx)}</{tag.split()[0]}>')
        start = ' class="g-start"' if any(spans[i][k] > 0 for k in key_cols[:1]) else ''
        rid = f' id="{esc(row_ids[i])}"' if row_ids and row_ids[i] else ''
        trs.append(f'<tr{start}{rid}>{"".join(tds)}</tr>')
    return (f'<div class="tbl-wrap"><table class="grouped {cls}"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def def_cell(text: str, ctx: Ctx, title: bool = True) -> str:
    """Shows 「DRV-01 配車の…」 as the ID above the name."""
    m = re.match(r'^([A-Z]{2,4}-\d{2})\s*(.*)$', text)
    if not m:
        return inline(text, ctx)
    name = m.group(2)
    if not name and title:
        name = ctx.titles.get(m.group(1), '').split(' ', 1)[-1] if ctx.titles.get(m.group(1)) else ''
    # an ID without a row on this page (an SLI or NFR of the quality chain) links to the quality summary
    out = (f'<span class="def-id">{esc(m.group(1))}</span>' if m.group(1) in ctx.own
           else f'<span class="def-id">{ctx.link(m.group(1))}</span>')
    if name:
        out += f'<span class="def-name">{inline(name, ctx)}</span>'
    return out


def ref_cell(text: str, ctx: Ctx) -> str:
    """Shows a cell that holds only an ID (「DRV-18」) as a link above the item's name."""
    m = re.match(r'^([A-Z]{2,4}-\d{2})$', text.strip())
    if not m:
        return inline(text, ctx)
    id_ = m.group(1)
    t = ctx.titles.get(id_, '')
    name = t.split(' ', 1)[1] if ' ' in t else ''
    return ctx.link(id_) + (f'<span class="def-name">{esc(name)}</span>' if name else '')


# ---------------------------------------------------------------- parts

def details(tid: str, title: str, body: str, count: str = '', open_: bool = False) -> str:
    o = ' open' if open_ else ''
    cnt = f'<span class="t-count">{esc(count)}</span>' if count else ''
    return (f'<details class="tbl" id="{esc(tid)}"{o}><summary><span class="t-title">{esc(title)}</span>{cnt}'
            f'<span class="chev" aria-hidden="true"></span></summary><div class="tbl-body">{body}</div></details>')


def item(iid: str, label: str, title: str, body: str, ctx: Ctx | None = None) -> str:
    lab = f'<span class="i-id">{esc(label)}</span>' if label else ''
    t = inline(title, ctx) if ctx else esc(title)
    return (f'<details class="item" id="{esc(iid)}"><summary>{lab}<span class="i-title">{t}</span>'
            f'<span class="chev" aria-hidden="true"></span></summary><div class="item-body">{body}</div></details>')


def _char_w(ch: str) -> float:
    return 0.55 if ord(ch) < 0x2000 else 1.0


def wrap_ja(text: str, limit: float) -> str:
    """Breaks Japanese text with <br/> at punctuation or spaces (Mermaid breaks only at spaces and hyphenates long
    words)."""
    if '<br' in text or sum(_char_w(c) for c in text) <= limit:
        return text
    lines, cur, w, brk = [], '', 0.0, -1
    for ch in text:
        cur += ch
        w += _char_w(ch)
        if ch in '、。）」 ,・':
            brk = len(cur)
        elif ch in '（「' and len(cur) > 1:
            brk = len(cur) - 1
        if w > limit:
            if 0 < brk:
                head, cur = cur[:brk], cur[brk:]
            else:
                head, cur = cur[:-1], cur[-1:]
            if head.strip():
                lines.append(head.rstrip())
            cur = cur.lstrip()
            w = sum(_char_w(c) for c in cur)
            brk = -1
    if cur.strip():
        lines.append(cur)
    return '<br/>'.join(lines)


SEQ_MSG_RE = re.compile(r'^(\s*[\w-]+\s*(?:-{1,2}>>|-{1,2}>|-{1,2}x|-{1,2}\))\s*[+-]?[\w-]+\s*:\s*)(.*)$')
SEQ_NOTE_RE = re.compile(r'^(\s*Note\s+(?:over|left of|right of)\s+[^:]+:\s*)(.*)$')
SEQ_BLOCK_RE = re.compile(r'^(\s*(?:alt|else|opt|loop|par|and|critical|break)\s+)(.*)$')
SEQ_PART_RE = re.compile(r'^(\s*(?:participant|actor)\s+[\w-]+\s+as\s+)((?:ELM|USR)-\d{2})\s+(.*)$')


def wrap_sequence(src: str) -> str:
    out = []
    for line in src.split('\n'):
        m = SEQ_PART_RE.match(line)
        if m:
            out.append(f'{m.group(1)}{m.group(2)}<br/>{m.group(3)}')
            continue
        for rx, lim in ((SEQ_MSG_RE, 24), (SEQ_NOTE_RE, 30), (SEQ_BLOCK_RE, 40)):
            m = rx.match(line)
            if m:
                line = m.group(1) + wrap_ja(m.group(2), lim)
                break
        out.append(line)
    return '\n'.join(out)


def set_direction(src: str, d: str) -> str:
    """Changes a diagram's direction (flowchart LR or TB, the ER diagram's direction). The content stays the same."""
    lines = src.split('\n')
    k = next((i for i, x in enumerate(lines) if x.strip()), 0)
    first = lines[k].strip()
    if first.startswith(('flowchart', 'graph')):
        lines[k] = re.sub(r'^(\s*(?:flowchart|graph))(?:\s+\w+)?', r'\1 ' + d, lines[k])
    elif first.startswith('erDiagram'):
        lines.insert(k + 1, f'  direction {d}')
    return '\n'.join(lines)


def mermaid(src: str, ctx: Ctx, where: str, kind_hint: str = '') -> str:
    src2, ch = clean_mermaid(src)
    if ch:
        ctx.cleaned.append((where + '（図）', '…', '…'))
    key = where.split(' > ', 1)[1] if ' > ' in where else where
    if key in ctx.directions:
        src2 = set_direction(src2, ctx.directions[key])
        ctx.used_directions.add(key)
    first = src2.strip().split('\n', 1)[0].strip()
    kind = first.split()[0] if first else kind_hint
    if kind == 'sequenceDiagram':
        src2 = wrap_sequence(src2)
    if kind in ('flowchart', 'graph'):
        # a box labelled only with an element ID (「ELM-04」) gets the element's name, so the diagram reads on its own
        def named(m):
            t = ctx.titles.get(m.group(2), '')
            return f'{m.group(1)}["{t}"]' if t.startswith(m.group(2) + ' ') and '"' not in t else m.group(0)
        src2 = re.sub(r'(\b\w+)\["(ELM-\d{2})"\]', named, src2)
    return (f'<figure class="mmd" data-kind="{esc(kind)}"><div class="mmd-bar">'
            f'<button type="button" class="mmd-fit" aria-pressed="false">幅に合わせる</button>'
            f'<button type="button" class="mmd-full">全画面</button></div>'
            f'<div class="mmd-out" aria-live="polite"><p class="mmd-wait">図を描いています…</p></div>'
            f'<pre class="mmd-src" hidden>{esc(src2)}</pre></figure>')


def chips_index(entries: list) -> str:
    """Turns [(href, text, tooltip)] into an index inside a toggle."""
    return '<nav class="idx" aria-label="この表の中">' + ''.join(
        f'<a class="chip qr-base" href="#{esc(h)}" data-tip="{esc(t)}">{esc(x)}</a>' for h, x, t in entries) + '</nav>'


def bullets(items: list, ctx: Ctx, cls: str = 'bul') -> str:
    lis = []
    for it in items:
        if isinstance(it, list) and len(it) == 2:
            lis.append(f'<li><span class="bl">{esc(it[0])}</span>{inline(it[1], ctx)}</li>')
        elif isinstance(it, dict):
            lab = it.get('label')
            body = inline(it.get('text', ''), ctx)
            sub = it.get('items')
            subh = bullets(sub, ctx, 'bul sub-bul') if sub else ''
            lis.append(f'<li>{f"<span class=bl>{esc(lab)}</span>" if lab else ""}{body}{subh}</li>')
        else:
            lis.append(f'<li>{inline(str(it), ctx)}</li>')
    return f'<ul class="{cls}">' + ''.join(lis) + '</ul>'


def subhead(text: str) -> str:
    return f'<p class="list-label">{esc(text)}</p>'


# ---------------------------------------------------------------- latency budget charts

KIND_NAMES = {'own': '自分の処理', 'ext': '外部サービスと回線', 'wait': '待ち',
              'ok': '新しい', 'edge': '境目', 'stale': '古い'}


def nice_step(span: float) -> float:
    for s in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300):
        if span / s <= 8:
            return s
    return 600


def fmt_num(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f'{int(round(v)):,}'
    return f'{v:.2f}'.rstrip('0').rstrip('.') if abs(v * 10 - round(v * 10)) < 1e-9 else f'{v:.2f}'


def fmt_tick(v: float, axis: dict) -> str:
    if axis.get('clock'):
        h0, m0 = (int(x) for x in axis['clock'].split(':'))
        t = h0 * 60 + m0 + int(round(v))
        return f'{t // 60:02d}:{t % 60:02d}'
    return fmt_num(v)


def budget_chart(spec: dict, ctx: Ctx) -> str:
    unit = spec.get('unit', '秒')
    axis = spec.get('axis', {})
    rows = spec['rows']
    ths = spec.get('thresholds', [])
    top = max([sum(s['v'] for s in r['segments']) for r in rows]
              + [r.get('mark', {}).get('v', 0) for r in rows] + [t['v'] for t in ths])
    amax = axis.get('max') or top * 1.06
    step = axis.get('step') or nice_step(amax)
    pct = lambda v: f'{min(v, amax) / amax * 100:.3f}%'
    used = []
    out = [f'<figure class="bud" style="--th:{esc(spec.get("track", ""))}">']
    rows_h = []
    table_rows = []
    for r in rows:
        segs = []
        total = 0.0
        for s in r['segments']:
            k = s.get('k', 'own')
            if k not in used:
                used.append(k)
            tip = f'{s["name"]}: {fmt_num(s["v"])} {unit}' + (f'（{s["note"]}）' if s.get('note') else '')
            lab = s.get('label', fmt_num(s['v']))
            segs.append(f'<span class="seg k-{esc(k)}" style="left:{pct(total)};width:{pct(s["v"])}" '
                        f'data-tip="{esc(tip)}" tabindex="0"><i>{esc(lab)}</i></span>')
            table_rows.append([r['label'], s['name'], fmt_num(s['v']), s.get('note', '')])
            total += s['v']
        track = r.get('track', ths[0]['v'] if ths else total)
        marks = ''
        if r.get('mark'):
            mk = r['mark']
            marks = (f'<span class="bud-mark" style="left:{pct(mk["v"])}" '
                     f'data-tip="{esc(mk["name"])}: {fmt_num(mk["v"])} {esc(unit)}" tabindex="0"></span>')
            table_rows.append([r['label'], mk['name'], fmt_num(mk['v']), ''])
        lines = ''.join(f'<span class="bud-th" style="left:{pct(t["v"])}"></span>' for t in ths)
        sub = f'<span class="bud-sub">{inline(r["sub"], ctx)}</span>' if r.get('sub') else ''
        tag = f'<span class="tag">{esc(r["tag"])}</span>' if r.get('tag') else ''
        rows_h.append(f'<div class="bud-row{" is-rejected" if r.get("rejected") else ""}">'
                      f'<div class="bud-label"><span class="bud-name">{inline(r["label"], ctx)}{tag}</span>{sub}</div>'
                      f'<div class="bud-plot"><span class="bud-track" style="width:{pct(track)}"></span>'
                      f'{"".join(segs)}{marks}{lines}</div></div>')
    # legend
    lg = []
    for k in used:
        lg.append(f'<span class="lg"><span class="sw k-{k}"></span>{esc(KIND_NAMES.get(k, k))}</span>')
    if spec.get('show_track', True) and ths:
        lg.append('<span class="lg"><span class="sw sw-track"></span>余り（しきい値までの下地）</span>')
    for t in ths:
        lg.append(f'<span class="lg"><span class="sw sw-th"></span>{esc(t["name"])}</span>')
    if any(r.get('mark') for r in rows):
        lg.append(f'<span class="lg"><span class="sw sw-mark"></span>{esc(spec.get("mark_name", "最悪"))}</span>')
    out.append('<div class="legend bud-legend">' + ''.join(lg) + '</div>')
    out.append('<div class="bud-rows">' + ''.join(rows_h) + '</div>')
    # axis ticks
    ticks = []
    v = 0.0
    th_vals = [t['v'] for t in ths]
    while v <= amax + 1e-9:
        if not any(abs(v - tv) < 1e-9 for tv in th_vals):   # where a tick falls on a threshold, only the threshold's tick is shown
            ticks.append(f'<span class="tick" style="left:{pct(v)}">{esc(fmt_tick(v, axis))}</span>')
        v += step
    th_lab = ''.join(f'<span class="tick th" style="left:{pct(t["v"])}">{esc(t.get("tick", fmt_tick(t["v"], axis)))}</span>'
                     for t in ths)
    unit_lab = '' if axis.get('clock') else f'<span class="unit">{esc(axis.get("unit_label", unit))}</span>'
    out.append(f'<div class="bud-axis"><div class="bud-label"></div><div class="bud-ticks">{"".join(ticks)}{th_lab}'
               f'{unit_lab}</div></div>')
    # the values as a table (the chart's readable twin)
    tb = render_table(['行', '区間', unit if not axis.get('clock') else '分', 'もと'], table_rows, ctx,
                      cls='bud-table', col_cls=['w-m', 'w-m', 'num', 'w-m'],
                      cell=lambda i, k, t: (f'<span class="num">{esc(t)}</span>' if k == 2 else inline(t, ctx)))
    out.append(f'<details class="bud-num"><summary>数値の表</summary>{tb}</details>')
    out.append('</figure>')
    return ''.join(out)


# ---------------------------------------------------------------- threat model figure

def threat_svg(spec: dict, flow_tips: dict) -> str:
    W, H = spec['width'], spec['height']
    o = [f'<div class="tm-wrap"><svg class="tm" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="信頼の境界と、境界を越える流れ F1〜F17">'
         '<defs><marker id="tm-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="tm-head"/></marker></defs>']
    for z in spec.get('zones', []):
        o.append(f'<g class="tm-zone{" " + z["cls"] if z.get("cls") else ""}"><rect x="{z["x"]}" y="{z["y"]}" '
                 f'width="{z["w"]}" height="{z["h"]}" rx="10"/>'
                 f'<text x="{z["x"] + 12}" y="{z["y"] + 20}" class="tm-zl">{esc(z["label"])}</text></g>')
    for f in spec.get('flows', []):
        if not f.get('points'):
            continue
        pts = ' '.join(f'{x},{y}' for x, y in f['points'])
        end = '' if f.get('arrow') is False else ' marker-end="url(#tm-arr)"'
        ids = f.get('chips') or f.get('joins') or []
        o.append(f'<polyline class="tm-flow" data-flows="{esc(" ".join(ids))}" points="{pts}"{end}/>')
    for n in spec.get('nodes', []):
        k = n.get('kind', 'comp')
        x, y, w, h = n['x'], n['y'], n['w'], n['h']
        lines = n['label'] if isinstance(n['label'], list) else [n['label']]
        o.append(f'<g class="tm-node k-{k}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{6 if k != "store" else 12}"/>')
        if k == 'ext':
            o.append(f'<rect class="tm-inner" x="{x + 4}" y="{y + 4}" width="{w - 8}" height="{h - 8}" rx="4"/>')
        ty = y + h / 2 - (len(lines) - 1) * 8 + 4
        for li, t in enumerate(lines):
            cls = 'tm-id' if li == 0 and re.match(r'^ELM-\d\d$', t) else 'tm-nt'
            o.append(f'<text x="{x + w / 2}" y="{ty + li * 16:.1f}" class="{cls}" text-anchor="middle">{esc(t)}</text>')
        o.append('</g>')
    for f in spec.get('flows', []):
        if not f.get('chips'):
            continue
        cx, cy = f['at']
        for k, fid in enumerate(f['chips']):
            w = 34 if len(fid) <= 2 else 40
            x = cx + k * (w + 4) - (len(f['chips']) * (w + 4) - 4) / 2
            tip = flow_tips.get(fid, fid)
            o.append(f'<a href="#flow-{esc(fid)}" class="tm-chip" data-tip="{esc(tip)}" data-flow="{esc(fid)}">'
                     f'<rect x="{x:.1f}" y="{cy - 10}" width="{w}" height="20" rx="4"/>'
                     f'<text x="{x + w / 2:.1f}" y="{cy + 4.5}" text-anchor="middle">{esc(fid)}</text></a>')
    for t in spec.get('notes', []):
        o.append(f'<text x="{t["x"]}" y="{t["y"]}" class="tm-note">{esc(t["text"])}</text>')
    o.append('</svg></div>')
    lg = ('<div class="legend tm-legend"><span class="lg"><span class="sw sw-zone"></span>信頼の境界</span>'
          '<span class="lg"><span class="sw sw-comp"></span>コンポーネント</span>'
          '<span class="lg"><span class="sw sw-store"></span>データの置き場所</span>'
          '<span class="lg"><span class="sw sw-ext"></span>外部システム</span>'
          '<span class="lg"><span class="chip qr-emph">F1</span>流れ（表の行へ）</span></div>')
    return lg + ''.join(o)


# ---------------------------------------------------------------- loading

def id_key(k: str) -> tuple:
    """Sorts IDs by prefix and number (DEC-9, DEC-10, DEC-100)."""
    m = re.match(r'^([A-Z]+)-(\d+)$', str(k))
    return (m.group(1), int(m.group(2))) if m else (str(k), 0)


def load_items(d: Path, ctx: Ctx | None = None) -> dict:
    out = {}
    if not d.is_dir():
        return out
    for f in sorted(d.glob('*.yaml')):
        try:
            x = yaml.safe_load(f.read_text(encoding='utf-8'))
        except yaml.YAMLError as e:
            msg = f'読めない: {f.parent.name}/{f.name}（{str(e).splitlines()[0]}）'
            if ctx:
                ctx.warn('YAML', msg)
            else:
                print(msg, file=sys.stderr)
            continue
        if isinstance(x, dict) and x.get('id'):
            out[x['id']] = x
    return dict(sorted(out.items(), key=lambda kv: id_key(kv[0])))


def short(s: str, n: int = 90) -> str:
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s if len(s) <= n else s[:n - 1] + '…'


def git(args: list, cwd: Path) -> str:
    try:
        return subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def norm(s) -> str:
    return re.sub(r'\s+', '', str(s or ''))


def lvl_badge(x: str) -> str:
    return f'<span class="lvl lvl-{ {"高": "h", "中": "m", "低": "l"}.get(x, "x") }">{esc(x)}</span>'


# ---------------------------------------------------------------- the page

class Builder:
    def __init__(self, ddir: Path, qdir: Path, text_path: Path, out: Path):
        self.ddir, self.qdir, self.text_path, self.out = ddir, qdir, text_path, out
        self.ctx = Ctx()
        self.toc: dict = {}            # stage → [(id, name)]
        self.text = {}
        self.hashes: dict = {}         # condensed-text key → current hash of its source
        self.docs: dict = {}
        self.md: dict = {}
        self.stages: list = []
        self._tables: dict = {}

    # --- inputs
    def load(self) -> bool:
        c = self.ctx
        # the design items are the source of truth (artifacts.md): every table that has items is built from them
        self.drv = load_items(self.ddir / 'drv', c)
        self.dec = load_items(self.ddir / 'dec', c)
        self.elm = load_items(self.ddir / 'elm', c)
        self.ifc = load_items(self.ddir / 'ifc', c)
        self.dat = load_items(self.ddir / 'dat', c)
        self.fnd = load_items(self.ddir / 'fnd', c)
        dc = self.ddir / 'design-context.yaml'
        self.dctx = {}
        if dc.exists():
            try:
                self.dctx = yaml.safe_load(dc.read_text(encoding='utf-8')) or {}
            except yaml.YAMLError as e:
                c.warn('YAML', f'読めない: design-context.yaml（{str(e).splitlines()[0]}）')
        # the reports: diagrams, and the sections that no item holds
        for n, fn in REPORT_FILES.items():
            p = self.ddir / fn
            if p.exists():
                self.docs[n] = p.read_text(encoding='utf-8')
        has = {1: bool(self.live(self.drv)),
               2: bool(self.live(self.elm)) or bool(self.decs('architecture')),
               3: bool(self.live(self.ifc)) or bool(self.live(self.dat)) or bool(self.decs('high-level-design'))}
        self.stages = [n for n in (1, 2, 3) if has[n] or n in self.docs]
        if not self.stages:
            return False
        for n in self.stages:
            if has[n] and n not in self.docs:
                c.warn('報告書', f'{REPORT_FILES[n]} がない（第 {n} 段階の図と、報告書にしかない表を省いた）')
            if not has[n]:
                c.warn('YAML', f'第 {n} 段階の YAML の項目がない（回答を反映する前の下書き）。報告書にしかない表と図だけを示した')
        if self.text_path.exists():
            self.text = yaml.safe_load(self.text_path.read_text(encoding='utf-8')) or {}
        else:
            c.warn('添削文', f'{self.text_path} がない（添削文の節は報告書の表と図で代える）')
        for k in self.text:
            if k not in TEXT_KEYS:
                why = '（DEC の中身は dec/*.yaml から作るので要らない）' if k == 'decisions' else ''
                c.warn('使わないキー', f'{self.text_path.name} の {k}{why}')
        c.directions = dict(self.text.get('diagram_direction') or {})
        # apply the fixes (exact text replacements) to the reports before parsing
        for fx in self.text.get('fixes', []) or []:
            n = next((k for k, v in REPORT_FILES.items() if v == fx.get('file')), None)
            if n is None or n not in self.docs:
                c.warn('手直し', f'{fx.get("file")}: ファイルがない')
                continue
            if fx['find'] not in self.docs[n]:
                c.warn('手直し', f'{fx["file"]}: 見つからない「{short(fx["find"], 50)}」')
                continue
            self.docs[n] = self.docs[n].replace(fx['find'], fx.get('replace', ''))
        self.md = {n: parse_md(t, REPORT_FILES[n]) for n, t in self.docs.items()}
        # tooltips, and the IDs that have a row on this page
        t = c.titles
        for coll in (self.drv, self.dec, self.elm, self.ifc, self.dat):
            for k, v in coll.items():
                if v.get('status') == 'retired':
                    t[k] = f'{k} {v.get("title", "")}（廃止）'
                    continue
                t[k] = short(f'{k} {self.t(v.get("title"))}')
                if not (k.startswith('DEC-') and v.get('stage') not in ('architecture', 'high-level-design')):
                    c.own.add(k)
        for k, v in self.fnd.items():
            t[k] = short(f'{k} {v.get("title", "")}（指摘）')
        for grp, key in (('technology_constraints', 'statement'), ('project_constraints', 'statement'),
                         ('teams', 'name'), ('anticipated_changes', 'change'), ('stakeholders', 'role')):
            for x in self.dctx.get(grp, []) or []:
                if isinstance(x, dict) and x.get('id'):
                    t[x['id']] = short(f'{x["id"]} {x.get(key) or ""}')
                    c.own.add(x['id'])
        # quality-chain items (tooltips, and links to the quality summary)
        q = self.qdir
        for sub in ('fr', 'qr', 'nfr', 'sli', 'qiu', 'kpi', 'ebp', 'frp'):
            for k, v in load_items(q / sub).items():
                extra = '（廃止）' if v.get('status') == 'retired' else ''
                t.setdefault(k, short(f'{k} {v.get("title", "")}{extra}'))
        qc = q / 'context.yaml'
        if qc.exists():
            qq = yaml.safe_load(qc.read_text(encoding='utf-8')) or {}
            for grp in ('users', 'cujs', 'kgis'):
                for x in qq.get(grp, []) or []:
                    t.setdefault(x['id'], f'{x["id"]} {x.get("name", "")}')
            for x in qq.get('outcomes', []) or []:
                t.setdefault(x['id'], short(f'{x["id"]} {x.get("statement", "")}'))
        qs = q / 'summary.html'
        if qs.exists():
            c.quality_anchor = set(re.findall(r' id="([A-Z]+-\d{2})"', qs.read_text(encoding='utf-8')))
            c.quality_href = Path(os.path.relpath(qs.resolve(), self.out.parent.resolve())).as_posix()
        for k in list(t):
            if k.split('-')[0] in QUALITY_PREFIXES and k in c.quality_anchor:
                t[k] = t[k] + '（品質の要約へ）'
        return True

    # --- items
    @staticmethod
    def live(d: dict) -> dict:
        return {k: v for k, v in d.items() if v.get('status') != 'retired'}

    def decs(self, stage: str) -> dict:
        return {k: v for k, v in self.dec.items() if v.get('stage') == stage and v.get('status') != 'retired'}

    def t(self, s, where: str = '') -> str:
        """A text from a YAML item, without revision notes."""
        if s is None:
            return ''
        if isinstance(s, (list, tuple)):
            return '、'.join(x for x in (self.t(v, where) for v in s) if x)
        if isinstance(s, dict):
            return '、'.join(f'{k}: {self.t(v, where)}' for k, v in s.items())
        s = str(s).strip()
        out, ch = clean_text(s)
        if ch:
            self.ctx.cleaned.append((where or 'YAML', s, out))
        return out

    def term(self, table: dict, value, where: str) -> str:
        if value is None or value == '':
            return '—'
        if value in table:
            return table[value]
        # a value with a note after it: 「personal（IP アドレス）」
        m = re.match(r'^([A-Za-z-]+)\s*[（(](.*)[）)]$', str(value).strip(), re.S)
        if m and m.group(1) in table:
            return f'{table[m.group(1)]}（{self.t(m.group(2), where)}）'
        self.ctx.warn('用語集にない値', f'{where}: {value}')
        return str(value)

    def title_of(self, id_: str) -> str:
        tt = self.ctx.titles.get(id_, '')
        return tt.split(' ', 1)[1] if ' ' in tt else ''

    def own_cell(self, id_: str, tag: str = '') -> str:
        """The ID cell of an item's own row: the ID above its title."""
        tg = f'<span class="tag">{esc(tag)}</span>' if tag else ''
        name = self.title_of(id_)
        return (f'<span class="def-id">{esc(id_)}{" " + tg if tg else ""}</span>'
                + (f'<span class="def-name">{inline(name, self.ctx)}</span>' if name else ''))

    # --- comparing a report table with the items (a stale report shows up here)
    def md_ids(self, n: int, titles: tuple, col: str) -> list | None:
        if n not in self.md:
            return None
        s = self.sec(n, *titles, quiet=True)
        if s is None or not s.tables():
            self.ctx.warn('突き合わせなかった表', f'{REPORT_FILES[n]} > {" > ".join(titles)}（見つからない）')
            return None
        rows = s.tables()[0].rows
        k = rows[0].index(col) if col in rows[0] else 0
        out = []
        for r in rows[1:]:
            cell = r[k] if k < len(r) else ''
            m = re.match(r'^\s*([A-Z]{2,5}-\d{2,})', cell)
            if m and '（廃止）' not in cell:
                out.append(m.group(1))
        return out

    def compare(self, what: str, n: int, titles: tuple, col: str, yaml_ids) -> None:
        got = self.md_ids(n, titles, col)
        if got is None:
            return
        a, b = set(got), set(yaml_ids)
        if a - b:
            self.ctx.warn('食い違い', f'{what}: 報告書にあって YAML にない {"、".join(sorted(a - b, key=id_key))}')
        if b - a:
            self.ctx.warn('食い違い', f'{what}: YAML にあって報告書にない {"、".join(sorted(b - a, key=id_key))}')

    # --- condensed texts
    def curated(self, key: str, *secs) -> dict:
        """Returns a condensed text, and reports it when its source section changed since it was written."""
        node = self.text
        for part in key.split('.'):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        secs = [s for s in secs if s is not None]
        if secs:
            self.check_hash(key, secs, present=bool(node))
        return node or {}

    def check_hash(self, key: str, secs: list, present: bool = True):
        h = section_hash(*secs)
        self.hashes[key] = h
        if not present:
            self.ctx.warn('添削文がない', f'{key}（{secs[0].path()}）')
        elif (self.text.get('hashes') or {}).get(key) != h:
            self.ctx.warn('添削文のもとが変わった', f'{key}（{secs[0].path()}）')

    def sec(self, n: int, *titles, quiet: bool = False) -> Section | None:
        root = self.md.get(n)
        if root is None:
            return None
        if len(root.children) == 1 and root.children[0].level == 1:
            root = root.children[0]
        s = root.find(*titles)
        if s is None and not quiet:
            self.ctx.warn('節', f'{REPORT_FILES[n]} > {" > ".join(titles)} が見つからない')
        return s

    def table(self, n: int, titles: tuple, idx: int = 0, drop=(), clean=True) -> Table | None:
        key = (n, titles, idx, tuple(drop), clean)
        if key in self._tables:
            return self._tables[key]
        s = self.sec(n, *titles)
        if s is None:
            return None
        tbs = s.tables()
        if len(tbs) <= idx:
            self.ctx.warn('表', f'{s.path()} の {idx + 1} つ目の表がない')
            return None
        self._tables[key] = Table(tbs[idx], s.path(), self.ctx, drop=drop, clean=clean)
        return self._tables[key]

    def add_toc(self, stage, tid, name):
        self.toc.setdefault(stage, []).append((tid, name))

    def stage_title(self, n: int) -> str:
        root = self.md.get(n)
        h1 = root.children[0].title if root is not None and root.children else STAGE_TITLES[n]
        return h1.split(':')[0].split('：')[0].strip()

    def stage_wrap(self, n: int, parts: list) -> str:
        src = STAGE_SOURCES[n] + (f' · {REPORT_FILES[n]}' if n in self.md else '')
        return (f'<section id="sec-{n}" class="stage"><header class="stage-head"><span class="stage-no">第 {n} 段階</span>'
                f'<h2>{esc(self.stage_title(n))}</h2><span class="src">{esc(src)}</span></header>'
                + ''.join(parts) + '</section>')

    # --- stage 1
    def stage1(self) -> str:
        if 1 not in self.stages:
            return ''
        c = self.ctx
        parts = []
        drv = self.live(self.drv)

        def rank_of(v):
            try:
                return int((v.get('priority') or {}).get('rank'))
            except (TypeError, ValueError):
                return None
        # ranking table (first, open)
        ranked = [v for v in drv.values() if v.get('kind') != 'principle']
        for v in ranked:
            if rank_of(v) is None:
                c.warn('YAML', f'drv/{v["id"]}.yaml: priority.rank がない（順位表の最後に置いた）')
        ranked.sort(key=lambda v: (rank_of(v) is None, rank_of(v) or 0, id_key(v['id'])))
        if ranked:
            rows = []
            for v in ranked:
                p = v.get('priority') or {}
                w = f'drv/{v["id"]}.yaml'
                rows.append([str(rank_of(v) or '—'), v['id'],
                             self.term(T_LEVEL, p.get('business'), w + ' priority.business'), self.t(p.get('business_reason'), w),
                             self.term(T_LEVEL, p.get('difficulty'), w + ' priority.difficulty'), self.t(p.get('difficulty_reason'), w),
                             'はい' if v.get('primary') else 'いいえ'])

            def cell(i, k, x):
                if k == 0:
                    return f'<span class="num">{esc(x)}</span>'
                if k == 1:
                    return ref_cell(x, c)
                if k in (2, 4):
                    return lvl_badge(x)
                if k == 6:
                    return f'<span class="chip {"qr-emph" if x == "はい" else "qr-out"}">{esc(x)}</span>'
                return inline(x, c)
            n_main = sum(1 for v in ranked if v.get('primary'))
            body = render_table(['順位', 'DRV', '事業の優先度', '理由', '設計上の難しさ', '理由', '主'], rows, c,
                                row_ids=['rank-' + v['id'] for v in ranked], cell=cell, cls='rank',
                                col_cls=['num', 'w-m', 'w-id', 'w-m', 'w-id', 'w-l', 'w-id'])
            parts.append(details('t-rank', '順位表', body, f'{len(rows)} 件 · 主 {n_main}', open_=True))
            self.add_toc(1, 't-rank', '順位表')
            got = self.md_ids(1, ('順位表',), 'DRV')
            if got is not None:
                self.compare('順位表', 1, ('順位表',), 'DRV', [v['id'] for v in ranked])
                order = [v['id'] for v in ranked if v['id'] in got]
                if order != [x for x in got if x in order]:
                    c.warn('食い違い', '順位表: 報告書と YAML（priority.rank）で順位が違う')
        # premises and stakeholders (design-context.yaml)
        dx = self.dctx
        rows = []
        for x in dx.get('technology_constraints') or []:
            rows.append([x.get('id', ''), '技術制約: ' + self.term(T_TC_KIND, x.get('kind'), f'{x.get("id")} kind'),
                         self.t(x.get('statement'), 'design-context.yaml') or '（未定）', self.t(x.get('source')),
                         self.term(T_BASIS, x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('project_constraints') or []:
            rows.append([x.get('id', ''), self.term(T_PC_KIND, x.get('kind'), f'{x.get("id")} kind'),
                         self.t(x.get('statement'), 'design-context.yaml') or '（未定）', self.t(x.get('source')),
                         self.term(T_BASIS, x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('teams') or []:
            rows.append([x.get('id', ''), 'チーム', f'{self.t(x.get("name"))}。受け持ち: {self.t(x.get("owns"))}',
                         self.t(x.get('source')) or '—', self.term(T_BASIS, x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('anticipated_changes') or []:
            when = f'（{self.t(x.get("expected"))}）' if x.get('expected') else ''
            rows.append([x.get('id', ''), '将来の変更', self.t(x.get('change')) + when, self.t(x.get('source')) or '—',
                         self.term(T_BASIS, x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('stakeholders') or []:
            conc = self.t(x.get('concerns'))
            rows.append([x.get('id', ''), '利害関係者', self.t(x.get('role')) + (f'。関心事: {conc}' if conc else ''),
                         self.t(x.get('source')) or '—', self.term(T_BASIS, x.get('basis'), f'{x.get("id")} basis')])
        if rows:
            body = render_table(['ID', '種類', '内容', '出どころ', '根拠'], rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: f'<span class="def-id">{esc(x)}</span>' if k == 0 else inline(x, c))
            parts.append(details('t-premise', '設計の前提と利害関係者', body, f'{len(rows)} 件'))
            self.add_toc(1, 't-premise', '設計の前提と利害関係者')
            self.compare('設計の前提と利害関係者', 1, ('設計の前提と利害関係者',), 'ID', [r[0] for r in rows])
        # concerns: only in the report (without the column of what each became)
        if 1 in self.md:
            t = self.table(1, ('関心事の一覧',), drop=('なったもの',))
            if t:
                parts.append(details('t-concern', '関心事の一覧', render_table(t.head, t.rows, c), f'{len(t.rows)} 件'))
                self.add_toc(1, 't-concern', '関心事の一覧')
        # drivers by kind
        sc_head = ['出どころ', '刺激', '対象', '環境', '応答', '応答の測定量']
        sc_keys = ['source', 'stimulus', 'artifact', 'environment', 'response', 'measure']

        def scen(v):
            s = v.get('scenario') or {}
            return [self.t(s.get(k), f'drv/{v["id"]}.yaml scenario') or '—' for k in sc_keys]
        sc = [v for v in drv.values() if v.get('kind') in ('quality', 'change')]
        if sc:
            rows = [[v['id']] + scen(v) for v in sc]
            kinds = {v['id']: T_DRV_KIND.get(v.get('kind'), '') for v in sc}
            body = render_table(['DRV'] + sc_head, rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x, kinds[x]) if k == 0 else inline(x, c))
            parts.append(details('t-scenario', '品質と変更のシナリオ', body, f'{len(rows)} 件'))
            self.add_toc(1, 't-scenario', '品質と変更のシナリオ')
            self.compare('品質と変更のシナリオ', 1, ('設計を動かす要求', '品質と変更のシナリオ'), 'DRV', [r[0] for r in rows])
        cs = [v for v in drv.values() if v.get('kind') == 'constraint']
        if cs:
            rows = [[v['id'], self.t(v.get('statement'), f'drv/{v["id"]}.yaml'), T_NEG.get(v.get('negotiable'), '—'),
                     ids_text(v.get('sources'), sort=False)] for v in cs]
            body = render_table(['DRV', '制約', '交渉', '出どころ'], rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            parts.append(details('t-constraint', '制約', body, f'{len(rows)} 件'))
            self.add_toc(1, 't-constraint', '制約')
            self.compare('制約', 1, ('設計を動かす要求', '制約'), 'DRV', [r[0] for r in rows])
        fs = [v for v in drv.values() if v.get('kind') in ('function', 'observability', 'security')]
        if fs:
            rows = [[v['id'], self.term(T_DRV_KIND, v.get('kind'), f'{v["id"]} kind'),
                     self.t(v.get('statement'), f'drv/{v["id"]}.yaml'), ids_text(v.get('sources'), sort=False)] for v in fs]
            b = render_table(['DRV', '種類', '内容', '出どころ'], rows, c, row_ids=[r[0] for r in rows],
                             cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            ws = [v for v in fs if v.get('scenario')]
            if ws:
                b += subhead('シナリオ')
                b += render_table(['DRV'] + sc_head, [[v['id']] + scen(v) for v in ws], c, col_cls={0: 'w-m'},
                                  cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            parts.append(details('t-fos', '機能・観測・セキュリティの要求', b, f'{len(rows)} 件'))
            self.add_toc(1, 't-fos', '機能・観測・セキュリティの要求')
            self.compare('機能・観測・セキュリティの要求', 1, ('設計を動かす要求', '機能・観測・セキュリティの要求'), 'DRV',
                         [r[0] for r in rows])
        ps = [v for v in drv.values() if v.get('kind') == 'principle']
        if ps:
            rows = []
            for v in ps:
                src = ids_text(v.get('sources'), sort=False)
                rows.append([v['id'], self.t(v.get('statement'), f'drv/{v["id"]}.yaml'),
                             ids_text(v.get('derived_from'), sort=False) + (f'（{src}）' if src else '')])
            body = render_table(['DRV', '原則', '導いたもと'], rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            parts.append(details('t-principle', '全体の原則', body, f'{len(rows)} 件'))
            self.add_toc(1, 't-principle', '全体の原則')
            self.compare('全体の原則', 1, ('設計を動かす要求', '全体の原則'), 'DRV', [r[0] for r in rows])
        # conflicts: both drivers of a pair record it; the side with more to say is shown
        pairs: dict = {}
        for v in drv.values():
            for x in v.get('conflicts') or []:
                if not isinstance(x, dict) or not x.get('with') or x['with'] not in drv:
                    continue
                key = tuple(sorted((v['id'], x['with']), key=id_key))
                note = self.t(x.get('note'), f'drv/{v["id"]}.yaml conflicts')
                side = pairs.setdefault(key, {}).setdefault(v['id'], [])
                if note and note not in side:
                    side.append(note)
        if pairs:
            rows = []
            for key in sorted(pairs, key=lambda k: (id_key(k[0]), id_key(k[1]))):
                sides = pairs[key]
                notes = max(sides.values(), key=lambda ns: (len(ns), sum(len(x) for x in ns)))
                rows.append([f'{key[0]} と {key[1]}', notes])

            def ccell(i, k, x):
                if k == 0:
                    a, b = x.split(' と ')
                    return ref_cell(a, c) + '<span class="vs">と</span>' + ref_cell(b, c)
                return inline(x[0], c) if len(x) == 1 else bullets(x, c, 'in-bul')
            body = render_table(['要求', '競合と解き方'], rows, c, cell=ccell, col_cls=['w-m', 'w-xl'])
            parts.append(details('t-conflict', '競合', body, f'{len(rows)} 組'))
            self.add_toc(1, 't-conflict', '競合')
        if 1 in self.md:
            t = self.table(1, ('実現できるか',))
            if t:
                body = render_table(t.head, t.rows, c, cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c),
                                    col_cls={0: 'w-m'})
                parts.append(details('t-feasible', '実現できるか', body, f'{len(t.rows)} 件'))
                self.add_toc(1, 't-feasible', '実現できるか')
        return self.stage_wrap(1, parts)

    # --- decisions (stages 2 and 3)
    def dec_table(self, decs: dict, tid: str, cards: bool) -> str:
        c = self.ctx
        rows = []
        for k, v in decs.items():
            w = f'dec/{k}.yaml'
            rej = [r for r in v.get('rejected') or [] if isinstance(r, dict)]
            rows.append([k, self.t(v.get('question'), w), self.t(v.get('chosen'), w),
                         ids_text(v.get('addresses'), sort=False) or '—',
                         [(self.t(r.get('option'), w), self.t(r.get('reason'), w)) for r in rej]])

        def cell(i, k, x):
            if k == 0:
                more = f'<a class="more" href="#d-{esc(x)}">中身</a>' if cards else ''
                return self.own_cell(x) + more
            if k == 4:
                if not x:
                    return '—'
                return ''.join(f'<span class="nr"><span class="opt">{inline(o, c)}</span>'
                               + (f'<span class="note">{inline(r, c)}</span>' if r else '') + '</span>' for o, r in x)
            return inline(x, c)
        return render_table(['DEC', '問い', '選んだ案', '対象', '退けた案'], rows, c, row_ids=[r[0] for r in rows], cell=cell,
                            col_cls=['w-m', 'w-l', 'w-xl', 'w-s', 'w-xl'])

    def dec_card(self, v: dict) -> str:
        c = self.ctx
        did = v['id']
        w = f'dec/{did}.yaml'
        chosen = v.get('chosen') or ''
        rej = {norm(r.get('option')): r.get('reason') for r in v.get('rejected') or [] if isinstance(r, dict)}
        rows, verdicts = [], []
        found = False
        for o in v.get('options') or []:
            if not isinstance(o, dict):
                continue
            name = o.get('name') or ''
            if chosen and norm(name) == norm(chosen):
                verdicts.append(('chosen', ''))
                found = True
            elif norm(name) in rej:
                verdicts.append(('rej', self.t(rej[norm(name)], w)))
            else:
                verdicts.append(('', ''))
            rows.append([self.t(name, w), self.t(o.get('effect'), w) or '—', self.t(o.get('cost'), w) or '—', ''])
        if chosen and rows and not found:
            c.warn('YAML', f'{w}: chosen が options のどの name とも合わない')

        def entry(label: str, val) -> str:
            if isinstance(val, list):
                val = [x for x in val if x]
                if not val:
                    return ''
                val = val[0] if len(val) == 1 else '<ul>' + ''.join(f'<li>{x}</li>' for x in val) + '</ul>'
            return f'<dt>{esc(label)}</dt><dd>{val}</dd>' if val else ''

        def il(x) -> str:
            return inline(self.t(x, w), c) if x else ''
        head = entry('問い', il(v.get('question')))
        if chosen and not found:
            head += entry('選んだ案', il(chosen))
        body = f'<dl class="vp dec">{head}</dl>' if head else ''
        if rows:
            def cell(i, k, x):
                if k == 3:
                    vd, reason = verdicts[i]
                    if vd == 'chosen':
                        return '<span class="mk mk-ok">選んだ</span>'
                    if vd == 'rej':
                        return '<span class="mk mk-part">退けた</span>' + (f'<span class="mk-n">{inline(reason, c)}</span>' if reason else '')
                    return '—'
                return inline(x, c)
            body += render_table(['案', '効き目', '費用', '判定'], rows, c, cls='opts', cell=cell,
                                 row_cls=['is-chosen' if vd == 'chosen' else '' for vd, _ in verdicts],
                                 col_cls=['w-l', 'w-l', 'w-l', 'w-m'])
        rest = entry('選んだ理由', il(v.get('rationale')))
        rest += entry('得るもの', [il(x) for x in v.get('gains') or []])
        rest += entry('失うもの', [il(x) for x in v.get('costs') or []])
        rest += entry('応答を左右する点', [il(x) for x in v.get('sensitive_points') or []])
        tos = []
        for x in v.get('trade_offs') or []:
            if isinstance(x, dict):
                wi = x.get('with')
                wi = ids_text(wi, sort=False) if isinstance(wi, list) else self.t(wi, w)
                tos.append(inline(f'{wi}: {self.t(x.get("note"), w)}' if wi else self.t(x.get('note'), w), c))
            else:
                tos.append(il(x))
        rest += entry('引き換え', tos)
        rest += entry('前提', [il(x) for x in v.get('assumptions') or []])
        ps = []
        for p in v.get('parameters') or []:
            if isinstance(p, dict):
                basis = self.t(p.get('basis'), w)
                ps.append(f'<b>{inline(self.t(p.get("name"), w), c)}</b>: {inline(self.t(p.get("value"), w), c)}'
                          + (f'<span class="note">{inline(basis, c)}</span>' if basis else ''))
        rest += entry('設計上の値', ps)
        d = v.get('debt')
        if isinstance(d, dict) and d.get('what'):
            sub = il(d.get('what'))
            if d.get('why_accepted'):
                sub += f'<span class="note"><span class="nl">受け入れた理由</span>{il(d["why_accepted"])}</span>'
            if d.get('repay_when'):
                sub += f'<span class="note"><span class="nl">返すとき</span>{il(d["repay_when"])}</span>'
            rest += entry('技術的負債', sub)
        if v.get('deferred'):
            rest += entry('先送り', '見直すとき: ' + (il(v.get('revisit_when')) or '（未定）'))
        rest += entry('対象', inline(ids_text(v.get('addresses'), sort=False), c) if v.get('addresses') else '')
        rest += entry('依存する決定', inline(ids_text(v.get('depends_on')), c) if v.get('depends_on') else '')
        if rest:
            body += f'<dl class="vp dec">{rest}</dl>'
        return item(f'd-{did}', did, self.title_of(did) or did, body, c)

    def values_table(self, decs: dict) -> tuple:
        rows = []
        for k, v in decs.items():
            for p in v.get('parameters') or []:
                if isinstance(p, dict):
                    w = f'dec/{k}.yaml parameters'
                    rows.append([self.t(p.get('name'), w), self.t(p.get('value'), w), self.t(p.get('basis'), w) or '—', k])
        if not rows:
            return '', 0
        return render_table(['値', '仮の値', 'もと', '決定'], rows, self.ctx, col_cls={0: 'w-m', 1: 'w-m', 3: 'w-id'}), len(rows)

    def debt_rows(self, decs: dict) -> list:
        rows = []
        for k, v in decs.items():
            w = f'dec/{k}.yaml'
            d = v.get('debt')
            if isinstance(d, dict) and d.get('what'):
                rows.append([k, '負債: ' + self.t(d.get('what'), w), self.t(d.get('why_accepted'), w) or '—',
                             self.t(d.get('repay_when'), w) or '—'])
            if v.get('deferred'):
                rows.append([k, '先送り: ' + self.t(v.get('question'), w), self.t(v.get('rationale'), w) or '—',
                             self.t(v.get('revisit_when'), w) or '（未定）'])
        return rows

    def debt_toggle(self, n: int, decs: dict, tid: str) -> str:
        rows = self.debt_rows(decs)
        if not rows:
            return ''
        body = render_table(['DEC', '負債か先送りか', '理由', '返す・見直すとき'], rows, self.ctx, col_cls={0: 'w-m'},
                            cell=lambda i, k, x: ref_cell(x, self.ctx) if k == 0 else inline(x, self.ctx))
        self.add_toc(n, tid, '技術的負債と先送りした決定')
        return details(tid, '技術的負債と先送りした決定', body, f'{len(rows)} 件')

    # --- stage 2
    def stage2(self) -> str:
        if 2 not in self.stages:
            return ''
        c = self.ctx
        parts = []
        # elements (first)
        elm = self.live(self.elm)
        if elm:
            rows = []
            kinds: dict = {}
            for k, v in elm.items():
                w = f'elm/{k}.yaml'
                kn = self.term(T_ELM_KIND, v.get('kind'), f'{k} kind')
                kinds[kn] = kinds.get(kn, 0) + 1
                rows.append([k, kn, self.t(v.get('name') or v.get('title'), w), self.t(v.get('responsibility'), w),
                             ids_text(v.get('functions')) or '—', ids_text(v.get('drivers')) or '—', v.get('team') or '—',
                             self.term(T_AS_IS, v.get('as_is'), f'{k} as_is')])

            def ecell(i, k, x):
                if k == 0:
                    return f'<span class="def-id">{esc(x)}</span>'
                if k == 2:
                    return f'<b>{inline(x, c)}</b>'
                return inline(x, c)
            body = render_table(['ELM', '種類', '名前', '責務', 'FR', '要求', 'チーム', '差分'], rows, c,
                                row_ids=[r[0] for r in rows], cell=ecell)
            parts.append(details('t-elm', '要素', body, f'{len(rows)} 件 · ' + ' · '.join(f'{k} {v}' for k, v in kinds.items())))
            self.add_toc(2, 't-elm', '要素')
            self.compare('要素', 2, ('要素',), 'ELM', list(elm))
        # views (second): the diagrams and the tables beside them are only in the report
        vs = self.sec(2, 'ビュー')
        if vs:
            its = []
            for k, v in enumerate(vs.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                for tb in v.tables():
                    tt = Table(tb, v.path(), c)
                    b += render_table(tt.head, tt.rows, c)
                if v.title == 'コードの分け方':
                    cr = self.curated('code_rules', v)
                    if cr.get('rows'):
                        b += subhead('依存の規則（CI で確かめる）')
                        b += render_table(cr.get('head', ['対象', '規則']), cr['rows'], c)
                its.append(item(f'v-{k}', '', v.title, b, c))
            parts.append(details('t-views', 'ビュー', ''.join(its), f'{len(vs.children)} 枚'))
            self.add_toc(2, 't-views', 'ビュー')
        # overall structure (condensed from the report's prose)
        s = self.sec(2, '全体の構造')
        if s:
            cu = self.curated('structure', s)
            body = bullets(cu.get('bullets', []), c) if cu.get('bullets') else '<p class="none">（添削文なし）</p>'
            parts.append(details('t-structure', '全体の構造', body))
            self.add_toc(2, 't-structure', '全体の構造')
        # decisions: the table, then one card per decision, both from dec/*.yaml
        dec2 = self.decs('architecture')
        if dec2:
            parts.append(details('t-dec', '設計の決定', self.dec_table(dec2, 't-dec', True), f'{len(dec2)} 件'))
            self.add_toc(2, 't-dec', '設計の決定')
            self.compare('設計の決定（第 2 段階）', 2, ('設計の決定',), 'DEC', list(dec2))
            cards = [self.dec_card(v) for v in dec2.values()]
            idx = chips_index([(f'd-{k}', k, c.titles.get(k, '')) for k in dec2])
            parts.append(details('t-decd', '決定の中身', idx + ''.join(cards), f'{len(cards)} 件'))
            self.add_toc(2, 't-decd', '決定の中身')
        # design concerns (condensed)
        s = self.sec(2, '設計の観点')
        if s:
            cu = self.curated('viewpoints', s)
            its = cu.get('items', [])
            body = ('<dl class="vp">' + ''.join(f'<dt>{esc(a)}</dt><dd>{inline(b, c)}</dd>' for a, b in its) + '</dl>'
                    if its else '<p class="none">（添削文なし）</p>')
            parts.append(details('t-viewpoint', '設計の観点', body, f'{len(its)} 件' if its else ''))
            self.add_toc(2, 't-viewpoint', '設計の観点')
        # threat model (only in the report)
        s = self.sec(2, '脅威のモデル')
        if s:
            cu = self.curated('threat', s)
            t = Table(s.tables()[0], s.path(), c) if s.tables() else None
            b = ''
            if cu.get('assets'):
                b += subhead('守るもの') + bullets(cu['assets'], c, 'bul cols')
            tips = {}
            if t:
                for r in t.rows:
                    m = re.match(r'^(F\d+)\s*(.*)$', r[0])
                    if m:
                        tips[m.group(1)] = f'{m.group(1)} {m.group(2)}'
            if cu.get('diagram'):
                b += subhead('信頼の境界と流れ') + threat_svg(cu['diagram'], tips)
            elif s.codes():
                # no hand-laid figure yet: show the report's own diagram
                b += subhead('信頼の境界と流れ') + mermaid(s.codes()[0].text, c, s.path())
            if cu.get('kinds'):
                b += subhead('六つの脅威') + bullets(cu['kinds'], c, 'bul cols')
            if t:
                ids = []
                for r in t.rows:
                    m = re.match(r'^(F\d+)', r[0])
                    ids.append('flow-' + m.group(1) if m else '')
                b += render_table(t.head, t.rows, c, row_ids=ids, cls='threat',
                                  cell=lambda i, k, x: self.flow_cell(x) if k == 0 else inline(x, c))
            parts.append(details('t-threat', '脅威のモデル', b, f'流れ {len(t.rows) if t else 0}'))
            self.add_toc(2, 't-threat', '脅威のモデル')
        # walkthroughs (only in the report)
        ws = self.sec(2, '通し確認', 'CUJ')
        if ws:
            cu = self.curated('walk_extra', ws)
            head, rows, groups = None, [], []
            label = None
            extra = list(cu.get('groups', [])) if cu else []

            def add_extra(after):
                # a CUJ that the report describes in prose gets rows from the condensed text; after is the start of its label
                for g in extra:
                    if after.startswith(g['after']):
                        m = re.match(r'^(CUJ-[\d〜]+)', g['label'])
                        gid = 'w-' + (m.group(1).replace('〜', '-') if m else str(len(groups)))
                        groups.append((len(rows), inline(g['label'], c), gid))
                        rows.extend(g['rows'])
            for b in ws.blocks:
                if b.kind == 'label':
                    if label:
                        add_extra(label)
                    label = clean_text(b.text)[0]
                elif b.kind == 'table' and label:
                    tt = Table(b, ws.path(), c)
                    head = head or tt.head
                    m = re.match(r'^(CUJ-\d{2})', label)
                    gid = 'w-' + m.group(1) if m else 'w-' + str(len(groups))
                    groups.append((len(rows), inline(label, c), gid))
                    rows.extend(tt.rows)
            if label:
                add_extra(label)
            if head:
                body = render_table(head, rows, c, groups=groups, cls='walk')
                parts.append(details('t-walk', '通し確認（CUJ）', body, f'CUJ {len(groups)} · 手順 {len(rows)}'))
                self.add_toc(2, 't-walk', '通し確認（CUJ）')
        ds = self.sec(2, '通し確認', '主な設計を動かす要求')
        if ds and ds.tables():
            tt = Table(ds.tables()[0], ds.path(), c)
            b = render_table(tt.head, tt.rows, c, col_cls={0: 'w-m'},
                             cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            n2 = 0
            if len(ds.tables()) > 1:
                t2 = Table(ds.tables()[1], ds.path(), c)
                n2 = len(t2.rows)
                b += subhead('主でない要求と原則')
                b += render_table(t2.head, t2.rows, c, col_cls={0: 'w-m'},
                                  cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            parts.append(details('t-walkdrv', '通し確認（設計を動かす要求）', b, f'主 {len(tt.rows)} · ほか {n2}'))
            self.add_toc(2, 't-walkdrv', '通し確認（設計を動かす要求）')
        # design parameters and debt (dec/*.yaml), running cost (only in the report)
        body, n = self.values_table(dec2)
        if n:
            parts.append(details('t-values2', '設計上の値', body, f'{n} 件'))
            self.add_toc(2, 't-values2', '設計上の値')
        dt = self.debt_toggle(2, dec2, 't-debt')
        if dt:
            parts.append(dt)
            got = self.md_ids(2, ('技術的負債と先送りした決定',), 'DEC')
            if got is not None:
                self.compare('技術的負債と先送りした決定', 2, ('技術的負債と先送りした決定',), 'DEC',
                             {r[0] for r in self.debt_rows(dec2)})
        if 2 in self.md:
            t = self.table(2, ('費用と体制', '走る費用'))
            if t:
                parts.append(details('t-cost', '走る費用', render_table(t.head, t.rows, c), f'{len(t.rows)} 件'))
                self.add_toc(2, 't-cost', '走る費用')
        return self.stage_wrap(2, parts)

    def flow_cell(self, x: str) -> str:
        m = re.match(r'^(F\d+)\s*(.*)$', x)
        if not m:
            return inline(x, self.ctx)
        return f'<span class="def-id">{esc(m.group(1))}</span><span class="def-name">{inline(m.group(2), self.ctx)}</span>'

    # --- stage 3
    def error_rows(self, ifcs: dict) -> tuple:
        """The error contracts of every interface. A case written 「操作: 場合」 gives the operation. Rows for 「共通」 that
        are the same in several interfaces are shown once, above the others."""
        raw = []
        for k, v in ifcs.items():
            w = f'ifc/{k}.yaml errors'
            ops = {str(o.get('name') or '').strip() for o in v.get('operations') or [] if isinstance(o, dict)}
            for e in v.get('errors') or []:
                if not isinstance(e, dict):
                    continue
                case, op = str(e.get('case') or '').strip(), ''
                m = re.match(r'^(.{1,60}?)(?::\s+|：\s*)(.+)$', case, re.S)
                if m and (m.group(1) in ops or m.group(1) == '共通' or (len(m.group(1)) <= 24 and '。' not in m.group(1))):
                    op, case = m.group(1), m.group(2)
                raw.append((k, op, self.t(case, w), self.t(e.get('signal'), w), self.t(e.get('caller_does'), w)))
        shared: dict = {}
        for r in raw:
            if r[1] == '共通':
                shared.setdefault(r[2:], []).append(r[0])
        multi = {key: ids for key, ids in shared.items() if len(ids) >= 2}
        by_set: dict = {}
        for key, ids in multi.items():
            by_set.setdefault(tuple(ids), []).append(key)
        rows = []
        for ids, keys in by_set.items():
            rows += [[ids_text(list(ids)), '共通', *key] for key in keys]
        for r in raw:
            if r[1] == '共通' and r[2:] in multi:
                continue
            rows.append([r[0], r[1] or '—', *r[2:]])
        return rows, len(multi)

    def stage3(self) -> str:
        if 3 not in self.stages:
            return ''
        c = self.ctx
        parts = []
        if 3 in self.md:
            t = self.table(3, ('共通の約束事',))
            if t:
                body = render_table(t.head, t.rows, c, cell=lambda i, k, x: f'<b>{esc(x)}</b>' if k == 0 else inline(x, c))
                parts.append(details('t-conv', '共通の約束事', body, f'{len(t.rows)} 件'))
                self.add_toc(3, 't-conv', '共通の約束事')
        dec3 = self.decs('high-level-design')
        if dec3:
            parts.append(details('t-dec3', '設計の決定', self.dec_table(dec3, 't-dec3', False), f'{len(dec3)} 件'))
            self.add_toc(3, 't-dec3', '設計の決定')
            self.compare('設計の決定（第 3 段階）', 3, ('設計の決定',), 'DEC', list(dec3))
        ifcs = self.live(self.ifc)
        if ifcs:
            rows, kinds = [], {}
            for k, v in ifcs.items():
                w = f'ifc/{k}.yaml'
                kn = self.term(T_IFC_KIND, v.get('kind'), f'{k} kind')
                kinds[kn] = kinds.get(kn, 0) + 1
                ops = [self.t(o.get('name'), w) for o in v.get('operations') or [] if isinstance(o, dict)]
                if not ops:
                    opc = '—'
                elif len(ops) <= 3 or v.get('kind') == 'event':
                    opc = '、'.join(ops)
                else:
                    opc = f'{len(ops)} 件（{ops[0]} ほか）'
                spec = v.get('spec')
                rows.append([k, kn, self.t(v.get('name') or v.get('title'), w), v.get('provider') or '—',
                             ids_text(v.get('consumers')) or '—', opc, ids_text(v.get('functions')) or '—',
                             Path(str(spec)).name if spec else '—'])

            def icell(i, k, x):
                if k == 0:
                    return f'<span class="def-id">{esc(x)}</span>'
                if k == 2:
                    return f'<b>{inline(x, c)}</b>'
                return inline(x, c)
            body = render_table(['IFC', '種類', '名前', '提供側', '利用側', '操作', 'FR', '仕様'], rows, c,
                                row_ids=[r[0] for r in rows], cell=icell)
            parts.append(details('t-ifc', 'インタフェース', body,
                                 f'{len(rows)} 件 · ' + ' · '.join(f'{k} {v}' for k, v in kinds.items())))
            self.add_toc(3, 't-ifc', 'インタフェース')
            self.compare('インタフェース', 3, ('インタフェース',), 'IFC', list(ifcs))
            erows, n_shared = self.error_rows(ifcs)
            if erows:
                body = render_grouped(['IFC', '操作', '場合', '知らせ方', '呼ぶ側'], erows, c, [0, 1], cls='err')
                cnt = f'{len(erows)} 件' + (f' · 共通 {n_shared}' if n_shared else '')
                parts.append(details('t-err', 'エラーの決まり', body, cnt))
                self.add_toc(3, 't-err', 'エラーの決まり')
        fs = self.sec(3, '端から端の流れ')
        if fs:
            its, idx = [], []
            for v in fs.children:
                if not v.codes():
                    continue
                label, title = split_label(v.title)
                iid = 'f-' + (label or str(len(its) + 1)).replace('〜', '-')
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                its.append(item(iid, label, title, b, c))
                idx.append((iid, label or title.split('（')[0], title))
            if its:
                parts.append(details('t-flows', '端から端の流れ', chips_index(idx) + ''.join(its), f'{len(its)} 図'))
                self.add_toc(3, 't-flows', '端から端の流れ')
        bs = self.sec(3, '遅延の予算')
        if bs:
            out_sec = bs.find('スクリプトの出力')
            its = []
            for bd in self.text.get('budgets', []) or []:
                src = bs.find(bd['source'] + '*') if bd.get('source') else None
                key = f'budgets.{bd["id"]}'
                if src is None:
                    c.warn('節', f'{REPORT_FILES[3]} > 遅延の予算 > {bd.get("source")} が見つからない')
                else:
                    self.check_hash(key, [x for x in (src, out_sec) if x])
                b = bullets(bd.get('text', []), c, 'bul pts') if bd.get('text') else ''
                if bd.get('chart'):
                    b = budget_chart(bd['chart'], c) + b
                its.append(item(f'b-{bd["id"]}', bd['id'], bd.get('title', ''), b, c))
            known = {(bd.get('source') or '') for bd in self.text.get('budgets', []) or []}
            for v in bs.children:
                if v.title.startswith('NFR-') and not any(v.title.startswith(k) for k in known if k):
                    c.warn('添削文がない', f'budgets（{v.path()}）')
                    # no condensed text yet: show the subsection's own tables
                    nid = v.title.split('（')[0]
                    rest = v.title[len(nid):].strip('（）')
                    tb = ''.join(render_table(Table(x, v.path(), c).head, Table(x, v.path(), c).rows, c)
                                 for x in v.tables()) or '<p class="none">（添削文なし）</p>'
                    its.append(item(f'b-{nid}', nid, rest, tb, c))
            parts.append(details('t-budget', '遅延の予算', ''.join(its), f'{len(its)} 件'))
            self.add_toc(3, 't-budget', '遅延の予算')
            t = self.table(3, ('遅延の予算', '失敗したときの流れとエラーバジェット'))
            if t:
                body = render_table(t.head, t.rows, c, col_cls={0: 'w-m'}, cell=lambda i, k, x: ref_cell(x.split('（')[0], c) +
                                    (f'<span class="rk">（{esc(x.split("（", 1)[1])}</span>' if '（' in x else '')
                                    if k == 0 else inline(x, c))
                parts.append(details('t-eb', '失敗したときの流れとエラーバジェット', body, f'{len(t.rows)} 件'))
                self.add_toc(3, 't-eb', '失敗したときの流れとエラーバジェット')
        ss = self.sec(3, '画面')
        if ss:
            its, idx = [], []
            for k, v in enumerate(ss.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                iid = f's-{k}'
                its.append(item(iid, '', v.title, b, c))
                idx.append((iid, re.sub(r'（.*?）', '', v.title).split('、')[0], v.title))
            parts.append(details('t-screens', '画面', chips_index(idx) + ''.join(its), f'{len(its)} 図'))
            self.add_toc(3, 't-screens', '画面')
        # data: the ER diagram from the report, the entities from dat/*.yaml
        ds = self.sec(3, 'データ')
        dat = self.live(self.dat)
        b = ''.join(mermaid(self.er_with_names(m.text), c, ds.path()) for m in ds.codes()) if ds else ''
        if dat:
            rows = []
            for k, v in dat.items():
                w = f'dat/{k}.yaml'
                rows.append([k, self.t(v.get('entity') or v.get('title'), w), v.get('owner') or '—', v.get('store') or '—',
                             self.t(v.get('consistency'), w) or '—', self.t(v.get('retention'), w) or '—',
                             self.term(T_CLASS, v.get('classification'), f'{k} classification')])
            b += render_table(['DAT', '実体', '持ち主', '置き場所', '整合の取り方', '保持期間', '扱いの区分'], rows, c,
                              row_ids=[r[0] for r in rows],
                              cell=lambda i, k, x: f'<span class="def-id">{esc(x)}</span>' if k == 0
                              else (f'<b>{inline(x, c)}</b>' if k == 1 else inline(x, c)))
            self.compare('データ', 3, ('データ',), 'DAT', list(dat))
        if b:
            parts.append(details('t-data', 'データ', b, f'{len(dat)} 件' if dat else ''))
            self.add_toc(3, 't-data', 'データ')
        qs = ds.find('データの品質の流れ') if ds else None
        if qs:
            b = ''
            cap = None
            for blk in qs.blocks:
                if blk.kind == 'para' and blk.text.endswith(':'):
                    cap = blk.text.rstrip(':')
                elif blk.kind == 'code' and blk.lang == 'mermaid':
                    if cap:
                        b += subhead(cap)
                    b += mermaid(blk.text, c, qs.path())
                    cap = None
                elif blk.kind == 'table':
                    tt = Table(blk, qs.path(), c)
                    b += subhead('ほかのデータの品質')
                    b += render_table(tt.head, tt.rows, c)
            parts.append(details('t-dq', 'データの品質の流れ', b, f'図 {len(qs.codes())}'))
            self.add_toc(3, 't-dq', 'データの品質の流れ')
        st = self.sec(3, '要素をまたぐ状態')
        if st:
            its, idx = [], []
            notes = self.text.get('states', {}) or {}
            for k, v in enumerate(st.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                name = re.sub(r'（.*?）$', '', v.title)
                nt = notes.get(name)
                if nt:
                    self.check_hash(f'states.{name}', [v])
                    if nt.get('note'):
                        b += bullets(nt['note'] if isinstance(nt['note'], list) else [nt['note']], c, 'bul pts')
                iid = f'st-{k}'
                its.append(item(iid, '', v.title, b, c))
                idx.append((iid, name, v.title))
            parts.append(details('t-states', '要素をまたぐ状態', chips_index(idx) + ''.join(its), f'{len(its)} 図'))
            self.add_toc(3, 't-states', '要素をまたぐ状態')
        ms = self.sec(3, '測定点')
        if ms and ms.tables():
            t1 = Table(ms.tables()[0], ms.path(), c)
            b = render_table(t1.head, t1.rows, c, cell=lambda i, k, x: def_cell(x, c) if k == 0 else inline(x, c))
            if len(ms.tables()) > 1:
                t2 = Table(ms.tables()[1], ms.path(), c)
                rows = merge_dup_rows(t2.rows)
                b += subhead('監視の NFR の出どころ')
                b += render_table(t2.head, rows, c, cell=lambda i, k, x: def_cell(x, c) if k == 0 else inline(x, c))
            parts.append(details('t-measure', '測定点と監視の NFR の出どころ', b, f'SLI {len(t1.rows)}'))
            self.add_toc(3, 't-measure', '測定点と監視の NFR の出どころ')
        # the criteria quote the quality chain's acceptance criteria, so nothing is removed from them
        if 3 in self.md:
            t = self.table(3, ('受け入れ基準のトレース',), clean=False)
            if t:
                head = [t.head[0], t.head[2], t.head[1], t.head[3]]  # FR, IFC, criterion, flow
                rows = [[r[0], r[2], r[1], r[3]] for r in t.rows]
                body = render_grouped(head, rows, c, [0, 1], cls='actrace', col_cls=['w-id', 'w-m', 'w-xl', 'w-m'])
                nfr = len({r[0] for r in rows})
                parts.append(details('t-actrace', '受け入れ基準のトレース', body, f'FR {nfr} · 基準 {len(rows)}'))
                self.add_toc(3, 't-actrace', '受け入れ基準のトレース')
        body, n = self.values_table(dec3)
        if n:
            parts.append(details('t-values3', '設計上の値', body, f'{n} 件'))
            self.add_toc(3, 't-values3', '設計上の値')
        dt = self.debt_toggle(3, dec3, 't-debt3')
        if dt:
            parts.append(dt)
        return self.stage_wrap(3, parts)

    def er_with_names(self, src: str) -> str:
        """Adds entity names to the DAT-xx boxes of the ER diagram (as aliases)."""
        names = {k: self.t(v.get('entity') or v.get('title')) for k, v in self.dat.items()}
        seen = set()
        lines = []
        for line in src.split('\n'):
            lines.append(line)
            for m in re.finditer(r'\b(DAT-\d{2})\b', line):
                seen.add(m.group(1))
        alias = [f'  {d}["{d} {names[d]}"]' for d in sorted(seen) if names.get(d) and '"' not in names[d]]
        if not alias or not lines or not lines[0].strip().startswith('erDiagram'):
            return src
        return '\n'.join([lines[0]] + alias + lines[1:])

    # --- the route at the top
    def route(self) -> str:
        def kinds(items, key, names):
            cnt = {}
            for v in items.values():
                k = names.get(v.get(key), v.get(key))
                cnt[k] = cnt.get(k, 0) + 1
            return cnt
        drv = self.live(self.drv)
        n_main = sum(1 for v in drv.values() if v.get('primary'))
        dkind = kinds(drv, 'kind', T_DRV_KIND)
        dec2, dec3 = self.decs('architecture'), self.decs('high-level-design')
        n_debt = sum(1 for v in dec2.values() if isinstance(v.get('debt'), dict) and v['debt'].get('what'))
        n_def = sum(1 for v in dec2.values() if v.get('deferred'))
        ek = kinds(self.live(self.elm), 'kind', T_ELM_KIND)
        ik = kinds(self.live(self.ifc), 'kind', T_IFC_KIND)
        own = kinds(self.live(self.dat), 'owner', {})
        flows = self.sec(3, '端から端の流れ', quiet=True)
        nf = [v for v in (flows.children if flows else []) if v.codes()]
        n_drv = sum(1 for v in nf if v.title.startswith('DRV'))
        conv = self.table(3, ('共通の約束事',)) if 3 in self.md else None
        stops = [
            (1, 't-rank', '設計を動かす要求', len(drv), '件', [f'主 {n_main}'] + [f'{k} {v}' for k, v in dkind.items()]),
            (2, 't-dec', '設計の決定', len(dec2), '件', [f'負債 {n_debt}' if n_debt else '', f'先送り {n_def}' if n_def else '']),
            (2, 't-elm', '要素', len(self.live(self.elm)), '件', [f'{k} {v}' for k, v in ek.items()]),
            (3, 't-dec3', '約束事と決定', len(dec3), '件',
             [f'共通の約束事 {len(conv.rows)}' if conv else '', f'ほか {len(dec3) - len(conv.rows)}' if conv else '']),
            (3, 't-ifc', 'インタフェース', len(self.live(self.ifc)), '件', [f'{k} {v}' for k, v in ik.items()]),
            (3, 't-flows', '端から端の流れ', len(nf), '図', [f'CUJ {len(nf) - n_drv}', f'設計を動かす要求 {n_drv}']),
            (3, 't-data', 'データ', len(self.live(self.dat)), '件',
             [('持ち主 ' if k == 0 else '') + f'{o} {n}' for k, (o, n) in enumerate(sorted(own.items(), key=lambda x: -x[1]))]),
        ]
        have = {tid for n in self.toc for tid, _ in self.toc[n]}
        stops = [s for s in stops if s[1] in have]
        lis = []
        for n, href, name, num, unit, sub in stops:
            sub = ' · '.join(f'<span class="nb">{esc(x)}</span>' for x in sub if x)
            lis.append(f'<li class="stop"><a href="#{href}"><span class="dot" aria-hidden="true"></span>'
                       f'<span class="st-body"><span class="st-stage">第 {n} 段階</span><span class="st-name">{esc(name)}</span>'
                       f'<span class="st-num">{num}<span class="st-unit">{esc(unit)}</span></span>'
                       f'<span class="st-sub">{sub}</span></span></a></li>')
        bands = []
        col = 1
        for n in self.stages:
            w = sum(1 for s in stops if s[0] == n)
            if not w:
                continue
            bands.append(f'<span class="band" style="grid-column:{col} / {col + w}"><b>第 {n} 段階</b>{esc(self.stage_title(n))}</span>')
            col += w
        srcs = ' · '.join(dict.fromkeys(x for n in self.stages for x in STAGE_SOURCES[n].split(' · ')))
        return (f'<section id="sec-map" class="stage"><header class="stage-head"><span class="stage-no">DRV → DAT</span>'
                f'<h2>成果物のつながり</h2><span class="src">{esc(srcs)}</span></header>'
                f'<div class="route-wrap" style="--n:{len(stops)}"><ol class="route" aria-label="設計の連鎖の成果物">{"".join(lis)}</ol>'
                f'<div class="bands">{"".join(bands)}</div></div></section>')

    # --- the whole page
    def build(self) -> str:
        c = self.ctx
        s1, s2, s3 = self.stage1(), self.stage2(), self.stage3()
        route = self.route()
        for k in sorted(set(c.directions) - c.used_directions):
            c.warn('手直し', f'diagram_direction: 図のある節「{k}」が見つからない')
        # notes and requirements
        tail = ''
        notes = []
        for kind in PAGE_NOTE_KINDS:
            for w in c.warnings.get(kind, []):
                notes.append(f'{kind}: {w}')
        if notes:
            tail += details('t-notes', 'この版の注記', '<div class="notes"><ul>' +
                            ''.join(f'<li>{esc(x)}</li>' for x in notes) + '</ul></div>', f'{len(notes)} 件')
        req = self.text.get('requirements')
        if req:
            ans = self.text.get('answers') or []
            body = f'<div class="req"><pre class="req-text">{esc(req.strip())}</pre>'
            if ans:
                body += subhead('質問への回答') + bullets(ans, c)
            body += '</div>'
            tail += details('t-req', 'このページの要件', body)
        # header
        dates = []
        for coll in (self.drv, self.dec, self.elm, self.ifc, self.dat):
            for v in coll.values():
                for ch in v.get('changelog') or []:
                    if isinstance(ch, dict) and ch.get('date'):
                        dates.append(str(ch['date']))
        for raw in self.docs.values():
            dates += re.findall(r'^## 再実行（(\d{4}-\d{2}-\d{2})', raw, re.M)
        updated = max(dates) if dates else ''
        root = self.ddir.parent.parent if self.ddir.parent.name == 'docs' else self.ddir.parent
        commit = git(['log', '-1', '--format=%h', '--', str(self.ddir)], root)
        dirty = git(['status', '--porcelain', '--', str(self.ddir)], root)
        dirty = [x for x in dirty.split('\n') if x.strip() and not x.endswith(self.out.name)]
        repo = root.name
        stages = self.stages
        meta = f'第 {stages[0]}〜{stages[-1]} 段階の成果物の要約' if len(stages) > 1 else f'第 {stages[0]} 段階の成果物の要約'
        if updated:
            meta += f' · 更新 {updated}'
        if commit:
            meta += f' · <span>{esc(commit)}</span>'
            if dirty:
                meta += '（未コミットの変更あり）'
        sysname = self.system_name()
        title = f'{sysname}の設計'
        toc = ['<nav class="toc" aria-label="目次"><a class="toc-sec" href="#sec-map">成果物のつながり</a>']
        for n in stages:
            subs = ''.join(f'<a href="#{t}">{esc(nm)}</a>' for t, nm in self.toc.get(n, []))
            toc.append(f'<div class="toc-grp"><a class="toc-sec" href="#sec-{n}"><span>{n}</span>{esc(self.stage_title(n))}</a>'
                       f'<div class="sub">{subs}</div></div>')
        if notes:
            toc.append('<a class="toc-sec toc-notes" href="#t-notes">この版の注記</a>')
        if req:
            toc.append('<a class="toc-sec toc-notes" href="#t-req">このページの要件</a>')
        toc.append('</nav>')
        css = (ASSETS / 'base.css').read_text(encoding='utf-8') + '\n' + (ASSETS / 'design.css').read_text(encoding='utf-8')
        js = (ASSETS / 'base.js').read_text(encoding='utf-8') + '\n' + (ASSETS / 'design.js').read_text(encoding='utf-8')
        js = js.replace('__MERMAID_URL__', MERMAID_URL)
        tips = {k: c.titles[k] for k in sorted(c.used_tips)}
        tips_json = json.dumps(tips, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
        desc = f'{title}を、設計を動かす要求、アーキテクチャ、概要設計の表と図でまとめたページ'
        page = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="generator" content="design-summary-html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(FONTS_URL)}">
<style>
{css}
</style>
</head>
<body>
<div class="page">
<header class="masthead">
<div class="mast-text">
<p class="eyebrow">{esc(repo)} · {esc(self.ddir.relative_to(root).as_posix() if self.ddir.is_relative_to(root) else self.ddir.name)}</p>
<h1>{esc(title)}</h1>
<p class="meta">{meta}</p>
</div>
<div class="tools"><button type="button" class="btn" id="open-all">すべて開く</button><button type="button" class="btn" id="close-all">すべて閉じる</button></div>
</header>
{''.join(toc)}
<main>
{route}
{s1}
{s2}
{s3}
{tail}
</main>
</div>
<script type="application/json" id="id-tips">{tips_json}</script>
<script>
{js}
</script>
</body>
</html>
'''
        return page

    def system_name(self) -> str:
        qc = self.qdir / 'context.yaml'
        if qc.exists():
            c = yaml.safe_load(qc.read_text(encoding='utf-8')) or {}
            n = (c.get('system') or {}).get('name') or ''
            n = re.sub(r'（.*?）$', '', n).strip()
            if n:
                return n
        if self.md:
            root = self.md[min(self.md)]
            h1 = root.children[0].title if root.children else ''
            m = re.search(r':\s*(.+?)(?:（.*）)?$', h1)
            if m:
                return m.group(1).strip()
        return 'システム'

    def counts(self) -> str:
        live = self.live
        parts = [f'DRV {len(live(self.drv))}',
                 f'DEC {len(self.decs("architecture")) + len(self.decs("high-level-design"))}'
                 f'（第 2 段階 {len(self.decs("architecture"))} · 第 3 段階 {len(self.decs("high-level-design"))}）',
                 f'ELM {len(live(self.elm))}', f'IFC {len(live(self.ifc))}', f'DAT {len(live(self.dat))}']
        return ' · '.join(parts)


def split_label(title: str) -> tuple:
    m = re.match(r'^((?:CUJ|DRV)-\d{2}(?:〜\d{2})?(?:-[A-Z])?)\s+(.*)$', title)
    if m:
        return m.group(1), m.group(2)
    return '', title


def merge_dup_rows(rows: list) -> list:
    """Merges rows with the same first cell, keeping the longer row at the first row's position."""
    out, pos = [], {}
    for r in rows:
        k = r[0]
        if k in pos:
            i = pos[k]
            if sum(len(x) for x in r) > sum(len(x) for x in out[i]):
                out[i] = r
            continue
        pos[k] = len(out)
        out.append(r)
    return out


def check_page(page: str, ctx: Ctx) -> tuple:
    """Turns ID links without a target into text, and finds duplicate ids and links without a target."""
    ids = re.findall(r' id="([^"]+)"', page)
    idset = set(ids)
    dup = sorted({x for x in ids if ids.count(x) > 1})
    unlinked = set()

    def fix(m):
        target = m.group(2)
        if target in idset:
            return m.group(0)
        unlinked.add(target)
        return f'<span class="id dead"{m.group(3)}>{m.group(4)}</span>'
    page = re.sub(r'<a class="(id)" href="#([^"]+)"((?: data-ref="[^"]*")?)>(.*?)</a>', fix, page)
    dangling = sorted({h for h in re.findall(r'href="#([^"]+)"', page) if h not in idset})
    return page, dup, dangling, sorted(unlinked)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Builds a design summary HTML page from the design chain outputs')
    ap.add_argument('design_dir', nargs='?', default='docs/design', help='the design outputs directory (default: docs/design)')
    ap.add_argument('--quality-dir', default=None, help='the quality chain outputs, for titles and links (default: quality next to DESIGN_DIR)')
    ap.add_argument('--text', default=None, help='the condensed-text YAML (default: DESIGN_DIR/summary-text.yaml)')
    ap.add_argument('--out', default=None, help='where to write the page (default: DESIGN_DIR/summary.html)')
    ap.add_argument('--show-cleaning', action='store_true', help='print every text (YAML value, table cell) whose revision notes were removed, before and after')
    ap.add_argument('--hashes', action='store_true', help='print the current hash of every condensed-text source')
    ap.add_argument('--write-hashes', action='store_true',
                    help='rewrite the hashes: block at the end of the condensed-text YAML (only after rewriting the texts)')
    a = ap.parse_args(argv)
    ddir = Path(a.design_dir).resolve()
    if not ddir.is_dir():
        print(f'設計の出力がない: {ddir}', file=sys.stderr)
        return 2
    qdir = Path(a.quality_dir).resolve() if a.quality_dir else ddir.parent / 'quality'
    text = Path(a.text).resolve() if a.text else ddir / 'summary-text.yaml'
    out = Path(a.out).resolve() if a.out else ddir / 'summary.html'
    b = Builder(ddir, qdir, text, out)
    if not b.load():
        print('設計の成果物がない: drv/ などの YAML の項目も報告書もない（requirements-to-architecture-drivers から始める）',
              file=sys.stderr)
        return 2
    page = b.build()
    page, dup, dangling, unlinked = check_page(page, b.ctx)
    out.write_text(page, encoding='utf-8')
    c = b.ctx
    try:
        shown = out.relative_to(Path.cwd())
    except ValueError:
        shown = out
    print(f'書いた: {shown}（{len(page.encode("utf-8")) // 1024} KB）')
    print(f'段階: 第 {"・".join(str(n) for n in b.stages)} 段階（報告書: '
          f'{"・".join(REPORT_FILES[n] for n in sorted(b.md)) or "なし"}）')
    print(f'項目: {b.counts()}')
    for kind in REPORT_KINDS:
        ws = c.warnings.get(kind, [])
        print(f'{kind}: {len(ws)} 件' if ws else f'{kind}: なし')
        for w in ws:
            print(f'  - {w}')
    print(f'履歴の注記を削った文: {len(c.cleaned)} 件' + ('（--show-cleaning で一覧）' if c.cleaned and not a.show_cleaning else ''))
    if a.show_cleaning:
        for where, before, after in c.cleaned:
            print(f'  @ {where}\n    前: {before}\n    後: {after}')
    if unlinked:
        print(f'行がないのでリンクにしなかった ID: {"、".join(unlinked)}')
    if a.hashes:
        print('今の hash（summary-text.yaml の hashes: に写す）:')
        print('hashes:')
        for k in sorted(b.hashes):
            print(f'  {k}: {b.hashes[k]}')
    if a.write_hashes and text.exists():
        src = text.read_text(encoding='utf-8')
        m = re.search(r'^hashes:.*\Z', src, re.M | re.S)
        block = 'hashes:\n' + ''.join(f'  {k}: {b.hashes[k]}\n' for k in sorted(b.hashes))
        src = (src[:m.start()] + block) if m else (src.rstrip('\n') + '\n\n' + block)
        text.write_text(src, encoding='utf-8')
        print(f'hashes を書き直した: {text.name}（{len(b.hashes)} 件）。もう一度動かすと「もとが変わった」は消える')
    if dup or dangling:
        print(f'ページの確かめに落ちた: 重なる id {dup}、行き先のないリンク {dangling}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
