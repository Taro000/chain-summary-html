#!/usr/bin/env python3
"""Builds docs/design/summary.html from the outputs of the design chain (stages 1 to 3, req-to-design).

  uv run --with pyyaml python3 build_design_summary.py [DESIGN_DIR] [--out PATH] [--quality-dir DIR] [--lang ja|en]

The page and the report are written in the language of the outputs: Japanese when the outputs are written in
Japanese, English otherwise. --lang overrides that; the content stays in the language it was written in.

The YAML items are the source of truth (req-to-design's artifacts.md), so every table that has items is built from
them: drv/ and design-context.yaml (stage 1), elm/ and dec/ (stage 2), ifc/, dat/ and dec/ (stage 3). The three
reports (1-architecture-drivers.md, 2-architecture.md, 3-high-level-design.md) are read for their Mermaid diagrams and
for the tables that no item holds; their prose is not shown. The reports are found by their headings in Japanese
(req-to-design's glossary) or English (its report templates). Report tables that restate items are compared with
them, so a stale report is reported. A latency budget whose hop table has seconds is drawn as a chart. Revision
notes are removed from YAML texts, table cells and diagram labels, by rules for the language the outputs are written
in. Labels, terms and report messages are in assets/lang/<lang>.json.
The same input always produces the same HTML.
Exit codes: 0 means the page was written (0 even with warnings), 1 means it was written but failed its own check
(duplicate ids or links without a target), 2 means the inputs could not be read.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / 'assets'
LANGS = ('ja', 'en')
REPORT_FILES = {1: '1-architecture-drivers.md', 2: '2-architecture.md', 3: '3-high-level-design.md'}
MERMAID_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.esm.min.mjs'
STAGE_SOURCES = {1: 'drv/ · design-context.yaml', 2: 'elm/ · dec/', 3: 'ifc/ · dat/ · dec/'}
# Report headings: the Japanese of req-to-design's glossary, then the English of its report templates
H = {
    'rank': ('順位表', 'Ranking table'),
    'premise': ('設計の前提と利害関係者', 'Design inputs and stakeholders'),
    'concern': ('関心事の一覧', 'Concern inventory'),
    'drivers': ('設計を動かす要求', 'Architecture drivers'),
    'scenario': ('品質と変更のシナリオ', 'Quality and change scenarios'),
    'constraint': ('制約', 'Constraints'),
    'fos': ('機能・観測・セキュリティの要求', 'Functional, observability and security drivers'),
    'principle': ('全体の原則', 'Principles'),
    'feasible': ('実現できるか', 'Feasibility'),
    'decisions': ('設計の決定', 'Decisions'),
    'viewpoint': ('設計の観点', 'Design concerns'),
    'threat': ('脅威のモデル', 'Threat model'),
    'elements': ('要素', 'Elements'),
    'views': ('ビュー', 'Views'),
    'walk': ('通し確認', 'Walkthroughs'),
    'walk_cuj': ('CUJ', 'CUJs'),
    'walk_drv': ('主な設計を動かす要求', 'Primary drivers'),
    'values': ('設計上の値', 'Design parameters'),
    'debt': ('技術的負債と先送りした決定', 'Debt and deferred decisions'),
    'cost': ('費用と体制', 'Cost and team'),
    'running': ('走る費用', 'Running cost'),
    'conv': ('共通の約束事', 'Shared conventions'),
    'ifc': ('インタフェース', 'Interfaces'),
    'flows': ('端から端の流れ', 'End-to-end flows'),
    'budget': ('遅延の予算', 'Latency budgets'),
    'eb': ('失敗したときの流れとエラーバジェット', 'Failure paths and error budgets', 'Failure paths and the error budget'),
    'screens': ('画面', 'Screens'),
    'data': ('データ', 'Data'),
    'dq': ('データの品質の流れ', 'Data quality flows'),
    'states': ('要素をまたぐ状態', 'States across elements'),
    'measure': ('測定点', 'Measurement points'),
    'actrace': ('受け入れ基準のトレース', 'Acceptance criteria trace'),
}
# Column and row names read in report tables, in both languages
COL_BECAME = ('なったもの', 'Became')
HOP_HEAD = ('区間', 'Hop')
BUDGET_HEAD = ('予算', 'Budget')
ROW_MARGIN = ('余り', 'Margin')
ROW_TOTAL = ('合計', 'Total')
COMMON_OP = ('共通', 'Common', 'All operations', 'Every operation')
RERUN_RE = re.compile(r'^## (?:再実行（|Re-run on )(\d{4}-\d{2}-\d{2})', re.M)
# The warnings of the report, in the order they are printed; those in PAGE_NOTE_KINDS also go into the page's notes
REPORT_KINDS = ('mismatch', 'uncompared', 'report', 'yaml', 'section', 'table', 'unknown', 'leftout', 'unused')
PAGE_NOTE_KINDS = ('mismatch', 'report', 'yaml', 'section', 'table')


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- language

def read_lang(code):
    return json.loads((ASSETS / 'lang' / f'{code}.json').read_text(encoding='utf-8'))


LANG_DATA = {c: read_lang(c) for c in LANGS}
LANG: dict = {}


def set_lang(code):
    """Chooses the language of the page and the report. Japanese until this is called"""
    LANG.clear()
    LANG.update(LANG_DATA[code])
    LANG['code'] = code


set_lang('ja')


def T(key, **kw) -> str:
    """A label or message of the current language, with its {placeholders} filled in"""
    t = LANG['text'][key]
    return t.format(**kw) if kw else t


def die_t(key, lang=None, **kw):
    """Stops on an input error. Until the language is known, the message is printed in every language"""
    print('\n'.join(LANG_DATA[c]['text'][key].format(**kw) for c in ((lang,) if lang else ('en', 'ja'))), file=sys.stderr)
    sys.exit(2)


try:
    import yaml
except ImportError:  # pragma: no cover
    die_t('die_no_yaml', script=Path(__file__).name)

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


def detect_lang(texts) -> str:
    """ja when kana make up a tenth or more of the letters (kana and Latin), en otherwise. Japanese prose always has
    kana; IDs, enum values and English terms are Latin. Outputs in a language other than Japanese get English"""
    kana = latin = 0
    for t in texts:
        kana += len(KANA.findall(t))
        latin += len(LATIN.findall(t))
    return 'ja' if kana and kana * 10 >= kana + latin else 'en'


# The language the outputs are written in, which chooses the rules for revision notes (not the page's language)
SRC = {'lang': 'ja'}


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

    def find(self, *keys) -> 'Section | None':
        """Follows headings down. Each key is a name or a tuple of names (one per language); a heading matches a
        name exactly, or starts with it followed by a space or a bracket."""
        cur = self
        for k in keys:
            names = (k,) if isinstance(k, str) else k
            nxt = None
            for c in cur.children:
                if any(c.title == n or re.match(re.escape(n) + r'(?:\s|（|\()', c.title) for n in names):
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


# ---------------------------------------------------------------- removing revision notes: Japanese

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


def clean_ja(s: str, top: bool = True) -> tuple:
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


# ---------------------------------------------------------------- removing revision notes: English

# The same kinds of note as in Japanese, in the wordings an English report uses. Wordings that can also describe the
# product are left alone: a job is "re-run", an image is rolled back to "the previous version"
EN_VER_ID_RE = re.compile(r'(\b[A-Z]{2,4}-\d{2,}(?:–\d{2,})?)\s+version\s+\d+\b')
_EN_FND = r'FND-\d+(?:(?:,\s*|\s+and\s+)(?:FND-)?\d+)*'
EN_FND_LIST_RES = [
    re.compile(r'[,;]\s*' + _EN_FND + r'(?=\s*(?:[,;.)]|$))'),
    re.compile(r'(?<=\()\s*' + _EN_FND + r'\s*[,;]\s*'),
    re.compile(r'(?<=\()\s*' + _EN_FND + r'(?=\s*\))'),
    re.compile(r'^\s*' + _EN_FND + r'(?=\s*(?:[.)]|$))'),
]
EN_HIST_RE = re.compile(
    r'\bFND-\d+'
    r'|\b(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth) re-?run\b'
    r'|\bre-?run on \d{4}-\d{2}-\d{2}'
    r'|\bre-?run of (?:this |the )?stage\b|\bthis stage\'s re-?run\b'
    r'|\b(?:in|since|after|before) the (?:last |previous )?re-?run\b'
    r'|\b(?:the )?previous (?:version|revision|draft) (?:of this (?:report|item|decision|driver|table|stage)'
    r'|said|says|showed|shows|had|has|was|were|listed|assumed|did|missed|used|left|gave|named|wrote|called|counted|kept|put|took'
    r'|relied|treated)\b'
    r'|\bthe (?:previous|last) run\b|^\s*Previously\b'
    r'|\bissue \d+ (?:is|was) (?:settled|closed|resolved)\b'
    r'|\bversion \d+ (?:of (?:this|the) (?:report|item|decision|driver)|said|had|was|assumed|listed|missed)\b', re.I)
EN_PROCESS_ONLY_RE = re.compile(
    r'^(?:\s*(?:(?:stage \d+(?:\'s)?|this stage\'s|the quality chain\'s|answer to)\s+)?'
    r'(?:issues?|questions?|answer designs?|version)\s+[\d,–\-\s]+(?:and\s+\d+)?\s*[,;.]?)+$', re.I)
_EN_ABBR = ('e.g.', 'i.e.', 'etc.', 'vs.', 'cf.')


def _en_parse(s: str) -> list:
    """Splits text into strings and bracket groups ('(' or '（'). A group is a tuple (open, items)."""
    pair = {'(': ')', '（': '）'}
    stack = [('', [])]
    buf = []
    for ch in s:
        if ch in pair:
            if buf:
                stack[-1][1].append(''.join(buf))
                buf = []
            stack.append((ch, []))
        elif len(stack) > 1 and ch == pair[stack[-1][0]]:
            if buf:
                stack[-1][1].append(''.join(buf))
                buf = []
            g = stack.pop()
            stack[-1][1].append(g)
        else:
            buf.append(ch)
    if buf:
        stack[-1][1].append(''.join(buf))
    while len(stack) > 1:
        o, g = stack.pop()
        stack[-1][1].append(o + _en_ser(g))
    return stack[0][1]


def _en_ser(items: list) -> str:
    return ''.join(x if isinstance(x, str) else x[0] + _en_ser(x[1]) + {'(': ')', '（': '）'}[x[0]] for x in items)


def _en_sentences(items: list) -> list:
    """Splits at a full stop followed by a space or the end, outside brackets (not after e.g., i.e. …).
    Returns [(items, whether the sentence ended with a full stop)]."""
    out = [[[], False]]
    for x in items:
        if not isinstance(x, str):
            out[-1][0].append(x)
            continue
        start = 0
        for m in re.finditer(r'\.(?=\s|$)', x):
            head = x[start:m.start() + 1]
            if any(head.endswith(a) for a in _EN_ABBR):
                continue
            if x[start:m.start()].strip() or out[-1][0]:
                if x[start:m.start()]:
                    out[-1][0].append(x[start:m.start()])
                out[-1][1] = True
                out.append([[], False])
            start = m.end()
        rest = x[start:]
        if rest.strip():
            out[-1][0].append(rest)
    return [(a, b) for a, b in out if a and _en_ser(a).strip()]


def _en_clean_items(items: list, drop_top: bool) -> tuple:
    changed = False
    inner = []
    for x in items:
        if isinstance(x, tuple):
            g, ch = _en_clean_items(x[1], True)
            changed |= ch
            if g and _en_ser(g).strip():
                inner.append((x[0], g))
            else:
                changed = True
        else:
            inner.append(x)
    if not drop_top:
        return inner, changed
    kept = []
    for sent, ended in _en_sentences(inner):
        if EN_HIST_RE.search(_en_ser(sent).strip()):
            changed = True
            continue
        kept.append((sent, ended))
    if changed and kept and EN_PROCESS_ONLY_RE.match(' '.join(_en_ser(s).strip() for s, _ in kept)):
        kept = []
    out = []
    for k, (sent, ended) in enumerate(kept):
        if k:
            out.append(' ')
        out.extend([sent[0].lstrip()] + sent[1:] if isinstance(sent[0], str) else sent)
        if k < len(kept) - 1 or ended:
            out.append('.')
    while out and out[-1] == '.' and len(kept) and not kept[-1][1]:
        out.pop()
    return out, changed


def _en_tidy(s: str) -> str:
    s = re.sub(r'[（(]\s*[)）]', '', s)
    s = re.sub(r'\(\s*[,;]\s*', '(', s)
    s = re.sub(r'\s*[,;]\s*\)', ')', s)
    s = re.sub(r'\.\s*\)', ')', s)
    s = re.sub(r'\s+([,;.)])', r'\1', s)
    s = re.sub(r'([,;])\1+', r'\1', s)
    s = re.sub(r'\.{2,}', '.', s)
    s = re.sub(r' {2,}', ' ', s)
    s = re.sub(r'^[,;.\s]+', '', s)
    s = re.sub(r'[,;\s]+$', '', s)
    return s


def clean_en(s: str, top: bool = True) -> tuple:
    orig = s
    s = EN_VER_ID_RE.sub(r'\1', s)
    for rx in EN_FND_LIST_RES:
        s = rx.sub('', s)
    items, _ = _en_clean_items(_en_parse(s), top)
    ended = orig.rstrip().endswith('.')
    out = _en_tidy(_en_ser(items))
    if top and ended and out and not out.endswith(('.', ')')):
        out += '.'
    return out, out != orig


def clean_text(s: str, top: bool = True) -> tuple:
    """Removes revision notes from a YAML text, a table cell or a diagram line, by the rules of the language the
    outputs are written in. Returns (text, changed)."""
    if not s:
        return s, False
    return clean_en(s, top) if SRC['lang'] == 'en' else clean_ja(s, top)


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


# ---------------------------------------------------------------- the gist of a text

# The page is for grasping the design's direction quickly; the whole text stays in the YAML item or the report. So every
# text on the page is cut to its gist: bracketed asides go, then everything after the first sentence. A bracket that
# holds only a quantity stays, because the number is the point: 「T_deliver（5 秒）以内」 "within T_deliver (5 s)"
QTY_RE = re.compile(
    r'^(?:(?:約|最大|最小|上限|下限|およそ|about|up to|at most|at least|within|max\.?|min\.?)\s*)?[\d.,]+\s*'
    r'(?:秒|分|時間|日|週間?|か月|ヶ月|年|件|回|人|台|%|％|ms|s|sec|seconds?|min|minutes?|h|hours?|days?|weeks?|months?|years?'
    r'|KB|MB|GB|KiB|MiB|GiB|円|倍|個|行|km|m|パーセンタイル|percentile)'
    r'(?:\s*(?:以内|以上|以下|未満|まで|ごと|or less|or more))?$', re.I)
_OPENERS, _CLOSERS = '（(', '）)'
# After a removed bracket, a Latin word gets its space back before the next word: 「DRV-05（…）と」 → 「DRV-05 と」
_NO_SPACE_BEFORE = re.compile(r'[\s、。，,.;:：）)」』!?！？・]')


def _closing(s: str, i: int) -> int | None:
    """The index of the bracket that closes the one at s[i], or None when it is never closed"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] in _OPENERS:
            depth += 1
        elif s[j] in _CLOSERS:
            depth -= 1
            if depth == 0:
                return j
    return None


def drop_asides(s: str, half: bool = True) -> str:
    """Removes bracketed asides: every （…）, and with half, every (…) that does not follow a Latin letter or digit as in
    f(x). A bracket that holds only a quantity stays, and so does code in backticks."""
    out, i, code = [], 0, False
    while i < len(s):
        ch = s[i]
        if ch == '`':
            code = not code
        elif (not code and (ch == '（' or (half and ch == '('))
              and not (ch == '(' and i and s[i - 1].isascii() and s[i - 1].isalnum())):
            j = _closing(s, i)
            if j is not None:
                if QTY_RE.match(s[i + 1:j].strip()):
                    out.append(s[i:j + 1])
                elif (out and re.match(r'[A-Za-z0-9_]', out[-1][-1:]) and j + 1 < len(s)
                      and not _NO_SPACE_BEFORE.match(s[j + 1])):
                    out.append(' ')
                i = j + 1
                continue
        out.append(ch)
        i += 1
    return ''.join(out)


def first_sentence(s: str) -> str:
    """The text up to its first 「。」, or up to a full stop followed by a space or the end (not after e.g., i.e. …),
    outside brackets, quotes and code. The full stop itself is left out; a question or exclamation mark stays."""
    depth, code = 0, False
    for k, ch in enumerate(s):
        if ch == '`':
            code = not code
        if code:
            continue
        if ch in '（(「『':
            depth += 1
        elif ch in '）)」』':
            depth = max(depth - 1, 0)
        elif depth == 0:
            if ch == '。':
                return s[:k]
            if ch in '？！':
                return s[:k + 1]
            if ch in '.?!' and (k + 1 == len(s) or s[k + 1].isspace()) and not s[:k + 1].endswith(_EN_ABBR):
                return s[:k] if ch == '.' else s[:k + 1]
    return s


def _tidy_gist(s: str) -> str:
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r' +([、。，,;:：])', r'\1', s)
    s = re.sub(r'([、，,])\1+', r'\1', s)
    return re.sub(r'^[、，,;:：・\s]+|[、，,;:：・\s]+$', '', s)


def gist(s) -> str:
    """The gist of a text, which is all the page shows of it: the first sentence, without bracketed asides and without
    its full stop. A text that is all aside keeps its first sentence as written."""
    s = str(s or '').strip()
    if not s:
        return s
    return _tidy_gist(first_sentence(_tidy_gist(drop_asides(s)))) or _tidy_gist(first_sentence(s))


# ---------------------------------------------------------------- IDs and links

ID_PREFIX = ('DRV|DEC|ELM|IFC|DAT|TEAM|STK|CHG|TC|PC|FND|USR|CUJ|QIU|KPI|KGI|OUT|FRP|FR|QR|NFR|SLI|EBP')
UNIT_AHEAD = (r'(?!\d|\s*(?:%|件|秒|回|分|日|時間|人|年|台|本|行|倍|円|個|組|km|m\b|MiB|ms|s\b|min\b|h\b|days?\b'
              r'|hours?\b|minutes?\b|seconds?\b|times?\b|requests?\b|items?\b|people\b|years?\b))')
# 「DRV-01、02」 and "DRV-01, 02" continue a list; 「FR-01〜14」 and "FR-01–14" are ranges
_SEP = r'(?:[、・]|,\s)'
_RNG = r'[〜–]'
ID_RE = re.compile(r'(?<![A-Za-z0-9_\-])(?P<p>' + ID_PREFIX + r')-(?P<n>\d{2})(?P<rng>' + _RNG + r'\d{2})?'
                   r'(?P<cont>(?:' + _SEP + r'\d{2}' + UNIT_AHEAD + r'(?:' + _RNG + r'\d{2})?)*)' + r'(?![\d])')
CONT_RE = re.compile(r'(' + _SEP + r')(\d{2})(?:(' + _RNG + r')(\d{2}))?')
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
    """Links the IDs in escaped text. In 「DRV-01、02」 and "DRV-01, 02", 02 links to DRV-02."""
    def rep(m):
        p, n = m.group('p'), m.group('n')
        out = [ctx.link(f'{p}-{n}')]
        if m.group('rng'):
            out.append(m.group('rng')[0] + ctx.link(f'{p}-{m.group("rng")[1:]}', m.group('rng')[1:]))
        for cm in CONT_RE.finditer(m.group('cont') or ''):
            out.append(cm.group(1) + ctx.link(f'{p}-{cm.group(2)}', cm.group(2)))
            if cm.group(3):
                out.append(cm.group(3) + ctx.link(f'{p}-{cm.group(4)}', cm.group(4)))
        return ''.join(out)
    return ID_RE.sub(rep, s)


def inline(s: str, ctx: Ctx) -> str:
    """Turns a table cell or a YAML text into HTML (`code`, **bold**, ID links)."""
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
    """Writes a list of IDs the way the reports do: 「FR-01〜14、24、DRV-03」 or "FR-01–14, 24, DRV-03". With sort, the
    numbers of each prefix are sorted and three or more in a row become a range; without it, the order is kept (the
    order means something, such as the drivers a decision addresses, most important first). Other texts are kept."""
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
            segs += [f'{r[0]}{T("range")}{r[-1]}'] if len(r) >= 3 else r
        parts.append(f'{p}-' + T('sep').join(segs))
    return T('sep').join(parts)


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
    """A table from a report, with columns dropped by name, revision notes removed from its cells (unless clean is false)
    and every cell cut to its gist."""

    def __init__(self, block: Block, where: str, ctx: Ctx, drop=(), clean=True):
        self.where = where
        head = block.rows[0]
        keep = [k for k, h in enumerate(head) if h not in drop]
        self.head = [gist(clean_text(head[k])[0] if clean else head[k]) for k in keep]
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
                row.append(gist(cell))
            self.rows.append(row)


def col_classes(head, rows, col_cls) -> list:
    """Width classes of the columns. col_cls is either the whole list or a dict that overrides some columns."""
    if isinstance(col_cls, list):
        return col_cls
    out = [width_class([r[k] for r in rows if k < len(r) and isinstance(r[k], str)]) for k in range(len(head))]
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
    """Breaks text with <br/> at punctuation or spaces (Mermaid breaks only at spaces and hyphenates long words)."""
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
SEQ_ALIAS_RE = re.compile(r'^(\s*(?:participant|actor)\s+[\w-]+\s+as\s+)(.*)$')
# Lines that hold no label, or whose parentheses and colons are syntax (styles, colors, links, directives)
MMD_SKIP_RE = re.compile(r'^\s*(?:%%|style\s|classDef\s|class\s|linkStyle\s|click\s|direction\s|rect\s|box\s)')
MMD_QUOTED_RE = re.compile(r'"([^"\n]*)"')
MMD_EDGE_RE = re.compile(r'\|([^|"\n]+)\|')                  # a flowchart's unquoted edge label: -->|label|
MMD_AFTER_COLON_RE = re.compile(r'^([^":]*:\s*)([^"\s][^"]*)$')  # a state or ER label: S1 --> S2: label


def gist_label(s: str) -> str:
    return gist(s) or s


def gist_mermaid(src: str, kind: str) -> str:
    """Cuts the labels of a diagram to their gist, as every text on the page. Only the label text is touched, never the
    syntax: in a sequence diagram the text of messages, notes, blocks and participants; elsewhere the quoted labels, a
    flowchart's edge labels, a state or ER diagram's label after the colon, and any （…）, which Mermaid never uses."""
    out = []
    for line in src.split('\n'):
        if MMD_SKIP_RE.match(line):
            out.append(line)
            continue
        if kind == 'sequenceDiagram':
            m = SEQ_ALIAS_RE.match(line)
            if m:
                line = m.group(1) + (_tidy_gist(drop_asides(m.group(2))) or m.group(2))
            else:
                for rx in (SEQ_MSG_RE, SEQ_NOTE_RE, SEQ_BLOCK_RE):
                    m = rx.match(line)
                    if m:
                        line = m.group(1) + gist_label(m.group(2))
                        break
            out.append(line)
            continue
        line = MMD_QUOTED_RE.sub(lambda m: '"' + gist_label(m.group(1)) + '"', line)
        if kind in ('flowchart', 'graph'):
            line = MMD_EDGE_RE.sub(lambda m: '|' + gist_label(m.group(1)) + '|', line)
        if kind in ('stateDiagram', 'stateDiagram-v2', 'erDiagram'):
            m = MMD_AFTER_COLON_RE.match(line)
            if m:
                line = m.group(1) + gist_label(m.group(2))
        out.append(drop_asides(line, half=False))
    return '\n'.join(out)


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


def mermaid(src: str, ctx: Ctx, where: str, links: str = '') -> str:
    """A Mermaid diagram, drawn by design.js when it comes into view. links="flow" makes the flow numbers on the
    diagram's arrows (F1, F2…) links to the threat table's rows."""
    src2, ch = clean_mermaid(src)
    if ch:
        ctx.cleaned.append((where + ' (mermaid)', '…', '…'))
    first = src2.strip().split('\n', 1)[0].strip()
    kind = first.split()[0] if first else ''
    src2 = gist_mermaid(src2, kind)
    if kind in ('flowchart', 'graph'):
        # a box labelled only with an element ID (「ELM-04」, also once its aside is gone) gets the element's name, so the
        # diagram reads on its own
        def named(m):
            t = gist(ctx.titles.get(m.group(2), ''))
            return f'{m.group(1)}["{t}"]' if t.startswith(m.group(2) + ' ') and '"' not in t else m.group(0)
        src2 = re.sub(r'(\b\w+)\["(ELM-\d{2})"\]', named, src2)
    if kind == 'sequenceDiagram':
        src2 = wrap_sequence(src2)
    lk = f' data-links="{esc(links)}"' if links else ''
    return (f'<figure class="mmd" data-kind="{esc(kind)}"{lk}><div class="mmd-bar">'
            f'<button type="button" class="mmd-fit" aria-pressed="false">{esc(T("fit"))}</button>'
            f'<button type="button" class="mmd-full">{esc(T("full"))}</button></div>'
            f'<div class="mmd-out" aria-live="polite"><p class="mmd-wait">{esc(T("drawing"))}</p></div>'
            f'<pre class="mmd-src" hidden>{esc(src2)}</pre></figure>')


def chips_index(entries: list) -> str:
    """Turns [(href, text, tooltip)] into an index inside a toggle."""
    return f'<nav class="idx" aria-label="{esc(T("idx"))}">' + ''.join(
        f'<a class="chip" href="#{esc(h)}" data-tip="{esc(t)}">{esc(x)}</a>' for h, x, t in entries) + '</nav>'


def subhead(text: str) -> str:
    return f'<p class="list-label">{esc(text)}</p>'


# ---------------------------------------------------------------- latency budget charts

# A budget value: 「1.00 秒」 or "0.15 s", "150 ms", 「2 分」, "1.5 min"
VALUE_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*(秒|ms|s|分|min)\s*$')
TO_SECONDS = {'秒': 1.0, 's': 1.0, 'ms': 0.001, '分': 60.0, 'min': 60.0}


def nice_step(span: float) -> float:
    for s in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300):
        if span / s <= 8:
            return s
    return 600


def fmt_num(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f'{int(round(v)):,}'
    return f'{v:.2f}'.rstrip('0').rstrip('.') if abs(v * 10 - round(v * 10)) < 1e-9 else f'{v:.2f}'


def hop_chart(table: Block, ctx: Ctx, where: str) -> dict | None:
    """Reads a hop table (区間 / Hop, 予算 / Budget …) into chart data: the hops, the margin and the threshold (the
    total). Returns None when the table has another shape or a value without a time unit."""
    head = table.rows[0]
    if len(head) < 2 or head[0].strip() not in HOP_HEAD or not head[1].strip().startswith(BUDGET_HEAD):
        return None
    hops, margin, total = [], None, None
    for r in table.rows[1:]:
        if len(r) < 2:
            continue
        name = gist(clean_text(r[0])[0])
        m = VALUE_RE.match(r[1])
        if not m:
            return None
        v = float(m.group(1)) * TO_SECONDS[m.group(2)]
        basis = gist(clean_text(r[2])[0]) if len(r) > 2 else ''
        if name in ROW_MARGIN:
            margin = v
        elif name in ROW_TOTAL:
            total = v
        else:
            hops.append({'name': name, 'v': v, 'note': basis})
    if not hops:
        return None
    s = sum(h['v'] for h in hops)
    if total is None:
        total = s + (margin or 0)
    if abs(s + (margin or 0) - total) > 1e-6 and margin is not None:
        ctx.warn('mismatch', T('w_budget_sum', where=where, sum=fmt_num(s), margin=fmt_num(margin), total=fmt_num(total)))
    # minutes read better than hundreds of seconds
    unit = 'min' if total >= 600 else 's'
    k = 60.0 if unit == 'min' else 1.0
    for h in hops:
        h['v'] /= k
    return {'hops': hops, 'threshold': total / k, 'unit': unit}


def budget_chart(specs: list, ctx: Ctx) -> str:
    """Horizontal stacked bars on one shared axis: each hop table is a row of its hops, with a light track up to the
    threshold (the margin) and a line at the threshold."""
    unit = specs[0]['unit']
    uname = T('unit_s') if unit == 's' else T('unit_min')
    top = max(max(sp['threshold'], sum(h['v'] for h in sp['hops'])) for sp in specs)
    amax = top * 1.06
    step = nice_step(amax)
    pct = lambda v: f'{min(v, amax) / amax * 100:.3f}%'
    rows_h, table_rows = [], []
    for k, sp in enumerate(specs, 1):
        label = T('budget_row') if len(specs) == 1 else T('budget_row_n', n=k)
        segs, total = [], 0.0
        for h in sp['hops']:
            tip = f'{h["name"]}: {fmt_num(h["v"])} {uname}' + (T('paren', x=h['note']) if h.get('note') else '')
            segs.append(f'<span class="seg k-hop" style="left:{pct(total)};width:{pct(h["v"])}" '
                        f'data-tip="{esc(tip)}" tabindex="0"><i>{esc(fmt_num(h["v"]))}</i></span>')
            table_rows.append([label, h['name'], fmt_num(h['v']), h.get('note', '')])
            total += h['v']
        rows_h.append(f'<div class="bud-row"><div class="bud-label"><span class="bud-name">{esc(label)}</span>'
                      f'<span class="bud-sub">{esc(T("budget_sum", sum=fmt_num(total), margin=fmt_num(sp["threshold"] - total), unit=uname))}</span></div>'
                      f'<div class="bud-plot"><span class="bud-track" style="width:{pct(sp["threshold"])}"></span>'
                      f'{"".join(segs)}<span class="bud-th" style="left:{pct(sp["threshold"])}"></span></div></div>')
    ths = sorted({sp['threshold'] for sp in specs})
    lg = (f'<span class="lg"><span class="sw k-hop"></span>{esc(T("budget_hops"))}</span>'
          f'<span class="lg"><span class="sw sw-track"></span>{esc(T("budget_margin"))}</span>'
          f'<span class="lg"><span class="sw sw-th"></span>{esc(T("budget_threshold"))}</span>')
    ticks, v = [], 0.0
    while v <= amax + 1e-9:
        if not any(abs(v - t) < 1e-9 for t in ths):
            ticks.append(f'<span class="tick" style="left:{pct(v)}">{esc(fmt_num(v))}</span>')
        v += step
    th_lab = ''.join(f'<span class="tick th" style="left:{pct(t)}">{esc(fmt_num(t))} {esc(uname)}</span>' for t in ths)
    tb = render_table([T('budget_col_row'), T('budget_col_hop'), uname, T('budget_col_basis')], table_rows, ctx,
                      cls='bud-table', col_cls=['w-m', 'w-m', 'num', 'w-m'],
                      cell=lambda i, k, x: (f'<span class="num">{esc(x)}</span>' if k == 2 else inline(x, ctx)))
    return (f'<figure class="bud"><div class="legend bud-legend">{lg}</div><div class="bud-rows">{"".join(rows_h)}</div>'
            f'<div class="bud-axis"><div class="bud-label"></div><div class="bud-ticks">{"".join(ticks)}{th_lab}'
            f'<span class="unit">{esc(uname)}</span></div></div>'
            f'<details class="bud-num"><summary>{esc(T("budget_values"))}</summary>{tb}</details></figure>')


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
            if ctx:
                ctx.warn('yaml', T('w_yaml_unreadable', file=f'{f.parent.name}/{f.name}', err=str(e).splitlines()[0]))
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


def addresses(v: dict) -> list:
    """What a decision answers, without findings: a finding number is review history, which the page leaves out."""
    return [a for a in v.get('addresses') or [] if not str(a).startswith('FND-')]


def norm(s) -> str:
    return re.sub(r'\s+', '', str(s or ''))


def lvl_badge(key: str, text: str) -> str:
    return f'<span class="lvl lvl-{ {"high": "h", "medium": "m", "low": "l"}.get(key, "x") }">{esc(text)}</span>'


# ---------------------------------------------------------------- the page

class Builder:
    def __init__(self, ddir: Path, qdir: Path, out: Path):
        self.ddir, self.qdir, self.out = ddir, qdir, out
        self.ctx = Ctx()
        self.toc: dict = {}            # stage → [(id, name)]
        self.docs: dict = {}
        self.md: dict = {}
        self.stages: list = []
        self.lang = self.lang_how = ''

    # --- inputs
    def load(self, lang: str | None) -> bool:
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
                c.warn('yaml', T('w_yaml_unreadable', file='design-context.yaml', err=str(e).splitlines()[0]))
        for n, fn in REPORT_FILES.items():
            p = self.ddir / fn
            if p.exists():
                self.docs[n] = p.read_text(encoding='utf-8')
        # the language of the outputs: of the page (unless --lang is given) and of the rules for revision notes
        texts = [s for coll in (self.drv, self.dec, self.elm, self.ifc, self.dat) for v in coll.values() for s in strings(v)]
        texts += list(strings(self.dctx)) + list(self.docs.values())
        SRC['lang'] = detect_lang(texts)
        self.lang, self.lang_how = (lang, 'lang_given') if lang else (SRC['lang'], 'lang_detected')
        set_lang(self.lang)
        has = {1: bool(self.live(self.drv)),
               2: bool(self.live(self.elm)) or bool(self.decs('architecture')),
               3: bool(self.live(self.ifc)) or bool(self.live(self.dat)) or bool(self.decs('high-level-design'))}
        self.stages = [n for n in (1, 2, 3) if has[n] or n in self.docs]
        if not self.stages:
            return False
        for n in self.stages:
            if has[n] and n not in self.docs:
                c.warn('report', T('w_no_report', file=REPORT_FILES[n], n=n))
            if not has[n]:
                c.warn('yaml', T('w_no_items', n=n))
        for n in range(max(self.stages) + 1, 4):
            c.warn('report', T('w_later_missing', n=n, title=T(f'stage_title_{n}')))
        for name in ('summary-text.yaml',):
            if (self.ddir / name).exists():
                c.warn('unused', T('w_unused_file', file=name))
        self.md = {n: parse_md(t, REPORT_FILES[n]) for n, t in self.docs.items()}
        # tooltips, and the IDs that have a row on this page
        t = c.titles
        for coll in (self.drv, self.dec, self.elm, self.ifc, self.dat):
            for k, v in coll.items():
                if v.get('status') == 'retired':
                    t[k] = f'{k} {v.get("title", "")}{T("retired")}'
                    continue
                t[k] = short(f'{k} {self.t(v.get("title"))}')
                if not (k.startswith('DEC-') and v.get('stage') not in ('architecture', 'high-level-design')):
                    c.own.add(k)
        for k, v in self.fnd.items():
            t[k] = short(f'{k} {v.get("title", "")}{T("finding")}')
        for grp, key in (('technology_constraints', 'statement'), ('project_constraints', 'statement'),
                         ('teams', 'name'), ('anticipated_changes', 'change'), ('stakeholders', 'role')):
            for x in self.dctx.get(grp, []) or []:
                if isinstance(x, dict) and x.get('id'):
                    t[x['id']] = short(f'{x["id"]} {x.get(key) or ""}')
                    c.own.add(x['id'])
        # quality-chain items (tooltips, and links to the quality summary)
        q = self.qdir
        self.qtitle = {}
        for sub in ('fr', 'qr', 'nfr', 'sli', 'qiu', 'kpi', 'ebp', 'frp'):
            for k, v in load_items(q / sub).items():
                extra = T('retired') if v.get('status') == 'retired' else ''
                t.setdefault(k, short(f'{k} {v.get("title", "")}{extra}'))
                self.qtitle[k] = clean_text(str(v.get('title') or '').strip())[0]
        qc = q / 'context.yaml'
        self.qctx = {}
        if qc.exists():
            self.qctx = yaml.safe_load(qc.read_text(encoding='utf-8')) or {}
            for grp in ('users', 'cujs', 'kgis'):
                for x in self.qctx.get(grp, []) or []:
                    t.setdefault(x['id'], f'{x["id"]} {x.get("name", "")}')
            for x in self.qctx.get('outcomes', []) or []:
                t.setdefault(x['id'], short(f'{x["id"]} {x.get("statement", "")}'))
        qs = q / 'summary.html'
        if qs.exists():
            c.quality_anchor = set(re.findall(r' id="([A-Z]+-\d{2})"', qs.read_text(encoding='utf-8')))
            c.quality_href = Path(os.path.relpath(qs.resolve(), self.out.parent.resolve())).as_posix()
        for k in list(t):
            if k.split('-')[0] in QUALITY_PREFIXES and k in c.quality_anchor:
                t[k] = t[k] + T('to_quality')
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
            return T('sep').join(x for x in (self.t(v, where) for v in s) if x)
        if isinstance(s, dict):
            return T('sep').join(f'{k}: {self.t(v, where)}' for k, v in s.items())
        s = str(s).strip()
        out, ch = clean_text(s)
        if ch:
            self.ctx.cleaned.append((where or 'YAML', s, out))
        return out

    def g(self, s, where: str = '') -> str:
        """The gist of a text from a YAML item (see gist); of a list, the gist of each entry. Titles and names are short
        already and are shown whole, with t."""
        if isinstance(s, (list, tuple)):
            return T('sep').join(x for x in (self.g(v, where) for v in s) if x)
        return gist(self.t(s, where))

    def term(self, group: str, value, where: str) -> str:
        if value is None or value == '':
            return '—'
        table = LANG['terms'][group]
        key = str(value).lower() if isinstance(value, bool) else value
        if key in table:
            return table[key]
        # a value with a note after it: 「personal（IP アドレス）」
        m = re.match(r'^([A-Za-z-]+)\s*[（(](.*)[）)]$', str(value).strip(), re.S)
        if m and m.group(1) in table:
            return table[m.group(1)] + T('paren', x=self.t(m.group(2), where))
        self.ctx.warn('unknown', f'{where}: {value}')
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
    def md_ids(self, n: int, keys: tuple, col: str) -> list | None:
        if n not in self.md:
            return None
        s = self.sec(n, *keys, quiet=True)
        if s is None or not s.tables():
            self.ctx.warn('uncompared', T('w_uncompared', where=f'{REPORT_FILES[n]} > {" > ".join(H[k][0 if self.lang == "ja" else 1] for k in keys)}'))
            return None
        rows = s.tables()[0].rows
        k = rows[0].index(col) if col in rows[0] else 0
        out = []
        for r in rows[1:]:
            cell = r[k] if k < len(r) else ''
            m = re.match(r'^\s*([A-Z]{2,5}-\d{2,})', cell)
            if m and not re.search(r'（廃止）|\(retired\)', cell, re.I):
                out.append(m.group(1))
        return out

    def compare(self, what: str, n: int, keys: tuple, col: str, yaml_ids) -> list | None:
        got = self.md_ids(n, keys, col)
        if got is None:
            return None
        a, b = set(got), set(yaml_ids)
        if a - b:
            self.ctx.warn('mismatch', T('w_report_only', what=what, ids=T('sep').join(sorted(a - b, key=id_key))))
        if b - a:
            self.ctx.warn('mismatch', T('w_yaml_only', what=what, ids=T('sep').join(sorted(b - a, key=id_key))))
        return got

    def sec(self, n: int, *keys, quiet: bool = False) -> Section | None:
        root = self.md.get(n)
        if root is None:
            return None
        if len(root.children) == 1 and root.children[0].level == 1:
            root = root.children[0]
        s = root.find(*(H[k] for k in keys))
        if s is None and not quiet:
            self.ctx.warn('section', T('w_section', file=REPORT_FILES[n], path=' > '.join(H[k][0 if self.lang == 'ja' else 1] for k in keys)))
        return s

    def table(self, n: int, keys: tuple, drop=(), clean=True) -> Table | None:
        s = self.sec(n, *keys)
        if s is None:
            return None
        if not s.tables():
            self.ctx.warn('table', T('w_table', where=s.path()))
            return None
        return Table(s.tables()[0], s.path(), self.ctx, drop=drop, clean=clean)

    def add_toc(self, stage, tid, name):
        self.toc.setdefault(stage, []).append((tid, name))

    def stage_title(self, n: int) -> str:
        root = self.md.get(n)
        if root is not None and root.children and root.children[0].level == 1:
            return root.children[0].title.split(':')[0].split('：')[0].strip()
        return T(f'stage_title_{n}')

    def stage_wrap(self, n: int, parts: list) -> str:
        src = STAGE_SOURCES[n] + (f' · {REPORT_FILES[n]}' if n in self.md else '')
        return (f'<section id="sec-{n}" class="stage"><header class="stage-head"><span class="stage-no">{esc(T("stage_no", n=n))}</span>'
                f'<h2>{esc(self.stage_title(n))}</h2><span class="src">{esc(src)}</span></header>'
                + ''.join(parts) + '</section>')

    def toggle(self, n: int, tid: str, name: str, body: str, count: str = '', open_: bool = False) -> str:
        self.add_toc(n, tid, name)
        return details(tid, name, body, count, open_)

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
                c.warn('yaml', T('w_no_rank', file=f'drv/{v["id"]}.yaml'))
        ranked.sort(key=lambda v: (rank_of(v) is None, rank_of(v) or 0, id_key(v['id'])))
        if ranked:
            # the levels without their reasons: the reasons justify the rank, and stay in drv/*.yaml
            rows, levels = [], []
            for v in ranked:
                p = v.get('priority') or {}
                w = f'drv/{v["id"]}.yaml'
                rows.append([str(rank_of(v) or '—'), v['id'],
                             self.term('level', p.get('business'), w + ' priority.business'),
                             self.term('level', p.get('difficulty'), w + ' priority.difficulty'),
                             T('yes') if v.get('primary') else T('no')])
                levels.append((p.get('business'), p.get('difficulty')))

            def cell(i, k, x):
                if k == 0:
                    return f'<span class="num">{esc(x)}</span>'
                if k == 1:
                    return ref_cell(x, c)
                if k in (2, 3):
                    return lvl_badge(levels[i][k - 2], x)
                if k == 4:
                    return f'<span class="chip {"qr-emph" if x == T("yes") else "qr-out"}">{esc(x)}</span>'
                return inline(x, c)
            n_main = sum(1 for v in ranked if v.get('primary'))
            body = render_table([T('h_rank'), 'DRV', T('h_business'), T('h_difficulty'), T('h_primary')],
                                rows, c, row_ids=['rank-' + v['id'] for v in ranked], cell=cell, cls='rank',
                                col_cls=['num', 'w-l', 'w-id', 'w-id', 'w-id'])
            parts.append(self.toggle(1, 't-rank', T('t_rank'), body, T('count_primary', n=len(rows), p=n_main), open_=True))
            got = self.compare(T('t_rank'), 1, ('rank',), 'DRV', [v['id'] for v in ranked])
            if got is not None:
                order = [v['id'] for v in ranked if v['id'] in got]
                if order != [x for x in got if x in order]:
                    c.warn('mismatch', T('w_rank_order'))
        # premises and stakeholders (design-context.yaml), without where each came from; the basis stays, since these
        # are the inputs (as quality-summary-html keeps it only for users and CUJs)
        dx = self.dctx
        rows = []
        w = 'design-context.yaml'
        for x in dx.get('technology_constraints') or []:
            rows.append([x.get('id', ''), T('kind_tc', kind=self.term('tc_kind', x.get('kind'), f'{x.get("id")} kind')),
                         self.g(x.get('statement'), w) or T('undecided'),
                         self.term('basis', x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('project_constraints') or []:
            rows.append([x.get('id', ''), self.term('pc_kind', x.get('kind'), f'{x.get("id")} kind'),
                         self.g(x.get('statement'), w) or T('undecided'),
                         self.term('basis', x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('teams') or []:
            owns = self.g(x.get('owns'), w)
            rows.append([x.get('id', ''), T('kind_team'), self.t(x.get('name'), w) + (T('team_owns', owns=owns) if owns else ''),
                         self.term('basis', x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('anticipated_changes') or []:
            when = T('paren', x=self.g(x.get('expected'), w)) if x.get('expected') else ''
            rows.append([x.get('id', ''), T('kind_chg'), self.g(x.get('change'), w) + when,
                         self.term('basis', x.get('basis'), f'{x.get("id")} basis')])
        for x in dx.get('stakeholders') or []:
            conc = self.g(x.get('concerns'), w)
            rows.append([x.get('id', ''), T('kind_stk'), self.g(x.get('role'), w) + (T('stk_concerns', x=conc) if conc else ''),
                         self.term('basis', x.get('basis'), f'{x.get("id")} basis')])
        if rows:
            body = render_table(['ID', T('h_kind'), T('h_statement'), T('h_basis')], rows, c,
                                row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: f'<span class="def-id">{esc(x)}</span>' if k == 0 else inline(x, c))
            parts.append(self.toggle(1, 't-premise', T('t_premise'), body, T('count', n=len(rows))))
            self.compare(T('t_premise'), 1, ('premise',), 'ID', [r[0] for r in rows])
        # concerns: only in the report (without the column of what each became)
        if 1 in self.md:
            t = self.table(1, ('concern',), drop=COL_BECAME)
            if t:
                parts.append(self.toggle(1, 't-concern', T('t_concern'), render_table(t.head, t.rows, c), T('count', n=len(t.rows))))
        # drivers by kind. A scenario shows its stimulus, environment and response measure: the source and the artifact are
        # mostly implied by the stimulus, and the response is the measure in words
        sc_head = [T('h_stimulus'), T('h_environment'), T('h_measure')]
        sc_keys = ['stimulus', 'environment', 'measure']

        def scen(v):
            s = v.get('scenario') or {}
            return [self.g(s.get(k), f'drv/{v["id"]}.yaml scenario') or '—' for k in sc_keys]
        sc = [v for v in drv.values() if v.get('kind') in ('quality', 'change')]
        if sc:
            rows = [[v['id']] + scen(v) for v in sc]
            kinds = {v['id']: self.term('drv_kind', v.get('kind'), f'{v["id"]} kind') for v in sc}
            body = render_table(['DRV'] + sc_head, rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x, kinds[x]) if k == 0 else inline(x, c))
            parts.append(self.toggle(1, 't-scenario', T('t_scenario'), body, T('count', n=len(rows))))
            self.compare(T('t_scenario'), 1, ('drivers', 'scenario'), 'DRV', [r[0] for r in rows])
        # constraints and the other drivers, without their sources (traceability, in drv/*.yaml)
        cs = [v for v in drv.values() if v.get('kind') == 'constraint']
        if cs:
            rows = [[v['id'], self.g(v.get('statement'), f'drv/{v["id"]}.yaml'),
                     self.term('negotiable', v.get('negotiable'), f'{v["id"]} negotiable') if v.get('negotiable') is not None else '—']
                    for v in cs]
            body = render_table(['DRV', T('h_constraint'), T('h_negotiable')], rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            parts.append(self.toggle(1, 't-constraint', T('t_constraint'), body, T('count', n=len(rows))))
            self.compare(T('t_constraint'), 1, ('drivers', 'constraint'), 'DRV', [r[0] for r in rows])
        fs = [v for v in drv.values() if v.get('kind') in ('function', 'observability', 'security')]
        if fs:
            rows = [[v['id'], self.term('drv_kind', v.get('kind'), f'{v["id"]} kind'),
                     self.g(v.get('statement'), f'drv/{v["id"]}.yaml')] for v in fs]
            b = render_table(['DRV', T('h_kind'), T('h_statement')], rows, c, row_ids=[r[0] for r in rows],
                             cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            ws = [v for v in fs if v.get('scenario')]
            if ws:
                b += subhead(T('sub_scenarios'))
                b += render_table(['DRV'] + sc_head, [[v['id']] + scen(v) for v in ws], c, col_cls={0: 'w-m'},
                                  cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            parts.append(self.toggle(1, 't-fos', T('t_fos'), b, T('count', n=len(rows))))
            self.compare(T('t_fos'), 1, ('drivers', 'fos'), 'DRV', [r[0] for r in rows])
        ps = [v for v in drv.values() if v.get('kind') == 'principle']
        if ps:
            rows = [[v['id'], self.g(v.get('statement'), f'drv/{v["id"]}.yaml'), ids_text(v.get('derived_from'), sort=False) or '—']
                    for v in ps]
            body = render_table(['DRV', T('h_principle'), T('h_derived')], rows, c, row_ids=[r[0] for r in rows],
                                cell=lambda i, k, x: self.own_cell(x) if k == 0 else inline(x, c))
            parts.append(self.toggle(1, 't-principle', T('t_principle'), body, T('count', n=len(rows))))
            self.compare(T('t_principle'), 1, ('drivers', 'principle'), 'DRV', [r[0] for r in rows])
        # conflicts: both drivers of a pair record it; the side with more to say is shown
        pairs: dict = {}
        for v in drv.values():
            for x in v.get('conflicts') or []:
                if not isinstance(x, dict) or not x.get('with') or x['with'] not in drv:
                    continue
                key = tuple(sorted((v['id'], x['with']), key=id_key))
                note = self.g(x.get('note'), f'drv/{v["id"]}.yaml conflicts')
                side = pairs.setdefault(key, {}).setdefault(v['id'], [])
                if note and note not in side:
                    side.append(note)
        if pairs:
            rows = []
            for key in sorted(pairs, key=lambda k: (id_key(k[0]), id_key(k[1]))):
                notes = max(pairs[key].values(), key=lambda ns: (len(ns), sum(len(x) for x in ns)))
                rows.append([key, notes])

            def ccell(i, k, x):
                if k == 0:
                    return ref_cell(x[0], c) + f'<span class="vs">{esc(T("and"))}</span>' + ref_cell(x[1], c)
                if not x:
                    return '—'
                return inline(x[0], c) if len(x) == 1 else '<ul class="in-bul">' + ''.join(f'<li>{inline(n, c)}</li>' for n in x) + '</ul>'
            body = render_table([T('h_drivers'), T('h_conflict')], rows, c, cell=ccell, col_cls=['w-m', 'w-xl'])
            parts.append(self.toggle(1, 't-conflict', T('t_conflict'), body, T('count_pairs', n=len(rows))))
        if 1 in self.md:
            t = self.table(1, ('feasible',))
            if t:
                body = render_table(t.head, t.rows, c, cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c),
                                    col_cls={0: 'w-m'})
                parts.append(self.toggle(1, 't-feasible', T('t_feasible'), body, T('count', n=len(t.rows))))
        return self.stage_wrap(1, parts)

    # --- decisions (stages 2 and 3)
    def dec_table(self, decs: dict, cards: bool) -> str:
        """One row per decision: the question, the chosen option and the rejected ones with their reasons. What the
        decision addresses is in its card (and in dec/*.yaml for the stages without cards)."""
        c = self.ctx
        rows = []
        for k, v in decs.items():
            w = f'dec/{k}.yaml'
            rej = [r for r in v.get('rejected') or [] if isinstance(r, dict)]
            chosen = self.g(v.get('chosen'), w) or (T('c_deferred') if v.get('deferred') else '—')
            rows.append([k, self.g(v.get('question'), w), chosen,
                         [(self.g(r.get('option'), w), self.g(r.get('reason'), w)) for r in rej]])

        def cell(i, k, x):
            if k == 0:
                more = f'<a class="more" href="#d-{esc(x)}">{esc(T("details_link"))}</a>' if cards else ''
                return self.own_cell(x) + more
            if k == 3:
                if not x:
                    return '—'
                return ''.join(f'<span class="nr"><span class="opt">{inline(o, c)}</span>'
                               + (f'<span class="note">{inline(r, c)}</span>' if r else '') + '</span>' for o, r in x)
            return inline(x, c)
        return render_table(['DEC', T('h_question'), T('h_chosen'), T('h_rejected')], rows, c,
                            row_ids=[r[0] for r in rows], cell=cell, col_cls=['w-m', 'w-l', 'w-l', 'w-l'])

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
                verdicts.append(('rej', self.g(rej[norm(name)], w)))
            else:
                verdicts.append(('', ''))
            rows.append([self.g(name, w), self.g(o.get('effect'), w) or '—', self.g(o.get('cost'), w) or '—', ''])
        if chosen and rows and not found:
            c.warn('yaml', T('w_chosen', file=w))

        def entry(label: str, val) -> str:
            if isinstance(val, list):
                val = [x for x in val if x]
                if not val:
                    return ''
                val = val[0] if len(val) == 1 else '<ul>' + ''.join(f'<li>{x}</li>' for x in val) + '</ul>'
            return f'<dt>{esc(label)}</dt><dd>{val}</dd>' if val else ''

        def il(x) -> str:
            return inline(self.g(x, w), c) if x else ''
        head = entry(T('h_question'), il(v.get('question')))
        if chosen and not found:
            head += entry(T('h_chosen'), il(chosen))
        body = f'<dl class="vp dec">{head}</dl>' if head else ''
        if rows:
            def cell(i, k, x):
                if k == 3:
                    vd, reason = verdicts[i]
                    if vd == 'chosen':
                        return f'<span class="mk mk-ok">{esc(T("v_chosen"))}</span>'
                    if vd == 'rej':
                        return f'<span class="mk mk-part">{esc(T("v_rejected"))}</span>' + (f'<span class="mk-n">{inline(reason, c)}</span>' if reason else '')
                    return '—'
                return inline(x, c)
            body += render_table([T('h_option'), T('h_effect'), T('h_cost'), T('h_verdict')], rows, c, cls='opts', cell=cell,
                                 row_cls=['is-chosen' if vd == 'chosen' else '' for vd, _ in verdicts],
                                 col_cls=['w-l', 'w-l', 'w-l', 'w-m'])
        rest = entry(T('c_rationale'), il(v.get('rationale')))
        rest += entry(T('c_gains'), [il(x) for x in v.get('gains') or []])
        rest += entry(T('c_costs'), [il(x) for x in v.get('costs') or []])
        rest += entry(T('c_sensitive'), [il(x) for x in v.get('sensitive_points') or []])
        tos = []
        for x in v.get('trade_offs') or []:
            if isinstance(x, dict):
                wi = x.get('with')
                wi = ids_text(wi, sort=False) if isinstance(wi, list) else self.t(wi, w)
                tos.append(inline(f'{wi}: {self.g(x.get("note"), w)}' if wi else self.g(x.get('note'), w), c))
            else:
                tos.append(il(x))
        rest += entry(T('c_tradeoffs'), tos)
        rest += entry(T('c_assumptions'), [il(x) for x in v.get('assumptions') or []])
        # the design parameters, and why the debt was accepted and when it is repaid, are in the tables of the stage
        d = v.get('debt')
        if isinstance(d, dict) and d.get('what'):
            rest += entry(T('c_debt'), il(d.get('what')))
        if v.get('deferred'):
            rest += entry(T('c_deferred'), esc(T('c_revisit_when')) + ' ' + (il(v.get('revisit_when')) or esc(T('undecided'))))
        rest += entry(T('h_addresses'), inline(ids_text(addresses(v), sort=False), c) if addresses(v) else '')
        rest += entry(T('c_depends'), inline(ids_text(v.get('depends_on')), c) if v.get('depends_on') else '')
        if rest:
            body += f'<dl class="vp dec">{rest}</dl>'
        return item(f'd-{did}', did, self.title_of(did) or did, body, c)

    def values_toggle(self, n: int, decs: dict, tid: str) -> str:
        """The provisional design parameters, without the basis of each value (in dec/*.yaml)"""
        rows = []
        for k, v in decs.items():
            for p in v.get('parameters') or []:
                if isinstance(p, dict):
                    w = f'dec/{k}.yaml parameters'
                    rows.append([self.t(p.get('name'), w), self.g(p.get('value'), w) or '—', k])
        if not rows:
            return ''
        body = render_table([T('h_param'), T('h_value'), T('h_decision')], rows, self.ctx,
                            col_cls={0: 'w-m', 1: 'w-m', 2: 'w-id'})
        return self.toggle(n, tid, T('t_values'), body, T('count', n=len(rows)))

    def debt_rows(self, decs: dict) -> list:
        rows = []
        for k, v in decs.items():
            w = f'dec/{k}.yaml'
            d = v.get('debt')
            if isinstance(d, dict) and d.get('what'):
                rows.append([k, T('debt_prefix', x=self.g(d.get('what'), w)), self.g(d.get('why_accepted'), w) or '—',
                             self.g(d.get('repay_when'), w) or '—'])
            if v.get('deferred'):
                rows.append([k, T('deferred_prefix', x=self.g(v.get('question'), w)), self.g(v.get('rationale'), w) or '—',
                             self.g(v.get('revisit_when'), w) or T('undecided')])
        return rows

    def debt_toggle(self, n: int, decs: dict, tid: str) -> str:
        rows = self.debt_rows(decs)
        if not rows:
            return ''
        body = render_table(['DEC', T('h_debt_kind'), T('h_why'), T('h_repay')], rows, self.ctx, col_cls={0: 'w-m'},
                            cell=lambda i, k, x: ref_cell(x, self.ctx) if k == 0 else inline(x, self.ctx))
        return self.toggle(n, tid, T('t_debt'), body, T('count', n=len(rows)))

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
                kn = self.term('elm_kind', v.get('kind'), f'{k} kind')
                kinds[kn] = kinds.get(kn, 0) + 1
                rows.append([k, kn, self.t(v.get('name') or v.get('title'), w), self.g(v.get('responsibility'), w),
                             ids_text(v.get('functions')) or '—', ids_text(v.get('drivers')) or '—', v.get('team') or '—',
                             self.term('as_is', v.get('as_is'), f'{k} as_is')])

            def ecell(i, k, x):
                if k == 0:
                    return f'<span class="def-id">{esc(x)}</span>'
                if k == 2:
                    return f'<b>{inline(x, c)}</b>'
                return inline(x, c)
            body = render_table(['ELM', T('h_kind'), T('h_name'), T('h_responsibility'), T('h_frs'), T('h_drivers'), T('h_team'), T('h_as_is')],
                                rows, c, row_ids=[r[0] for r in rows], cell=ecell)
            parts.append(self.toggle(2, 't-elm', T('t_elm'), body, T('count', n=len(rows)) + ' · ' + ' · '.join(f'{k} {v}' for k, v in kinds.items())))
            self.compare(T('t_elm'), 2, ('elements',), 'ELM', list(elm))
        # views (second): the diagrams and the tables beside them, from the report
        vs = self.sec(2, 'views')
        if vs:
            its = []
            for k, v in enumerate(vs.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                for tb in v.tables():
                    tt = Table(tb, v.path(), c)
                    b += render_table(tt.head, tt.rows, c)
                if b:
                    its.append(item(f'v-{k}', '', gist(clean_text(v.title)[0]), b, c))
            if its:
                parts.append(self.toggle(2, 't-views', T('t_views'), ''.join(its), T('count_views', n=len(its))))
        # decisions: the table, then one card per decision, both from dec/*.yaml
        dec2 = self.decs('architecture')
        if dec2:
            parts.append(self.toggle(2, 't-dec', T('t_dec'), self.dec_table(dec2, True), T('count', n=len(dec2))))
            self.compare(T('t_dec_stage', n=2), 2, ('decisions',), 'DEC', list(dec2))
            cards = [self.dec_card(v) for v in dec2.values()]
            idx = chips_index([(f'd-{k}', k, c.titles.get(k, '')) for k in dec2])
            parts.append(self.toggle(2, 't-decd', T('t_decd'), idx + ''.join(cards), T('count', n=len(cards))))
        # design concerns: the report's table, as a definition list
        s = self.sec(2, 'viewpoint')
        if s and s.tables():
            t = Table(s.tables()[0], s.path(), c)
            body = ('<dl class="vp">' + ''.join(f'<dt>{inline(r[0], c)}</dt><dd>{inline(r[1] if len(r) > 1 else "", c)}</dd>'
                                                 for r in t.rows) + '</dl>')
            parts.append(self.toggle(2, 't-viewpoint', T('t_viewpoint'), body, T('count', n=len(t.rows))))
        # threat model: the report's diagram (its flow numbers link to the table) and the table
        s = self.sec(2, 'threat')
        if s:
            t = Table(s.tables()[0], s.path(), c) if s.tables() else None
            b = ''.join(mermaid(m.text, c, s.path(), links='flow') for m in s.codes()[:1])
            if t:
                ids = []
                for r in t.rows:
                    m = re.match(r'^(F\d+)\b', r[0])
                    ids.append('flow-' + m.group(1) if m else '')
                b += render_table(t.head, t.rows, c, row_ids=ids, cls='threat',
                                  cell=lambda i, k, x: self.flow_cell(x) if k == 0 else inline(x, c))
            if b:
                parts.append(self.toggle(2, 't-threat', T('t_threat'), b, T('count_flows', n=len(t.rows)) if t else ''))
        # walkthroughs: the CUJ tables merged into one, then the drivers' tables (a CUJ written as prose is left out)
        ws = self.sec(2, 'walk', 'walk_cuj')
        if ws:
            head, rows, groups, prose = None, [], [], []

            def group(label):
                m = re.match(r'^(CUJ-\d{2}(?:[〜–]\d{2})?)', label)
                gid = 'w-' + (m.group(1).replace('〜', '-').replace('–', '-') if m else str(len(groups)))
                groups.append((len(rows), inline(label, c), gid))

            def add_rows(tbl):
                nonlocal head
                tt = Table(tbl, ws.path(), c)
                head = head or tt.head
                rows.extend(tt.rows)
            cur = None                        # [label, whether a table followed it]
            for b in ws.blocks:
                if b.kind == 'label':
                    if cur and not cur[1]:
                        prose.append(cur[0])
                    cur = [clean_text(b.text)[0], False]
                elif b.kind == 'table' and cur:
                    if not cur[1]:
                        group(gist(cur[0]))
                        cur[1] = True
                    add_rows(b)
            if cur and not cur[1]:
                prose.append(cur[0])
            for sub in ws.children:          # a CUJ under its own heading
                if sub.tables():
                    group(gist(clean_text(sub.title)[0]))
                    for tb in sub.tables():
                        add_rows(tb)
                else:
                    prose.append(sub.title)
            for p in prose:
                c.warn('leftout', T('w_leftout_walk', label=short(p, 60)))
            if head:
                body = render_table(head, rows, c, groups=groups, cls='walk')
                parts.append(self.toggle(2, 't-walk', T('t_walk'), body, T('count_walk', n=len(groups), steps=len(rows))))
        ds = self.sec(2, 'walk', 'walk_drv')
        if ds and ds.tables():
            tt = Table(ds.tables()[0], ds.path(), c)
            b = render_table(tt.head, tt.rows, c, col_cls={0: 'w-m'},
                             cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            n2 = 0
            if len(ds.tables()) > 1:
                t2 = Table(ds.tables()[1], ds.path(), c)
                n2 = len(t2.rows)
                b += subhead(T('sub_other_drivers'))
                b += render_table(t2.head, t2.rows, c, col_cls={0: 'w-m'},
                                  cell=lambda i, k, x: ref_cell(x, c) if k == 0 else inline(x, c))
            parts.append(self.toggle(2, 't-walkdrv', T('t_walkdrv'), b, T('count_walkdrv', n=len(tt.rows), m=n2)))
        # design parameters and debt (dec/*.yaml), running cost (the report)
        x = self.values_toggle(2, dec2, 't-values2')
        if x:
            parts.append(x)
        x = self.debt_toggle(2, dec2, 't-debt')
        if x:
            parts.append(x)
            self.compare(T('t_debt'), 2, ('debt',), 'DEC', {r[0] for r in self.debt_rows(dec2)})
        if 2 in self.md:
            s = self.sec(2, 'cost', 'running', quiet=True) or self.sec(2, 'cost', quiet=True)
            if s and s.tables():
                t = Table(s.tables()[0], s.path(), c)
                parts.append(self.toggle(2, 't-cost', T('t_cost'), render_table(t.head, t.rows, c), T('count', n=len(t.rows))))
            else:
                c.warn('table', T('w_table', where=f'{REPORT_FILES[2]} > {H["cost"][0 if self.lang == "ja" else 1]}'))
        return self.stage_wrap(2, parts)

    def flow_cell(self, x: str) -> str:
        m = re.match(r'^(F\d+)\s*(.*)$', x)
        if not m:
            return inline(x, self.ctx)
        return f'<span class="def-id">{esc(m.group(1))}</span><span class="def-name">{inline(m.group(2), self.ctx)}</span>'

    # --- stage 3
    def error_rows(self, ifcs: dict) -> tuple:
        """The error contracts of every interface. A case written 「操作: 場合」 or "Operation: case" gives the
        operation. Rows for all operations that are the same in several interfaces are shown once, above the others."""
        raw = []
        for k, v in ifcs.items():
            w = f'ifc/{k}.yaml errors'
            ops = {str(o.get('name') or '').strip() for o in v.get('operations') or [] if isinstance(o, dict)}
            for e in v.get('errors') or []:
                if not isinstance(e, dict):
                    continue
                case, op = str(e.get('case') or '').strip(), ''
                m = re.match(r'^(.{1,60}?)(?::\s+|：\s*)(.+)$', case, re.S)
                if m and (m.group(1) in ops or m.group(1) in COMMON_OP
                          or (len(m.group(1)) <= 24 and '。' not in m.group(1) and '. ' not in m.group(1))):
                    op, case = m.group(1), m.group(2)
                if op in COMMON_OP:
                    op = '*'
                raw.append((k, op, self.g(case, w), self.g(e.get('signal'), w), self.g(e.get('caller_does'), w)))
        shared: dict = {}
        for r in raw:
            if r[1] == '*':
                shared.setdefault(r[2:], []).append(r[0])
        multi = {key: ids for key, ids in shared.items() if len(ids) >= 2}
        by_set: dict = {}
        for key, ids in multi.items():
            by_set.setdefault(tuple(ids), []).append(key)
        rows = []
        for ids, keys in by_set.items():
            rows += [[ids_text(list(ids)), T('all_ops'), *key] for key in keys]
        for r in raw:
            if r[1] == '*' and r[2:] in multi:
                continue
            rows.append([r[0], T('all_ops') if r[1] == '*' else (r[1] or '—'), *r[2:]])
        return rows, len(multi)

    def stage3(self) -> str:
        if 3 not in self.stages:
            return ''
        c = self.ctx
        parts = []
        if 3 in self.md:
            t = self.table(3, ('conv',))
            if t:
                body = render_table(t.head, t.rows, c, cell=lambda i, k, x: f'<b>{esc(x)}</b>' if k == 0 else inline(x, c))
                parts.append(self.toggle(3, 't-conv', T('t_conv'), body, T('count', n=len(t.rows))))
        dec3 = self.decs('high-level-design')
        if dec3:
            parts.append(self.toggle(3, 't-dec3', T('t_dec'), self.dec_table(dec3, False), T('count', n=len(dec3))))
            self.compare(T('t_dec_stage', n=3), 3, ('decisions',), 'DEC', list(dec3))
        ifcs = self.live(self.ifc)
        if ifcs:
            rows, kinds = [], {}
            for k, v in ifcs.items():
                w = f'ifc/{k}.yaml'
                kn = self.term('ifc_kind', v.get('kind'), f'{k} kind')
                kinds[kn] = kinds.get(kn, 0) + 1
                ops = [self.g(o.get('name'), w) for o in v.get('operations') or [] if isinstance(o, dict)]
                if not ops:
                    opc = '—'
                elif len(ops) <= 3 or v.get('kind') == 'event':
                    opc = T('sep').join(ops)
                else:
                    opc = T('ops_more', n=len(ops), first=ops[0])
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
            body = render_table(['IFC', T('h_kind'), T('h_name'), T('h_provider'), T('h_consumers'), T('h_operations'), T('h_frs'), T('h_spec')],
                                rows, c, row_ids=[r[0] for r in rows], cell=icell)
            parts.append(self.toggle(3, 't-ifc', T('t_ifc'), body,
                                     T('count', n=len(rows)) + ' · ' + ' · '.join(f'{k} {v}' for k, v in kinds.items())))
            self.compare(T('t_ifc'), 3, ('ifc',), 'IFC', list(ifcs))
            erows, n_shared = self.error_rows(ifcs)
            if erows:
                body = render_grouped(['IFC', T('h_operation'), T('h_case'), T('h_signal'), T('h_caller')], erows, c, [0, 1], cls='err')
                cnt = T('count', n=len(erows)) + (' · ' + T('count_shared', n=n_shared) if n_shared else '')
                parts.append(self.toggle(3, 't-err', T('t_err'), body, cnt))
        fs = self.sec(3, 'flows')
        if fs:
            its, idx = [], []
            for v in fs.children:
                if not v.codes():
                    continue
                label, title = split_label(gist(clean_text(v.title)[0]))
                iid = 'f-' + (label or str(len(its) + 1)).replace('〜', '-').replace('–', '-')
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                its.append(item(iid, label, title, b, c))
                idx.append((iid, label or re.split(r'[（(]', title)[0], title))
            if its:
                parts.append(self.toggle(3, 't-flows', T('t_flows'), chips_index(idx) + ''.join(its), T('count_diagrams', n=len(its))))
        bs = self.sec(3, 'budget')
        if bs:
            its = []
            for v in bs.children:
                if not v.title.startswith('NFR-'):
                    continue
                nid = re.split(r'[（(\s]', v.title, 1)[0]
                rest = v.title[len(nid):].strip().strip('（）()')
                specs, other = [], []
                for tb in v.tables():
                    sp = hop_chart(tb, c, v.path())
                    if sp:
                        specs.append(sp)
                    else:
                        other.append(tb)
                b = ''
                if specs:
                    by_unit = {}
                    for sp in specs:
                        by_unit.setdefault(sp['unit'], []).append(sp)
                    b += ''.join(budget_chart(g, c) for g in by_unit.values())
                for tb in other:
                    tt = Table(tb, v.path(), c)
                    b += render_table(tt.head, tt.rows, c)
                if b:
                    # the NFR's title from docs/quality, which the heading's bracket only restates
                    its.append(item(f'b-{nid}', nid, self.qtitle.get(nid) or gist(clean_text(rest)[0]), b, c))
                else:
                    c.warn('leftout', T('w_leftout_budget', nfr=nid))
            if its:
                parts.append(self.toggle(3, 't-budget', T('t_budget'), ''.join(its), T('count', n=len(its))))
            eb = bs.find(H['eb'])
            if eb and eb.tables():
                t = Table(eb.tables()[0], eb.path(), c)
                body = render_table(t.head, t.rows, c, col_cls={0: 'w-m'},
                                    cell=lambda i, k, x: (ref_cell(re.split(r'[（(]', x)[0].strip(), c)
                                                          + (f'<span class="rk">{esc(x[len(re.split(r"[（(]", x)[0]):])}</span>'
                                                             if re.search(r'[（(]', x) else '')) if k == 0 else inline(x, c))
                parts.append(self.toggle(3, 't-eb', T('t_eb'), body, T('count', n=len(t.rows))))
        ss = self.sec(3, 'screens')
        if ss:
            its, idx = [], []
            for k, v in enumerate(ss.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                if not b:
                    continue
                iid = f's-{k}'
                title = gist(clean_text(v.title)[0])
                its.append(item(iid, '', title, b, c))
                idx.append((iid, re.split(r'[、,]', title)[0].strip(), title))
            if its:
                parts.append(self.toggle(3, 't-screens', T('t_screens'), chips_index(idx) + ''.join(its), T('count_diagrams', n=len(its))))
        # data: the ER diagram from the report, the entities from dat/*.yaml
        ds = self.sec(3, 'data')
        dat = self.live(self.dat)
        b = ''.join(mermaid(self.er_with_names(m.text), c, ds.path()) for m in ds.codes()) if ds else ''
        if dat:
            rows = []
            for k, v in dat.items():
                w = f'dat/{k}.yaml'
                rows.append([k, self.t(v.get('entity') or v.get('title'), w), v.get('owner') or '—', v.get('store') or '—',
                             self.g(v.get('consistency'), w) or '—', self.g(v.get('retention'), w) or '—',
                             self.term('classification', v.get('classification'), f'{k} classification')])
            b += render_table(['DAT', T('h_entity'), T('h_owner'), T('h_store'), T('h_consistency'), T('h_retention'), T('h_classification')],
                              rows, c, row_ids=[r[0] for r in rows],
                              cell=lambda i, k, x: f'<span class="def-id">{esc(x)}</span>' if k == 0
                              else (f'<b>{inline(x, c)}</b>' if k == 1 else inline(x, c)))
            self.compare(T('t_data'), 3, ('data',), 'DAT', list(dat))
        if b:
            parts.append(self.toggle(3, 't-data', T('t_data'), b, T('count', n=len(dat)) if dat else ''))
        qs = ds.find(H['dq']) if ds else None
        if qs:
            b, cap = '', None
            for blk in qs.blocks:
                if blk.kind == 'para' and re.search(r'[:：]$', blk.text) and len(blk.text) <= 80:
                    cap = gist(clean_text(blk.text.rstrip(':：'))[0])     # a caption of the diagram that follows
                elif blk.kind == 'code' and blk.lang == 'mermaid':
                    if cap:
                        b += subhead(cap)
                    b += mermaid(blk.text, c, qs.path())
                    cap = None
                elif blk.kind == 'table':
                    tt = Table(blk, qs.path(), c)
                    b += subhead(T('sub_other_dq'))
                    b += render_table(tt.head, tt.rows, c)
            if b:
                parts.append(self.toggle(3, 't-dq', T('t_dq'), b, T('count_diagrams', n=len(qs.codes()))))
        st = self.sec(3, 'states')
        if st:
            its, idx = [], []
            for k, v in enumerate(st.children, 1):
                b = ''.join(mermaid(m.text, c, v.path()) for m in v.codes())
                if not b:
                    continue
                title = gist(clean_text(v.title)[0])
                iid = f'st-{k}'
                its.append(item(iid, '', title, b, c))
                idx.append((iid, title, title))
            if its:
                parts.append(self.toggle(3, 't-states', T('t_states'), chips_index(idx) + ''.join(its), T('count_diagrams', n=len(its))))
        ms = self.sec(3, 'measure')
        if ms and ms.tables():
            t1 = Table(ms.tables()[0], ms.path(), c)
            b = render_table(t1.head, t1.rows, c, cell=lambda i, k, x: def_cell(x, c) if k == 0 else inline(x, c))
            if len(ms.tables()) > 1:
                t2 = Table(ms.tables()[1], ms.path(), c)
                b += subhead(T('sub_monitor_sources'))
                b += render_table(t2.head, merge_dup_rows(t2.rows), c, cell=lambda i, k, x: def_cell(x, c) if k == 0 else inline(x, c))
            parts.append(self.toggle(3, 't-measure', T('t_measure'), b, T('count_sli', n=len(t1.rows))))
        # the criteria quote the quality chain's acceptance criteria, so nothing is removed from them
        if 3 in self.md:
            t = self.table(3, ('actrace',), clean=False)
            if t and len(t.head) >= 4:
                head = [t.head[0], t.head[2], t.head[1], t.head[3]]  # FR, IFC, criterion, flow
                rows = [[r[0], r[2], r[1], r[3]] for r in t.rows]
                body = render_grouped(head, rows, c, [0, 1], cls='actrace', col_cls=['w-id', 'w-m', 'w-xl', 'w-m'])
                parts.append(self.toggle(3, 't-actrace', T('t_actrace'), body,
                                         T('count_actrace', n=len({r[0] for r in rows}), m=len(rows))))
        x = self.values_toggle(3, dec3, 't-values3')
        if x:
            parts.append(x)
        x = self.debt_toggle(3, dec3, 't-debt3')
        if x:
            parts.append(x)
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
        def kinds(items, key, group=None):
            cnt = {}
            for v in items.values():
                k = LANG['terms'][group].get(v.get(key), v.get(key)) if group else v.get(key)
                cnt[k] = cnt.get(k, 0) + 1
            return cnt
        drv = self.live(self.drv)
        n_main = sum(1 for v in drv.values() if v.get('primary'))
        dec2, dec3 = self.decs('architecture'), self.decs('high-level-design')
        n_debt = sum(1 for v in dec2.values() if isinstance(v.get('debt'), dict) and v['debt'].get('what'))
        n_def = sum(1 for v in dec2.values() if v.get('deferred'))
        own = kinds(self.live(self.dat), 'owner')
        flows = self.sec(3, 'flows', quiet=True)
        nf = [v for v in (flows.children if flows else []) if v.codes()]
        n_drv = sum(1 for v in nf if v.title.startswith('DRV'))
        conv = self.sec(3, 'conv', quiet=True)
        n_conv = len(conv.tables()[0].rows) - 1 if conv and conv.tables() else None
        stops = [
            (1, 't-rank', T('r_drivers'), len(drv), [T('r_primary', n=n_main)] + [f'{k} {v}' for k, v in kinds(drv, 'kind', 'drv_kind').items()]),
            (2, 't-dec', T('r_decisions'), len(dec2), [T('r_debt', n=n_debt) if n_debt else '', T('r_deferred', n=n_def) if n_def else '']),
            (2, 't-elm', T('r_elements'), len(self.live(self.elm)), [f'{k} {v}' for k, v in kinds(self.live(self.elm), 'kind', 'elm_kind').items()]),
            (3, 't-dec3', T('r_conv_dec'), len(dec3),
             [T('r_conv', n=n_conv) if n_conv is not None else '', T('r_others', n=len(dec3) - n_conv) if n_conv is not None else '']),
            (3, 't-ifc', T('r_ifc'), len(self.live(self.ifc)), [f'{k} {v}' for k, v in kinds(self.live(self.ifc), 'kind', 'ifc_kind').items()]),
            (3, 't-flows', T('r_flows'), len(nf), [T('r_flows_cuj', n=len(nf) - n_drv), T('r_flows_drv', n=n_drv)]),
            (3, 't-data', T('r_data'), len(self.live(self.dat)),
             [(T('r_owners') if k == 0 else '') + f'{o} {n}' for k, (o, n) in enumerate(sorted(own.items(), key=lambda x: -x[1]))]),
        ]
        have = {tid for n in self.toc for tid, _ in self.toc[n]}
        stops = [s for s in stops if s[1] in have]
        lis = []
        for n, href, name, num, sub in stops:
            sub = ' · '.join(f'<span class="nb">{esc(x)}</span>' for x in sub if x)
            unit = T('unit_diagrams') if href == 't-flows' else T('unit_items')
            lis.append(f'<li class="stop"><a href="#{href}"><span class="dot" aria-hidden="true"></span>'
                       f'<span class="st-body"><span class="st-stage">{esc(T("stage_no", n=n))}</span><span class="st-name">{esc(name)}</span>'
                       f'<span class="st-num">{num}<span class="st-unit">{esc(unit)}</span></span>'
                       f'<span class="st-sub">{sub}</span></span></a></li>')
        bands = []
        col = 1
        for n in self.stages:
            w = sum(1 for s in stops if s[0] == n)
            if not w:
                continue
            bands.append(f'<span class="band" style="grid-column:{col} / {col + w}"><b>{esc(T("stage_no", n=n))}</b>{esc(self.stage_title(n))}</span>')
            col += w
        srcs = ' · '.join(dict.fromkeys(x for n in self.stages for x in STAGE_SOURCES[n].split(' · ')))
        return (f'<section id="sec-map" class="stage"><header class="stage-head"><span class="stage-no">DRV → DAT</span>'
                f'<h2>{esc(T("t_map"))}</h2><span class="src">{esc(srcs)}</span></header>'
                f'<div class="route-wrap" style="--n:{len(stops)}"><ol class="route" aria-label="{esc(T("route_label"))}">{"".join(lis)}</ol>'
                f'<div class="bands">{"".join(bands)}</div></div></section>')

    # --- the whole page
    def build(self) -> str:
        c = self.ctx
        s1, s2, s3 = self.stage1(), self.stage2(), self.stage3()
        route = self.route()
        tail = ''
        notes = [f'{T("k_" + kind)}: {w}' for kind in PAGE_NOTE_KINDS for w in c.warnings.get(kind, [])]
        if notes:
            tail = details('t-notes', T('t_notes'), '<div class="notes"><ul>' +
                           ''.join(f'<li>{esc(x)}</li>' for x in notes) + '</ul></div>', T('count', n=len(notes)))
        # header
        dates = []
        for coll in (self.drv, self.dec, self.elm, self.ifc, self.dat):
            for v in coll.values():
                for ch in v.get('changelog') or []:
                    if isinstance(ch, dict) and ch.get('date'):
                        dates.append(str(ch['date']))
        for raw in self.docs.values():
            dates += RERUN_RE.findall(raw)
        updated = max(dates) if dates else ''
        root = self.ddir.parent.parent if self.ddir.parent.name == 'docs' else self.ddir.parent
        commit = git(['log', '-1', '--format=%h', '--', str(self.ddir)], root)
        dirty = git(['status', '--porcelain', '--', str(self.ddir)], root)
        dirty = [x for x in dirty.split('\n') if x.strip() and not x.endswith(self.out.name)]
        stages = self.stages
        meta = esc(T('meta_stages', a=stages[0], b=stages[-1]) if len(stages) > 1 else T('meta_stage', a=stages[0]))
        if updated:
            meta += ' · ' + esc(T('meta_updated', d=updated))
        if commit:
            meta += f' · <span>{esc(commit)}</span>'
            if dirty:
                meta += esc(T('meta_dirty'))
        title = T('title', name=self.system_name())
        toc = [f'<nav class="toc" aria-label="{esc(T("toc"))}"><a class="toc-sec" href="#sec-map">{esc(T("t_map"))}</a>']
        for n in stages:
            subs = ''.join(f'<a href="#{t}">{esc(nm)}</a>' for t, nm in self.toc.get(n, []))
            toc.append(f'<div class="toc-grp"><a class="toc-sec" href="#sec-{n}"><span>{n}</span>{esc(self.stage_title(n))}</a>'
                       f'<div class="sub">{subs}</div></div>')
        if notes:
            toc.append(f'<a class="toc-sec toc-notes" href="#t-notes">{esc(T("t_notes"))}</a>')
        toc.append('</nav>')
        css = (ASSETS / 'base.css').read_text(encoding='utf-8') + '\n' + (ASSETS / 'design.css').read_text(encoding='utf-8')
        js = (ASSETS / 'base.js').read_text(encoding='utf-8') + '\n' + (ASSETS / 'design.js').read_text(encoding='utf-8')
        js = js.replace('__MERMAID_URL__', MERMAID_URL)
        tips = {k: c.titles[k] for k in sorted(c.used_tips)}
        tips_json = json.dumps(tips, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
        ui = {k[3:]: v for k, v in LANG['text'].items() if k.startswith('js_')}
        ui_json = json.dumps(ui, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
        repo = root.name
        where = self.ddir.relative_to(root).as_posix() if self.ddir.is_relative_to(root) else self.ddir.name
        return f'''<!doctype html>
<html lang="{LANG['code']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(T('description', title=title))}">
<meta name="generator" content="design-summary-html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(LANG['fonts'])}">
<style>
{css}
</style>
</head>
<body>
<div class="page">
<header class="masthead">
<div class="mast-text">
<p class="eyebrow">{esc(repo)} · {esc(where)}</p>
<h1>{esc(title)}</h1>
<p class="meta">{meta}</p>
</div>
<div class="tools"><button type="button" class="btn" id="open-all">{esc(T('open_all'))}</button><button type="button" class="btn" id="close-all">{esc(T('close_all'))}</button></div>
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
<script type="application/json" id="ui-text">{ui_json}</script>
<script>
{js}
</script>
</body>
</html>
'''

    def system_name(self) -> str:
        n = ((self.qctx or {}).get('system') or {}).get('name') or ''
        n = re.sub(r'\s*[（(][^（()）]*[）)]$', '', n).strip()
        if n:
            return n
        for k in sorted(self.md):
            root = self.md[k]
            h1 = root.children[0].title if root.children and root.children[0].level == 1 else ''
            m = re.search(r'[:：]\s*(.+?)(?:\s*[（(].*[）)])?$', h1)
            if m:
                return m.group(1).strip()
        return T('system_fallback')

    def counts(self) -> str:
        live = self.live
        return T('rep_counts', drv=len(live(self.drv)), dec=len(self.decs('architecture')) + len(self.decs('high-level-design')),
                 dec2=len(self.decs('architecture')), dec3=len(self.decs('high-level-design')),
                 elm=len(live(self.elm)), ifc=len(live(self.ifc)), dat=len(live(self.dat)))


def split_label(title: str) -> tuple:
    m = re.match(r'^((?:CUJ|DRV)-\d{2}(?:[〜–]\d{2})?(?:-[A-Z])?)\s+(.*)$', title)
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


def check_page(page: str) -> tuple:
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
    ap.add_argument('--out', default=None, help='where to write the page (default: DESIGN_DIR/summary.html)')
    ap.add_argument('--lang', choices=LANGS, help='language of the page and the report (default: Japanese when the outputs are '
                                                  'written in Japanese, English otherwise)')
    ap.add_argument('--show-cleaning', action='store_true',
                    help='print every text (YAML value, table cell) whose revision notes were removed, before and after')
    a = ap.parse_args(argv)
    ddir = Path(a.design_dir).resolve()
    if not ddir.is_dir():
        die_t('die_no_dir', a.lang, path=ddir)
    qdir = Path(a.quality_dir).resolve() if a.quality_dir else ddir.parent / 'quality'
    out = Path(a.out).resolve() if a.out else ddir / 'summary.html'
    b = Builder(ddir, qdir, out)
    if not b.load(a.lang):
        die_t('die_no_outputs', a.lang, path=ddir)
    page = b.build()
    page, dup, dangling, unlinked = check_page(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    c = b.ctx
    try:
        shown = out.relative_to(Path.cwd())
    except ValueError:
        shown = out
    print(T('rep_written', path=shown, kb=len(page.encode('utf-8')) // 1024))
    print(T('rep_lang', lang=b.lang, how=T(b.lang_how)))
    print(T('rep_stages', stages=T('stage_sep').join(str(n) for n in b.stages),
            reports=T('sep').join(REPORT_FILES[n] for n in sorted(b.md)) or T('none')))
    print(T('rep_items', counts=b.counts()))
    for kind in REPORT_KINDS:
        ws = c.warnings.get(kind, [])
        print(T('rep_kind', kind=T('k_' + kind), n=len(ws)) if ws else T('rep_kind_none', kind=T('k_' + kind)))
        for w in ws:
            print(f'  - {w}')
    print(T('rep_cleaned', n=len(c.cleaned)) + (T('rep_cleaned_hint') if c.cleaned and not a.show_cleaning else ''))
    if a.show_cleaning:
        for where, before, after in c.cleaned:
            print(f'  @ {where}\n    - {before}\n    + {after}')
    if unlinked:
        print(T('rep_unlinked', ids=T('sep').join(unlinked)))
    if dup or dangling:
        print(T('rep_selfcheck', dup=dup, dangling=dangling))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
