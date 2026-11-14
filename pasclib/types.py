"""Pascal types as seen by the checker and code generator.

Sizes follow FPC on 64-bit targets.  Values of every type live in a flat
byte memory (see vm.py); the 'mk' attribute names the memory access kind
used to load and store a scalar of that type.
"""

INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


class Type:
	size = 0
	mk = None		# memory kind for scalars
	name = '?'

	def __repr__(self):
		return self.name

	# classification helpers
	is_ord = is_int = is_char = is_bool = is_enum = False
	is_real = is_string = is_array = is_record = is_pointer = is_file = False
	is_nil = False

	def is_chararray(self):
		return False

	def structured(self):
		"""Values passed around by address (copied as blocks)."""
		return False


class OrdType(Type):
	"""integer, int64, char, boolean, enumerations and their subranges."""
	is_ord = True

	def __init__(self, kind, lo, hi, name, base=None, names=None):
		self.kind = kind		# 'int' 'char' 'bool' 'enum'
		self.lo = lo
		self.hi = hi
		self.name = name
		self.base = base or self	# host type of a subrange
		self.names = names if names is not None else (base.names if base else None)
		self.is_int = kind == 'int'
		self.is_char = kind == 'char'
		self.is_bool = kind == 'bool'
		self.is_enum = kind == 'enum'
		if kind == 'int':
			if base is None:
				self.size = 8 if (lo < -(1 << 31) or hi > (1 << 31) - 1) else 4
			elif lo >= 0 and hi <= 0xff:
				self.size = 1
			elif lo >= -0x80 and hi <= 0x7f:
				self.size = 1
			elif lo >= 0 and hi <= 0xffff:
				self.size = 2
			elif lo >= -0x8000 and hi <= 0x7fff:
				self.size = 2
			elif lo >= 0 and hi <= 0xffffffff:
				self.size = 4
			elif lo >= -(1 << 31) and hi <= (1 << 31) - 1:
				self.size = 4
			else:
				self.size = 8
			signed = lo < 0
			self.mk = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}[self.size]
			if not signed:
				self.mk = self.mk.upper()
		elif kind in ('char', 'bool'):
			self.size = 1
			self.mk = 'B'
		else:
			self.size = 4
			self.mk = 'i'

	def root(self):
		"""Types with the same root are assignment compatible."""
		t = self
		while t.base is not t:
			t = t.base
		if t.kind == 'int':
			return 'int'
		return t

	def contains(self, other):
		return self.lo <= other.lo and other.hi <= self.hi

	def is_subrange(self):
		return self.base is not self


class RealType(Type):
	is_real = True

	def __init__(self, name, single=False):
		self.name = name
		self.single = single
		self.size = 4 if single else 8
		self.mk = 'f' if single else 'd'


class StringType(Type):
	"""shortstring: a length byte followed by maxlen chars."""
	is_string = True

	def __init__(self, maxlen, name=None):
		self.maxlen = maxlen
		self.size = maxlen + 1
		self.name = name or ('ShortString' if maxlen == 255 else 'String[%d]' % maxlen)

	def structured(self):
		return True


class ArrayType(Type):
	is_array = True

	def __init__(self, index, elem, name=None):
		self.index = index		# an OrdType
		self.elem = elem
		self.lo = index.lo
		self.hi = index.hi
		self.count = index.hi - index.lo + 1
		self.size = self.count * elem.size
		self.name = name or 'Array[%s..%s] Of %s' % (self.lo, self.hi, elem.name)

	def is_chararray(self):
		return self.elem.is_ord and self.elem.kind == 'char' and self.elem.base is self.elem

	def structured(self):
		return True


class RecordType(Type):
	is_record = True

	def __init__(self, fields, name=None):
		self.fields = {}		# lowercase name -> (offset, type, spelling)
		off = 0
		for fname, spelling, ftype in fields:
			self.fields[fname] = (off, ftype, spelling)
			off += ftype.size
		self.size = off
		self.name = name or 'record'

	def structured(self):
		return True


class PointerType(Type):
	is_pointer = True
	size = 8
	mk = 'Q'

	def __init__(self, target, name=None):
		self.target = target		# may be filled in later (forward)
		self._name = name

	@property
	def name(self):
		if self._name:
			return self._name
		return '^' + (self.target.name if self.target else '?')


class NilType(Type):
	is_nil = True
	is_pointer = True
	size = 8
	mk = 'Q'
	name = 'Pointer'


class FileType(Type):
	"""text: 8 bytes holding a VM file handle."""
	is_file = True
	size = 8
	mk = 'Q'
	name = 'Text'


INTEGER = OrdType('int', -(1 << 31), (1 << 31) - 1, 'LongInt')
INT64 = OrdType('int', INT64_MIN, INT64_MAX, 'Int64')
CHAR = OrdType('char', 0, 255, 'Char')
BOOLEAN = OrdType('bool', 0, 1, 'Boolean', names=['FALSE', 'TRUE'])
REAL = RealType('Real')
DOUBLE = REAL
SINGLE = RealType('Single', single=True)
STRING = StringType(255)
TEXT = FileType()
NIL = NilType()


def is_structured(t):
	return t.structured()


def same_type(a, b):
	"""Type identity, as required for var parameters."""
	if a is b:
		return True
	if a.is_string and b.is_string:
		return a.maxlen == b.maxlen
	if a.is_pointer and b.is_pointer and not a.is_nil and not b.is_nil:
		return a.target is b.target
	if a.is_real and b.is_real:
		return a.single == b.single
	if a.is_file and b.is_file:
		return True
	if a.is_array and b.is_array:
		# FPC treats arrays with the same bounds and element type as equal
		return a.lo == b.lo and a.hi == b.hi and a.index.root() == b.index.root() \
			and same_type(a.elem, b.elem)
	return False
