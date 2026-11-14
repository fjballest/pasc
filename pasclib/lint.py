"""Style checks reported by pasc -w (see limits.py for the limits).

Naming checks need the symbol tables and live in compiler.py; this module
checks the program text and its structure: long lines, long bodies,
long parameter lists, duplicated routines and repeated code.
"""

from . import ast as A
from .limits import LIMITS


def lint_program(tree, prog):
	found = []
	lines_check(tree, found)
	routines = [d for d in tree.decls if isinstance(d, A.Routine)]
	for r in routines:
		size_check(r, found)
	body_check(tree.body, LIMITS.get('main_body_lines'), 'the main program', tree.body.pos, found)
	duplicates_check(tree, routines, found)
	for body in [r.body for r in routines] + [tree.body]:
		repeat_check(tree.tokens, body, found)
	if LIMITS.get('boolean_if'):
		for r in routines:
			boolean_if_check(r.body, r, found)
		boolean_if_check(tree.body, None, found)
	return found


def single(st):
	while isinstance(st, A.Compound):
		stmts = [s for s in st.stmts if not isinstance(s, A.Empty)]
		if len(stmts) != 1:
			return None
		st = stmts[0]
	return st


def bool_lit(e):
	if isinstance(e, A.Name) and e.name in ('true', 'false'):
		return e.name == 'true'
	return None


def same_target(a, b):
	return repr(a).lower() == repr(b).lower()


def all_stmts(st):
	yield st
	if isinstance(st, (A.Compound, A.Repeat)):
		for s in st.stmts:
			yield from all_stmts(s)
	elif isinstance(st, A.If):
		yield from all_stmts(st.then)
		if st.else_ is not None:
			yield from all_stmts(st.else_)
	elif isinstance(st, (A.While, A.For, A.ForIn)):
		yield from all_stmts(st.body)
	elif isinstance(st, A.Case):
		for labels, s in st.branches:
			yield from all_stmts(s)
		for s in st.else_ or []:
			yield from all_stmts(s)


def boolean_if_check(body, r, found):
	"""if c then x := true else x := false: assign c (or not c)."""
	fname = r.name[0] if r is not None and r.kind == 'function' else None
	for st in all_stmts(body):
		if not isinstance(st, A.If) or st.else_ is None:
			continue
		a, b = single(st.then), single(st.else_)
		if not (isinstance(a, A.Assign) and isinstance(b, A.Assign)):
			continue
		va, vb = bool_lit(a.expr), bool_lit(b.expr)
		if va is None or vb is None or va == vb or not same_target(a.target, b.target):
			continue
		cond = 'the condition' if va else 'the negation of the condition (not ...)'
		t = a.target
		if isinstance(t, A.Name) and (t.name == 'result' or t.name == fname):
			found.append((st.line, st.col, 'returning true or false from both branches of an if: '
				'return %s instead' % cond))
		else:
			found.append((st.line, st.col, 'assigning true or false in both branches of an if: '
				'assign %s instead' % cond))


def lines_check(tree, found):
	limit = LIMITS.get('line_length')
	if not limit:
		return
	for i, line in enumerate(tree.source.split('\n')):
		n = len(line.rstrip('\r').expandtabs(8))
		if n > limit:
			found.append((i + 1, limit + 1, 'line is %d characters long (the limit is %d)' % (n, limit)))


def kind_name(r):
	return '%s "%s"' % (r.kind, r.name[1])


def size_check(r, found):
	limit = LIMITS.get('parameters')
	n = sum(len(p.names) for p in r.params)
	if limit and n > limit:
		found.append((r.line, r.col, '%s has %d parameters (the limit is %d): '
			'consider grouping them in a record or an array' % (kind_name(r), n, limit)))
	body_check(r.body, LIMITS.get('routine_body_lines'), kind_name(r), r.pos, found)


def body_check(body, limit, what, pos, found):
	if not limit:
		return
	n = body.endline - body.line - 1
	if n > limit:
		found.append((pos[0], pos[1], 'the body of %s is %d lines long (the limit is %d): '
			'split the problem into subproblems' % (what, n, limit)))


def local_names(r):
	names = {r.name[0], 'result'}
	for p in r.params:
		for (key, text), pos in p.names:
			names.add(key)
	for d in r.decls:
		if isinstance(d, A.VarDecl):
			for (key, text), pos in d.names:
				names.add(key)
	return names


def normalized_body(tokens, r):
	"""Tokens of r's body, with its own names numbered by first use."""
	local = local_names(r)
	own = r.name[0]
	seen = {}
	out = []
	# the parameter and local types are part of what the routine does
	tkey = lambda t: repr(t).lower()
	for p in r.params:
		out.append(('param', p.mode, len(p.names), tkey(p.typ)))
	out.append(('result', tkey(r.rettype) if r.rettype is not None else None))
	out.append(('locals', tuple(sorted(tkey(d.typ) for d in r.decls if isinstance(d, A.VarDecl)
		for _ in d.names))))
	for t in tokens[r.body.tok0:r.body.tok1]:
		if t.kind == 'id' and t.value in local:
			if t.value == own:
				out.append('<self>')
			else:
				out.append(seen.setdefault(t.value, '<%d>' % len(seen)))
		else:
			out.append((t.kind, t.value))
	return out


def duplicates_check(tree, routines, found):
	limit = LIMITS.get('duplicate_min_tokens')
	if not limit:
		return
	bodies = []
	for r in routines:
		b = normalized_body(tree.tokens, r)
		ntok = r.body.tok1 - r.body.tok0
		if ntok - 2 < limit:		# not counting begin and end
			continue
		for other, ob in bodies:
			if ob == b:
				found.append((r.line, r.col, '%s does exactly the same as %s (line %d): '
					'keep only one' % (kind_name(r), kind_name(other), other.line)))
				break
		else:
			bodies.append((r, b))


def stmt_lists(st):
	"""Every statement list inside statement st."""
	if isinstance(st, A.Compound):
		yield st.stmts
		for s in st.stmts:
			yield from stmt_lists(s)
	elif isinstance(st, A.Repeat):
		yield st.stmts
		for s in st.stmts:
			yield from stmt_lists(s)
	elif isinstance(st, A.If):
		yield from stmt_lists(st.then)
		if st.else_ is not None:
			yield from stmt_lists(st.else_)
	elif isinstance(st, (A.While, A.For, A.ForIn)):
		yield from stmt_lists(st.body)
	elif isinstance(st, A.Case):
		for labels, s in st.branches:
			yield from stmt_lists(s)
		if st.else_:
			yield st.else_
			for s in st.else_:
				yield from stmt_lists(s)


def stmt_key(tokens, st):
	"""A statement's tokens; numbers may differ between repeated copies."""
	key = []
	for t in tokens[st.tok0:st.tok1]:
		if t.kind in ('int', 'real'):
			key.append('<number>')
		else:
			key.append((t.kind, t.value))
	return tuple(key)


def repeat_check(tokens, body, found):
	times = LIMITS.get('repeat_times')
	if not times:
		return
	maxgroup = LIMITS.get('repeat_max_group') or 1
	mintok = LIMITS.get('repeat_min_tokens') or 1
	for lst in stmt_lists(body):
		stmts = [s for s in lst if not isinstance(s, A.Empty)]
		keys = [stmt_key(tokens, s) for s in stmts]
		n = len(stmts)
		i = 0
		while i < n:
			step = 1
			for k in range(1, maxgroup + 1):
				unit = keys[i:i + k]
				if len(unit) < k or sum(len(u) for u in unit) < mintok:
					continue
				reps = 1
				while keys[i + reps * k:i + (reps + 1) * k] == unit:
					reps += 1
				if reps >= times:
					what = 'statement' if k == 1 else 'group of %d statements' % k
					found.append((stmts[i].line, stmts[i].col, 'the same %s is written %d times in a row: '
						'use a loop or a procedure' % (what, reps)))
					step = reps * k
					break
			i += step
