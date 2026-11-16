#!/usr/bin/env python3
"""Check pasc's warnings: for each tests/lint/X.p, every line of
X.expected must appear in the warnings of 'pasc -c X.p', and
nothing else may be reported."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, 'lint')
PASC = os.path.join(os.path.dirname(HERE), 'pasc.py')
fail = 0
for f in sorted(os.listdir(LINT)):
	if not f.endswith('.p'):
		continue
	r = subprocess.run([sys.executable, PASC, '-g', '-L', '-c', f], cwd=LINT, capture_output=True)
	got = [l for l in r.stderr.decode().splitlines() if 'warning:' in l]
	want = [l for l in open(os.path.join(LINT, f[:-2] + '.expected')).read().splitlines() if l.strip()]
	probs = ['missing: ' + w for w in want if not any(w in g for g in got)]
	probs += ['unexpected: ' + g for g in got if not any(w in g for w in want)]
	if probs:
		fail += 1
		print('FAIL ' + f + '\n  ' + '\n  '.join(probs))
	else:
		print('ok   ' + f)
sys.exit(1 if fail else 0)
