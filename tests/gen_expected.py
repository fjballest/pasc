#!/usr/bin/env python3
"""Compile every course program with fpc and record what it does, as the
reference for pasc. Writes tests/expected/<prog>.{out,err,status}."""
import os, sys, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cases

def main():
	exp = os.path.join(cases.HERE, 'expected')
	os.makedirs(exp, exist_ok=True)
	tmp = tempfile.mkdtemp(prefix='pasc-fpc-')
	names = sys.argv[1:] or cases.programs()
	for name in names:
		d = cases.fresh_dir(tmp, name)
		base = os.path.join(exp, name[:-2])
		c = subprocess.run(['fpc', '-g', '-oa.out', name], cwd=d,
			capture_output=True)
		comp = c.stdout.decode('latin-1')
		if c.returncode != 0:
			errs = [l for l in comp.splitlines() if ' Error: ' in l or ' Fatal: ' in l]
			with open(base + '.compile', 'w') as f:
				f.write('\n'.join(errs) + '\n')
			status = 'compile-error'
			out = b''; err = b''
		else:
			if os.path.exists(base + '.compile'):
				os.remove(base + '.compile')
			try:
				r = subprocess.run(['./a.out'], cwd=d, input=cases.stdin_for(name),
					capture_output=True, timeout=10)
				out, err, status = r.stdout, r.stderr, str(r.returncode)
			except subprocess.TimeoutExpired as e:
				out, err, status = e.stdout or b'', e.stderr or b'', 'timeout'
		with open(base + '.out', 'wb') as f: f.write(out)
		with open(base + '.err', 'wb') as f: f.write(err)
		with open(base + '.status', 'w') as f: f.write(status + '\n')
		print(f'{name:24} {status}')

main()
