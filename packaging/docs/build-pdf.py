#!/usr/bin/env python3
"""Make INSTALAR.pdf from INSTALAR.md: Markdown -> HTML (markdown-it-py)
-> PDF (headless Chrome or Chromium).
usage: build-pdf.py INSTALAR.md out.pdf   (CHROME=path overrides the browser)
"""
import os, re, shutil, subprocess, sys, tempfile
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin


def slug(title):
	"""GitHub's heading anchors, so the links in the guide work."""
	s = title.strip().lower()
	s = re.sub(r'[^\w\- ]', '', s)
	return s.replace(' ', '-')

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt;
	line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 22pt; border-bottom: 2px solid #345; padding-bottom: 4px; }
h2 { font-size: 15pt; color: #234; border-bottom: 1px solid #bbb; margin-top: 1.6em;
	page-break-after: avoid; }
h3 { font-size: 12pt; color: #234; page-break-after: avoid; }
code { font-family: "DejaVu Sans Mono", Menlo, Consolas, monospace; font-size: 9.5pt;
	background: #f2f2f2; padding: 0 2px; }
pre { background: #f2f2f2; border-left: 3px solid #567; padding: 6px 10px;
	white-space: pre-wrap; page-break-inside: avoid; tab-size: 4; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; margin: 0.8em 0; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 4px 8px; text-align: left; vertical-align: top; }
th { background: #e8ecf0; }
a { color: #1a4f8a; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
li { margin: 0.2em 0; }
"""

def find_chrome():
	if os.environ.get('CHROME'):
		return os.environ['CHROME']
	for c in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
			'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'):
		p = shutil.which(c) or (c if os.path.exists(c) else None)
		if p:
			return p
	sys.exit('build-pdf: Chrome or Chromium not found (set CHROME)')

def main():
	src, out = sys.argv[1], os.path.abspath(sys.argv[2])
	text = open(src, encoding='utf-8').read()
	md = MarkdownIt('commonmark').enable('table').use(anchors_plugin, max_level=3, slug_func=slug)
	body = md.render(text)
	m = re.search(r'^#\s+(.+)$', text, re.M)
	title = m.group(1).strip() if m else os.path.basename(src)
	html = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
		'<title>%s</title><style>%s</style></head><body>%s</body></html>'
		% (title, CSS, body))
	d = tempfile.mkdtemp()
	h = os.path.join(d, 'guia.html')
	open(h, 'w', encoding='utf-8').write(html)
	subprocess.run([find_chrome(), '--headless', '--disable-gpu', '--no-sandbox',
		'--no-pdf-header-footer', '--print-to-pdf=' + out, 'file://' + h],
		check=True, capture_output=True)
	print('wrote', out)

main()
