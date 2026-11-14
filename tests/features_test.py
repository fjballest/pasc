#!/usr/bin/env python3
"""Checks for the teaching features: stack(), the leak report and random
uninitialised memory."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'features')
PASC = os.path.join(os.path.dirname(HERE), 'pasc.py')
fail = 0

def run(*args):
	r = subprocess.run([sys.executable, PASC] + list(args), cwd=D, capture_output=True)
	return r.stdout.decode(), r.stderr.decode(), r.returncode

def check(what, cond):
	global fail
	print(('ok   ' if cond else 'FAIL ') + what)
	fail += not cond

out, err, st = run('-z', 'stack1.p')
for s in ['--- stack() at stack1.p:27 ---', 'procedure muestra, line 27',
		"p: TipoPunto = (x: 3; y: 4; c: Verde)  {parameter}", 'total: integer = 1  {var parameter}',
		"s: string = 'hola'  {parameter}", 'r: real = 2.5  {local}', 'function suma, line 35',
		'Result: integer = 0  {function result}', 'main program, line 50',
		'lista: TipoNodo = ^(v: 10; sig: ^heap', 'nums: TipoNums = [1, 4, 9', '... 8 more]',
		"nombre: String[10] = 'ana'", 'heap: 2 blocks in use (24 bytes)',
		'Memory leak: 3 blocks (36 bytes) allocated with new were never disposed:',
		'1 x TipoRNodo (12 bytes) allocated at stack1.p:51']:
	check('stack/leaks: ' + s, s in err)
check('stack1 output', out == '7\n' and st == 0)
out, err, st = run('-z', 'stack2.p')
for s in ['--- stack(2) at stack2.p:27 ---', '      p: TipoPunto = (  {parameter}', '          x: 3',
		'          c: Verde', '      lista: TipoNodo = ^heap@', '          sig: ^heap@', '              v: 20',
		'              sig: nil', '          [16] = 256', '          ... 4 more']:
	check('stack(2): ' + s, s in err)
out, err, st = run('-z', 'runs.p')
check('runs compact', 'nums: TipoNums = [0, 0, 7, 0, 0, ... 23 more, the same, 0, 9]' in err)
check('runs pretty', '          ... 23 more, the same\n          [29] = 0\n          [30] = 9' in err)
out, err, st = run('files.p')
check('file opened again', 'files.p:12: warning: file "uno.tmp" is opened again (it was first opened at line 8)' in err)
check('file not closed', 'files.p:12: warning: file "uno.tmp" was never closed' in err)
a = run('--seed', '5', 'garbage.p')[0]
b = run('--seed', '5', 'garbage.p')[0]
c = run('--seed', '6', 'garbage.p')[0]
z = run('-z', 'garbage.p')[0]
check('same seed, same garbage', a == b)
check('other seed, other garbage', a != c)
check('-z gives zeros', z == '0\n0\n')
sys.exit(1 if fail else 0)
