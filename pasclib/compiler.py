"""Type checker and bytecode generator.

compile_program(tree, fname) checks a parsed program against the
restricted FPC objfpc dialect used in the course and produces a
code.Program.  Every check that FPC performs at compile time for this
subset (types, $V+ string parameters, constant range checks, for-loop
variables, ...) is an error here too.
"""

import math
import struct

from . import ast as A
from . import code as C
from . import types as T
from .errors import CompileError
from .fmt import arctan, to_single
from .limits import LIMITS

IO_BUILTINS = frozenset('write writeln read readln eof eoln assign reset rewrite close'.split())

LABEL = -1

INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


class Sym:
	def __init__(self, kind, name, typ=None, **kw):
		self.kind = kind	# const var type routine builtin program unit
		self.name = name	# source spelling
		self.type = typ
		self.value = None
		self.where = None	# vars: ('g', addr) ('l', off) ('r', off)
		self.locked = 0		# for-loop control variable
		self.__dict__.update(kw)


class Ex:
	"""A checked expression: its type, folded constant and code."""
	def __init__(self, typ, const=None, vcode=None, acode=None):
		self.type = typ
		self.const = const
		self.vcode = vcode	# pushes the value (address, for structured types)
		self.acode = acode	# pushes the address, for designators
		self.assignable = False
		self.sym = None
		self.istype = None	# set when the expression names a type
		self.isproc = False


class Routine:
	def __init__(self, sym, info):
		self.sym = sym
		self.info = info
		self.frame = 0
		self.tempmark = 0
		self.maxframe = 0
		self.result = None
		self.resultset = False
		self.io = None		# first input/output done by the routine
		self.wio = None		# first output (write/writeln) done by it
		self.uses = {}		# var parameter -> references
		self.whole = {}		# var parameter -> whole assignments

	def alloc(self, size):
		off = self.frame
		self.frame += size
		self.maxframe = max(self.maxframe, self.frame)
		return off


class Compiler:
	def __init__(self, fname, lint=False, debug=False, early_globals=False):
		self.fname = fname
		self.early_globals = early_globals	# -g: globals before routines
		self.debug = debug		# emit LINE instructions for pascdb
		self.lint = lint
		self.lints = []			# style warnings (pasc -w)
		self.casewarned = set()
		self.prog = C.Program(fname)
		self.nlabels = 0
		self.line = 0
		self.col = 0
		self.uses_math = False
		self.code = []			# instruction list for the whole program
		self.warnings = []
		self.glob = 16			# next free global address
		self.image = bytearray(64)
		self.system = {}
		self.scopes = [self.system]
		self.progname = None
		self.globscope = None
		self.rt = None
		self.init_system()

	# diagnostics
	def error(self, msg, node=None):
		if node is not None:
			raise CompileError(self.fname, node.line, node.col, msg)
		raise CompileError(self.fname, self.line, self.col, msg)

	def warn(self, msg, node):
		self.warnings.append('%s:%d:%d: warning: %s' % (self.fname, node.line, node.col, msg))

	def style(self, msg, pos):
		self.lints.append((pos[0], pos[1], msg))

	def check_case(self, sym, node):
		"""Style: a name must be written as it was declared."""
		if not self.lint or not LIMITS.get('consistent_case') or not getattr(sym, 'user', False):
			return
		text = getattr(node, 'text', None)
		if text is None and isinstance(node, A.TName):
			text = node.name[1]
		if text is None or text == sym.name or getattr(sym, 'isresult', False):
			return
		k = (id(sym), text)
		if k not in self.casewarned:
			self.casewarned.add(k)
			self.style('"%s" is declared as "%s"; write it the same way' % (text, sym.name), node.pos)

	def check_name(self, sym, pos, what=None):
		"""Style: naming conventions for a new declaration."""
		if not self.lint:
			return
		name = sym.name
		kind = what or sym.kind
		if kind == 'var' and getattr(sym, 'typedconst', False):
			kind = 'const'
		if kind == 'const' and LIMITS.get('const_uppercase') and not name[0].isupper():
			self.style('constant "%s" should start with an uppercase letter' % name, pos)
		elif kind == 'type' and LIMITS.get('type_uppercase') and not name[0].isupper():
			self.style('type "%s" should start with an uppercase letter' % name, pos)
		elif kind in ('var', 'field') and LIMITS.get('var_lowercase') and name != name.lower():
			what = 'field' if kind == 'field' else ('parameter' if getattr(sym, 'param', None) else 'variable')
			self.style('%s "%s" should be written in lowercase' % (what, name), pos)
		elif kind == 'routine' and LIMITS.get('routine_lowercase') and name != name.lower():
			self.style('%s "%s" should be written in lowercase' % (sym.node.kind, name), pos)

	halt_after = False	# a halt follows in the statement list being compiled

	def io(self, node, what):
		"""Record input/output done by the routine being compiled.
		Writing an error message right before halt does not count."""
		rt = self.rt
		if rt is None or rt.sym is None:
			return
		soft = what in ('write', 'writeln') or what.endswith('which writes output')
		if what in ('write', 'writeln') and self.halt_after:
			return
		if soft:
			# output in a function is permitted, for debugging, with a warning
			if rt.sym.type is not None:
				self.warn('function "%s" writes output (%s): fine for debugging, '
					'but functions should not do input/output' % (rt.sym.name, what), node)
			if rt.wio is None:
				rt.wio = what
			return
		if rt.sym.type is not None:
			self.error('Functions must not do input/output (%s); use a procedure' % what, node)
		if rt.io is None:
			rt.io = what

	def at(self, node):
		self.line, self.col = node.line, node.col

	def incompatible(self, got, want, node=None):
		self.error('Incompatible types: got "%s" expected "%s"' % (got.name, want.name), node)

	def newlabel(self):
		self.nlabels += 1
		return self.nlabels

	# scopes and symbols
	def init_system(self):
		s = self.system
		for name, t in (('integer', T.INTEGER), ('char', T.CHAR), ('boolean', T.BOOLEAN),
				('real', T.REAL), ('text', T.TEXT), ('string', T.STRING)):
			s[name] = Sym('type', name, t)
		for name, v in (('false', 0), ('true', 1)):
			c = Sym('const', name, T.BOOLEAN)
			c.value = v
			s[name] = c
		for name in ('write writeln read readln eof eoln assign reset rewrite close '
				'halt ord chr succ pred low high length setlength val sqr sqrt abs '
				'sin cos arctan exp ln frac int odd pi random randomize '
				'trunc round new dispose stack').split():
			s[name] = Sym('builtin', name)
		# standard text files live at fixed global addresses (see vm.py)
		for name, addr in (('output', 16), ('input', 24)):
			v = Sym('var', name, T.TEXT)
			v.where = ('g', addr)
			s[name] = v
		self.glob = 32

	def math_scope(self):
		m = {}
		m['float'] = Sym('type', 'float', T.REAL)
		m['intpower'] = Sym('builtin', 'intpower')
		return m

	def lookup(self, name, node=None):
		for sc in reversed(self.scopes):
			if name in sc:
				return sc[name]
		self.error('Identifier not found "%s"' % (node.text if node is not None and hasattr(node, 'text') else name), node)

	def use(self, name, node):
		"""lookup() for a name written in the program (style checked)."""
		s = self.lookup(name, node)
		self.check_case(s, node)
		return s

	def find(self, name):
		for sc in reversed(self.scopes):
			if name in sc:
				return sc[name]
		return None

	def declare(self, key, sym, pos):
		sc = self.scopes[-1]
		if key in sc:
			raise CompileError(self.fname, pos[0], pos[1], 'Duplicate identifier "%s"' % sym.name)
		if sc is self.globscope and self.progname == key and sym.kind != 'routine':
			raise CompileError(self.fname, pos[0], pos[1], 'Duplicate identifier "%s"' % sym.name)
		sc[key] = sym
		sym.user = True
		if not getattr(sym, 'isresult', False):
			self.check_name(sym, pos)
		return sym

	# memory
	def alloc_global(self, size):
		addr = self.glob
		self.glob += size
		if len(self.image) < self.glob:
			self.image.extend(bytes(self.glob - len(self.image) + 1024))
		return addr

	def alloc_var(self, t):
		if self.rt is None or self.rt.sym is None:
			return ('g', self.alloc_global(t.size))
		return ('l', self.rt.alloc(t.size))

	def temp(self, size):
		return self.rt.alloc(size)

	# types
	def resolve_type(self, tn, name=None):
		self.at(tn)
		if isinstance(tn, A.TName):
			key, text = tn.name
			if key == 'string':
				return T.STRING
			s = self.find(key)
			if s is None:
				self.error('Identifier not found "%s"' % text, tn)
			if s.kind != 'type':
				self.error('Type identifier expected', tn)
			self.check_case(s, tn)
			if s.type is None:
				self.error('Type "%s" is not completely defined' % text, tn)
			return s.type
		if isinstance(tn, A.TString):
			if tn.size is None:
				return T.STRING
			n = self.const_int(tn.size)
			if n < 1 or n > 255:
				self.error('string length must be a value from 1 to 255', tn.size)
			return T.StringType(n)
		if isinstance(tn, A.TEnum):
			names = [text for (key, text), pos in tn.names]
			et = T.OrdType('enum', 0, len(names) - 1, name or 'enum', names=names)
			for i, ((key, text), pos) in enumerate(tn.names):
				c = Sym('const', text, et)
				c.value = i
				self.declare(key, c, pos)
			return et
		if isinstance(tn, A.TSubrange):
			lo = self.const_expr(tn.lo)
			hi = self.const_expr(tn.hi)
			if not (lo.type.is_ord and hi.type.is_ord):
				self.error('Ordinal expression expected', tn)
			if lo.type.root() != hi.type.root():
				self.incompatible(hi.type, lo.type, tn.hi)
			if lo.const > hi.const:
				self.error('High range limit < low range limit', tn)
			base = lo.type.base
			while base.base is not base:
				base = base.base
			if base.kind == 'int':
				base = T.INTEGER if lo.const >= INT32_MIN and hi.const <= INT32_MAX else T.INT64
			return T.OrdType(base.kind, lo.const, hi.const, name or '%s..%s' % (lo.const, hi.const), base=base)
		if isinstance(tn, A.TArray):
			elem = self.resolve_type(tn.elem) if len(tn.indexes) == 1 else None
			if len(tn.indexes) > 1:
				sub = A.TArray(tn.pos, tn.indexes[1:], tn.elem)
				elem = self.resolve_type(sub)
			idx = self.resolve_type(tn.indexes[0])
			if not idx.is_ord:
				self.error('Ordinal type expected', tn.indexes[0])
			if idx.is_int and idx.base is idx:
				self.error('Array index type is too large (use a subrange)', tn.indexes[0])
			at = T.ArrayType(idx, elem, name)
			if at.size > (1 << 31):
				self.error('Data element too large', tn)
			return at
		if isinstance(tn, A.TRecord):
			fields = []
			seen = set()
			for names, ft in tn.fields:
				t = self.resolve_type(ft)
				for (key, text), pos in names:
					if key in seen:
						raise CompileError(self.fname, pos[0], pos[1], 'Duplicate identifier "%s"' % text)
					seen.add(key)
					self.check_name(Sym('var', text), pos, 'field')
					fields.append((key, text, t))
			return T.RecordType(fields, name)
		if isinstance(tn, A.TPointer):
			key, text = tn.target.name
			s = self.find(key)
			if s is not None and s.kind == 'type' and s.type is not None:
				return T.PointerType(s.type, name)
			if self.pending is not None and key in self.pending:
				pt = T.PointerType(None, name)
				self.forwards.append((pt, key, tn.target))
				return pt
			self.error('Identifier not found "%s"' % text, tn.target)
		self.error('Error in type definition', tn)

	def type_section(self, decls):
		self.pending = {d.name[0] for d in decls}
		self.forwards = []
		for d in decls:
			key, text = d.name
			sym = Sym('type', text, None)
			t = self.resolve_type(d.typ, text)
			alias = isinstance(d.typ, A.TName) or (isinstance(d.typ, A.TString) and d.typ.size is None)
			if not alias:
				if t.is_pointer:
					t._name = text
				else:
					t.name = text
			sym.type = t
			self.declare(key, sym, d.pos)
			self.pending.discard(key)
		for pt, key, tn in self.forwards:
			s = self.find(key)
			if s is None or s.kind != 'type':
				self.error('Identifier not found "%s"' % tn.name[1], tn)
			pt.target = s.type
		self.pending = None

	pending = None

	# constants
	def const_expr(self, e):
		x = self.expr(e)
		if x.const is None:
			self.error('Illegal expression (a constant is required)', e)
		return x

	def const_int(self, e):
		x = self.const_expr(e)
		if not x.type.is_ord:
			self.error('Ordinal expression expected', e)
		return x.const

	def check_range(self, value, t, node):
		if t.is_ord and not (t.lo <= value <= t.hi):
			self.error('range check error while evaluating constants (%d must be between %d and %d)'
				% (value, t.lo, t.hi), node)

	def pack(self, t, v, node):
		"""Bytes for a constant v of type t (typed constant images)."""
		if t.is_ord:
			return struct.pack('<' + t.mk, v)
		if t.is_real:
			return struct.pack('<d', v)
		if t.is_pointer:
			return bytes(8)
		self.error('Illegal expression', node)

	def init_image(self, t, init):
		"""Initial memory image of a typed constant or initialised variable."""
		self.at(init)
		if t.is_record:
			if not isinstance(init, A.InitRecord):
				self.error('Syntax error, "(" expected', init)
			buf = bytearray(t.size)
			order = list(t.fields)
			last = -1
			for key, pos, sub in init.fields:
				if key not in t.fields:
					raise CompileError(self.fname, pos[0], pos[1], 'Unknown record field identifier "%s"' % key)
				k = order.index(key)
				if k <= last:
					raise CompileError(self.fname, pos[0], pos[1], 'Some fields coming before "%s" were not initialized' % key)
				last = k
				off, ft, _ = t.fields[key]
				buf[off:off + ft.size] = self.init_image(ft, sub)
			return bytes(buf)
		if t.is_array:
			if t.is_chararray() and not isinstance(init, A.InitList):
				x = self.const_expr(init)
				s = self.as_bytes(x, init)
				if len(s) > t.count:
					self.error('Constant strings can\'t be longer than 255 chars' if t.count > 255
						else 'Expect %d array elements, but got %d' % (t.count, len(s)), init)
				return s + bytes(t.count - len(s))
			items = init.items if isinstance(init, A.InitList) else [init]
			if len(items) != t.count:
				self.error('Expect %d array elements, but got %d' % (t.count, len(items)), init)
			return b''.join(self.init_image(t.elem, it) for it in items)
		if isinstance(init, (A.InitList, A.InitRecord)):
			self.error('Syntax error, illegal initialisation of %s' % t.name, init)
		x = self.const_expr(init)
		if t.is_string:
			s = self.as_bytes(x, init)[:t.maxlen]
			return bytes([len(s)]) + s + bytes(t.maxlen - len(s))
		v = self.convert_const(x, t, init)
		return self.pack(t, v, init)

	def as_bytes(self, x, node):
		if x.type.is_string:
			return x.const
		if x.type.is_char:
			return bytes([x.const])
		self.incompatible(x.type, T.STRING, node)

	def convert_const(self, x, t, node):
		"""Value of constant x assigned to type t, checked."""
		if t.is_ord:
			if not x.type.is_ord or x.type.root() != t.root():
				self.incompatible(x.type, t, node)
			self.check_range(x.const, t, node)
			return x.const
		if t.is_real:
			if x.type.is_real:
				return x.const
			if x.type.is_int:
				return float(x.const)
			self.incompatible(x.type, t, node)
		if t.is_pointer:
			if x.type.is_nil:
				return 0
		self.incompatible(x.type, t, node)

	# declarations
	def declarations(self, decls):
		for d in decls:
			if isinstance(d, list):
				self.type_section(d)
			elif isinstance(d, A.ConstDecl):
				self.const_decl(d)
			elif isinstance(d, A.VarDecl):
				self.var_decl(d)
			elif isinstance(d, A.Routine):
				self.routine(d)

	def const_decl(self, d):
		key, text = d.name
		self.at(d)
		if d.typ is None:
			x = self.const_expr(d.init)
			sym = Sym('const', text, x.type)
			sym.value = x.const
			self.declare(key, sym, d.pos)
			return
		t = self.resolve_type(d.typ)
		if t.is_file:
			self.error('Typed constants of type Text are not allowed', d)
		img = self.init_image(t, d.init)
		addr = self.alloc_global(t.size)
		self.image[addr:addr + t.size] = img
		self.prog.init_ranges.append((addr, t.size))
		sym = Sym('var', text, t)
		sym.where = ('g', addr)
		sym.typedconst = True
		# unlike fpc, the value of a typed constant may be used in later
		# constant expressions (typed constants are read-only here)
		if (t.is_ord or t.is_real or t.is_string) and not isinstance(d.init, (A.InitList, A.InitRecord)):
			x = self.const_expr(d.init)
			sym.value = self.as_bytes(x, d.init)[:t.maxlen] if t.is_string else self.convert_const(x, t, d.init)
		self.declare(key, sym, d.pos)

	def var_decl(self, d):
		t = self.resolve_type(d.typ)
		for (key, text), pos in d.names:
			sym = Sym('var', text, t)
			if d.init is not None:
				if t.is_file:
					self.error('Text variables cannot be initialised', d)
				img = self.init_image(t, d.init)
				if self.rt is None or self.rt.sym is None:
					addr = self.alloc_global(t.size)
					self.image[addr:addr + t.size] = img
					self.prog.init_ranges.append((addr, t.size))
					sym.where = ('g', addr)
				else:
					src = self.alloc_global(t.size)
					self.image[src:src + t.size] = img
					self.prog.init_ranges.append((src, t.size))
					sym.where = ('l', self.rt.alloc(t.size))
					self.rt.inits.append((sym.where[1], src, t.size))
			else:
				sym.where = self.alloc_var(t)
			self.declare(key, sym, pos)
			if sym.where[0] == 'g':
				self.prog.globals.append((text, sym.where[1], t))
			else:
				self.rt.info.vars.append((text, 'local', sym.where, t))

	def unchanged_params(self, r, params):
		"""Value parameters of array or record type that r's body cannot change."""
		from .lint import walk
		cands = {pk for pk, ptext, pos, mode, t in params
			if mode == 'value' and (t.is_array or t.is_record)}
		if not cands:
			return set()

		def root(e):
			while isinstance(e, (A.Field, A.Index)):
				e = e.base
			return e.name if isinstance(e, A.Name) else None

		changed = set()
		for n, par in walk(r.body):
			if isinstance(n, A.Assign):
				changed.add(root(n.target))
			elif isinstance(n, A.AddrOf):
				changed.add(root(n.expr))
			elif isinstance(n, (A.Call, A.ProcCall)):
				c = n.call if isinstance(n, A.ProcCall) else n
				if not isinstance(c, A.Call) or not isinstance(c.func, A.Name):
					continue
				s = self.find(c.func.name)
				if c.func.name == r.name[0]:
					modes = [m for pk, pt, pp, m, t in params]
				elif s is not None and s.kind == 'routine':
					modes = [p[3] for p in s.params]
				else:
					modes = ['var'] * len(c.args)	# builtins: be conservative
				for a, m in zip(c.args, modes):
					if m == 'var':
						changed.add(root(a.expr))
		return cands - changed

	def param_type(self, tn):
		t = self.resolve_type(tn)
		return t

	def routine(self, r):
		key, text = r.name
		self.at(r)
		info = C.RoutineInfo(text, r.kind)
		info.line = r.line
		info.index = len(self.prog.routines)
		self.prog.routines.append(info)
		params = []
		for p in r.params:
			t = self.param_type(p.typ)
			if t.is_file and p.mode != 'var':
				self.error('Typed files and text files must be var parameters', p)
			for (pk, ptext), pos in p.names:
				params.append((pk, ptext, pos, p.mode, t))
		ret = None
		if r.kind == 'function':
			ret = self.param_type(r.rettype)
			if ret.is_file:
				self.error('Illegal function result type', r.rettype)
		sym = Sym('routine', text, ret, params=params, info=info, node=r, does_io=None)
		self.declare(key, sym, r.pos)
		self.scopes.append({})
		ctx = Routine(sym, info)
		ctx.inits = []
		saved = self.rt
		self.rt = ctx
		unchanged = self.unchanged_params(r, params)
		for pk, ptext, pos, mode, t in params:
			if pk == 'result' and ret is not None:
				self.error('Duplicate identifier "result"', r.body)
			ps = Sym('var', ptext, t)
			if mode == 'var':
				ps.where = ('r', ctx.alloc(8))
				info.params.append(('ref', ps.where[1], None))
			elif pk in unchanged:
				# an array or record the routine never changes is passed by
				# reference: same meaning, but no copy (and no stack overflow)
				ps.where = ('r', ctx.alloc(8))
				info.params.append(('ref', ps.where[1], None))
			else:
				ps.where = ('l', ctx.alloc(t.size))
				if t.is_string:
					info.params.append(('str', ps.where[1], t.maxlen))
				elif t.structured():
					info.params.append(('copy', ps.where[1], t.size))
				else:
					info.params.append(('val', ps.where[1], t.mk))
			ps.param = mode
			self.declare(pk, ps, pos)
			info.vars.append((ptext, 'var param' if mode == 'var' else 'param', ps.where, t))
		if ret is not None:
			rs = Sym('var', 'Result', ret)
			if ret.structured() and not ret.is_string:
				rs.where = ('r', ctx.alloc(8))
				info.params.append(('ref', rs.where[1], None))
				info.result = ('none', 0, None)
			else:
				rs.where = ('l', ctx.alloc(ret.size))
				if ret.is_string:
					info.result = ('str', rs.where[1], None)
				else:
					info.result = ('val', rs.where[1], ret.mk)
			rs.isresult = True
			self.declare('result', rs, r.pos)
			ctx.result = rs
			info.vars.append(('Result', 'result', rs.where, ret))
		info.params.reverse()
		self.declarations(r.decls)
		ctx.tempmark = ctx.frame
		lab = self.newlabel()
		info.entry_label = lab
		body = [(LABEL, lab, r.line)]
		for off, src, size in ctx.inits:
			body += [(C.LADDR, off, r.line), (C.GADDR, src, r.line), (C.COPY, size, r.line)]
		body += self.stmt(r.body)
		if self.debug:
			body.append(self.line_op(r.body.endline, 1))
		body.append((C.RET, info.index, r.body.endline))
		if ret is not None and not ctx.resultset:
			self.warn('Function result does not seem to be set', r)
		sym.does_io = ctx.io
		sym.does_write = ctx.wio
		vps = [p for p in self.scopes[-1].values() if getattr(p, 'param', None) == 'var']
		if ret is None and ctx.io is None and ctx.wio is None and len(vps) == 1:
			p = vps[0]
			w = ctx.whole.get(p, 0)
			if w and ctx.uses.get(p, 0) == w:
				self.warn('procedure "%s" only computes a value for var parameter "%s": '
					'it should be a function' % (text, p.name), r)
		info.framesize = ctx.maxframe
		self.code.extend(body)
		self.rt = saved
		self.scopes.pop()

	# expressions
	def expr(self, e):
		"""Check expression e; return an Ex with its code."""
		m = getattr(self, 'x_' + type(e).__name__)
		line = e.line
		self.at(e)
		x = m(e)
		if x.const is not None and x.vcode is None:
			x.vcode = [(C.PUSH, x.const, line)]
		return x

	def x_IntLit(self, e):
		t = T.INTEGER if INT32_MIN <= e.value <= INT32_MAX else T.INT64
		if e.value > T.INT64_MAX:
			self.error('Overflow in arithmetic operation', e)
		return Ex(t, e.value)

	def x_RealLit(self, e):
		v = e.value
		if math.isinf(v):
			self.error('Error in constant real "%s"' % e.text, e)
		if to_single(v) == v:
			return Ex(T.SINGLE, v)
		return Ex(T.REAL, v)

	def x_StrLit(self, e):
		if len(e.value) == 1:
			return Ex(T.CHAR, e.value[0])
		if len(e.value) > 255:
			self.error('String exceeds 255 characters', e)
		return Ex(T.STRING, e.value)

	def x_NilLit(self, e):
		return Ex(T.NIL, 0)

	def var_code(self, sym, line):
		"""acode and vcode for a variable symbol."""
		kind, off = sym.where
		t = sym.type
		if kind == 'g':
			acode = [(C.GADDR, off, line)]
			vcode = self.load_code(acode, t, line, ('g', off))
		elif kind == 'l':
			acode = [(C.LADDR, off, line)]
			vcode = self.load_code(acode, t, line, ('l', off))
		else:
			acode = [(C.LDL, ('Q', off), line)]
			vcode = self.load_code(acode, t, line)
		return acode, vcode

	def load_code(self, acode, t, line, direct=None):
		if t.is_string:
			return acode + [(C.LDS, None, line)]
		if t.structured():
			return acode
		if t.is_file:
			return acode
		mk = t.mk
		if direct is not None:
			if direct[0] == 'g':
				return [(C.LDG, (mk, direct[1]), line)]
			return [(C.LDL, (mk, direct[1]), line)]
		return acode + [(C.LD, mk, line)]

	def x_Name(self, e):
		s = self.use(e.name, e)
		if s.kind == 'const':
			return Ex(s.type, s.value)
		if s.kind == 'var':
			acode, vcode = self.var_code(s, e.line)
			tc = getattr(s, 'typedconst', False)
			if getattr(s, 'param', None) == 'var' and self.rt is not None:
				self.rt.uses[s] = self.rt.uses.get(s, 0) + 1
			if tc and s.value is not None:
				x = Ex(s.type, s.value, None, acode)
			else:
				x = Ex(s.type, None, vcode, acode)
			x.assignable = not tc
			x.sym = s
			return x
		if s.kind == 'type':
			x = Ex(s.type)
			x.istype = s.type
			return x
		if s.kind in ('routine', 'builtin'):
			return self.call(e, s, [], e)
		if s.kind == 'program':
			self.error('Illegal expression', e)
		self.error('Illegal expression', e)

	def x_Field(self, e):
		b = self.expr(e.base)
		if not b.type.is_record or b.istype:
			self.error('Illegal qualifier', e)
		if e.name not in b.type.fields:
			self.error('identifier idents no member "%s"' % e.text, e)
		off, ft, _ = b.type.fields[e.name]
		base = b.acode if b.acode is not None else b.vcode
		acode = base + ([(C.ADDI, off, e.line)] if off else [])
		x = Ex(ft, None, self.load_code(acode, ft, e.line), acode)
		x.assignable = b.assignable
		x.sym = b.sym
		return x

	def x_Index(self, e):
		b = self.expr(e.base)
		x = b
		for k, ie in enumerate(e.indexes):
			x = self.index1(x, ie, e)
		return x

	def index1(self, b, ie, e):
		t = b.type
		if b.istype:
			self.error('Illegal qualifier', e)
		i = self.expr(ie)
		if t.is_string:
			idx = T.OrdType('int', 0, t.maxlen, 'idx', base=T.INTEGER)
			et = T.CHAR
		elif t.is_array:
			idx = t.index
			et = t.elem
		else:
			self.error('Illegal qualifier', e)
		if not i.type.is_ord or i.type.root() != idx.root():
			self.incompatible(i.type, idx, ie)
		base = b.acode if b.acode is not None else b.vcode
		if b.acode is None and t.is_string:
			self.error('Illegal qualifier', e)
		if i.const is not None:
			self.check_range(i.const, idx, ie)
			off = (i.const - idx.lo) * et.size
			acode = base + ([(C.ADDI, off, ie.line)] if off else [])
		else:
			check = not idx.contains(i.type)
			acode = base + i.vcode + [(C.INDEX, (idx.lo, idx.hi, et.size, check), ie.line)]
		x = Ex(et, None, self.load_code(acode, et, ie.line), acode)
		x.assignable = b.assignable
		x.sym = b.sym
		return x

	def x_Deref(self, e):
		b = self.expr(e.base)
		if b.istype or not b.type.is_pointer or b.type.is_nil:
			self.error('Illegal qualifier', e)
		t = b.type.target
		acode = b.vcode + [(C.DEREF, None, e.line)]
		x = Ex(t, None, self.load_code(acode, t, e.line), acode)
		x.assignable = True
		return x

	def x_AddrOf(self, e):
		b = self.expr(e.expr)
		if b.acode is None or b.istype:
			self.error('Can\'t take the address of constant expressions', e)
		x = Ex(T.PointerType(b.type), None, b.acode)
		return x

	def x_Call(self, e):
		if not isinstance(e.func, A.Name):
			self.error('Illegal expression', e)
		s = self.use(e.func.name, e.func)
		if s.kind == 'type':
			return self.typecast(s.type, e)
		if s.kind not in ('routine', 'builtin'):
			self.error('Illegal expression', e)
		return self.call(e, s, e.args, e.func)

	def typecast(self, t, e):
		if len(e.args) != 1 or e.args[0].width is not None:
			self.error('Illegal type conversion', e)
		x = self.expr(e.args[0].expr)
		st = x.type
		if t.is_ord and st.is_ord:
			if x.const is not None:
				v = x.const
				if t.is_char:
					v &= 0xff
				elif t.is_bool:
					v = 1 if v else 0
				return Ex(t, v)
			code = list(x.vcode)
			if t.is_char:
				code += [(C.PUSH, 0xff, e.line), (C.AND, None, e.line)]
			elif t.is_int and t.size < 8:
				code += [(C.SYS, ('wrap', t.mk), e.line)]
			return Ex(t, None, code)
		if t.is_real and (st.is_int or st.is_real):
			if x.const is not None:
				return Ex(T.REAL, float(x.const))
			code = x.vcode + ([(C.I2F, None, e.line)] if st.is_int else [])
			return Ex(T.REAL, None, code)
		if t.is_string and (st.is_string or st.is_char):
			if x.const is not None:
				return Ex(T.STRING, self.as_bytes(x, e))
			return Ex(T.STRING, None, self.str_value(x, e))
		if t is st:
			return x
		self.error('Illegal type conversion: "%s" to "%s"' % (st.name, t.name), e)

	def x_Unary(self, e):
		x = self.expr(e.expr)
		t = x.type
		op = e.op
		if op == 'not':
			if t.is_bool:
				if x.const is not None:
					return Ex(T.BOOLEAN, 1 - x.const)
				return Ex(T.BOOLEAN, None, x.vcode + [(C.BNOT, None, e.line)])
			if t.is_int:
				if x.const is not None:
					return Ex(T.INT64, ~x.const)
				return Ex(T.INT64, None, x.vcode + [(C.NOT, None, e.line)])
			self.error('Operator is not overloaded: "not" "%s"' % t.name, e)
		if t.is_int:
			if op == '+':
				return Ex(T.INT64, x.const, x.vcode)
			if x.const is not None:
				v = -x.const
				if v > T.INT64_MAX:
					self.error('Overflow in arithmetic operation', e)
				return Ex(T.INTEGER if INT32_MIN <= v <= INT32_MAX else T.INT64, v)
			return Ex(T.INT64, None, x.vcode + [(C.NEG, None, e.line)])
		if t.is_real:
			if op == '+':
				return Ex(t, x.const, x.vcode)
			if x.const is not None:
				return Ex(t, -x.const)
			return Ex(t, None, x.vcode + [(C.FNEG, None, e.line)])
		self.error('Operator is not overloaded: "%s" "%s"' % (op, t.name), e)

	def str_value(self, x, node):
		"""Code pushing x (string, char or char array) as a bytes value."""
		t = x.type
		if t.is_string:
			return x.vcode
		if t.is_char:
			if x.const is not None:
				return [(C.PUSH, bytes([x.const]), node.line)]
			return x.vcode + [(C.C2S, None, node.line)]
		if t.is_array and t.is_chararray():
			return x.vcode + [(C.LDCA, (t.count, t.lo == 0), node.line)]
		self.incompatible(t, T.STRING, node)

	def is_strlike(self, t):
		return t.is_string or t.is_char or (t.is_array and t.is_chararray())

	def x_Binary(self, e):
		op = e.op
		l = self.expr(e.left)
		r = self.expr(e.right)
		lt, rt = l.type, r.type
		line = e.line
		if l.istype or r.istype:
			self.error('Illegal expression', e)
		if op in ('and', 'or') and lt.is_bool and rt.is_bool:
			if l.const is not None and r.const is not None:
				v = (l.const and r.const) if op == 'and' else (l.const or r.const)
				return Ex(T.BOOLEAN, 1 if v else 0)
			lab = self.newlabel()
			j = C.JZK if op == 'and' else C.JNZK
			code = l.vcode + [(j, lab, line)] + r.vcode + [(LABEL, lab, line)]
			return Ex(T.BOOLEAN, None, code)
		if op in ('and', 'or', 'xor'):
			if lt.is_bool and rt.is_bool:
				if l.const is not None and r.const is not None:
					return Ex(T.BOOLEAN, l.const ^ r.const)
				return Ex(T.BOOLEAN, None, l.vcode + r.vcode + [(C.XOR, None, line)])
			if lt.is_int and rt.is_int:
				if l.const is not None and r.const is not None:
					f = {'and': lambda a, b: a & b, 'or': lambda a, b: a | b, 'xor': lambda a, b: a ^ b}[op]
					return Ex(T.INT64, f(l.const, r.const))
				o = {'and': C.AND, 'or': C.OR, 'xor': C.XOR}[op]
				return Ex(T.INT64, None, l.vcode + r.vcode + [(o, None, line)])
			self.op_error(op, lt, rt, e)
		if op in ('=', '<>', '<', '>', '<=', '>='):
			self.compare_checks(op, l, r, e)
			return self.compare(op, l, r, e)
		if op == '+' and self.is_strlike(lt) and self.is_strlike(rt):
			if lt.is_array or rt.is_array:
				self.op_error(op, lt, rt, e)
			if l.const is not None and r.const is not None:
				return Ex(T.STRING, (self.as_bytes(l, e) + self.as_bytes(r, e))[:255])
			code = self.str_value(l, e) + self.str_value(r, e) + [(C.CONCAT, None, line)]
			return Ex(T.STRING, None, code)
		if op == '**':
			if not self.uses_math:
				self.op_error(op, lt, rt, e)
			if lt.is_int and rt.is_int:
				if l.const is not None and r.const is not None:
					return Ex(T.INT64, self.fold_ipow(l.const, r.const, e))
				return Ex(T.INT64, None, l.vcode + r.vcode + [(C.FN, 'ipow', line)])
			if (lt.is_int or lt.is_real) and (rt.is_int or rt.is_real):
				code = l.vcode + ([(C.I2F, None, line)] if lt.is_int else []) + \
					r.vcode + ([(C.I2F, None, line)] if rt.is_int else []) + [(C.FN, 'power', line)]
				return Ex(T.REAL, None, code)
			self.op_error(op, lt, rt, e)
		if op in ('div', 'mod', 'shl', 'shr') or (op in '+-*' and lt.is_int and rt.is_int):
			if op == 'mod' and self.uses_math and (lt.is_real or rt.is_real) and \
					(lt.is_int or lt.is_real) and (rt.is_int or rt.is_real):
				code = l.vcode + ([(C.I2F, None, line)] if lt.is_int else []) + \
					r.vcode + ([(C.I2F, None, line)] if rt.is_int else []) + [(C.FN, 'fmod', line)]
				return Ex(T.REAL, None, code)
			if not (lt.is_int and rt.is_int):
				self.op_error(op, lt, rt, e)
			if l.const is not None and r.const is not None:
				return Ex(T.INT64, self.fold_int(op, l.const, r.const, e))
			o = {'+': C.ADD, '-': C.SUB, '*': C.MUL, 'div': C.DIV, 'mod': C.MOD,
				'shl': C.SHL, 'shr': C.SHR}[op]
			return Ex(T.INT64, None, l.vcode + r.vcode + [(o, None, line)])
		if op in '+-*/':
			if not ((lt.is_int or lt.is_real) and (rt.is_int or rt.is_real)):
				self.op_error(op, lt, rt, e)
			# as in fpc, an operation whose real operands are all singles
			# (real constants exact in single) is done in single precision
			single = self.is_single(lt, rt)
			rtyp = T.SINGLE if single else T.REAL
			if l.const is not None and r.const is not None:
				a, b = self.real_const(l, single), self.real_const(r, single)
				return Ex(rtyp, self.fold_real(op, a, b, single, e))
			o = {'+': C.FADD, '-': C.FSUB, '*': C.FMUL, '/': C.FDIV}[op]
			code = l.vcode + self.to_real(lt, single, line) + r.vcode + self.to_real(rt, single, line)
			code.append((o, None, line))
			if single:
				code.append((C.SGL, None, line))
			return Ex(rtyp, None, code)
		self.op_error(op, lt, rt, e)

	def is_single(self, lt, rt):
		return (not lt.is_real or lt.single) and (not rt.is_real or rt.single) and \
			(lt.is_real or rt.is_real)

	def real_const(self, x, single):
		v = float(x.const)
		return to_single(v) if single and x.type.is_int else v

	def to_real(self, t, single, line):
		"""Code converting a value of type t to a real operand."""
		if t.is_int:
			return [(C.I2F, None, line)] + ([(C.SGL, None, line)] if single else [])
		return []

	def is_ord_char(self, node):
		"""node is ord(c) with c a char."""
		if not (isinstance(node, A.Call) and isinstance(node.func, A.Name) and len(node.args) == 1):
			return False
		s = self.find(node.func.name)
		if s is None or s.kind != 'builtin' or s.name != 'ord':
			return False
		return self.expr(node.args[0].expr).type.is_char

	def compare_checks(self, op, l, r, e):
		# comparing ord(c1) with ord(c2): chars must be compared directly
		if self.is_ord_char(e.left) and self.is_ord_char(e.right):
			self.error('Do not use ord to compare characters: compare the characters directly '
				'(c1 %s c2)' % op, e)
		# x = True, x <> False, ...
		if self.lint and LIMITS.get('boolean_compare') and op in ('=', '<>') and l.type.is_bool and r.type.is_bool \
				and (l.const is None) != (r.const is None):
			v = l.const if l.const is not None else r.const
			k = 'True' if v else 'False'
			plain = (op == '=') == bool(v)
			self.style('"%s %s" is not needed: %s' % (op, k,
				'use the condition itself' if plain else 'use "not" and the condition'), e.pos)

	def op_error(self, op, lt, rt, e):
		self.error('Operator is not overloaded: "%s" %s "%s"' % (lt.name, op, rt.name), e)

	def fold_int(self, op, a, b, e):
		if op in ('div', 'mod') and b == 0:
			self.error('Division by zero', e)
		if op == '+':
			v = a + b
		elif op == '-':
			v = a - b
		elif op == '*':
			v = a * b
		elif op == 'div':
			v = abs(a) // abs(b)
			if (a < 0) != (b < 0):
				v = -v
		elif op == 'mod':
			q = abs(a) // abs(b)
			if (a < 0) != (b < 0):
				q = -q
			v = a - b * q
		elif op == 'shl':
			v = (a << (b & 63)) & 0xffffffffffffffff
			if v >= 1 << 63:
				v -= 1 << 64
		else:
			v = (a & 0xffffffffffffffff) >> (b & 63)
			if v >= 1 << 63:
				v -= 1 << 64
		if not (T.INT64_MIN <= v <= T.INT64_MAX):
			self.error('Overflow in arithmetic operation', e)
		return v

	def fold_real(self, op, a, b, single, e):
		try:
			if op == '+':
				v = a + b
			elif op == '-':
				v = a - b
			elif op == '*':
				v = a * b
			else:
				if b == 0.0:
					if a == 0.0 or math.isnan(a):
						v = math.nan
					else:
						v = math.copysign(math.inf, a) * math.copysign(1.0, b)
				else:
					v = a / b
		except OverflowError:
			v = math.inf
		if single:
			v = to_single(v)
		return v

	def fold_ipow(self, a, b, e):
		from .fmt import intpower, fpc_round
		try:
			return fpc_round(intpower(float(a), b))
		except (OverflowError, ValueError):
			self.error('Overflow in arithmetic operation', e)

	def compare(self, op, l, r, e):
		lt, rt = l.type, r.type
		line = e.line
		o = {'=': C.EQ, '<>': C.NE, '<': C.LT, '>': C.GT, '<=': C.LE, '>=': C.GE}[op]
		pyop = {'=': lambda a, b: a == b, '<>': lambda a, b: a != b, '<': lambda a, b: a < b,
			'>': lambda a, b: a > b, '<=': lambda a, b: a <= b, '>=': lambda a, b: a >= b}[op]
		if lt.is_ord and rt.is_ord:
			if lt.root() != rt.root():
				self.incompatible(rt, lt, e)
			lc, rc = l.vcode, r.vcode
		elif (lt.is_int or lt.is_real) and (rt.is_int or rt.is_real):
			single = self.is_single(lt, rt)
			lc = l.vcode + self.to_real(lt, single, line)
			rc = r.vcode + self.to_real(rt, single, line)
			if l.const is not None and r.const is not None:
				a, b = self.real_const(l, single), self.real_const(r, single)
				return Ex(T.BOOLEAN, 1 if pyop(a, b) else 0)
		elif (lt.is_string or rt.is_string) and self.is_strlike(lt) and self.is_strlike(rt):
			if l.const is not None and r.const is not None:
				return Ex(T.BOOLEAN, 1 if pyop(self.as_bytes(l, e), self.as_bytes(r, e)) else 0)
			lc, rc = self.str_value(l, e), self.str_value(r, e)
		elif lt.is_pointer and rt.is_pointer and op in ('=', '<>'):
			if not (lt.is_nil or rt.is_nil or T.same_type(lt, rt)):
				self.incompatible(rt, lt, e)
			lc, rc = l.vcode, r.vcode
		else:
			self.op_error(op, lt, rt, e)
		if l.const is not None and r.const is not None:
			return Ex(T.BOOLEAN, 1 if pyop(l.const, r.const) else 0)
		return Ex(T.BOOLEAN, None, lc + rc + [(o, None, line)])

	# assignment compatibility
	def coerce(self, x, t, node, what='value'):
		"""Code pushing the value of x converted to type t (checked)."""
		st = x.type
		line = node.line
		if x.istype:
			self.error('Illegal expression', node)
		if x.isproc:
			self.error('Illegal expression', node)
		if t.is_ord:
			if not st.is_ord or st.root() != t.root():
				self.incompatible(st, t, node)
			if x.const is not None:
				self.check_range(x.const, t, node)
				return [(C.PUSH, x.const, line)]
			if t.contains(st):
				return x.vcode
			return x.vcode + [(C.CHK, (t.lo, t.hi), line)]
		if t.is_real:
			if st.is_real:
				if x.const is not None:
					return [(C.PUSH, float(x.const), line)]
				return x.vcode
			if st.is_int:
				if x.const is not None:
					return [(C.PUSH, float(x.const), line)]
				return x.vcode + [(C.I2F, None, line)]
			self.incompatible(st, t, node)
		if t.is_string:
			if self.is_strlike(st):
				if x.const is not None:
					return [(C.PUSH, self.as_bytes(x, node), line)]
				return self.str_value(x, node)
			self.incompatible(st, t, node)
		if t.is_pointer:
			if st.is_nil:
				return [(C.PUSH, 0, line)]
			if st.is_pointer and T.same_type(st, t):
				return x.vcode
			self.incompatible(st, t, node)
		if t.is_file:
			self.error('Operation not allowed on Text variables (they cannot be assigned)', node)
		if st is t:
			return x.vcode
		self.incompatible(st, t, node)

	# calls
	def call(self, e, s, args, fnode):
		if s.kind == 'builtin':
			return self.builtin(s.name, e, args)
		params = s.params
		for a in args:
			if a.width is not None:
				self.error('Illegal parameter list', a)
		if len(args) != len(params):
			self.error('Wrong number of parameters specified for call to "%s"' % s.name, fnode)
		if s.does_io:
			self.io(fnode, 'calls %s, which does input/output' % s.name)
		elif getattr(s, 'does_write', None):
			self.io(fnode, 'calls %s, which writes output' % s.name)
		code = []
		line = e.line
		for k, (a, (pk, ptext, pos, mode, pt)) in enumerate(zip(args, params)):
			x = self.expr(a.expr)
			if mode == 'var':
				if x.sym is not None and getattr(x.sym, 'typedconst', False):
					self.error('Can\'t assign values to const variable "%s"' % x.sym.name, a)
				if not x.assignable or x.acode is None:
					self.error('Variable identifier expected', a)
				if x.sym is not None and x.sym.locked:
					self.error('Illegal assignment to for-loop variable "%s"' % x.sym.name, a)
				if x.sym is not None and getattr(x.sym, 'isresult', False):
					self.rt.resultset = True
				if not T.same_type(x.type, pt):
					if x.type.is_string and pt.is_string:
						self.error('String types have to match exactly in $V+ mode', a)
					self.error('Call by var for arg no. %d has to match exactly: Got "%s" expected "%s"'
						% (k + 1, x.type.name, pt.name), a)
				code += x.acode
			elif pt.is_string:
				code += self.coerce(x, pt, a)
			elif pt.is_array and pt.is_chararray() and (x.type.is_string or x.type.is_char):
				# a string passed for a char array: copy it into a temporary
				off = self.temp(pt.size)
				code += [(C.LADDR, off, line)] + self.coerce(x, T.STRING, a) + \
					[(C.STCA, pt.count, line), (C.LADDR, off, line)]
			elif pt.structured():
				if not T.same_type(x.type, pt):
					self.incompatible(x.type, pt, a)
				code += x.vcode
			else:
				code += self.coerce(x, pt, a)
		ret = s.type
		if ret is not None and ret.structured() and not ret.is_string:
			off = self.temp(ret.size)
			code += [(C.LADDR, off, line), (C.CALL, s.info.index, line), (C.LADDR, off, line)]
			x = Ex(ret, None, code)
		else:
			code.append((C.CALL, s.info.index, line))
			x = Ex(ret if ret is not None else T.NIL, None, code)
		if ret is None:
			x.isproc = True
			x.type = VOID
		return x

	def file_arg(self, args, e, default='output'):
		"""If the first argument is a Text variable, use it as the file."""
		if args:
			x = self.expr(args[0].expr)
			if x.type.is_file:
				if args[0].width is not None:
					self.error('Illegal parameter list', args[0])
				if x.acode is None:
					self.error('Variable identifier expected', args[0])
				return x.acode, args[1:]
		s = self.system[default]
		return [(C.GADDR, s.where[1], e.line)], args

	def builtin(self, name, e, args):
		line = e.line
		n = len(args)
		if name in IO_BUILTINS:
			self.io(e, name)
		for a in args:
			if a.width is not None and name not in ('write', 'writeln'):
				self.error('Illegal parameter list', a)

		def nargs(*ok):
			if n not in ok:
				self.error('Wrong number of parameters specified for call to "%s"' % name, e)

		def arg(k):
			return self.expr(args[k].expr)

		def var_arg(k):
			x = arg(k)
			if x.sym is not None and getattr(x.sym, 'typedconst', False):
				self.error('Can\'t assign values to const variable "%s"' % x.sym.name, args[k])
			if (isinstance(args[k].expr, A.Name) and x.sym is not None
					and getattr(x.sym, 'param', None) == 'var' and name in ('read', 'readln', 'new')):
				self.rt.whole[x.sym] = self.rt.whole.get(x.sym, 0) + 1
			if not x.assignable or x.acode is None:
				self.error('Variable identifier expected', args[k])
			if x.sym is not None and getattr(x.sym, 'isresult', False):
				self.rt.resultset = True
			if x.sym is not None and x.sym.locked:
				self.error('Illegal assignment to for-loop variable "%s"' % x.sym.name, args[k])
			return x

		def proc(code):
			x = Ex(VOID, None, code)
			x.isproc = True
			return x

		if name in ('write', 'writeln'):
			fcode, rest = self.file_arg(args, e)
			code = []
			for a in rest:
				code += self.write_arg(fcode, a)
			if name == 'writeln':
				code += fcode + [(C.WRLN, None, line)]
			return proc(code)
		if name in ('read', 'readln'):
			fcode, rest = self.file_arg(args, e, 'input')
			code = []
			for a in rest:
				x = var_arg(args.index(a))
				t = x.type
				if t.is_int:
					spec = ('i', t.mk, t.lo, t.hi)
				elif t.is_char:
					spec = ('c', 'B', t.lo, t.hi)
				elif t.is_enum:
					spec = ('e', t.mk, t.lo, t.hi, t.names)
				elif t.is_real:
					spec = ('r', 'd')
				elif t.is_string:
					spec = ('s', t.maxlen)
				elif t.is_array and t.is_chararray():
					spec = ('a', t.count, t.lo == 0)
				else:
					self.error("Can't read or write variables of this type", a)
				code += fcode + x.acode + [(C.RD, spec, a.line)]
			if name == 'readln':
				code += fcode + [(C.RDLN, None, line)]
			elif not rest:
				self.error('Wrong number of parameters specified for call to "read"', e)
			return proc(code)
		if name in ('eof', 'eoln'):
			nargs(0, 1)
			if n == 1:
				x = arg(0)
				if not x.type.is_file:
					self.incompatible(x.type, T.TEXT, args[0])
				fcode = x.acode
			else:
				fcode = [(C.GADDR, 24, line)]
			return Ex(T.BOOLEAN, None, fcode + [(C.SYS, name, line)])
		if name in ('assign', 'reset', 'rewrite', 'close'):
			nargs(2 if name == 'assign' else 1)
			x = var_arg(0)
			if not x.type.is_file:
				self.incompatible(x.type, T.TEXT, args[0])
			code = list(x.acode)
			if name == 'assign':
				y = arg(1)
				if not self.is_strlike(y.type):
					self.incompatible(y.type, T.STRING, args[1])
				code += self.coerce(y, T.STRING, args[1])
			return proc(code + [(C.SYS, name, line)])
		if name == 'halt':
			nargs(0, 1)
			code = self.coerce(arg(0), T.INTEGER, args[0]) if n else [(C.PUSH, 0, line)]
			return proc(code + [(C.HALT, None, line)])
		if name in ('new', 'dispose'):
			nargs(1)
			x = var_arg(0)
			if not x.type.is_pointer or x.type.is_nil:
				self.error('Pointer type expected', args[0])
			size = x.type.target.size
			return proc(x.acode + [(C.SYS, (name, size, x.type.target, line), line)])
		if name == 'stack':
			nargs(0, 1)
			code = self.coerce(arg(0), T.INTEGER, args[0]) if n else [(C.PUSH, 0, line)]
			return proc(code + [(C.SYS, 'stack', line)])
		if name == 'ord':
			nargs(1)
			x = arg(0)
			if not x.type.is_ord or x.istype:
				self.error('Ordinal expression expected', args[0])
			rt = T.INT64 if x.type.is_int and x.type.size == 8 else T.INTEGER
			return Ex(rt, x.const, x.vcode)
		if name == 'chr':
			nargs(1)
			x = arg(0)
			if not x.type.is_int:
				self.incompatible(x.type, T.INT64, args[0])
			if x.const is not None:
				self.check_range(x.const, T.CHAR, args[0])
				return Ex(T.CHAR, x.const)
			return Ex(T.CHAR, None, x.vcode + [(C.CHK, (0, 255), line)])
		if name in ('succ', 'pred'):
			nargs(1)
			x = arg(0)
			t = x.type
			if not t.is_ord or x.istype:
				self.error('Ordinal expression expected', args[0])
			d = 1 if name == 'succ' else -1
			if x.const is not None:
				v = x.const + d
				self.check_range(v, t, args[0])
				return Ex(t, v)
			return Ex(t, None, x.vcode + [(C.PUSH, d, line), (C.ADD, None, line), (C.CHK, (t.lo, t.hi), line)])
		if name in ('low', 'high'):
			nargs(1)
			x = arg(0)
			t = x.istype or x.type
			if t.is_ord:
				return Ex(t, t.lo if name == 'low' else t.hi)
			if t.is_array:
				return Ex(t.index, t.lo if name == 'low' else t.hi)
			if t.is_string:
				return Ex(T.INTEGER, 0 if name == 'low' else t.maxlen)
			self.error('Type mismatch', args[0])
		if name == 'length':
			nargs(1)
			x = arg(0)
			t = x.type
			if x.const is not None and (t.is_string or t.is_char):
				return Ex(T.INTEGER, len(self.as_bytes(x, args[0])))
			if t.is_string and not x.istype:
				if x.acode is not None:
					return Ex(T.INTEGER, None, x.acode + [(C.LD, 'B', line)])
				return Ex(T.INTEGER, None, x.vcode + [(C.FN, 'length', line)])
			if t.is_char and not x.istype:
				return Ex(T.INTEGER, 1)
			if t.is_array and not x.istype:
				return Ex(T.INTEGER, t.count)
			self.error('Type mismatch', args[0])
		if name == 'setlength':
			nargs(2)
			x = var_arg(0)
			if not x.type.is_string:
				self.error('Type mismatch', args[0])
			code = x.acode + self.coerce(arg(1), T.INT64, args[1])
			return proc(code + [(C.SYS, 'setlength', line)])
		if name == 'val':
			nargs(3)
			s = arg(0)
			if not self.is_strlike(s.type):
				self.incompatible(s.type, T.STRING, args[0])
			v = var_arg(1)
			c = var_arg(2)
			t = v.type
			if t.is_int:
				spec = ('i', t.mk, t.lo, t.hi)
			elif t.is_enum:
				spec = ('e', t.mk, t.lo, t.hi, t.names)
			elif t.is_real:
				spec = ('r', 'd')
			else:
				self.error('Type mismatch', args[1])
			if not c.type.is_int:
				self.error('Type mismatch', args[2])
			code = self.coerce(s, T.STRING, args[0]) + v.acode + c.acode
			return proc(code + [(C.SYS, ('val', spec, c.type.mk, c.type.lo, c.type.hi), line)])
		if name in ('sqr', 'abs'):
			nargs(1)
			x = arg(0)
			t = x.type
			if t.is_int and not x.istype:
				if x.const is not None:
					v = x.const * x.const if name == 'sqr' else abs(x.const)
					if v > T.INT64_MAX:
						self.error('Overflow in arithmetic operation', e)
					return Ex(T.INT64, v)
				op = [(C.DUP, None, line), (C.MUL, None, line)] if name == 'sqr' else [(C.FN, 'iabs', line)]
				return Ex(T.INT64, None, x.vcode + op)
			if t.is_real:
				if x.const is not None:
					try:
						v = x.const * x.const if name == 'sqr' else abs(x.const)
					except OverflowError:
						v = math.inf
					return Ex(T.REAL, v)
				op = [(C.DUP, None, line), (C.FMUL, None, line)] if name == 'sqr' else [(C.FN, 'fabs', line)]
				if t.single and name == 'sqr':
					op.append((C.SGL, None, line))
				return Ex(t, None, x.vcode + op)
			self.error('Type mismatch', args[0])
		if name in ('sqrt', 'sin', 'cos', 'arctan', 'exp', 'ln', 'frac', 'int'):
			nargs(1)
			x = arg(0)
			if not (x.type.is_int or x.type.is_real) or x.istype:
				self.error('Type mismatch', args[0])
			if x.const is not None:
				v = float(x.const)
				if name == 'sqrt':
					v = math.sqrt(v) if v >= 0 else math.nan
					return Ex(T.REAL, v)
				if name == 'sin':
					return Ex(T.REAL, math.sin(v) if math.isfinite(v) else math.nan)
				# like fpc, folding gives Inf or NaN where the run time fails
				return Ex(T.REAL, real_fn(name, v))
			code = x.vcode + ([(C.I2F, None, line)] if x.type.is_int else []) + [(C.FN, name, line)]
			if name == 'sqrt' and x.type.is_real and x.type.single:
				return Ex(T.SINGLE, None, code + [(C.SGL, None, line)])
			return Ex(T.REAL, None, code)
		if name in ('trunc', 'round'):
			nargs(1)
			x = arg(0)
			if x.type.is_int and not x.istype:
				if x.const is not None:
					return Ex(T.INT64, x.const)
				return Ex(T.INT64, None, x.vcode)
			if not x.type.is_real:
				self.error('Type mismatch', args[0])
			if x.const is not None:
				from .fmt import fpc_round
				v = x.const
				if not math.isfinite(v) or abs(v) >= 2.0 ** 63:
					self.error('Overflow in arithmetic operation', e)
				return Ex(T.INT64, int(v) if name == 'trunc' else fpc_round(v))
			return Ex(T.INT64, None, x.vcode + [(C.FN, name, line)])
		if name == 'odd':
			nargs(1)
			x = arg(0)
			if not x.type.is_int or x.istype:
				self.error('Type mismatch', args[0])
			if x.const is not None:
				return Ex(T.BOOLEAN, x.const & 1)
			return Ex(T.BOOLEAN, None, x.vcode + [(C.PUSH, 1, line), (C.AND, None, line)])
		if name == 'pi':
			nargs(0)
			return Ex(T.REAL, math.pi)
		if name == 'random':
			nargs(0, 1)
			if n == 0:
				return Ex(T.REAL, None, [(C.FN, 'random', line)])
			x = arg(0)
			if not x.type.is_int or x.istype:
				self.error('Type mismatch', args[0])
			t = T.INT64 if x.type.size == 8 else T.INTEGER
			code = self.coerce(x, t, args[0])
			return Ex(t, None, code + [(C.FN, 'random64' if t is T.INT64 else 'randomn', line)])
		if name == 'randomize':
			nargs(0)
			return proc([(C.SYS, 'randomize', line)])
		if name == 'intpower':
			nargs(2)
			x = arg(0)
			y = arg(1)
			code = self.coerce(x, T.REAL, args[0]) + self.coerce(y, T.INTEGER, args[1])
			return Ex(T.REAL, None, code + [(C.FN, 'intpower', line)])
		self.error('Identifier not found "%s"' % name, e)

	def write_arg(self, fcode, a):
		x = self.expr(a.expr)
		t = x.type
		line = a.line
		if x.istype or x.isproc:
			self.error('Illegal expression', a)
		if t.is_int:
			spec = ('i',)
		elif t.is_char:
			spec = ('c',)
		elif t.is_bool:
			spec = ('b',)
		elif t.is_enum:
			spec = ('e', t.names)
		elif t.is_real:
			spec = ('r', t.single)
		elif t.is_string:
			spec = ('s',)
		elif t.is_array and t.is_chararray():
			spec = ('s',)
		else:
			self.error("Can't read or write variables of this type", a)
		vcode = self.str_value(x, a) if t.is_array else x.vcode
		code = fcode + vcode
		w = d = None
		if a.width is not None:
			code += self.coerce(self.expr(a.width), T.INT64, a.width)
			w = True
		if a.prec is not None:
			if not t.is_real:
				self.error('Illegal use of \':\'', a.prec)
			code += self.coerce(self.expr(a.prec), T.INT64, a.prec)
			d = True
		return code + [(C.WR, (spec, w, d), line)]

	# statements
	def stmt(self, s):
		self.at(s)
		mark = self.rt.frame
		code = getattr(self, 's_' + type(s).__name__)(s)
		self.rt.frame = mark
		if self.debug and not isinstance(s, (A.Compound, A.Empty, A.While, A.Repeat)):
			code = [self.line_op(s.line, s.col)] + code
		return code

	def line_op(self, line, col):
		"""pascdb stops before executing the statement at line:col."""
		return (C.LINE, (line, col), line)

	def s_Empty(self, s):
		return []

	def stmt_list(self, stmts):
		code = []
		saved = self.halt_after
		for k, st in enumerate(stmts):
			self.halt_after = saved or any(is_halt(x) for x in stmts[k + 1:])
			code += self.stmt(st)
		self.halt_after = saved
		return code

	def s_Compound(self, s):
		return self.stmt_list(s.stmts)

	def s_Assign(self, s):
		tgt = s.target
		line = s.line
		# assignment to the function name sets the result
		if isinstance(tgt, A.Name):
			sym = self.lookup(tgt.name, tgt)
			if getattr(sym, 'param', None) == 'var':
				self.rt.whole[sym] = self.rt.whole.get(sym, 0) + 1
			if sym.kind == 'routine' and self.rt.sym is sym and sym.type is not None:
				self.check_case(sym, tgt)
				sym = self.rt.result
				tgt = A.Name(tgt.pos, 'result', 'result')
			elif sym.kind == 'const':
				self.error('Variable identifier expected', tgt)
			elif sym.kind != 'var':
				self.error('Variable identifier expected', tgt)
		lv = self.expr(tgt)
		if lv.sym is not None and getattr(lv.sym, 'typedconst', False):
			self.error('Can\'t assign values to const variable "%s"' % lv.sym.name, tgt)
		if not lv.assignable or lv.acode is None:
			self.error('Variable identifier expected', tgt)
		if lv.sym is not None and lv.sym.locked:
			self.error('Illegal assignment to for-loop variable "%s"' % lv.sym.name, tgt)
		if lv.sym is not None and getattr(lv.sym, 'isresult', False):
			self.rt.resultset = True
		x = self.expr(s.expr)
		return self.store(lv, x, s.expr, line)

	def store(self, lv, x, enode, line):
		t = lv.type
		if t.is_file:
			self.error('Operation not allowed on Text variables (they cannot be assigned)', enode)
		if x.isproc:
			self.error('Illegal expression', enode)
		if t.is_string:
			return lv.acode + self.coerce(x, t, enode) + [(C.STS, t.maxlen, line)]
		if t.is_array and t.is_chararray() and not T.same_type(x.type, t):
			if not (x.type.is_string or x.type.is_char):
				self.incompatible(x.type, t, enode)
			return lv.acode + self.coerce(x, T.STRING, enode) + [(C.STCA, t.count, line)]
		if t.structured():
			if not T.same_type(x.type, t):
				self.incompatible(x.type, t, enode)
			return lv.acode + x.vcode + [(C.COPY, t.size, line)]
		vcode = self.coerce(x, t, enode)
		ac = lv.acode
		if len(ac) == 1 and ac[0][0] in (C.GADDR, C.LADDR):
			op = C.STG if ac[0][0] == C.GADDR else C.STL
			return vcode + [(op, (t.mk, ac[0][1]), line)]
		return ac + vcode + [(C.ST, t.mk, line)]

	def s_ProcCall(self, s):
		c = s.call
		if isinstance(c, A.Name):
			sym = self.use(c.name, c)
			if sym.kind not in ('routine', 'builtin'):
				self.error('Illegal expression', c)
			x = self.call(c, sym, [], c)
		elif isinstance(c, A.Call) and isinstance(c.func, A.Name):
			sym = self.use(c.func.name, c.func)
			if sym.kind not in ('routine', 'builtin'):
				self.error('Illegal expression', c)
			x = self.call(c, sym, c.args, c.func)
		else:
			self.error('Illegal expression', c)
		if not x.isproc:
			self.error('Illegal expression: function results must be used ($X- extended syntax is off)', c)
		return x.vcode

	def cond(self, e):
		x = self.expr(e)
		if not x.type.is_bool:
			self.incompatible(x.type, T.BOOLEAN, e)
		return x.vcode

	def s_If(self, s):
		lelse = self.newlabel()
		code = self.cond(s.cond) + [(C.JZ, lelse, s.line)]
		code += self.stmt(s.then)
		if s.else_ is not None:
			lend = self.newlabel()
			code += [(C.JMP, lend, s.line), (LABEL, lelse, s.line)]
			code += self.stmt(s.else_)
			code.append((LABEL, lend, s.line))
		else:
			code.append((LABEL, lelse, s.line))
		return code

	def s_While(self, s):
		ltop = self.newlabel()
		lend = self.newlabel()
		code = [(LABEL, ltop, s.line)] + ([self.line_op(s.line, s.col)] if self.debug else [])
		code += self.cond(s.cond) + [(C.JZ, lend, s.line)]
		code += self.stmt(s.body)
		code += [(C.JMP, ltop, s.line), (LABEL, lend, s.line)]
		return code

	def s_Repeat(self, s):
		ltop = self.newlabel()
		code = [(LABEL, ltop, s.line)] + self.stmt_list(s.stmts)
		self.at(s.cond)
		if self.debug:
			code.append(self.line_op(s.cond.line, s.cond.col))
		code += self.cond(s.cond) + [(C.JZ, ltop, s.cond.line)]
		return code

	def loop_var(self, v):
		sym = self.use(v.name, v)
		if getattr(sym, 'typedconst', False):
			self.error('Can\'t assign values to const variable "%s"' % sym.name, v)
		if sym.kind != 'var' or getattr(sym, 'param', None) == 'var':
			self.error('Illegal counter variable', v)
		if not sym.type.is_ord:
			self.error('Ordinal expression expected', v)
		if sym.locked:
			self.error('Illegal assignment to for-loop variable "%s"' % sym.name, v)
		return sym

	def s_For(self, s):
		sym = self.loop_var(s.var)
		t = sym.type
		line = s.line
		start = self.expr(s.start)
		stop = self.expr(s.stop)
		for x, node in ((start, s.start), (stop, s.stop)):
			if not x.type.is_ord or x.type.root() != t.root():
				self.incompatible(x.type, t, node)
			if x.const is not None:
				self.check_range(x.const, t, node)
		ts = self.temp(8)
		te = self.temp(8)
		acode, vcode = self.var_code(sym, line)
		lend = self.newlabel()
		ltop = self.newlabel()
		code = start.vcode + [(C.STL, ('q', ts), line)]
		code += stop.vcode + [(C.STL, ('q', te), line)]
		code += [(C.LDL, ('q', ts), line), (C.LDL, ('q', te), line),
			(C.LT if s.down else C.GT, None, line), (C.JNZ, lend, line)]
		chk = [] if t.contains(start.type) else [(C.CHK, (t.lo, t.hi), line)]
		code += [(C.LDL, ('q', ts), line)] + chk
		code += self.store_scalar(sym, line)
		if not t.contains(stop.type):
			code += [(C.LDL, ('q', te), line), (C.CHK, (t.lo, t.hi), line), (C.POP, None, line)]
		code.append((LABEL, ltop, line))
		sym.locked += 1
		code += self.stmt(s.body)
		sym.locked -= 1
		if self.debug:
			code.append(self.line_op(s.line, s.col))
		code += vcode + [(C.LDL, ('q', te), line), (C.EQ, None, line), (C.JNZ, lend, line)]
		code += vcode + [(C.PUSH, -1 if s.down else 1, line), (C.ADD, None, line)]
		code += self.store_scalar(sym, line)
		code += [(C.JMP, ltop, line), (LABEL, lend, line)]
		return code

	def store_scalar(self, sym, line):
		kind, off = sym.where
		mk = sym.type.mk
		if kind == 'g':
			return [(C.STG, (mk, off), line)]
		return [(C.STL, (mk, off), line)]

	def s_ForIn(self, s):
		sym = self.loop_var(s.var)
		x = self.expr(s.typ)
		if not x.istype or not x.istype.is_ord:
			self.error('for-in loops are only supported over ordinal types', s.typ)
		it = x.istype
		if it.root() != sym.type.root():
			self.incompatible(it, sym.type, s.typ)
		line = s.line
		lo = A.IntLit(s.pos, it.lo)
		hi = A.IntLit(s.pos, it.hi)
		# reuse the counting loop; the bounds are constants of the right type
		self.check_range(it.lo, sym.type, s.typ)
		self.check_range(it.hi, sym.type, s.typ)
		acode, vcode = self.var_code(sym, line)
		lend = self.newlabel()
		ltop = self.newlabel()
		code = [(C.PUSH, it.lo, line)] + self.store_scalar(sym, line)
		code.append((LABEL, ltop, line))
		sym.locked += 1
		code += self.stmt(s.body)
		sym.locked -= 1
		if self.debug:
			code.append(self.line_op(s.line, s.col))
		code += vcode + [(C.PUSH, it.hi, line), (C.EQ, None, line), (C.JNZ, lend, line)]
		code += vcode + [(C.PUSH, 1, line), (C.ADD, None, line)]
		code += self.store_scalar(sym, line)
		code += [(C.JMP, ltop, line), (LABEL, lend, line)]
		return code

	def s_Case(self, s):
		x = self.expr(s.expr)
		t = x.type
		line = s.line
		isstr = self.is_strlike(t) and not t.is_char
		if not (t.is_ord or isstr):
			self.error('Ordinal expression expected', s.expr)
		code = self.str_value(x, s.expr) if isstr else list(x.vcode)
		lend = self.newlabel()
		lelse = self.newlabel()
		seen = []
		bodies = []
		for labels, st in s.branches:
			lb = self.newlabel()
			for lo, hi in labels:
				a = self.const_expr(lo)
				b = self.const_expr(hi) if hi is not None else a
				for y, nd in ((a, lo), (b, hi or lo)):
					if isstr:
						if not self.is_strlike(y.type):
							self.incompatible(y.type, t, nd)
					elif not y.type.is_ord or y.type.root() != t.root():
						self.incompatible(y.type, t, nd)
				av = self.as_bytes(a, lo) if isstr else a.const
				bv = self.as_bytes(b, hi or lo) if isstr else b.const
				if av > bv:
					self.error('High range limit < low range limit', lo)
				for p, q in seen:
					if not (bv < p or av > q):
						self.error('Duplicate case label', lo)
				seen.append((av, bv))
				if hi is None:
					code += [(C.DUP, None, lo.line), (C.PUSH, av, lo.line), (C.EQ, None, lo.line),
						(C.JNZ, lb, lo.line)]
				else:
					lnext = self.newlabel()
					code += [(C.DUP, None, lo.line), (C.PUSH, av, lo.line), (C.GE, None, lo.line),
						(C.JZ, lnext, lo.line), (C.DUP, None, lo.line), (C.PUSH, bv, lo.line),
						(C.LE, None, lo.line), (C.JNZ, lb, lo.line), (LABEL, lnext, lo.line)]
			bodies.append((lb, st))
		code.append((C.JMP, lelse, line))
		for lb, st in bodies:
			code += [(LABEL, lb, st.line), (C.POP, None, st.line)]
			code += self.stmt(st)
			code.append((C.JMP, lend, st.line))
		code += [(LABEL, lelse, line), (C.POP, None, line)]
		if s.else_ is not None:
			code += self.stmt_list(s.else_)
		code.append((LABEL, lend, line))
		return code

	# program
	def program(self, p):
		self.progname = p.name.lower()
		for key, pos, text in p.uses:
			if key != 'math':
				raise CompileError(self.fname, pos[0], pos[1], 'Can\'t find unit %s used by %s' % (text, p.name))
			if not self.uses_math:
				self.uses_math = True
				self.scopes.append(self.math_scope())
		glob = {}
		self.globscope = glob
		self.scopes.append(glob)
		main = C.RoutineInfo('main program', 'program')
		main.index = 0
		main.line = p.body.line
		self.prog.routines.append(main)
		self.rt = Routine(None, main)
		if not self.early_globals:
			# global variables are the main program's locals: they go after
			# every procedure and function, right before the main program
			last = max((k for k, d in enumerate(p.decls) if isinstance(d, A.Routine)), default=-1)
			for d in (p.decls[:last] if last > 0 else []):
				if isinstance(d, A.VarDecl):
					self.error('global variables must be declared after all procedures and functions, '
						'just before the main program (pasc -g allows them earlier)', d)
		self.declarations(p.decls)
		self.rt.tempmark = 0
		lab = self.newlabel()
		main.entry_label = lab
		body = [(LABEL, lab, p.body.line)] + self.stmt(p.body)
		if self.debug:
			body.append(self.line_op(p.endpos[0], 1))
		body += [(C.PUSH, 0, p.endpos[0]), (C.HALT, None, p.endpos[0])]
		main.framesize = self.rt.maxframe
		self.code = body + self.code
		self.assemble()
		return self.prog

	def peephole(self, code):
		"""Fuse common instruction pairs into single instructions."""
		out = []
		jfalse = {C.EQ: C.JNEQ, C.NE: C.JNNE, C.LT: C.JNLT, C.LE: C.JNLE, C.GT: C.JNGT, C.GE: C.JNGE}
		jtrue = {C.EQ: C.JNNE, C.NE: C.JNEQ, C.LT: C.JNGE, C.LE: C.JNGT, C.GT: C.JNLE, C.GE: C.JNLT}
		for ins in code:
			op, arg, line = ins
			if out:
				pop_, parg, pline = out[-1]
				if op == C.ADD and pop_ == C.PUSH and type(parg) is int:
					out[-1] = (C.ADDK, parg, line)
					continue
				if op == C.SUB and pop_ == C.PUSH and type(parg) is int:
					out[-1] = (C.ADDK, -parg, line)
					continue
				if op == C.JZ and pop_ in jfalse:
					out[-1] = (jfalse[pop_], arg, line)
					continue
				if op == C.JNZ and pop_ in jtrue:
					out[-1] = (jtrue[pop_], arg, line)
					continue
				if op == C.LD and pop_ == C.INDEX:
					out[-1] = (C.LDX, parg + (arg,), line)
					continue
				# x := x + k on a global or local scalar
				if op in (C.STG, C.STL):
					ld = C.LDG if op == C.STG else C.LDL
					k = len(out)
					chk = None
					if pop_ == C.CHK and k >= 3:
						chk = parg
						k -= 1
					if k >= 2 and out[k - 1][0] == C.ADDK and out[k - 2][0] == ld and out[k - 2][1] == arg:
						inc = out[k - 1][1]
						lo, hi = chk if chk else (T.INT64_MIN, T.INT64_MAX)
						del out[k - 2:]
						out.append((C.INCG if op == C.STG else C.INCL, (arg[0], arg[1], inc, lo, hi), line))
						continue
			out.append(ins)
		return out

	def assemble(self):
		self.code = self.peephole(self.code)
		pos = {}
		n = 0
		for op, arg, line in self.code:
			if op == LABEL:
				pos[arg] = n
			else:
				n += 1
		prog = self.prog
		jumps = (C.JMP, C.JZ, C.JNZ, C.JZK, C.JNZK, C.JNEQ, C.JNNE, C.JNLT, C.JNLE, C.JNGT, C.JNGE)
		for op, arg, line in self.code:
			if op == LABEL:
				continue
			if op in jumps:
				arg = pos[arg]
			prog.emit(op, arg, line)
		for r in prog.routines:
			r.entry = pos[r.entry_label]
		prog.main = prog.routines[0]
		prog.globsize = self.glob
		prog.image = bytes(self.image[:self.glob])
		prog.warnings = self.warnings
		prog.uses_math = self.uses_math
		prog.init_ranges.append((16, 16))


def real_fn(name, v):
	"""cos, arctan, exp, ln, frac or int of constant v, as fpc folds them:
	Inf or NaN where the operation fails at run time."""
	if name == 'ln':
		if v != v or v < 0:
			return math.nan
		return -math.inf if v == 0 else (math.inf if v == math.inf else math.log(v))
	if name == 'exp':
		if v != v:
			return v
		try:
			return math.exp(v)
		except OverflowError:
			return math.inf
	if name == 'arctan':
		return arctan(v)
	if not math.isfinite(v):
		return math.nan
	if name == 'cos':
		return math.cos(v)
	if name == 'frac':
		return math.fmod(v, 1.0)
	return float(math.trunc(v))		# int


def is_halt(st):
	c = getattr(st, 'call', None)
	if isinstance(c, A.Call):
		c = c.func
	return isinstance(st, A.ProcCall) and isinstance(c, A.Name) and c.name == 'halt'


class _Void(T.Type):
	name = 'untyped'


VOID = _Void()


def compile_program(tree, fname, lint=False, debug=False, early_globals=False):
	from .indent import check_indentation
	iwarn = check_indentation(tree, fname)
	c = Compiler(fname, lint, debug, early_globals)
	prog = c.program(tree)
	prog.warnings[:0] = iwarn
	if lint:
		from .lint import lint_program
		found = c.lints + lint_program(tree, prog)
		for line, col, msg in sorted(found):
			prog.warnings.append('%s:%d:%d: warning: %s' % (fname, line, col, msg))

		def where(w):
			parts = w[len(fname) + 1:].split(':')
			return (int(parts[0]), int(parts[1]))
		prog.warnings.sort(key=where)
	return prog
