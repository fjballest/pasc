"""Syntax tree nodes produced by the parser.

Every node records the source position (line, col) where it starts.
The checker annotates expression nodes with .type and .const (the folded
value, or None when the expression is not constant).
"""


class Node:
	_fields = ()

	def __init__(self, pos, *args):
		self.line, self.col = pos
		assert len(args) == len(self._fields), (type(self).__name__, args)
		for f, a in zip(self._fields, args):
			setattr(self, f, a)

	@property
	def pos(self):
		return (self.line, self.col)

	def __repr__(self):
		return '%s(%s)' % (type(self).__name__,
			', '.join('%s=%r' % (f, getattr(self, f)) for f in self._fields))


def node(name, fields):
	return type(name, (Node,), {'_fields': tuple(fields.split())})


# program structure
Program = node('Program', 'name uses decls body endpos')
ConstDecl = node('ConstDecl', 'name typ init')		# typ None: untyped constant
TypeDecl = node('TypeDecl', 'name typ')
VarDecl = node('VarDecl', 'names typ init')		# names: [(name, pos)]
Param = node('Param', 'names mode typ')			# mode: 'value' or 'var'
Routine = node('Routine', 'kind name params rettype decls body')

# type expressions
TName = node('TName', 'name')
TSubrange = node('TSubrange', 'lo hi')
TEnum = node('TEnum', 'names')				# [(name, pos)]
TArray = node('TArray', 'indexes elem')
TRecord = node('TRecord', 'fields')			# [([(name,pos)], type)]
TPointer = node('TPointer', 'target')			# a TName
TString = node('TString', 'size')			# size expr or None

# typed constant initialisers
InitList = node('InitList', 'items')
InitRecord = node('InitRecord', 'fields')		# [(name, pos, init)]

# statements
Compound = node('Compound', 'stmts')
Assign = node('Assign', 'target expr')
ProcCall = node('ProcCall', 'call')			# call: Name or Call expr
If = node('If', 'cond then else_')
While = node('While', 'cond body')
Repeat = node('Repeat', 'stmts cond')
For = node('For', 'var start stop down body')
ForIn = node('ForIn', 'var typ body')
Case = node('Case', 'expr branches else_')		# branches: [([(lo,hi)], stmt)]
Empty = node('Empty', '')

# expressions
IntLit = node('IntLit', 'value')
RealLit = node('RealLit', 'value text')
StrLit = node('StrLit', 'value')			# bytes
NilLit = node('NilLit', '')
Name = node('Name', 'name text')
Field = node('Field', 'base name text')
Index = node('Index', 'base indexes')
Deref = node('Deref', 'base')
Call = node('Call', 'func args')			# args: [Arg]
Arg = node('Arg', 'expr width prec')
Unary = node('Unary', 'op expr')
Binary = node('Binary', 'op left right')
AddrOf = node('AddrOf', 'expr')
