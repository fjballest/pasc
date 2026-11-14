"""Indentation checks.

A badly indented program is a compile error: statements of a block must be
indented more than the line that opens the block and all start at the
same column, and 'end', 'else' and 'until' line up with the line that
opened them.  Only statements and keywords that start a line are checked,
so a short statement may share a line with others.  Tabs count as 8
columns.  Indenting with spaces where other lines use tabs is a warning.
"""

from . import ast as A
from .errors import CompileError


class Indent:
	def __init__(self, tree, fname):
		self.fname = fname
		self.toks = tree.tokens
		self.lines = tree.source.split('\n')
		self.at = {(t.line, t.col): i for i, t in enumerate(self.toks)}

	# columns
	def vcol(self, line, col):
		text = self.lines[line - 1] if 0 < line <= len(self.lines) else ''
		return len(text[:col - 1].expandtabs(8)) + 1

	def first(self, line, col):
		"""Is (line, col) the first thing on its line?"""
		text = self.lines[line - 1] if 0 < line <= len(self.lines) else ''
		return text[:col - 1].strip() == ''

	def indent(self, line):
		"""Visual column of the first character of a line."""
		text = self.lines[line - 1]
		n = len(text) - len(text.lstrip())
		return len(text[:n].expandtabs(8)) + 1

	def tok(self, i):
		return self.toks[i]

	def error(self, line, col, msg):
		raise CompileError(self.fname, line, col, 'bad indentation: ' + msg)

	# checks
	def check_list(self, stmts, base, what):
		"""Statements that start a line: same column, deeper than base."""
		col = None
		for st in stmts:
			if isinstance(st, A.Empty) or not hasattr(st, 'tok0'):
				continue
			t = self.tok(st.tok0)
			if not self.first(t.line, t.col):
				continue
			c = self.vcol(t.line, t.col)
			if c <= base:
				self.error(t.line, t.col, 'this statement must be indented more than %s' % what)
			if col is None:
				col = c
			elif c != col:
				self.error(t.line, t.col, 'statements of the same block must start at the same column')

	def align(self, t, base, what):
		if self.first(t.line, t.col) and self.vcol(t.line, t.col) != base:
			self.error(t.line, t.col, '"%s" must line up with %s' % (t.text, what))

	def body(self, st, ownerline, what):
		"""The statement controlled by if/while/for/else/a case label."""
		if st is None or isinstance(st, A.Empty) or not hasattr(st, 'tok0'):
			return
		base = self.indent(ownerline)
		t = self.tok(st.tok0)
		if isinstance(st, A.Compound):
			# 'begin' may end the owner line (even a continuation line of a
			# long condition) or start a line of its own
			if self.first(t.line, t.col):
				if self.vcol(t.line, t.col) < base:
					self.error(t.line, t.col, '"begin" must not be indented less than %s' % what)
				self.compound(st)
			else:
				self.compound(st, base)
			return
		if self.first(t.line, t.col) and self.vcol(t.line, t.col) <= base:
			self.error(t.line, t.col, 'this statement must be indented more than %s' % what)
		self.stmt(st)

	def compound(self, c, base=None):
		begin = self.tok(c.tok0)
		end = self.tok(c.tok1 - 1)
		if base is None:
			base = self.indent(begin.line)
		self.check_list(c.stmts, base, 'the line with its "begin"')
		self.align(end, base, 'the line with its "begin"')
		for s in c.stmts:
			self.stmt(s)

	def find(self, kw, lo, hi):
		"""Index of keyword kw among tokens lo..hi-1 (last one)."""
		for i in range(hi - 1, lo - 1, -1):
			t = self.toks[i]
			if t.kind in ('kw', 'id') and t.value == kw:
				return i
		return None

	def stmt(self, st):
		if isinstance(st, A.Compound):
			self.compound(st)
		elif isinstance(st, A.If):
			line = self.tok(st.tok0).line
			self.body(st.then, line, 'its "if"')
			if st.else_ is not None and hasattr(st.else_, 'tok0'):
				k = self.find('else', st.then.tok1, st.else_.tok0)
				if k is not None:
					e = self.tok(k)
					self.align(e, self.indent(line), 'its "if"')
					self.body(st.else_, e.line, 'its "else"')
		elif isinstance(st, (A.While, A.For, A.ForIn)):
			self.body(st.body, self.tok(st.tok0).line, 'its "%s"' % self.tok(st.tok0).text)
		elif isinstance(st, A.Repeat):
			line = self.tok(st.tok0).line
			base = self.indent(line)
			self.check_list(st.stmts, base, 'its "repeat"')
			for s in st.stmts:
				self.stmt(s)
			k = self.find('until', st.tok0, st.tok1)
			if k is not None:
				self.align(self.tok(k), base, 'its "repeat"')
		elif isinstance(st, A.Case):
			self.case(st)

	def case(self, st):
		line = self.tok(st.tok0).line
		base = self.indent(line)
		labcol = None
		for labels, s in st.branches:
			lo = labels[0][0]
			if self.first(lo.line, lo.col):
				c = self.vcol(lo.line, lo.col)
				if c < base:
					self.error(lo.line, lo.col, 'case labels must not be indented less than their "case"')
				if labcol is None:
					labcol = c
				elif c != labcol:
					self.error(lo.line, lo.col, 'the labels of a case must start at the same column')
			self.body(s, lo.line, 'its case label')
		last = st.branches[-1][1]
		if st.else_:
			first = next((s for s in st.else_ if hasattr(s, 'tok0') and not isinstance(s, A.Empty)), None)
			k = self.find('else', last.tok1, first.tok0) if first else None
			if k is None and first is not None:
				k = self.find('otherwise', last.tok1, first.tok0)
			if k is not None:
				e = self.tok(k)
				if self.first(e.line, e.col) and self.vcol(e.line, e.col) not in (base, labcol):
					self.error(e.line, e.col, '"%s" must line up with the case labels or its "case"' % e.text)
				self.check_list(st.else_, self.indent(e.line), 'its "%s"' % e.text)
				for s in st.else_:
					self.stmt(s)
		k = self.find('end', last.tok1, st.tok1)
		if k is not None:
			self.align(self.tok(k), base, 'its "case"')

	def routine_body(self, r):
		head = self.indent(r.line)
		begin = self.tok(r.body.tok0)
		self.align(begin, head, 'its procedure or function heading')
		self.compound(r.body, head)

	def tabs_warning(self):
		"""Indentation with spaces in a file that also indents with tabs."""
		tabs = spaces = 0
		first = None
		for i, text in enumerate(self.lines):
			if not text.strip():
				continue
			lead = text[:len(text) - len(text.lstrip())]
			if (i + 1, len(lead) + 1) not in self.at:
				continue	# inside a comment or a string
			if '\t' in lead:
				tabs += 1
			if ' ' in lead:
				spaces += 1
				if first is None:
					first = i + 1
		if spaces and tabs and first is not None:
			more = '' if spaces == 1 else ' (and %d more lines)' % (spaces - 1)
			return '%s:%d:1: warning: indentation uses spaces%s: indent with tabs' % (self.fname, first, more)
		return None


def check_indentation(tree, fname):
	"""Raise CompileError for bad indentation; return warnings."""
	ind = Indent(tree, fname)
	for d in tree.decls:
		if isinstance(d, A.Routine):
			ind.routine_body(d)
	ind.compound(tree.body, ind.indent(tree.body.line))
	w = ind.tabs_warning()
	return [w] if w else []
