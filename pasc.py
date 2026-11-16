#!/usr/bin/env python3
"""pasc: run a program written in the course's restricted Free Pascal.

usage: pasc [-c] [-S] [-w] [-z] [-g] [-L] [--seed N] [--stack MB] prog.p

The program is compiled to an in-memory bytecode (errors are reported as
file:line:col) and then executed.  It behaves like the program built with
	fpc {$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}
and exits with the program's halt code, or with the FPC run-time error
number after reporting it.

Uninitialised memory holds random garbage (-z: zeros, as fpc gives for
global variables).  When the program ends, memory allocated with new and
never disposed is reported.  Style warnings are reported unless -w; their limits are in
pasclib/limits.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pasclib.errors import CompileError			# noqa: E402
from pasclib.parser import parse				# noqa: E402
from pasclib.compiler import compile_program		# noqa: E402
from pasclib import vm					# noqa: E402
from pasclib import VERSION				# noqa: E402


def usage():
	sys.stderr.write('usage: pasc [-c] [-S] [-w] [-z] [-g] [-L] [--seed N] [--stack MB] prog.p\n'
		'  -c          only compile (check) the program\n'
		'  -S          print the bytecode\n'
		'  -w          do not report style warnings (limits in pasclib/limits.py)\n'
		'  -z          uninitialised memory is zero instead of random\n'
		'  -g          allow global variables before procedures and functions\n'
		'  -L          do not enforce the limits on loops and nesting (see limits.py)\n'
		'  --seed N    seed for the random contents of uninitialised memory\n'
		'  --stack MB  stack size in megabytes (default %d)\n'
		'  --version   print the version\n' % (vm.DEFAULT_STACK >> 20))
	sys.exit(2)


def compile_file(path, lint=False, early_globals=False, enforce=True):
	"""Return the compiled program, or exit after printing the errors."""
	fname = os.path.basename(path) if os.path.dirname(path) in ('', '.') else path
	try:
		with open(path, 'rb') as f:
			src = f.read().decode('latin-1')
	except OSError as e:
		sys.stderr.write('pasc: %s: %s\n' % (path, e.strerror))
		sys.exit(1)
	try:
		tree = parse(src, fname)
		prog = compile_program(tree, fname, lint, early_globals=early_globals, enforce=enforce)
	except CompileError as e:
		sys.stderr.write('%s\n' % e)
		sys.exit(1)
	for w in prog.warnings:
		sys.stderr.write(w + '\n')
	return prog


def main(argv):
	only_check = False
	dump = False
	stack = vm.DEFAULT_STACK
	lint = True
	early_globals = False
	enforce = True
	randomize = True
	seed = None
	files = []
	i = 0
	while i < len(argv):
		a = argv[i]
		if a in ('--version', '-v'):
			print('pasc ' + VERSION)
			return 0
		if a == '-c':
			only_check = True
		elif a == '-S':
			dump = True
		elif a == '-w':
			lint = False
		elif a == '-g':
			early_globals = True
		elif a == '-L':
			enforce = False
		elif a == '-z':
			randomize = False
		elif a == '--seed' and i + 1 < len(argv):
			i += 1
			try:
				seed = int(argv[i])
			except ValueError:
				usage()
		elif a == '--stack' and i + 1 < len(argv):
			i += 1
			try:
				stack = int(argv[i]) << 20
			except ValueError:
				usage()
		elif a.startswith('-') and a != '-':
			usage()
		else:
			files.append(a)
		i += 1
	if len(files) != 1:
		usage()
	prog = compile_file(files[0], lint, early_globals, enforce)
	if dump:
		print(prog.disassemble())
	if only_check or dump:
		return 0
	return vm.run(prog, stack, randomize, seed)


if __name__ == '__main__':
	sys.setrecursionlimit(10000)
	sys.exit(main(sys.argv[1:]))
