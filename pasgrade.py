#!/usr/bin/env python3
"""pasgrade: a first pass at grading the Pascal programs in a directory.

usage: pasgrade [-t SECS] [-i INPUT] [-r RESULT] [-c CHANGED] [-o NOTAS] [-p] [-z] [-M] [dir]

For each NAME.p in dir (default .), pasgrade:

  - compiles it with pasc and records whether it compiles and whether it
    gets warnings;
  - runs it in a scratch directory, with INPUT (default datos.txt) as
    datos.txt and also as its standard input, using pasc --datos so that
    every file the program opens is datos.txt; a run longer than SECS
    seconds (default 10) is stopped and counts as an endless loop;
  - writes NAME.p.out with pasc's messages, the program's output and how it
    ended;
  - if RESULT (default result.txt) exists, checks that each line of RESULT
    appears in the output, in order, ignoring blank space, empty lines and
    case (and, with -p, punctuation), and allowing extra text such as
    prompts or labels and different line breaks; that decides whether it
    works;
  - if CHANGED (default result.chg.txt) exists, the result expected once
    the change asked for in the exam is made, checks the output against it
    in the same way: that decides modok (whether the change works).  Then
    the program works if its output matches RESULT or CHANGED, so that a
    program with the change made also counts as working.

Meanwhile, unless -M is given, it sends the programs to the moss service
(with the moss script found in the PATH) to look for similar programs. The
ten most similar pairs are copied, in plain text, to the end of NOTAS,
after the moss URL, and the programs of a pair that is more than 80 %
similar are flagged with '*' in the nota column. If moss is not there,
fails or its server does not answer, NOTAS says so and nothing else changes.

With -z, uninitialised variables are zero, as with fpc (pasc fills them
with garbage, which shows programs that forget to initialise them).

It then writes a NOTAS file (default NOTAS.pasgrade, never NOTAS itself)
with tab separated columns, '-' meaning "not known":

	nota  clean  burr  works  modok  comp  warn  who

comp is y if it compiles, r if it only compiles with pasc -R (it breaks the
course rules, such as indentation or the limits, but is valid Pascal) and n
if it does not compile; warn is y/n; works is y/n when there is a RESULT
(m, "maybe", when the expected words are all there, in order, but mixed
with other text: worth a look), and n when the program does not compile,
fails or loops; modok is the same, against CHANGED, when there is one.
The other columns are left for the teacher. If dir has an IDS file
(written by pasclean), NOTAS gets one more column, id, with each student's
Moodle "Número de ID", which pasnotas uses to put the grades in Moodle.
"""

import html
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PASC = [sys.executable, os.path.join(HERE, 'pasc.py')]
RUNFLAGS = []		# extra pasc flags for running (-z)
MOSSSECS = 600		# how long to wait for moss
MOSSTOP = 10		# similar pairs kept in NOTAS
MOSSFLAG = 80		# % of similarity flagged with '*'
COLUMNS = ['nota', 'clean', 'burr', 'works', 'modok', 'comp', 'warn', 'who']


def usage():
	sys.stderr.write('usage: pasgrade [-t secs] [-i input] [-r result] [-c changed] [-o notas] [-p] [-z] [-M] [dir]\n')
	sys.exit(2)


def compact(text, punct):
	"""text without blank space, in lower case and, with -p, without
	punctuation."""
	text = text.lower()
	if punct:
		text = text.translate(str.maketrans('', '', string.punctuation))
	return ''.join(text.split())


def compare(out, result, punct):
	"""'y' if the output has the expected lines, in order; 'm' (maybe) if
	some of them are only there word by word, with other text in between
	(labels such as "Columna: B"); 'n' otherwise.  Blank space, empty
	lines and case do not matter, nor does extra text before, after or
	between lines, nor how the output is split in lines: everything is
	compared once all blank space is removed."""
	got = compact(out, punct)
	pos = 0
	verdict = 'y'
	for line in result.split('\n'):
		want = compact(line, punct)
		if not want:
			continue
		k = got.find(want, pos)
		if k >= 0:
			pos = k + len(want)
			continue
		for word in line.split():		# word by word
			w = compact(word, punct)
			k = got.find(w, pos) if w else pos
			if k < 0:
				return 'n'
			pos = k + len(w)
		verdict = 'm'
	return verdict


def compile_check(path, flags):
	"""(compiles, has warnings, pasc's messages)."""
	r = subprocess.run(PASC + flags + ['-c', path], capture_output=True, text=True, errors='replace')
	msgs = r.stderr
	return r.returncode == 0, ' warning: ' in msgs, msgs


def run(path, inp, secs, flags):
	"""(output, how it ended): runs the program in a scratch directory."""
	d = tempfile.mkdtemp(prefix='pasgrade-')
	try:
		shutil.copy(path, os.path.join(d, 'prog.p'))
		data = b''
		if inp and os.path.exists(inp):
			shutil.copy(inp, os.path.join(d, 'datos.txt'))
			with open(inp, 'rb') as f:
				data = f.read()
		try:
			r = subprocess.run(PASC + flags + RUNFLAGS + ['--datos', 'prog.p'], cwd=d, input=data,
				capture_output=True, timeout=secs)
			out = r.stdout.decode('latin-1')
			err = r.stderr.decode('latin-1').replace('prog.p:', os.path.basename(path) + ':')
			how = 'exit status %d' % r.returncode
			ok = r.returncode == 0
		except subprocess.TimeoutExpired as e:
			out = (e.stdout or b'').decode('latin-1')
			err = (e.stderr or b'').decode('latin-1')
			how = 'stopped after %g seconds: endless loop?' % secs
			ok = False
		return out, err, how, ok
	finally:
		shutil.rmtree(d, ignore_errors=True)


def startmoss(d, progs):
	"""starts moss on the programs in the background: (process, error)."""
	moss = shutil.which('moss')
	if moss is None:
		return None, 'moss not found in the PATH'
	if len(progs) < 2:
		return None, 'fewer than two programs'
	try:
		p = subprocess.Popen([moss] + progs, cwd=d, stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	except OSError as e:
		return None, 'moss: %s' % e
	return p, None


def mossreport(p):
	"""(url, top pairs, error): waits for moss and reads its report; a pair
	is (prog1, %1, prog2, %2, lines)."""
	try:
		out = p.communicate(timeout=MOSSSECS)[0].decode('latin-1')
	except subprocess.TimeoutExpired:
		p.kill()
		return None, [], 'moss did not answer in %d seconds' % MOSSSECS
	urls = re.findall(r'https?://\S+', out)
	if p.returncode != 0 or not urls:
		last = out.strip().splitlines()[-1:] or ['no output']
		return None, [], 'moss failed: %s' % last[0]
	url = urls[-1]
	try:
		with urllib.request.urlopen(url, timeout=60) as r:
			page = r.read().decode('latin-1')
	except Exception as e:
		return url, [], 'cannot read the moss report: %s' % e
	pairs = []
	for row in re.findall(r'(?is)<tr>(.*?)(?=<tr>|</table>)', page):
		files = re.findall(r'(?is)<a [^>]*>\s*([^<]*?)\s*\((\d+)%\)\s*</a>', row)
		lines = re.findall(r'(?is)<td[^>]*>\s*(\d+)\s*$', row.strip())
		if len(files) == 2:
			(f1, p1), (f2, p2) = files
			pairs.append((html.unescape(f1), int(p1), html.unescape(f2), int(p2),
				lines[0] if lines else '-'))
	pairs.sort(key=lambda x: -max(x[1], x[3]))
	return url, pairs[:MOSSTOP], None


def best(a, b):
	"""the better of two verdicts (y, m, n), '-' meaning not known."""
	for v in 'ymn':
		if v in (a, b):
			return v
	return '-'


def grade(path, inp, result, changed, secs, punct):
	name = os.path.basename(path)
	comp, warn, msgs = compile_check(path, [])
	flags = []
	row = dict.fromkeys(COLUMNS, '-')
	row['who'] = name
	row['comp'] = 'y' if comp else 'n'
	row['warn'] = 'y' if warn else 'n'
	report = ['=== pasc', msgs.rstrip() or '(no messages)']
	if not comp:
		# perhaps it breaks only the course rules (indentation, limits...):
		# then pasc -R compiles it, and it can still be run and checked
		rcomp, rwarn, rmsgs = compile_check(path, ['-R'])
		if rcomp:
			comp, flags = True, ['-R']
			row['comp'] = 'r'
			report += ['=== it only compiles with pasc -R (it breaks the course rules)', rmsgs.rstrip()]
	if not comp:
		row['works'] = 'n'
		if changed is not None:
			row['modok'] = 'n'
		report.append('=== not run: it does not compile')
	else:
		out, err, how, ok = run(path, inp, secs, flags)
		report += ['=== output', out.rstrip('\n'), '=== messages', err.rstrip() or '(none)', '=== ' + how]
		if not ok:
			row['works'] = 'n'
			if changed is not None:
				row['modok'] = 'n'
		else:
			if result is not None:
				row['works'] = compare(out, result, punct)
			if changed is not None:
				row['modok'] = compare(out, changed, punct)
				row['works'] = best(row['works'], row['modok'])
	with open(path + '.out', 'w', encoding='latin-1', errors='replace') as f:
		f.write('\n'.join(report) + '\n')
	return row


def main(argv):
	secs, inp, resname, notas, punct, d = 10.0, 'datos.txt', 'result.txt', 'NOTAS.pasgrade', False, '.'
	chgname = 'result.chg.txt'
	usemoss = True
	i = 0
	while i < len(argv):
		a = argv[i]
		if a in ('-t', '-i', '-r', '-c', '-o') and i + 1 < len(argv):
			i += 1
			if a == '-t':
				secs = float(argv[i])
			elif a == '-i':
				inp = argv[i]
			elif a == '-r':
				resname = argv[i]
			elif a == '-c':
				chgname = argv[i]
			else:
				notas = argv[i]
		elif a == '-p':
			punct = True
		elif a == '-z':
			RUNFLAGS.append('-z')
		elif a == '-M':
			usemoss = False
		elif a.startswith('-'):
			usage()
		else:
			d = a
		i += 1
	if os.path.basename(notas) == 'NOTAS':
		sys.exit('pasgrade: will not overwrite NOTAS; use another name')
	join = lambda p: p if os.path.isabs(p) else os.path.join(d, p)
	inp, notas = join(inp), join(notas)

	def readres(name):
		path = join(name)
		if not os.path.exists(path):
			return None
		with open(path, encoding='latin-1') as f:
			return f.read()
	result, changed = readres(resname), readres(chgname)
	progs = sorted(p for p in os.listdir(d) if p.endswith('.p') and not p.startswith('.'))
	ids, cols = None, COLUMNS
	if os.path.exists(join('IDS')):		# written by pasclean
		with open(join('IDS')) as f:
			ids = dict(l.rstrip('\n').split('\t', 1) for l in f if '\t' in l)
		cols = COLUMNS + ['id']
	moss, mosserr = startmoss(d, progs) if usemoss else (None, None)
	rows = []
	for p in progs:
		row = grade(os.path.join(d, p), inp, result, changed, secs, punct)
		if ids is not None:
			row['id'] = ids.get(p, '-')
		rows.append(row)
		print('\t'.join(row[c] for c in cols))
		sys.stdout.flush()
	url, pairs = None, []
	if moss is not None:
		sys.stderr.write('pasgrade: waiting for moss...\n')
		url, pairs, mosserr = mossreport(moss)
	similar = set()
	for f1, p1, f2, p2, lines in pairs:
		if max(p1, p2) > MOSSFLAG:
			similar.update((os.path.basename(f1), os.path.basename(f2)))
	for row in rows:
		if row['who'] in similar:
			row['nota'] = '*'
	with open(notas, 'w') as f:
		f.write('Tab 8\n')
		f.write('\t'.join(cols) + '\n')
		for row in rows:
			f.write('\t'.join(row[c] for c in cols) + '\n')
		if usemoss:
			f.write('\nmoss: %s\n' % (url or 'no report'))
			if mosserr:
				f.write('moss error: %s\n' % mosserr)
			if pairs:
				f.write('most similar pairs (* more than %d %%):\n' % MOSSFLAG)
				for f1, p1, f2, p2, lines in pairs:
					mark = '*' if max(p1, p2) > MOSSFLAG else ' '
					f.write('%s %3d%%  %-40s %3d%%  %-40s %s lines\n' % (mark, p1, f1, p2, f2, lines))
			if mosserr:
				sys.stderr.write('pasgrade: %s\n' % mosserr)
	sys.stderr.write('pasgrade: %d programs; wrote %s%s%s\n' % (len(rows), notas,
		'' if result is not None or changed is not None else ' (no %s: works not checked)' % resname,
		'' if changed is None else ' (modok checked with %s)' % chgname))
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
