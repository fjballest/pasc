#!/usr/bin/env python3
"""Run every course program with pasc and compare with fpc's results
recorded in tests/expected (see gen_expected.py).

A program passes when its standard output and exit status match fpc's;
for programs fpc rejects, pasc must reject them too, at the same line.
Known, deliberate differences are listed in KNOWN below.
usage: run_tests.py [-v] [prog.p ...]
"""
import os, re, sys, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cases

PASC = os.path.join(os.path.dirname(cases.HERE), 'pasc.py')
EXP = os.path.join(cases.HERE, 'expected')

# program -> reason; these differ from fpc on purpose (see README)
KNOWN = {
	'02.holapi.p': 'float division by zero: pasc reports 200 (as fpc on x86-64/Windows); fpc on arm64 macOS reports 216',
	'64a.ptrint.p': 'reads uninitialised and disposed heap memory: fpc prints garbage, pasc prints 0 and the old value',
}


def read(p, mode='rb'):
	try:
		with open(p, mode) as f:
			return f.read()
	except FileNotFoundError:
		return None


def main():
	verbose = '-v' in sys.argv
	names = [a for a in sys.argv[1:] if not a.startswith('-')] or cases.programs()
	# programs added to the course directory after the fpc results were
	# recorded (run gen_expected.py to add them)
	names = [n for n in names if os.path.exists(os.path.join(EXP, n[:-2] + '.status'))]
	tmp = tempfile.mkdtemp(prefix='pasc-test-')
	ok = fail = known = 0
	for name in names:
		base = os.path.join(EXP, name[:-2])
		d = cases.fresh_dir(tmp, name)
		try:
			r = subprocess.run([sys.executable, PASC, '-g'] + (['-z'] if not os.environ.get('RANDOM_MEM') else []) + [name], cwd=d, input=cases.stdin_for(name),
				capture_output=True, timeout=60)
			out, err, status = r.stdout, r.stderr.decode('latin-1'), str(r.returncode)
		except subprocess.TimeoutExpired as e:
			out, err, status = e.stdout or b'', '', 'timeout'
		comp = read(base + '.compile', 'r')
		problems = []
		if comp is not None:
			m = re.match(r'[^(]*\((\d+)', comp)
			want = m.group(1) if m else '?'
			m = re.match(r'[^:]*:(\d+):', err)
			got = m.group(1) if m else None
			if status != '1' or 'error:' not in err:
				problems.append('fpc rejects it (%s) but pasc did not' % comp.strip().splitlines()[0])
			elif got != want:
				problems.append('compile error at line %s, fpc at line %s\n    pasc: %s\n    fpc:  %s'
					% (got, want, err.strip().splitlines()[0], comp.strip().splitlines()[0]))
		else:
			if 'error:' in err and status == '1':
				problems.append('pasc rejects it: ' + err.strip().splitlines()[0])
			else:
				eout = read(base + '.out')
				estatus = read(base + '.status', 'r').strip()
				if out != eout:
					problems.append('stdout differs')
					if verbose:
						problems.append('--- fpc\n%s\n--- pasc\n%s' % (eout.decode('latin-1')[:1500],
							out.decode('latin-1')[:1500]))
				if status != estatus:
					problems.append('exit status %s, fpc %s' % (status, estatus))
				if verbose and err:
					problems.append('stderr: ' + err.strip()[:500])
		if not problems:
			ok += 1
			print('ok    ' + name)
		elif name in KNOWN:
			known += 1
			print('known ' + name + ': ' + KNOWN[name])
			if verbose:
				print('    ' + '\n    '.join(problems))
		else:
			fail += 1
			print('FAIL  ' + name + ': ' + '\n    '.join(problems))
	print('\n%d ok, %d known differences, %d failed' % (ok, known, fail))
	return 1 if fail else 0

sys.exit(main())
