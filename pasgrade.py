#!/usr/bin/env python3
"""pasgrade: a first pass at grading the Pascal programs in a directory.

usage: pasgrade [-t SECS] [-i INPUT] [-r RESULT] [-o NOTAS] [-p] [-z] [dir]

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
    works.

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
fails or loops. The other columns are left for the teacher.
"""

import os
import re
import shutil
import string
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PASC = [sys.executable, os.path.join(HERE, 'pasc.py')]
RUNFLAGS = []		# extra pasc flags for running (-z)
COLUMNS = ['nota', 'clean', 'burr', 'works', 'modok', 'comp', 'warn', 'who']


def usage():
	sys.stderr.write('usage: pasgrade [-t secs] [-i input] [-r result] [-o notas] [-p] [-z] [dir]\n')
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


def grade(path, inp, result, secs, punct):
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
		report.append('=== not run: it does not compile')
	else:
		out, err, how, ok = run(path, inp, secs, flags)
		report += ['=== output', out.rstrip('\n'), '=== messages', err.rstrip() or '(none)', '=== ' + how]
		if not ok:
			row['works'] = 'n'
		elif result is not None:
			row['works'] = compare(out, result, punct)
	with open(path + '.out', 'w', encoding='latin-1', errors='replace') as f:
		f.write('\n'.join(report) + '\n')
	return row


def main(argv):
	secs, inp, resname, notas, punct, d = 10.0, 'datos.txt', 'result.txt', 'NOTAS.pasgrade', False, '.'
	i = 0
	while i < len(argv):
		a = argv[i]
		if a in ('-t', '-i', '-r', '-o') and i + 1 < len(argv):
			i += 1
			if a == '-t':
				secs = float(argv[i])
			elif a == '-i':
				inp = argv[i]
			elif a == '-r':
				resname = argv[i]
			else:
				notas = argv[i]
		elif a == '-p':
			punct = True
		elif a == '-z':
			RUNFLAGS.append('-z')
		elif a.startswith('-'):
			usage()
		else:
			d = a
		i += 1
	if os.path.basename(notas) == 'NOTAS':
		sys.exit('pasgrade: will not overwrite NOTAS; use another name')
	join = lambda p: p if os.path.isabs(p) else os.path.join(d, p)
	inp, respath, notas = join(inp), join(resname), join(notas)
	result = None
	if os.path.exists(respath):
		with open(respath, encoding='latin-1') as f:
			result = f.read()
	progs = sorted(p for p in os.listdir(d) if p.endswith('.p') and not p.startswith('.'))
	rows = []
	for p in progs:
		row = grade(os.path.join(d, p), inp, result, secs, punct)
		rows.append(row)
		print('\t'.join(row[c] for c in COLUMNS))
		sys.stdout.flush()
	with open(notas, 'w') as f:
		f.write('Tab 8\n')
		f.write('\t'.join(COLUMNS) + '\n')
		for row in rows:
			f.write('\t'.join(row[c] for c in COLUMNS) + '\n')
	sys.stderr.write('pasgrade: %d programs; wrote %s%s\n' % (len(rows), notas,
		'' if result is not None else ' (no %s: works not checked)' % resname))
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
