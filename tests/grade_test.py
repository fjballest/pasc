#!/usr/bin/env python3
"""Checks pasgrade on tests/grade: compiling, relaxed compiling, endless
loops, files read through --datos and the comparison with result.txt
and result.chg.txt."""
import os, subprocess, sys, shutil, tempfile
os.environ['PASCLIMITS'] = ''	# ignore the user's ~/.pasclimits

HERE = os.path.dirname(os.path.abspath(__file__))
GRADE = os.path.join(os.path.dirname(HERE), 'pasgrade.py')
fail = 0

def check(what, cond):
	global fail
	print(('ok   ' if cond else 'FAIL ') + what)
	fail += not cond

d = tempfile.mkdtemp()
try:
	for f in os.listdir(os.path.join(HERE, 'grade')):
		shutil.copy(os.path.join(HERE, 'grade', f), d)
	for punct, want in (([], {'bien.p': 'y y', 'bucle.p': 'n y', 'etiqueta.p': 'n y', 'fichero.p': 'y y',
			'mal.p': 'n y', 'roto.p': 'n n', 'sangria.p': 'y r'}), (['-p'], {'etiqueta.p': 'm y'})):
		r = subprocess.run([sys.executable, GRADE, '-M', '-t', '2'] + punct + [d], capture_output=True, text=True)
		got = {l.split('\t')[-1]: ' '.join(l.split('\t')[i] for i in (3, 5)) for l in r.stdout.splitlines()}
		for prog, w in want.items():
			check('%s %s: works/comp %s' % (' '.join(punct), prog, w), got.get(prog) == w)
	notas = open(os.path.join(d, 'NOTAS.pasgrade')).read().splitlines()
	check('NOTAS header', notas[1].split('\t') == ['nota', 'clean', 'burr', 'works', 'modok', 'comp', 'warn', 'who'])
	out = open(os.path.join(d, 'bucle.p.out')).read()
	check('endless loop reported', 'endless loop' in out)
	check('relaxed compile reported', 'only compiles with pasc -R' in open(os.path.join(d, 'sangria.p.out')).read())
	# the change asked for in the exam: result.chg.txt decides modok
	with open(os.path.join(d, 'result.chg.txt'), 'w') as f:
		f.write('doble: 42\ntriple: 63\n')
	with open(os.path.join(d, 'cambio.p'), 'w') as f:
		f.write("program cambio;\n\nvar\n\tn: integer;\nbegin\n\treadln(n);\n"
			"\twriteln('doble: ', 2 * n);\n\twriteln('triple: ', 3 * n);\nend.\n")
	env = dict(os.environ, PATH=os.path.dirname(sys.executable))	# no moss here
	r = subprocess.run([sys.executable, GRADE, '-t', '2', d], capture_output=True, text=True, env=env)
	got = {l.split('\t')[-1]: ' '.join(l.split('\t')[i] for i in (3, 4)) for l in r.stdout.splitlines()}
	for prog, w in {'cambio.p': 'y y', 'bien.p': 'y n', 'roto.p': 'n n', 'bucle.p': 'n n'}.items():
		check('change: %s works/modok %s' % (prog, w), got.get(prog) == w)
	notas = open(os.path.join(d, 'NOTAS.pasgrade')).read()
	check('no moss: noted in NOTAS', 'moss error: moss not found' in notas)
finally:
	shutil.rmtree(d)
sys.exit(1 if fail else 0)
