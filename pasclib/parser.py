"""Recursive-descent parser: tokens -> syntax tree (see ast.py)."""

from . import ast as A
from .errors import CompileError
from .lexer import tokenize

RELOPS = ('=', '<>', '<', '>', '<=', '>=')


class Parser:
	def __init__(self, src, fname):
		self.fname = fname
		self.toks = tokenize(src, fname)
		self.i = 0
		self.tok = self.toks[0]

	# token helpers
	def next(self):
		t = self.tok
		self.i += 1
		self.tok = self.toks[min(self.i, len(self.toks) - 1)]
		return t

	def peek(self, k=1):
		return self.toks[min(self.i + k, len(self.toks) - 1)]

	def error(self, msg, tok=None):
		tok = tok or self.tok
		raise CompileError(self.fname, tok.line, tok.col, msg)

	def expected(self, what):
		if self.tok.kind == 'eof':
			self.error('Unexpected end of file')
		self.error('Syntax error, "%s" expected but "%s" found' % (what, self.tok.desc()))

	def is_kw(self, *kws):
		return self.tok.kind == 'kw' and self.tok.value in kws

	def is_sym(self, *syms):
		return self.tok.kind == 'sym' and self.tok.value in syms

	def is_id(self, name=None):
		return self.tok.kind == 'id' and (name is None or self.tok.value == name)

	def expect_kw(self, kw):
		if not self.is_kw(kw):
			self.expected(kw.upper())
		return self.next()

	def expect_sym(self, s):
		if not self.is_sym(s):
			self.expected(s)
		return self.next()

	def expect_id(self):
		if self.tok.kind != 'id':
			self.expected('identifier')
		return self.next()

	def pos(self, tok=None):
		tok = tok or self.tok
		return (tok.line, tok.col)

	# program
	def parse_program(self):
		p = self.pos()
		self.expect_kw('program')
		name = self.expect_id()
		if self.is_sym('('):
			self.next()
			while True:
				self.expect_id()
				if not self.is_sym(','):
					break
				self.next()
			self.expect_sym(')')
		self.expect_sym(';')
		uses = []
		if self.is_kw('uses'):
			self.next()
			while True:
				t = self.expect_id()
				uses.append((t.value, self.pos(t), t.text))
				if not self.is_sym(','):
					break
				self.next()
			self.expect_sym(';')
		decls = self.parse_decls(toplevel=True)
		body = self.parse_compound()
		endpos = self.pos()
		self.expect_sym('.')
		return A.Program(p, name.text, uses, decls, body, endpos)

	def parse_decls(self, toplevel):
		decls = []
		while True:
			if self.is_kw('const'):
				self.next()
				decls.extend(self.parse_consts())
			elif self.is_kw('type'):
				self.next()
				decls.append(self.parse_types())
			elif self.is_kw('var'):
				self.next()
				decls.extend(self.parse_vars())
			elif self.is_kw('procedure', 'function'):
				decls.append(self.parse_routine())
			elif self.is_kw('begin'):
				return decls
			else:
				self.expected('BEGIN')

	def parse_consts(self):
		out = []
		while self.tok.kind == 'id':
			t = self.next()
			typ = None
			if self.is_sym(':'):
				self.next()
				typ = self.parse_type()
				self.expect_sym('=')
				init = self.parse_init()
			else:
				self.expect_sym('=')
				init = self.parse_expr()
			self.expect_sym(';')
			out.append(A.ConstDecl(self.pos(t), (t.value, t.text), typ, init))
		if not out:
			self.expected('identifier')
		return out

	def parse_types(self):
		# a type section is kept together so pointer types may refer
		# to types declared later in the same section
		out = []
		while self.tok.kind == 'id':
			t = self.next()
			self.expect_sym('=')
			typ = self.parse_type()
			self.expect_sym(';')
			out.append(A.TypeDecl(self.pos(t), (t.value, t.text), typ))
		if not out:
			self.expected('identifier')
		return out

	def parse_vars(self):
		out = []
		while self.tok.kind == 'id':
			p = self.pos()
			names = self.parse_idlist()
			self.expect_sym(':')
			typ = self.parse_type()
			init = None
			if self.is_sym('='):
				if len(names) > 1:
					self.error('Syntax error, ";" expected but "=" found')
				self.next()
				init = self.parse_init()
			self.expect_sym(';')
			out.append(A.VarDecl(p, names, typ, init))
		if not out:
			self.expected('identifier')
		return out

	def parse_idlist(self):
		names = []
		while True:
			t = self.expect_id()
			names.append(((t.value, t.text), self.pos(t)))
			if not self.is_sym(','):
				return names
			self.next()

	def parse_routine(self):
		kt = self.next()
		kind = kt.value
		name = self.expect_id()
		params = []
		if self.is_sym('('):
			self.next()
			if not self.is_sym(')'):
				while True:
					p = self.pos()
					mode = 'value'
					if self.is_kw('var'):
						self.next()
						mode = 'var'
					elif self.is_kw('const') or self.is_id('out') or self.is_id('constref'):
						self.error('Only value and var parameters are supported')
					names = self.parse_idlist()
					if not self.is_sym(':'):
						self.expected(':')
					self.next()
					typ = self.parse_param_type()
					params.append(A.Param(p, names, mode, typ))
					if not self.is_sym(';'):
						break
					self.next()
			self.expect_sym(')')
		rettype = None
		if kind == 'function':
			self.expect_sym(':')
			rettype = self.parse_param_type()
		elif self.is_sym(':'):
			self.error('Syntax error, ";" expected but ":" found')
		self.expect_sym(';')
		if self.tok.kind == 'id' and self.tok.value in ('forward', 'inline', 'overload', 'external', 'cdecl'):
			self.error('Procedure directives (%s) are not supported' % self.tok.text)
		decls = []
		while self.is_kw('const', 'type', 'var', 'procedure', 'function'):
			if self.is_kw('procedure', 'function'):
				self.error('Nested procedures and functions are not supported')
			if self.is_kw('const'):
				self.next()
				decls.extend(self.parse_consts())
			elif self.is_kw('type'):
				self.next()
				decls.append(self.parse_types())
			else:
				self.next()
				decls.extend(self.parse_vars())
		if not self.is_kw('begin'):
			self.expected('BEGIN')
		body = self.parse_compound()
		self.expect_sym(';')
		return A.Routine(self.pos(kt), kind, (name.value, name.text), params, rettype, decls, body)

	def parse_param_type(self):
		if self.is_kw('string'):
			t = self.next()
			if self.is_sym('['):
				self.error('Syntax error, ";" expected but "[" found')
			return A.TName(self.pos(t), ('string', 'String'))
		if self.is_kw('array'):
			self.error('Open array parameters are not supported; declare a named array type')
		t = self.expect_id()
		return A.TName(self.pos(t), (t.value, t.text))

	# types
	def parse_type(self):
		p = self.pos()
		t = self.tok
		if self.is_sym('('):
			self.next()
			names = self.parse_idlist()
			self.expect_sym(')')
			return A.TEnum(p, names)
		if self.is_sym('^'):
			self.next()
			t = self.expect_id()
			return A.TPointer(p, A.TName(self.pos(t), (t.value, t.text)))
		if self.is_kw('record'):
			self.next()
			fields = []
			while self.tok.kind == 'id':
				names = self.parse_idlist()
				self.expect_sym(':')
				ft = self.parse_type()
				fields.append((names, ft))
				if not self.is_sym(';'):
					break
				self.next()
			if self.is_kw('case'):
				self.error('Variant records are not supported')
			self.expect_kw('end')
			return A.TRecord(p, fields)
		if self.is_kw('array'):
			self.next()
			if not self.is_sym('['):
				self.error('Dynamic arrays are not supported')
			self.next()
			idx = [self.parse_type()]
			while self.is_sym(','):
				self.next()
				idx.append(self.parse_type())
			self.expect_sym(']')
			self.expect_kw('of')
			elem = self.parse_type()
			return A.TArray(p, idx, elem)
		if self.is_kw('string'):
			self.next()
			size = None
			if self.is_sym('['):
				self.next()
				size = self.parse_expr()
				self.expect_sym(']')
			return A.TString(p, size)
		if self.is_kw('set', 'file', 'packed', 'class', 'object', 'procedure', 'function'):
			self.error('%s types are not supported' % t.text.upper())
		if t.kind == 'id' and not (self.peek().kind == 'sym' and self.peek().value in
				('..', '+', '-', '*', '/', '(', '.')) and not (self.peek().kind == 'kw' and
				self.peek().value in ('div', 'mod')):
			self.next()
			return A.TName(p, (t.value, t.text))
		lo = self.parse_expr()
		if not self.is_sym('..'):
			self.expected('..')
		self.next()
		hi = self.parse_expr()
		return A.TSubrange(p, lo, hi)

	# typed constant initialisers
	def parse_init(self):
		if not self.is_sym('('):
			return self.parse_expr()
		p = self.pos()
		if self.peek().kind == 'id' and self.peek(2).kind == 'sym' and self.peek(2).value == ':':
			self.next()
			fields = []
			while self.tok.kind == 'id':
				t = self.next()
				self.expect_sym(':')
				fields.append((t.value, self.pos(t), self.parse_init()))
				if not self.is_sym(';'):
					break
				self.next()
			self.expect_sym(')')
			return A.InitRecord(p, fields)
		save = self.i
		first = None
		try:
			e = self.parse_expr()
			if self.is_sym(';', ')', ','):
				return e
			end = self.i
		except CompileError as ce:
			first = ce
			end = self.i
		self.i = save
		self.tok = self.toks[save]
		try:
			self.next()
			items = [self.parse_init()]
			while self.is_sym(','):
				self.next()
				items.append(self.parse_init())
			self.expect_sym(')')
		except CompileError as ce:
			# report the error of whichever reading got further
			if first is not None and (first.line, first.col) > (ce.line, ce.col):
				raise first
			raise
		if not self.is_sym(';', ')', ',') and end > self.i:
			self.i = save
			self.tok = self.toks[save]
			self.parse_expr()
			self.expected(';')
		return A.InitList(p, items)

	# statements
	def parse_compound(self):
		p = self.pos()
		t0 = self.i
		self.expect_kw('begin')
		stmts = self.parse_stmt_list()
		endtok = self.expect_kw('end')
		c = A.Compound(p, stmts)
		c.endline = endtok.line
		c.tok0, c.tok1 = t0, self.i
		return c

	def parse_stmt_list(self):
		stmts = [self.parse_stmt()]
		while self.is_sym(';'):
			self.next()
			stmts.append(self.parse_stmt())
		return stmts

	def parse_stmt(self):
		t0 = self.i
		st = self.parse_stmt1()
		# token range of the statement, used by the style checks
		st.tok0, st.tok1 = t0, self.i
		return st

	def parse_stmt1(self):
		p = self.pos()
		t = self.tok
		if t.kind == 'kw':
			k = t.value
			if k == 'begin':
				return self.parse_compound()
			if k == 'if':
				self.next()
				cond = self.parse_expr()
				self.expect_kw('then')
				then = self.parse_stmt()
				else_ = None
				if self.is_kw('else'):
					self.next()
					else_ = self.parse_stmt()
				return A.If(p, cond, then, else_)
			if k == 'while':
				self.next()
				cond = self.parse_expr()
				self.expect_kw('do')
				return A.While(p, cond, self.parse_stmt())
			if k == 'repeat':
				self.next()
				stmts = self.parse_stmt_list()
				self.expect_kw('until')
				return A.Repeat(p, stmts, self.parse_expr())
			if k == 'for':
				self.next()
				vt = self.expect_id()
				var = A.Name(self.pos(vt), vt.value, vt.text)
				if self.is_kw('in'):
					self.next()
					typ = self.parse_expr()
					self.expect_kw('do')
					return A.ForIn(p, var, typ, self.parse_stmt())
				self.expect_sym(':=')
				start = self.parse_expr()
				if self.is_kw('to'):
					down = False
				elif self.is_kw('downto'):
					down = True
				else:
					self.expected('TO')
				self.next()
				stop = self.parse_expr()
				self.expect_kw('do')
				return A.For(p, var, start, stop, down, self.parse_stmt())
			if k == 'case':
				return self.parse_case()
			if k in ('end', 'until', 'else'):
				return A.Empty(p)
			if k in ('with', 'goto', 'try', 'raise', 'asm'):
				self.error('%s statements are not supported' % t.text.upper())
			self.error('Illegal expression' if k != 'nil' else 'Illegal expression')
		if t.kind == 'sym' and t.value == ';':
			return A.Empty(p)
		if t.kind == 'eof':
			self.error('Unexpected end of file')
		if t.kind == 'id':
			d = self.parse_designator()
			if self.is_sym(':='):
				self.next()
				return A.Assign(p, d, self.parse_expr())
			if self.is_sym('='):
				self.error('Syntax error, ":=" expected but "=" found')
			return A.ProcCall(p, d)
		self.error('Illegal expression')

	def parse_case(self):
		p = self.pos()
		self.next()
		e = self.parse_expr()
		self.expect_kw('of')
		branches = []
		else_ = None
		while not self.is_kw('end', 'else') and not self.is_id('otherwise'):
			labels = []
			while True:
				lo = self.parse_expr()
				hi = None
				if self.is_sym('..'):
					self.next()
					hi = self.parse_expr()
				labels.append((lo, hi))
				if not self.is_sym(','):
					break
				self.next()
			self.expect_sym(':')
			st = self.parse_stmt()
			branches.append((labels, st))
			if not self.is_sym(';'):
				break
			self.next()
		if self.is_kw('else') or self.is_id('otherwise'):
			self.next()
			else_ = self.parse_stmt_list()
		self.expect_kw('end')
		if not branches:
			self.error('Syntax error, "constant" expected but "%s" found' % self.tok.desc())
		return A.Case(p, e, branches, else_)

	# expressions
	def parse_designator(self):
		t = self.expect_id()
		e = A.Name(self.pos(t), t.value, t.text)
		return self.parse_postfix(e)

	def parse_postfix(self, e):
		while True:
			if self.is_sym('.'):
				self.next()
				t = self.expect_id()
				e = A.Field(self.pos(t), e, t.value, t.text)
			elif self.is_sym('['):
				p = self.pos()
				self.next()
				idx = [self.parse_expr()]
				while self.is_sym(','):
					self.next()
					idx.append(self.parse_expr())
				self.expect_sym(']')
				e = A.Index(p, e, idx)
			elif self.is_sym('^'):
				p = self.pos()
				self.next()
				e = A.Deref(p, e)
			elif self.is_sym('('):
				p = self.pos()
				self.next()
				args = []
				if not self.is_sym(')'):
					while True:
						ap = self.pos()
						ex = self.parse_expr()
						w = d = None
						if self.is_sym(':'):
							self.next()
							w = self.parse_expr()
							if self.is_sym(':'):
								self.next()
								d = self.parse_expr()
						args.append(A.Arg(ap, ex, w, d))
						if not self.is_sym(','):
							break
						self.next()
				self.expect_sym(')')
				e = A.Call(p, e, args)
			else:
				return e

	def parse_expr(self):
		e = self.parse_simple()
		# like fpc, a = b = c means (a = b) = c
		while self.is_sym(*RELOPS) or self.is_kw('in', 'is'):
			t = self.next()
			if t.value in ('in', 'is'):
				self.error('Operator "%s" is not supported' % t.value)
			r = self.parse_simple()
			e = A.Binary(self.pos(t), t.value, e, r)
		return e

	def parse_simple(self):
		if self.is_sym('+', '-'):
			t = self.next()
			e = A.Unary(self.pos(t), t.value, self.parse_term())
		else:
			e = self.parse_term()
		while self.is_sym('+', '-') or self.is_kw('or', 'xor'):
			t = self.next()
			e = A.Binary(self.pos(t), t.value, e, self.parse_term())
		return e

	def parse_term(self):
		e = self.parse_power()
		while self.is_sym('*', '/') or self.is_kw('div', 'mod', 'and', 'shl', 'shr', 'as'):
			t = self.next()
			if t.value == 'as':
				self.error('Operator "as" is not supported')
			e = A.Binary(self.pos(t), t.value, e, self.parse_power())
		return e

	def parse_power(self):
		e = self.parse_factor()
		while self.is_sym('**'):
			t = self.next()
			e = A.Binary(self.pos(t), '**', e, self.parse_factor())
		return e

	def parse_factor(self):
		t = self.tok
		p = self.pos()
		if t.kind == 'int':
			self.next()
			return A.IntLit(p, t.value)
		if t.kind == 'real':
			self.next()
			return A.RealLit(p, t.value, t.text)
		if t.kind == 'str':
			self.next()
			return A.StrLit(p, t.value)
		if t.kind == 'id':
			return self.parse_designator()
		if t.kind == 'kw':
			if t.value == 'nil':
				self.next()
				return A.NilLit(p)
			if t.value == 'not':
				self.next()
				return A.Unary(p, 'not', self.parse_factor())
			if t.value == 'string':
				# string(...) typecast
				self.next()
				e = A.Name(p, 'string', 'String')
				return self.parse_postfix(e)
		if t.kind == 'sym':
			if t.value == '(':
				self.next()
				e = self.parse_expr()
				self.expect_sym(')')
				return self.parse_postfix_paren(e)
			if t.value in ('+', '-'):
				self.next()
				return A.Unary(p, t.value, self.parse_factor())
			if t.value == '@':
				self.next()
				return A.AddrOf(p, self.parse_factor())
			if t.value == '[':
				self.error('Set constructors are not supported')
		self.error('Illegal expression')

	def parse_postfix_paren(self, e):
		# (p)^ and similar after a parenthesised expression
		if self.is_sym('^', '.', '['):
			return self.parse_postfix(e)
		return e


def parse(src, fname):
	p = Parser(src, fname)
	prog = p.parse_program()
	prog.tokens = p.toks
	prog.source = src
	return prog
