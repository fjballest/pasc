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
	for body in [r.body for r in routines] + [tree.body]:
		if LIMITS.get('begin_end'):
			begin_end_check(body, found)
		if LIMITS.get('search_loop'):
			search_loop_check(body, found)
	layout_check(tree, found)
	types = global_types(tree)
	for r in routines:
		array_param_checks(r, types, found)
	return found


# begin/end around the bodies of loops and conditionals

def begin_end_check(body, found):
	for st in all_stmts(body):
		bodies = []
		if isinstance(st, A.If):
			bodies = [('if', st.then)]
			if st.else_ is not None and not isinstance(st.else_, A.If):
				bodies.append(('else', st.else_))
		elif isinstance(st, A.While):
			bodies = [('while', st.body)]
		elif isinstance(st, (A.For, A.ForIn)):
			bodies = [('for', st.body)]
		for kw, b in bodies:
			if not isinstance(b, (A.Compound, A.Empty)):
				found.append((b.line, b.col, 'write the body of this "%s" between begin and end' % kw))
			elif isinstance(b, A.Empty):
				found.append((st.line, st.col, 'the body of this "%s" is empty' % kw))


# a for loop that keeps going after finding what it looks for

def is_bool_set(st):
	return isinstance(st, A.Assign) and bool_lit(st.expr) is not None


def indexed(e):
	while isinstance(e, (A.Field, A.Deref)):
		e = e.base
	return isinstance(e, A.Index)


def search_loop_check(body, found):
	for st in all_stmts(body):
		if not isinstance(st, (A.For, A.ForIn)):
			continue
		b = single(st.body)
		if not isinstance(b, A.If) or b.else_ is not None:
			continue
		then = b.then
		stmts = [x for x in (then.stmts if isinstance(then, A.Compound) else [then])
			if not isinstance(x, A.Empty)]
		# a flag set when something is found; setting an element of an
		# array (marking it) is not a search
		flags = [x for x in stmts if is_bool_set(x) and not indexed(x.target)]
		if stmts and all(isinstance(x, A.Assign) for x in stmts) and flags:
			found.append((st.line, st.col, 'this loop goes on after finding what it looks for: '
				'use while or repeat and stop when it is found'))


# arrays passed with an index or with a count

def global_types(tree):
	"""Type declarations of the program: name -> type node."""
	types = {}
	for d in tree.decls:
		if isinstance(d, list):
			for td in d:
				types[td.name[0]] = td.typ
	return types


def resolve(tn, types, local=None, depth=0):
	while isinstance(tn, A.TName) and depth < 20:
		k = tn.name[0]
		if local and k in local:
			tn = local[k]
		elif k in types:
			tn = types[k]
		else:
			return tn
		depth += 1
	return tn


def is_array(tn, types, local):
	return isinstance(resolve(tn, types, local), A.TArray)


def is_integer(tn, types, local):
	t = resolve(tn, types, local)
	return (isinstance(t, A.TName) and t.name[0] == 'integer') or isinstance(t, A.TSubrange)


def walk(n, parent=None):
	"""Every node under n, with its parent."""
	yield n, parent
	if isinstance(n, A.Node):
		for f in n._fields:
			v = getattr(n, f)
			for c in (v if isinstance(v, (list, tuple)) else [v]):
				if isinstance(c, tuple):
					for cc in c:
						if isinstance(cc, A.Node):
							yield from walk(cc, n)
				elif isinstance(c, A.Node):
					yield from walk(c, n)


def array_param_checks(r, types, found):
	local = {}
	for d in r.decls:
		if isinstance(d, list):
			for td in d:
				local[td.name[0]] = td.typ
	arrays = []
	ints = []
	for p in r.params:
		for (key, text), pos in p.names:
			if is_array(p.typ, types, local):
				arrays.append((key, text))
			elif is_integer(p.typ, types, local) and p.mode == 'value':
				ints.append((key, text))
	if not arrays or not ints:
		return
	nodes = list(walk(r.body))
	for ik, itext in ints:
		uses = [(n, par) for n, par in nodes if isinstance(n, A.Name) and n.name == ik]
		if not uses:
			continue
		# only ever used as a[i] on one array parameter a
		if LIMITS.get('array_index_param'):
			bases = set()
			for n, par in uses:
				if (isinstance(par, A.Index) and len(par.indexes) == 1 and par.indexes[0] is n
						and isinstance(par.base, A.Name)):
					bases.add(par.base.name)
				else:
					bases.add(None)
			if len(bases) == 1 and None not in bases:
				ak = bases.pop()
				a = dict(arrays).get(ak)
				ause = [(n, par) for n, par in nodes if isinstance(n, A.Name) and n.name == ak]
				if a and all(isinstance(par, A.Index) and par.base is n and isinstance(par.indexes[0], A.Name)
						and par.indexes[0].name == ik for n, par in ause):
					found.append((r.line, r.col, '%s only uses %s[%s]: pass that element instead of '
						'the array "%s" and the index "%s"' % (kind_name(r), a, itext, a, itext)))
					continue
		# used as the number of elements of an array parameter
		if LIMITS.get('array_count_param'):
			# index variables of array parameters: a[x]
			idxvars = {}
			for n, par in nodes:
				if isinstance(n, A.Index) and isinstance(n.base, A.Name) and n.base.name in dict(arrays) \
						and len(n.indexes) == 1 and isinstance(n.indexes[0], A.Name):
					idxvars.setdefault(n.indexes[0].name, n.base.name)
			counted = None
			for st, par in nodes:
				# for x := ... to n do ... a[x] ...
				if isinstance(st, A.For) and isinstance(st.stop, A.Name) and st.stop.name == ik \
						and st.var.name in idxvars:
					counted = idxvars[st.var.name]
				# x <= n, x < n, ... with a[x]
				elif isinstance(st, A.Binary) and st.op in ('<', '<=', '>', '>=') and \
						isinstance(st.left, A.Name) and isinstance(st.right, A.Name):
					names = {st.left.name, st.right.name}
					if ik in names:
						other = (names - {ik}).pop() if len(names) == 2 else None
						if other in idxvars:
							counted = idxvars[other]
			if counted:
				a = dict(arrays)[counted]
				found.append((r.line, r.col, '%s uses "%s" as the number of elements of "%s": keep the '
					'array and its count together in a record and pass that instead' % (kind_name(r), itext, a)))


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


# loops and nesting

LOOPS = (A.While, A.Repeat, A.For, A.ForIn)
CONTROL = LOOPS + (A.If, A.Case)


def children(st):
	"""The statements directly inside st, and whether each is an 'else
	if' (which continues st instead of nesting in it)."""
	if isinstance(st, (A.Compound, A.Repeat)):
		return [(s, False) for s in st.stmts]
	if isinstance(st, A.If):
		out = [(st.then, False)]
		if st.else_ is not None:
			out.append((st.else_, isinstance(st.else_, A.If)))
		return out
	if isinstance(st, (A.While, A.For, A.ForIn)):
		return [(st.body, False)]
	if isinstance(st, A.Case):
		return [(s, False) for labels, s in st.branches] + [(s, False) for s in st.else_ or []]
	return []


def structure_findings(tree):
	"""(line, col, message, limit) for every routine and the main program
	going over the 'loops', 'nested_loops', 'nested_structures' or
	'consecutive_ifs' limits.  These are errors when the limit is in
	LIMITS['enforced'] (see compiler.compile_program), else warnings."""
	found = []
	for r in tree.decls:
		if isinstance(r, A.Routine):
			structure_check(r.body, kind_name(r), r.pos, found)
	structure_check(tree.body, 'the main program', tree.body.pos, found)
	return found


def structure_check(body, what, pos, found):
	"""Too many loops, loops nested too deep, control structures nested
	too deep and too many ifs in a row, in one routine or the main program."""
	max_loops = LIMITS.get('loops')
	max_loop_depth = LIMITS.get('nested_loops')
	max_depth = LIMITS.get('nested_structures')
	max_ifs = LIMITS.get('consecutive_ifs')
	loops = []

	def visit(st, depth, ldepth):
		if isinstance(st, CONTROL):
			depth += 1
			if max_depth and depth == max_depth + 1:
				found.append((st.line, st.col, 'control structures nested %d deep in %s (the limit is %d): '
					'move the inner part to a procedure or function' % (depth, what, max_depth), 'nested_structures'))
		if isinstance(st, LOOPS):
			loops.append(st)
			ldepth += 1
			if max_loop_depth and ldepth == max_loop_depth + 1:
				found.append((st.line, st.col, 'loops nested %d deep in %s (the limit is %d): '
					'move the inner loop to a procedure or function' % (ldepth, what, max_loop_depth), 'nested_loops'))
		for c, continues in children(st):
			visit(c, depth - 1 if continues else depth, ldepth)

	visit(body, 0, 0)
	if max_loops and len(loops) > max_loops:
		found.append((pos[0], pos[1], '%s has %d loops (the limit is %d): '
			'split the problem into subproblems' % (what, len(loops), max_loops), 'loops'))
	if max_ifs:
		for stmts in stmt_lists(body):
			run = []
			for st in stmts + [None]:
				if isinstance(st, A.If):
					run.append(st)
					continue
				if not isinstance(st, A.Empty):
					if len(run) > max_ifs:
						found.append((run[0].line, run[0].col, '%d if statements in a row (the limit is %d): '
							'use if ... else if ..., a case, or a procedure' % (len(run), max_ifs), 'consecutive_ifs'))
					run = []


def layout_check(tree, found):
	"""Where begin, end and else go: 'end' and 'else' on different lines
	(else right under the end), begin and end of a block on different
	lines (a case branch may be a short begin ... end on one line), and
	begin at the end of the line of its then, do or else (a
	case branch may have begin on a line of its own)."""
	toks = tree.tokens
	kw = lambda t, *w: t.kind == 'kw' and t.value in w
	for i in range(1, len(toks)):
		t, prev = toks[i], toks[i - 1]
		if LIMITS.get('else_own_line') and kw(t, 'else') and kw(prev, 'end') and t.line == prev.line:
			found.append((t.line, t.col, 'write else on its own line, right under the end'))
		if LIMITS.get('begin_same_line') and kw(t, 'begin') and kw(prev, 'then', 'do', 'else') \
				and t.line != prev.line:
			found.append((t.line, t.col, 'write begin at the end of the line of its %s' % prev.value))
	if LIMITS.get('begin_end_lines'):
		for n, parent in walk(tree):
			if isinstance(n, A.Compound) and n.line == n.endline and not isinstance(parent, A.Case):
				found.append((n.line, n.col, 'write begin and end on different lines'))


# anonymous types

KINDS = {A.TArray: 'array', A.TRecord: 'record', A.TSubrange: 'subrange',
	A.TEnum: 'enumeration', A.TPointer: 'pointer'}


def named(t):
	"""Named, or a string[n], which may be written in place."""
	return isinstance(t, (A.TName, A.TString))


def anonymous_types(tree):
	"""(line, col, message, 'named_types') for every type written in
	place instead of declared with a name: in a variable or typed
	constant, a record field or an array element.  Subranges may be
	written in place as array indexes, and string[n] anywhere."""
	found = []
	if not LIMITS.get('named_types'):
		return found

	def anon(t):
		found.append((t.line, t.col, 'declare a type for this %s and use its name '
			'(anonymous types are not allowed)' % KINDS.get(type(t), 'type'), 'named_types'))

	def inside(t):
		if isinstance(t, A.TArray):
			for ix in t.indexes:
				if not (named(ix) or isinstance(ix, A.TSubrange)):
					anon(ix)
			if not named(t.elem):
				anon(t.elem)
		elif isinstance(t, A.TRecord):
			for names, ft in t.fields:
				if not named(ft):
					anon(ft)

	def decls(ds):
		for d in ds:
			if isinstance(d, list):		# a type section
				decls(d)
			elif isinstance(d, A.TypeDecl):
				inside(d.typ)
			elif isinstance(d, (A.VarDecl, A.ConstDecl)) and d.typ is not None and not named(d.typ):
				anon(d.typ)
			elif isinstance(d, A.Routine):
				decls(d.decls)

	decls(tree.decls)
	return found
