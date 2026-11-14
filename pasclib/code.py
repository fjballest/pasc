"""The in-memory bytecode produced by the compiler and run by the VM.

The VM is a stack machine.  Scalars on the operand stack are Python ints
(ordinals, pointers, addresses) and floats (reals); shortstring values
are bytes objects.  Records and arrays are handled by address.

Memory accesses name a "kind" (struct format letter): b/B 8-bit, h/H
16-bit, i/I 32-bit, q/Q 64-bit signed/unsigned, d double.
"""

OPS = '''
	NOP PUSH POP DUP SWAP
	GADDR LADDR LDL STL LDG STG LD ST LDS STS LDCA STCA COPY ADDI INDEX DEREF
	ADD SUB MUL DIV MOD NEG CHK
	FADD FSUB FMUL FDIV FNEG I2F
	AND OR XOR NOT BNOT SHL SHR
	EQ NE LT LE GT GE
	CONCAT C2S
	JMP JZ JNZ JZK JNZK
	CALL RET HALT
	FN WR WRLN RD RDLN SYS
	ADDK LDX JNEQ JNNE JNLT JNLE JNGT JNGE SGL INCG INCL
'''.split()

for _i, _n in enumerate(OPS):
	globals()[_n] = _i


class RoutineInfo:
	def __init__(self, name, kind):
		self.name = name
		self.kind = kind		# 'procedure' 'function' 'program'
		self.entry = None
		self.framesize = 0
		self.params = []		# in pop order: (how, off, x)
		self.result = None		# (how, off, x) for functions
		self.line = 0
		self.vars = []			# (name, kind, where, type) for stack()


class Program:
	def __init__(self, fname):
		self.fname = fname
		self.ops = []
		self.args = []
		self.lines = []
		self.routines = []
		self.globsize = 0
		self.image = bytearray()	# initial contents of global memory
		self.main = None
		self.uses_math = False
		self.warnings = []
		self.globals = []		# (name, address, type) for stack()
		self.init_ranges = []		# global memory with initial values

	def emit(self, op, arg=None, line=0):
		self.ops.append(op)
		self.args.append(arg)
		self.lines.append(line)
		return len(self.ops) - 1

	def disassemble(self):
		out = []
		starts = {r.entry: r for r in self.routines}
		for pc, (op, arg) in enumerate(zip(self.ops, self.args)):
			if pc in starts:
				r = starts[pc]
				out.append('%s %s (frame %d):' % (r.kind, r.name, r.framesize))
			a = '' if arg is None else repr(arg)
			if op == CALL:
				a = self.routines[arg].name
			out.append('%5d  %4d  %-6s %s' % (pc, self.lines[pc], OPS[op], a))
		return '\n'.join(out)
