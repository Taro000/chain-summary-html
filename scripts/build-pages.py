#!/usr/bin/env python3
"""Build the GitHub Pages site: the pages both skills build for two fictional projects, and an index of them.

  uv run --with pyyaml python3 scripts/build-pages.py [OUT]      (default: _site)

Each project is copied from skills/design-summary-html/evals/<case>/files, which holds docs/quality and docs/design
side by side as a real project does, so the design page links to the quality page. The quality page is built first,
since the design page reads it for those links. The pages are built in a temporary directory outside git, so they show
no commit; the index shows the commit they were built from. Only the pages and the index go to OUT.
Exits with 1 when a generator does not exit with 0.
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / 'skills' / 'design-summary-html' / 'evals'
REPO = 'https://github.com/' + os.environ.get('GITHUB_REPOSITORY', 'Taro000/chain-summary-html')
# (eval case, project name on the index)
CASES = (('ride-hailing-full', 'Ride-hailing app'), ('homework-service-full-en', 'Homework submission service'))
# in build order: the design page links to the quality page
GENERATORS = (('quality', ROOT / 'skills' / 'quality-summary-html' / 'scripts' / 'build_summary.py'),
              ('design', ROOT / 'skills' / 'design-summary-html' / 'scripts' / 'build_design_summary.py'))
LANGS = {'ja': 'Japanese', 'en': 'English'}

STYLE = '''
body{margin:0;background:#fff;color:#1d1d1f;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:720px;margin:0 auto;padding:48px 16px}
h1{font-size:1.6rem;margin:0 0 8px}
p{margin:0 0 24px;color:#4a4a4f}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid #e3e3e8;vertical-align:top}
th{font-size:.85rem;color:#6b6b70;font-weight:600}
td small{display:block;color:#6b6b70}
a{color:#0b57d0}
footer{margin-top:32px;font-size:.85rem;color:#6b6b70}
'''


def run(script: Path, docs: Path) -> None:
    r = subprocess.run([sys.executable, str(script), str(docs)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'{script.name} exited with {r.returncode} on {docs}:\n{r.stdout}{r.stderr}')


def head(page: Path) -> tuple:
    """The page's title and language"""
    src = page.read_text(encoding='utf-8')
    return html.unescape(re.search(r'<title>(.*?)</title>', src).group(1)), re.search(r'<html lang="(\w+)"', src).group(1)


def commit() -> str:
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def index(rows: list) -> str:
    e = html.escape
    trs = []
    for case, name, lang, pages in rows:
        cells = ''.join(f'<td><a href="{e(href)}">{e(title)}</a></td>' for href, title in pages)
        inputs = f'{REPO}/tree/main/skills/design-summary-html/evals/{case}/files/docs'
        trs.append(f'<tr><td>{e(name)}<small>{e(LANGS.get(lang, lang))}</small></td>{cells}'
                   f'<td><a href="{e(inputs)}">docs/</a></td></tr>')
    sha = commit()
    built = f'Built from <a href="{e(REPO)}/commit/{e(sha)}">{e(sha)}</a>.' if sha else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>chain-summary-html demo</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>chain-summary-html</h1>
<p>Pages that <a href="{e(REPO)}#quality-summary-html">quality-summary-html</a> and
<a href="{e(REPO)}#design-summary-html">design-summary-html</a> built from two fictional projects' outputs.</p>
<table>
<thead><tr><th>Project</th><th>Quality</th><th>Design</th><th>Outputs read</th></tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody>
</table>
<footer>{built}</footer>
</main>
</body>
</html>
'''


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '_site').resolve()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for case, name in CASES:
            shutil.copytree(EVALS / case / 'files', Path(tmp) / case, ignore=shutil.ignore_patterns('summary.html'))
            target = out / case
            if target.exists():
                shutil.rmtree(target)
            pages = []
            for kind, script in GENERATORS:
                docs = Path(tmp) / case / 'docs' / kind
                run(script, docs)
                rel = f'{case}/docs/{kind}/summary.html'
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(docs / 'summary.html', out / rel)
                title, lang = head(out / rel)
                pages.append((rel, title))
                print(f'wrote {rel} ({title})')
            rows.append((case, name, lang, pages))
    (out / 'index.html').write_text(index(rows), encoding='utf-8')
    print(f'wrote index.html in {out}')


if __name__ == '__main__':
    main()
