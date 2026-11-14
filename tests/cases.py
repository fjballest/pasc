"""Shared helpers for the test harness: find course programs and the
stdin each one expects (taken from the 'fpc ... && <cmd>' line in its
header comment)."""
import os, re, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(os.path.dirname(HERE))	# the course src directory
DATAFILES = ['datos', 'datos.txt', 'texto', 'guide', 'fich.txt', 'edin.txt']

def programs():
	return sorted(os.path.basename(p) for p in glob.glob(os.path.join(SRC, '*.p')))

def runcmd(name):
	with open(os.path.join(SRC, name), encoding='latin-1') as f:
		for line in f:
			if 'fpc ' in line and '&&' in line:
				return line.split('&&', 1)[1].strip()
	return 'a.out'

def stdin_for(name):
	"""Return bytes for stdin, or None for /dev/null-like empty input."""
	cmd = runcmd(name).replace('$%', name).strip('{} ')
	m = re.match(r'echo (.*?)\s*\|', cmd)
	if m:
		return (m.group(1) + '\n').encode()
	m = re.search(r'<\s*(\S+)', cmd)
	if m:
		fn = m.group(1)
		if fn == '/dev/null':
			return b''
		with open(os.path.join(SRC, fn), 'rb') as f:
			return f.read()
	return b''

def fresh_dir(base, name):
	"""A clean directory holding the program and copies of the data files."""
	d = os.path.join(base, name)
	if os.path.isdir(d):
		shutil.rmtree(d)
	os.makedirs(d)
	for fn in DATAFILES + [name]:
		p = os.path.join(SRC, fn)
		if os.path.exists(p):
			shutil.copy(p, d)
	return d
