"""Lexical analysis for the pasc Pascal subset.

Identifiers and keywords are case-insensitive.  Comments are { }, (* *)
and //; { } comments may nest, as in FPC's own modes.  Compiler
directives ({$...}) are accepted and ignored: pasc always implements
{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}.
"""

from .errors import CompileError

# Reserved words in FPC's objfpc mode (a program cannot use them as names).
KEYWORDS = frozenset('''
and array as asm begin case class const constructor destructor
dispinterface div do downto else end except exports file finalization
finally for function goto if implementation in inherited initialization
inline interface is label library mod nil not object of operator or
packed procedure program property raise record repeat resourcestring set
shl shr string then threadvar to try type unit until uses var while with
xor
'''.split())

# Multi-character symbols first, so the longest match wins.
SYMBOLS = [':=', '..', '<=', '>=', '<>', '**', '(.', '.)',
	'+', '-', '*', '/', '=', '<', '>', '(', ')', '[', ']', '.', ',',
	':', ';', '^', '@']


DIGITS = '0123456789'


class Token:
	__slots__ = ('kind', 'value', 'text', 'line', 'col')

	def __init__(self, kind, value, text, line, col):
		self.kind = kind	# 'id' 'kw' 'int' 'real' 'str' 'sym' 'eof'
		self.value = value	# lowercase name, number, bytes, symbol
		self.text = text	# source spelling
		self.line = line
		self.col = col

	def desc(self):
		"""How FPC names the token in "expected but X found" messages."""
		if self.kind == 'eof':
			return 'end of file'
		if self.kind == 'id':
			return 'identifier ' + self.text.upper()
		if self.kind == 'kw':
			return self.text.upper()
		if self.kind == 'str':
			return 'constant string' if len(self.value) != 1 else 'constant char'
		if self.kind in ('int', 'real'):
			return 'ordinal const' if self.kind == 'int' else 'real const'
		return self.text

	def __repr__(self):
		return 'Token(%s,%r,%d:%d)' % (self.kind, self.text, self.line, self.col)


def tokenize(src, fname):
	"""Return the list of tokens of src (a str decoded as latin-1)."""
	toks = []
	i = 3 if src.startswith('\xef\xbb\xbf') else 0	# UTF-8 byte order mark
	n = len(src)
	line = 1
	linestart = 0

	def err(msg, ln, col):
		raise CompileError(fname, ln, col, msg)

	while True:
		# skip blanks and comments
		while i < n:
			c = src[i]
			if c == '\n':
				line += 1
				i += 1
				linestart = i
			elif c in ' \t\r\f\v\x1a':
				i += 1
			elif c == '{':
				sl, sc = line, i - linestart + 1
				depth = 1
				i += 1
				while i < n and depth > 0:
					c = src[i]
					if c == '{':
						depth += 1
					elif c == '}':
						depth -= 1
					elif c == '\n':
						line += 1
						linestart = i + 1
					i += 1
				if depth > 0:
					err('Unexpected end of file (comment not closed)', sl, sc)
			elif c == '(' and i + 1 < n and src[i+1] == '*':
				sl, sc = line, i - linestart + 1
				i += 2
				while i < n and not (src[i] == '*' and i + 1 < n and src[i+1] == ')'):
					if src[i] == '\n':
						line += 1
						linestart = i + 1
					i += 1
				if i >= n:
					err('Unexpected end of file (comment not closed)', sl, sc)
				i += 2
			elif c == '/' and i + 1 < n and src[i+1] == '/':
				while i < n and src[i] != '\n':
					i += 1
			else:
				break
		col = i - linestart + 1
		if i >= n:
			toks.append(Token('eof', None, '', line, col))
			return toks
		c = src[i]
		start = i
		if c.isalpha() or c == '_':
			while i < n and (src[i].isalnum() or src[i] == '_'):
				i += 1
			text = src[start:i]
			low = text.lower()
			if not text.isascii():
				err('Illegal character "%s"' % text, line, col)
			kind = 'kw' if low in KEYWORDS else 'id'
			toks.append(Token(kind, low, text, line, col))
		elif c in DIGITS:
			while i < n and src[i] in DIGITS:
				i += 1
			isreal = False
			# a '.' followed by a digit makes a real; '..' is a range
			if i + 1 < n and src[i] == '.' and src[i+1] in DIGITS:
				isreal = True
				i += 1
				while i < n and src[i] in DIGITS:
					i += 1
			if i < n and src[i] in 'eE':
				j = i + 1
				if j < n and src[j] in '+-':
					j += 1
				if j < n and src[j] in DIGITS:
					isreal = True
					i = j
					while i < n and src[i] in DIGITS:
						i += 1
			text = src[start:i]
			if isreal:
				toks.append(Token('real', float(text), text, line, col))
			else:
				toks.append(Token('int', int(text), text, line, col))
		elif c == '$':
			i += 1
			while i < n and src[i] in '0123456789abcdefABCDEF':
				i += 1
			text = src[start:i]
			if len(text) == 1:
				err('Illegal character "\'$\'" ($24)', line, col)
			toks.append(Token('int', int(text[1:], 16), text, line, col))
		elif c == "'" or c == '#':
			buf = bytearray()
			while i < n and src[i] in "'#":
				if src[i] == "'":
					i += 1
					while True:
						if i >= n or src[i] == '\n':
							err('String exceeds line', line, col)
						if src[i] == "'":
							if i + 1 < n and src[i+1] == "'":
								buf.append(39)
								i += 2
								continue
							i += 1
							break
						buf.append(ord(src[i]) & 0xff)
						i += 1
				else:
					i += 1
					j = i
					if i < n and src[i] == '$':
						i += 1
						while i < n and src[i] in '0123456789abcdefABCDEF':
							i += 1
						digits = src[j+1:i]
						v = int(digits, 16) if digits else -1
					else:
						while i < n and src[i] in DIGITS:
							i += 1
						digits = src[j:i]
						v = int(digits) if digits else -1
					if v < 0 or v > 255:
						err('Illegal char constant', line, col)
					buf.append(v)
			toks.append(Token('str', bytes(buf), src[start:i], line, col))
		else:
			for s in SYMBOLS:
				if src.startswith(s, i):
					break
			else:
				err('Illegal character "\'%s\'" ($%02X)' % (c, ord(c)), line, col)
			i += len(s)
			if s == '(.':
				s = '['
			elif s == '.)':
				s = ']'
			toks.append(Token('sym', s, src[start:i], line, col))
