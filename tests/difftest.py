#!/usr/bin/env python3
"""Differential test: run each tests/extra/*.p with fpc and with pasc and
compare standard output, exit status and (for rejected programs) the line
of the first compile error.  X.in, if present, is the program's input.
The fpc results are cached in tests/extra/expected so the suite also runs
where fpc is not installed.
usage: difftest.py [-v] [-r] [names...]   (-r: rerun fpc, refresh cache)
"""
import os, re, sys, shutil, subprocess, tempfile, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRA = os.path.join(HERE, 'extra')
CACHE = os.path.join(EXTRA, 'expected')
PASC = os.path.join(os.path.dirname(HERE), 'pasc.py')

# deliberate differences from fpc
KNOWN = {
	'recinf.p': 'infinite recursion: pasc reports run-time error 202 (stack overflow); fpc on macOS dies with SIGSEGV',
}

def run(cmd, d, inp):
	try:
		r = subprocess.run(cmd, cwd=d, input=inp, capture_output=True, timeout=30)
		return r.stdout, r.stderr, r.returncode
	except subprocess.TimeoutExpired as e:
		return e.stdout or b'', b'timeout', 'timeout'

def setup(tmp, name, src):
	d = tempfile.mkdtemp(dir=tmp)
	shutil.copy(src, os.path.join(d, name))
	for f in os.listdir(EXTRA):
		if f.endswith('.txt'):
			shutil.copy(os.path.join(EXTRA, f), d)
	return d

def fpc_result(tmp, name, src, inp, refresh):
	cp = os.path.join(CACHE, name[:-2] + '.json')
	h = hashlib.sha1(open(src, 'rb').read() + b'\0' + inp).hexdigest()
	if not refresh and os.path.exists(cp):
		with open(cp) as f:
			res = json.load(f)
		# the cache is valid for this exact program and input; without fpc
		# it is used anyway
		if res.get('sha1') == h or shutil.which('fpc') is None:
			return res
	d = setup(tmp, name, src)
	c = subprocess.run(['fpc', '-g', '-oa.out', name], cwd=d, capture_output=True)
	log = c.stdout.decode('latin-1')
	if c.returncode != 0:
		errs = [l for l in log.splitlines() if re.search(r'\(\d+(,\d+)?\) (Error|Fatal):', l)]
		res = {'compile': errs[0] if errs else log[-300:]}
	else:
		o, e, s = run(['./a.out'], d, inp)
		res = {'out': o.decode('latin-1'), 'status': s}
	res['sha1'] = h
	os.makedirs(CACHE, exist_ok=True)
	with open(cp, 'w') as f:
		json.dump(res, f, indent=1)
	return res

def main():
	args = sys.argv[1:]
	verbose = '-v' in args
	refresh = '-r' in args
	names = [a for a in args if not a.startswith('-')]
	if not names:
		names = sorted(f for f in os.listdir(EXTRA) if f.endswith('.p'))
	names = [n if n.endswith('.p') else n + '.p' for n in names]
	tmp = tempfile.mkdtemp(prefix='pasc-diff-')
	nok = nfail = 0
	for name in names:
		src = os.path.join(EXTRA, name)
		inp = b''
		if os.path.exists(src[:-2] + '.in'):
			with open(src[:-2] + '.in', 'rb') as f:
				inp = f.read()
		d = setup(tmp, name, src)
		o, e, s = run([sys.executable, PASC, '-z', name], d, inp)
		e = e.decode('latin-1')
		probs = []
		if name.startswith('restr_'):
			# outside the course subset: fpc accepts it, pasc must not
			if not re.match(r'[^:]*:(\d+):\d+: error', e):
				probs.append('pasc accepted a program outside the subset')
			elif verbose:
				print('      pasc: ' + e.strip().splitlines()[0])
			want = {}
		elif name.startswith('ext_'):
			# a pasc extension (fpc rejects it): the program must run and
			# print what X.out says
			want = {}
			exp = open(src[:-2] + '.out', 'rb').read() if os.path.exists(src[:-2] + '.out') else b''
			if s != 0 or o != exp:
				probs.append('extension failed (status %s): %s %s' % (s, o[:200], e[:200]))
		else:
			want = fpc_result(tmp, name, src, inp, refresh)
		if name.startswith(('restr_', 'ext_')):
			pass
		elif 'compile' in want:
			m = re.search(r'\((\d+)', want['compile'])
			wl = m.group(1) if m else '?'
			m = re.match(r'[^:]*:(\d+):\d+: error', e)
			if not m:
				probs.append('fpc: %s; pasc accepted it (status %s)' % (want['compile'], s))
			elif m.group(1) != wl:
				probs.append('error line %s vs fpc %s\n   pasc: %s\n   fpc:  %s' % (m.group(1), wl, e.strip().splitlines()[0], want['compile']))
			elif verbose:
				probs.append(None)
				print('      pasc: %s\n      fpc:  %s' % (e.strip().splitlines()[0], want['compile']))
		else:
			if re.match(r'[^:]*:(\d+):\d+: error', e):
				probs.append('pasc rejects: ' + e.strip().splitlines()[0])
			else:
				if o.decode('latin-1') != want['out']:
					probs.append('stdout differs')
					if verbose:
						probs.append('--- fpc:\n' + want['out'][:3000] + '\n--- pasc:\n' + o.decode('latin-1')[:3000])
				if str(s) != str(want['status']):
					probs.append('status %s vs fpc %s %s' % (s, want['status'], e.strip()[:200]))
		probs = [p for p in probs if p]
		if probs and name in KNOWN:
			nok += 1
			print('known ' + name + ': ' + KNOWN[name])
		elif probs:
			nfail += 1
			print('FAIL ' + name + ': ' + '\n  '.join(probs))
		else:
			nok += 1
			print('ok   ' + name)
	print('%d ok, %d failed' % (nok, nfail))
	return 1 if nfail else 0

sys.exit(main())
