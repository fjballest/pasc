"""Text files (Pascal 'text') with FPC's reading rules (rtl/inc/text.inc)."""

import os
import sys

from .errors import RunError

BUFSIZE = 256		# FPC's TextRec buffer size


class TextFile:
	def __init__(self, name=None, std=None):
		self.name = name
		self.mode = 'closed'		# 'closed' 'input' 'output'
		self.buf = b''			# input data
		self.pos = 0
		self.fd = None			# stdin fd for lazy reading
		self.out = None			# binary stream for output
		self.obuf = bytearray()
		self.tty = False
		self.std = std

	# opening
	def reset(self):
		if self.std == 'input':
			self.mode = 'input'
			return
		self.close_quiet()
		try:
			with open(self.name, 'rb') as f:
				self.buf = f.read()
		except FileNotFoundError:
			raise RunError(2)
		except IsADirectoryError:
			raise RunError(2)
		except PermissionError:
			raise RunError(5)
		except OSError:
			raise RunError(2)
		self.pos = 0
		self.fd = None
		self.mode = 'input'

	def rewrite(self):
		if self.std == 'output':
			self.mode = 'output'
			return
		self.close_quiet()
		try:
			self.out = open(self.name, 'wb', buffering=0)
		except FileNotFoundError:
			raise RunError(3)
		except PermissionError:
			raise RunError(5)
		except OSError:
			raise RunError(5)
		self.mode = 'output'

	def close(self):
		if self.mode == 'closed':
			raise RunError(103)
		self.close_quiet()

	def close_quiet(self):
		if self.mode == 'output':
			self.flush()
			if self.std is None and self.out is not None:
				self.out.close()
				self.out = None
		if self.std is None:
			self.mode = 'closed'
			self.buf = b''
			self.pos = 0

	# output
	def check_out(self):
		if self.mode != 'output':
			raise RunError(105 if self.mode == 'input' else 103)

	def write(self, b):
		if self.mode != 'output':
			raise RunError(105 if self.mode == 'input' else 103)
		self.obuf += b
		if self.std:
			if len(self.obuf) >= 8192:
				self.flush()
		elif len(self.obuf) >= BUFSIZE:
			# like FPC: full 256-byte buffers go to the file; what is left
			# is only written by close (and lost if the file is not closed)
			n = len(self.obuf) - len(self.obuf) % BUFSIZE
			chunk = bytes(self.obuf[:n])
			del self.obuf[:n]
			try:
				self.out.write(chunk)
			except OSError:
				raise RunError(101)

	def flush(self):
		if self.obuf and self.out is not None:
			try:
				self.out.write(self.obuf)
				if self.std:
					self.out.flush()
			except (BrokenPipeError, OSError):
				raise RunError(101)
			self.obuf = bytearray()

	# input
	def check_in(self):
		if self.mode != 'input':
			raise RunError(104 if self.mode == 'output' else 103)

	def fill(self):
		"""True if a character is available (refilling the buffer)."""
		if self.pos < len(self.buf):
			return True
		if self.fd is None:
			return False
		if self.flushout is not None:
			self.flushout()
		try:
			data = os.read(self.fd, 65536)
		except OSError:
			data = b''
		if not data:
			return False
		self.buf = data
		self.pos = 0
		return True

	flushout = None

	def eof(self):
		self.check_in()
		return not self.fill()

	def eoln(self):
		self.check_in()
		if not self.fill():
			return True
		return self.buf[self.pos] in (10, 13)

	def read_char(self):
		self.check_in()
		if not self.fill():
			return 26
		c = self.buf[self.pos]
		self.pos += 1
		return c

	def ignore_spaces(self):
		"""Skip characters <= ' '; False if already at end of file."""
		if not self.fill():
			return False
		while self.buf[self.pos] <= 32:
			self.pos += 1
			if not self.fill():
				break
		return True

	def read_numeric(self):
		s = bytearray()
		while self.fill():
			c = self.buf[self.pos]
			if c <= 32:
				break
			if len(s) < 255:
				s.append(c)
			self.pos += 1
			if len(s) == 255:
				break
		return bytes(s)

	def read_token(self, kind):
		"""The text FPC's read() gives to val() for numbers and enums.
		Returns None when read() should leave the value as 0."""
		self.check_in()
		if not self.ignore_spaces():
			return b''
		if not self.fill():
			return None
		return self.read_numeric()

	def read_line_chars(self, maxlen):
		self.check_in()
		s = bytearray()
		while len(s) < maxlen and self.fill():
			c = self.buf[self.pos]
			if c in (10, 13):
				break
			s.append(c)
			self.pos += 1
		return bytes(s)

	def readln(self):
		self.check_in()
		if not self.fill():
			return
		while True:
			prev = self.buf[self.pos]
			self.pos += 1
			if prev == 10:
				return
			if not self.fill():
				return
			if prev == 13:
				if self.buf[self.pos] == 10:
					self.pos += 1
				return


def std_files():
	out = TextFile('stdout', std='output')
	out.mode = 'output'
	out.out = sys.stdout.buffer
	try:
		out.tty = os.isatty(sys.stdout.fileno())
	except (OSError, ValueError, AttributeError):
		out.tty = False
	inp = TextFile('stdin', std='input')
	inp.mode = 'input'
	try:
		inp.fd = sys.stdin.fileno()
	except (OSError, ValueError, AttributeError):
		inp.fd = None
	inp.flushout = out.flush
	return out, inp
