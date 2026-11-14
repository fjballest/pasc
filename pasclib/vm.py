"""The pasc virtual machine: runs a code.Program.

Memory is one bytearray:

	[0, 16)            reserved (address 0 is nil)
	[16, globsize)     output, input and the program's global variables
	[stack, stack+N)   call frames (parameters, locals, temporaries)
	[heap, ...)        new() allocations; grows as needed

Run-time errors use FPC's numbers and stop the program with that exit
status, after flushing the output written so far.
"""

import math
import os
import random
import struct
import sys

from . import code as C
from .errors import RunError, Halt, RTE_NAMES, EXCEPTIONS
from .fmt import to_single, real_to_str, intpower, power, fpc_round, val_int, val_real, val_enum
from .textio import TextFile, std_files
from . import debug

MAXI = (1 << 63) - 1
MINI = -(1 << 63)

STRUCTS = {k: struct.Struct('<' + k) for k in 'bBhHiIqQd'}
SIZES = {k: s.size for k, s in STRUCTS.items()}

DEFAULT_STACK = 16 << 20
EOL = b'\r\n' if os.name == 'nt' else b'\n'	# FPC's LineEnding
DEBUG = bool(os.environ.get('PASC_DEBUG'))


class VM:
	def __init__(self, prog, stack_size=DEFAULT_STACK, randomize=True, seed=None):
		self.prog = prog
		self.stack = (prog.globsize + 15) & ~15
		self.stack_end = self.stack + stack_size
		self.mem = bytearray(self.stack_end)
		# uninitialised memory holds random garbage (or zeros, with -z)
		self.randomize = randomize
		if randomize:
			self.rng = random.Random(seed)
			self.pool = self.rng.getrandbits(8 << 20).to_bytes(1 << 20, 'little')
			self.mem[32:self.stack] = self.garbage(self.stack - 32)
		if not randomize:
			self.mem[0:len(prog.image)] = prog.image
		for addr, size in prog.init_ranges:
			self.mem[addr:addr + size] = prog.image[addr:addr + size]
		self.heap_free = {}		# size -> [addresses]
		self.heap_live = {}		# address -> (size, (line, type name))
		self.heap_dead = set()		# disposed blocks
		self.opened = {}		# file path -> line where first opened
		self.warned = set()
		self.out, self.inp = std_files()
		self.files = [None, self.out, self.inp]
		STRUCTS['Q'].pack_into(self.mem, 16, 1)
		STRUCTS['Q'].pack_into(self.mem, 24, 2)
		self.callstack = []
		self.pc = 0

	# files
	def file(self, addr):
		h = STRUCTS['Q'].unpack_from(self.mem, addr)[0]
		if h <= 0 or h >= len(self.files):
			raise RunError(102 if h == 0 else 103)
		return self.files[h]

	def flush_all(self):
		try:
			self.out.flush()
		except RunError:
			pass

	def garbage(self, n):
		"""n random bytes for uninitialised memory."""
		if not self.randomize:
			return bytes(n)
		pool = self.pool
		if n <= len(pool):
			k = self.rng.randrange(len(pool) - n + 1)
			return pool[k:k + n]
		reps = n // len(pool) + 1
		return (pool * reps)[:n]

	# file warnings
	def warn(self, line, msg):
		self.flush_all()
		sys.stderr.write('%s:%d: warning: %s\n' % (self.prog.fname, line, msg))

	def note_open(self, f):
		"""Warn when the same file is opened again in the program."""
		if f.std is not None:
			return
		line = self.prog.lines[self.pc - 1]
		key = os.path.abspath(f.name)
		first = self.opened.get(key)
		if first is None:
			self.opened[key] = line
		elif key not in self.warned:
			self.warned.add(key)
			self.warn(line, 'file "%s" is opened again (it was first opened at line %d)' % (f.name, first))

	def files_report(self):
		"""Warn about files still open when the program ends."""
		for f in self.files[3:]:
			if f.mode != 'closed':
				self.warn(getattr(f, 'opened_at', 0), 'file "%s" was never closed' % f.name)

	# heap
	def new(self, size, site):
		req = size
		size = max(size, 1)
		size = (size + 7) & ~7
		lst = self.heap_free.get(size)
		if lst:
			a = lst.pop()
			self.heap_dead.discard(a)
			self.mem[a:a + size] = self.garbage(size)
		else:
			a = len(self.mem)
			self.mem.extend(self.garbage(size))
		self.heap_live[a] = (req, site)
		return a

	def dispose(self, a):
		if a == 0:
			return
		blk = self.heap_live.pop(a, None)
		if blk is None:
			raise RunError(204)
		size = (max(blk[0], 1) + 7) & ~7
		self.heap_free.setdefault(size, []).append(a)
		self.heap_dead.add(a)

	# running
	def run(self):
		"""Run the program; return the exit status."""
		try:
			try:
				self.loop()
				status = 0
			except Halt as h:
				status = h.code
		except RunError as e:
			self.flush_all()
			self.report(e)
			return 217 if self.prog.uses_math else e.code
		except RecursionError:
			self.flush_all()
			self.report(RunError(202))
			return 202
		except KeyboardInterrupt:
			self.flush_all()
			sys.stderr.write('\nInterrupted\n')
			return 130
		self.flush_all()
		debug.leak_report(self)
		self.files_report()
		return status & 0xff if status >= 0 else status & 0xff

	def where(self, pc):
		pc = max(pc, 0)
		return '%s:%d' % (self.prog.fname, self.prog.lines[pc] if pc < len(self.prog.lines) else 0)

	def report(self, e):
		pc = self.pc - 1
		cur = self.cur_routine
		if self.prog.uses_math:
			cls, msg = EXCEPTIONS.get(e.code, ('EInOutError', 'Unknown Run-Time error : %d' % e.code))
			lines = ['An unhandled exception occurred at %s:' % self.where(pc), '%s: %s' % (cls, msg)]
		else:
			lines = ['Runtime error %d at %s: %s' % (e.code, self.where(pc), RTE_NAMES.get(e.code, ''))]
		lines.append('  in %s' % self.rname(cur))
		calls = ['  called from %s at %s' % (self.rname(r), self.where(rpc - 1))
			for (rpc, fp, sp, r) in reversed(self.callstack[-20:])]
		if len(self.callstack) > 20:
			calls.append('  ... (%d more calls)' % (len(self.callstack) - 20))
		sys.stderr.write('\n'.join(lines + calls) + '\n')
		sys.stderr.flush()

	def rname(self, r):
		if r.kind == 'program':
			return 'main program'
		return '%s %s' % (r.kind, r.name)

	def loop(self):
		prog = self.prog
		ops = prog.ops
		args = prog.args
		routines = prog.routines
		mem = self.mem
		stack = []
		push = stack.append
		pop = stack.pop
		S = STRUCTS
		SQ = S['Q']
		unpack = {k: s.unpack_from for k, s in S.items()}
		packi = {k: s.pack_into for k, s in S.items()}
		callstack = self.callstack
		main = prog.main
		self.cur_routine = main
		fp = self.stack
		sp = fp + main.framesize
		mem[fp:sp] = self.garbage(main.framesize)
		garbage = self.garbage
		if sp > self.stack_end:
			raise RunError(202)
		stack_end = self.stack_end
		pc = main.entry
		cur = main
		(PUSH, POP, DUP, LDL, STL, LDG, STG, LD, ST, LDS, STS, ADD, SUB, MUL, JMP, JZ, JNZ,
		 EQ, NE, LT, LE, GT, GE, CALL, RET, CHK, INDEX, ADDI, GADDR, LADDR, COPY, DEREF,
		 JZK, JNZK, ADDK, LDX, JNEQ, JNNE, JNLT, JNLE, JNGT, JNGE) = (C.PUSH, C.POP, C.DUP, C.LDL, C.STL, C.LDG, C.STG, C.LD, C.ST,
		 C.LDS, C.STS, C.ADD, C.SUB, C.MUL, C.JMP, C.JZ, C.JNZ, C.EQ, C.NE, C.LT,
		 C.LE, C.GT, C.GE, C.CALL, C.RET, C.CHK, C.INDEX, C.ADDI, C.GADDR, C.LADDR,
		 C.COPY, C.DEREF, C.JZK, C.JNZK, C.ADDK, C.LDX, C.JNEQ, C.JNNE, C.JNLT, C.JNLE,
		 C.JNGT, C.JNGE)
		DIV, MOD, INCG, INCL = C.DIV, C.MOD, C.INCG, C.INCL
		try:
			while True:
				op = ops[pc]
				a = args[pc]
				pc += 1
				if op == LDG:
					push(unpack[a[0]](mem, a[1])[0])
				elif op == LDL:
					push(unpack[a[0]](mem, fp + a[1])[0])
				elif op == GADDR:
					push(a)
				elif op == ADDK:
					r = stack[-1] + a
					if r > MAXI or r < MINI:
						raise RunError(215)
					stack[-1] = r
				elif op == LDX:
					i = pop()
					lo = a[0]
					if a[3] and (i < lo or i > a[1]):
						raise RunError(201)
					addr = stack[-1] + (i - lo) * a[2]
					if a[4] == 'B':
						stack[-1] = mem[addr]
					else:
						stack[-1] = unpack[a[4]](mem, addr)[0]
				elif op == INCG:
					addr = a[1]
					v = unpack[a[0]](mem, addr)[0] + a[2]
					if v < a[3] or v > a[4]:
						raise RunError(201 if a[3] > MINI else 215)
					packi[a[0]](mem, addr, v)
				elif op == INCL:
					addr = fp + a[1]
					v = unpack[a[0]](mem, addr)[0] + a[2]
					if v < a[3] or v > a[4]:
						raise RunError(201 if a[3] > MINI else 215)
					packi[a[0]](mem, addr, v)
				elif op == JMP:
					pc = a
				elif op == STG:
					packi[a[0]](mem, a[1], pop())
				elif op == JNNE:
					b = pop()
					if pop() == b:
						pc = a
				elif op == INDEX:
					i = pop()
					lo = a[0]
					if a[3] and (i < lo or i > a[1]):
						raise RunError(201)
					stack[-1] += (i - lo) * a[2]
				elif op == ST:
					v = pop()
					addr = pop()
					if a == 'B':
						mem[addr] = v
					else:
						packi[a](mem, addr, v)
				elif op == JNGT:
					b = pop()
					if not pop() > b:
						pc = a
				elif op == PUSH:
					push(a)
				elif op == STL:
					packi[a[0]](mem, fp + a[1], pop())
				elif op == JZ:
					if not pop():
						pc = a
				elif op == JNEQ:
					b = pop()
					if pop() != b:
						pc = a
				elif op == JNLT:
					b = pop()
					if not pop() < b:
						pc = a
				elif op == JNLE:
					b = pop()
					if not pop() <= b:
						pc = a
				elif op == JNGE:
					b = pop()
					if not pop() >= b:
						pc = a
				elif op == JZK:
					if not stack[-1]:
						pc = a
					else:
						pop()
				elif op == JNZK:
					if stack[-1]:
						pc = a
					else:
						pop()
				elif op == CHK:
					v = stack[-1]
					if v < a[0] or v > a[1]:
						raise RunError(201)
				elif op == LD:
					if a == 'B':
						push(mem[pop()])
					else:
						push(unpack[a](mem, pop())[0])
				elif op == LADDR:
					push(fp + a)
				elif op == MUL:
					b = pop()
					r = stack[-1] * b
					if r > MAXI or r < MINI:
						raise RunError(215)
					stack[-1] = r
				elif op == MOD or op == DIV:
					b = pop()
					x = stack[-1]
					if b == 0:
						raise RunError(200)
					if x >= 0 and b > 0:
						stack[-1] = x // b if op == DIV else x % b
					else:
						q = abs(x) // abs(b)
						if (x < 0) != (b < 0):
							q = -q
						if op == DIV:
							if q > MAXI:
								raise RunError(215)
							stack[-1] = q
						else:
							stack[-1] = x - b * q
				elif op == ADD:
					b = pop()
					r = stack[-1] + b
					if r > MAXI or r < MINI:
						raise RunError(215)
					stack[-1] = r
				elif op == SUB:
					b = pop()
					r = stack[-1] - b
					if r > MAXI or r < MINI:
						raise RunError(215)
					stack[-1] = r
				elif op == LDS:
					addr = pop()
					push(bytes(mem[addr + 1:addr + 1 + mem[addr]]))
				elif op == STS:
					v = pop()
					addr = pop()
					n = len(v)
					if n > a:
						v = v[:a]
						n = a
					mem[addr] = n
					mem[addr + 1:addr + 1 + n] = v
				elif op == JNZ:
					if pop():
						pc = a
				elif op == CALL:
					r = routines[a]
					nfp = sp + 32		# room for the saved registers of a real call
					nsp = nfp + r.framesize
					if nsp > stack_end:
						raise RunError(202)
					mem[nfp:nsp] = garbage(r.framesize)
					for how, off, x in r.params:
						v = pop()
						if how == 'val':
							packi[x](mem, nfp + off, v)
						elif how == 'ref':
							SQ.pack_into(mem, nfp + off, v)
						elif how == 'str':
							n = len(v)
							if n > x:
								v = v[:x]
								n = x
							mem[nfp + off] = n
							mem[nfp + off + 1:nfp + off + 1 + n] = v
						else:
							mem[nfp + off:nfp + off + x] = mem[v:v + x]
					callstack.append((pc, fp, sp, cur))
					cur = r
					self.cur_routine = r
					fp = nfp
					sp = nsp
					pc = r.entry
				elif op == RET:
					res = cur.result
					if res is not None:
						how, off, x = res
						if how == 'val':
							push(unpack[x](mem, fp + off)[0])
						elif how == 'str':
							addr = fp + off
							push(bytes(mem[addr + 1:addr + 1 + mem[addr]]))
					pc, fp, sp, cur = callstack.pop()
					self.cur_routine = cur
				elif op == ADDI:
					stack[-1] += a
				elif op == EQ:
					b = pop()
					stack[-1] = 1 if stack[-1] == b else 0
				elif op == NE:
					b = pop()
					stack[-1] = 1 if stack[-1] != b else 0
				elif op == LT:
					b = pop()
					stack[-1] = 1 if stack[-1] < b else 0
				elif op == LE:
					b = pop()
					stack[-1] = 1 if stack[-1] <= b else 0
				elif op == GT:
					b = pop()
					stack[-1] = 1 if stack[-1] > b else 0
				elif op == GE:
					b = pop()
					stack[-1] = 1 if stack[-1] >= b else 0
				elif op == POP:
					pop()
				elif op == DUP:
					push(stack[-1])
				elif op == COPY:
					src = pop()
					dst = pop()
					mem[dst:dst + a] = mem[src:src + a]
				elif op == DEREF:
					p = stack[-1]
					if p <= 0 or p >= len(mem):
						raise RunError(216)
				else:
					pc, fp, sp = self.slow(op, a, stack, pc, fp, sp)
		except RunError:
			self.pc = pc
			raise
		except struct.error:
			self.pc = pc
			raise RunError(201)
		except (IndexError, ValueError):
			self.pc = pc
			if DEBUG:
				raise
			raise RunError(216)
		except Halt:
			self.pc = pc
			raise

	def slow(self, op, a, stack, pc, fp, sp):
		"""Less frequent instructions."""
		pop = stack.pop
		push = stack.append
		mem = self.mem
		if op == C.FADD or op == C.FSUB or op == C.FMUL:
			b = pop()
			x = stack[-1]
			if op == C.FADD:
				r = x + b
			elif op == C.FSUB:
				r = x - b
			else:
				r = x * b
			stack[-1] = self.fcheck(r, x, b)
		elif op == C.FDIV:
			b = pop()
			x = stack[-1]
			if b == 0.0:
				if x == 0.0 or x != x:
					raise RunError(207)
				raise RunError(200)
			stack[-1] = self.fcheck(x / b, x, b)
		elif op == C.I2F:
			stack[-1] = float(stack[-1])
		elif op == C.SGL:
			x = stack[-1]
			r = to_single(x)
			if r - r != 0.0 and x - x == 0.0:
				raise RunError(205)
			stack[-1] = r
		elif op == C.FNEG:
			stack[-1] = -stack[-1]
		elif op == C.DIV or op == C.MOD:
			b = pop()
			x = stack[-1]
			if b == 0:
				raise RunError(200)
			q = abs(x) // abs(b)
			if (x < 0) != (b < 0):
				q = -q
			if op == C.DIV:
				if q > MAXI:
					raise RunError(215)
				stack[-1] = q
			else:
				stack[-1] = x - b * q
		elif op == C.NEG:
			v = -stack[-1]
			if v > MAXI:
				raise RunError(215)
			stack[-1] = v
		elif op == C.AND:
			b = pop()
			stack[-1] &= b
		elif op == C.OR:
			b = pop()
			stack[-1] |= b
		elif op == C.XOR:
			b = pop()
			stack[-1] ^= b
		elif op == C.NOT:
			stack[-1] = ~stack[-1]
		elif op == C.BNOT:
			stack[-1] = 1 - stack[-1]
		elif op == C.SHL or op == C.SHR:
			b = pop() & 63
			x = stack[-1] & 0xffffffffffffffff
			r = (x << b) & 0xffffffffffffffff if op == C.SHL else x >> b
			stack[-1] = r - (1 << 64) if r >= 1 << 63 else r
		elif op == C.CONCAT:
			b = pop()
			stack[-1] = (stack[-1] + b)[:255]
		elif op == C.C2S:
			stack[-1] = bytes([stack[-1]])
		elif op == C.LDCA:
			addr = pop()
			n, zb = a
			b = bytes(mem[addr:addr + n])
			if zb:
				k = b.find(0)
				if k >= 0:
					b = b[:k]
			push(b)
		elif op == C.STCA:
			v = pop()[:a]
			addr = pop()
			mem[addr:addr + a] = v + bytes(a - len(v))
		elif op == C.SWAP:
			stack[-1], stack[-2] = stack[-2], stack[-1]
		elif op == C.FN:
			self.fn(a, stack)
		elif op == C.WR:
			self.wr(a, stack)
		elif op == C.WRLN:
			f = self.file(pop())
			f.write(EOL)
			if f.tty:
				f.flush()
		elif op == C.RD:
			self.rd(a, stack)
		elif op == C.RDLN:
			self.file(pop()).readln()
		elif op == C.SYS:
			if a == 'stack':
				debug.dump_stack(self, pc, fp, max(0, stack.pop()))
			else:
				self.pc = pc
				self.sys(a, stack)
		elif op == C.HALT:
			raise Halt(pop())
		elif op == C.NOP:
			pass
		else:
			raise AssertionError('bad opcode %d' % op)
		return pc, fp, sp

	def fcheck(self, r, x, b):
		if r - r != 0.0:		# inf or nan
			if r != r:
				if x == x and b == b:
					raise RunError(207)
			elif x - x == 0.0 and b - b == 0.0:
				raise RunError(205)
		return r

	def fn(self, name, stack):
		x = stack[-1]
		if name == 'sqrt':
			if x < 0.0 or x != x:
				raise RunError(207)
			stack[-1] = math.sqrt(x)
		elif name == 'sin':
			if x - x != 0.0:
				raise RunError(207)
			stack[-1] = math.sin(x)
		elif name == 'trunc' or name == 'round':
			if x - x != 0.0 or abs(x) >= 9.223372036854775807e18:
				raise RunError(207)
			stack[-1] = int(x) if name == 'trunc' else fpc_round(x)
		elif name == 'iabs':
			if x == MINI:
				raise RunError(215)
			stack[-1] = abs(x)
		elif name == 'fabs':
			stack[-1] = abs(x)
		elif name == 'length':
			stack[-1] = len(x)
		elif name == 'intpower' or name == 'ipow':
			e = stack.pop()
			b = stack[-1]
			if name == 'ipow':
				if e < -(1 << 31) or e > (1 << 31) - 1:
					raise RunError(201)
				b = float(b)
			try:
				r = intpower(b, e)
			except ZeroDivisionError:
				raise RunError(200)
			except OverflowError:
				raise RunError(205)
			if r - r != 0.0:
				raise RunError(205 if r == r else 207)
			if name == 'ipow':
				if abs(r) >= 9.223372036854775807e18:
					raise RunError(207)
				r = fpc_round(r)
			stack[-1] = r
		elif name == 'power':
			e = stack.pop()
			b = stack[-1]
			try:
				r = power(b, e)
			except ZeroDivisionError:
				raise RunError(200)
			except OverflowError:
				raise RunError(205)
			except ValueError:
				raise RunError(207)
			if r - r != 0.0:
				raise RunError(205 if r == r else 207)
			stack[-1] = r
		elif name == 'fmod':
			b = stack.pop()
			x = stack[-1]
			if b == 0.0:
				raise RunError(200)
			q = x / b
			c = x - b * float(math.trunc(q)) if q - q == 0.0 else math.nan
			eps = max(min(abs(c), abs(b)) * 1e-12, 1e-12)
			if abs(abs(c) - abs(b)) <= eps:
				c = 0.0
			stack[-1] = c
		else:
			raise AssertionError(name)

	# write
	def wr(self, a, stack):
		spec, hw, hd = a
		d = stack.pop() if hd else None
		w = stack.pop() if hw else None
		v = stack.pop()
		f = self.file(stack.pop())
		k = spec[0]
		if k == 'r':
			s = real_to_str(v, w, d, spec[1]).encode('latin-1')
			if w is not None and w > len(s):
				s = b' ' * (w - len(s)) + s
			f.write(s)
		else:
			if k == 'i':
				s = str(v).encode()
			elif k == 's':
				s = v
			elif k == 'c':
				s = bytes([v])
			elif k == 'b':
				s = b'TRUE' if v else b'FALSE'
			else:
				names = spec[1]
				if 0 <= v < len(names):
					s = names[v].encode('latin-1')
				else:
					raise RunError(107)
				if w is not None and w > len(s):
					s = s + b' ' * (w - len(s))
			if w is not None and w > len(s):
				s = b' ' * (w - len(s)) + s
			f.write(s)
		if f.tty:
			f.flush()

	# read
	def store_ord(self, addr, mk, lo, hi, v):
		if v < lo or v > hi:
			raise RunError(201)
		STRUCTS[mk].pack_into(self.mem, addr, v)

	def rd(self, spec, stack):
		dest = stack.pop()
		f = self.file(stack.pop())
		k = spec[0]
		mem = self.mem
		if k == 'c':
			c = f.read_char()
			self.store_ord(dest, 'B', spec[2], spec[3], c)
		elif k == 'i':
			tok = f.read_token('i')
			if not tok:
				v = 0
			else:
				v, code = val_int(tok.decode('latin-1'), spec[2], spec[3])
				if code:
					raise RunError(106)
			self.store_ord(dest, spec[1], spec[2], spec[3], v)
		elif k == 'r':
			tok = f.read_token('r')
			if tok is None:
				v = 0.0
			else:
				v, code = val_real(tok.decode('latin-1'))
				if code:
					raise RunError(106)
			STRUCTS['d'].pack_into(mem, dest, v)
		elif k == 'e':
			tok = f.read_token('e')
			if tok is None:
				return
			v, code = val_enum(tok.decode('latin-1'), spec[4])
			if code:
				raise RunError(106)
			self.store_ord(dest, spec[1], spec[2], spec[3], v)
		elif k == 's':
			s = f.read_line_chars(spec[1])
			mem[dest] = len(s)
			mem[dest + 1:dest + 1 + len(s)] = s
		elif k == 'a':
			n, zb = spec[1], spec[2]
			s = f.read_line_chars(n)
			ln = len(s)
			mem[dest:dest + ln] = s
			if zb and ln > n - 1:
				ln = n - 1
			if ln <= n - 1:
				mem[dest + ln] = 0
		else:
			raise AssertionError(spec)

	# system routines
	def sys(self, a, stack):
		mem = self.mem
		name = a if isinstance(a, str) else a[0]
		if name == 'eof':
			stack[-1] = 1 if self.file(stack[-1]).eof() else 0
		elif name == 'eoln':
			stack[-1] = 1 if self.file(stack[-1]).eoln() else 0
		elif name == 'assign':
			fname = stack.pop().decode('latin-1')
			addr = stack.pop()
			h = STRUCTS['Q'].unpack_from(mem, addr)[0]
			if 0 < h < len(self.files) and self.files[h].std is None:
				f = self.files[h]
				f.close_quiet()
				f.name = fname
			else:
				f = TextFile(fname)
				self.files.append(f)
				STRUCTS['Q'].pack_into(mem, addr, len(self.files) - 1)
		elif name == 'reset' or name == 'rewrite':
			f = self.file(stack.pop())
			self.note_open(f)
			if name == 'reset':
				f.reset()
			else:
				f.rewrite()
			f.opened_at = self.prog.lines[self.pc - 1]
		elif name == 'close':
			self.file(stack.pop()).close()
		elif name == 'new':
			addr = stack.pop()
			STRUCTS['Q'].pack_into(mem, addr, self.new(a[1], (a[3], a[2].name)))
		elif name == 'dispose':
			addr = stack.pop()
			self.dispose(STRUCTS['Q'].unpack_from(mem, addr)[0])
		elif name == 'setlength':
			n = stack.pop()
			addr = stack.pop()
			mem[addr] = max(0, min(n, 255))
		elif name == 'wrap':
			mk = a[1]
			bits = struct.calcsize(mk) * 8
			v = stack[-1] & ((1 << bits) - 1)
			if mk.islower() and v >= 1 << (bits - 1):
				v -= 1 << bits
			stack[-1] = v
		elif name == 'val':
			spec, cmk, clo, chi = a[1], a[2], a[3], a[4]
			caddr = stack.pop()
			dest = stack.pop()
			s = stack.pop().decode('latin-1')
			k = spec[0]
			if k == 'i':
				v, code = val_int(s, spec[2], spec[3])
				if code == 0 or True:
					self.store_ord(dest, spec[1], spec[2], spec[3], v)
			elif k == 'e':
				v, code = val_enum(s, spec[4])
				if code == 0:
					self.store_ord(dest, spec[1], spec[2], spec[3], v)
			else:
				v, code = val_real(s)
				STRUCTS['d'].pack_into(mem, dest, v)
			self.store_ord(caddr, cmk, clo, chi, code)
		else:
			raise AssertionError(a)


def run(prog, stack_size=DEFAULT_STACK, randomize=True, seed=None):
	vm = VM(prog, stack_size, randomize, seed)
	return vm.run()
