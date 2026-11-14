#!/usr/bin/env python3
"""pascdb: watch a pasc program run, step by step, in the browser.

usage: pascdb [--port N] [--no-browser] prog.p

The page shows the source with the statement about to run, the program's
data drawn as boxes (records, arrays, linked lists through the heap), the
raw memory and the stack with its return addresses.  Step runs one source
line, entering every procedure and function; Play runs the program slowly
on its own.  pascdb uses pasc (pasclib); pasc does not need pascdb.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pasclib.errors import CompileError		# noqa: E402
from pasclib.parser import parse			# noqa: E402
from pasclib.compiler import compile_program	# noqa: E402
from pascdblib.server import serve		# noqa: E402


def usage():
	sys.stderr.write('usage: pascdb [--port N] [--no-browser] prog.p\n')
	sys.exit(2)


def main(argv):
	port = 0
	browser = True
	files = []
	i = 0
	while i < len(argv):
		a = argv[i]
		if a in ('--version', '-v'):
			from pasclib import VERSION
			print('pascdb ' + VERSION)
			return 0
		if a == '--port' and i + 1 < len(argv):
			i += 1
			port = int(argv[i])
		elif a == '--no-browser':
			browser = False
		elif a.startswith('-'):
			usage()
		else:
			files.append(a)
		i += 1
	if len(files) != 1:
		usage()
	path = files[0]
	fname = os.path.basename(path) if os.path.dirname(path) in ('', '.') else path
	try:
		with open(path, 'rb') as f:
			src = f.read().decode('latin-1')
	except OSError as e:
		sys.stderr.write('pascdb: %s: %s\n' % (path, e.strerror))
		return 1
	try:
		prog = compile_program(parse(src, fname), fname, debug=True)
	except CompileError as e:
		sys.stderr.write('%s\n' % e)
		return 1
	for w in prog.warnings:
		sys.stderr.write(w + '\n')
	return serve(prog, src, browser, port)


if __name__ == '__main__':
	sys.setrecursionlimit(10000)
	sys.exit(main(sys.argv[1:]))
