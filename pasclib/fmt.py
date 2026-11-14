"""Number formatting and math helpers that reproduce FPC's RTL.

real_to_str follows str_real() in FPC's rtl/inc/flt_core.inc (Grisu
digit generation, "round half up" for fixed notation, the aggressive
round-up of ...4999 tails, field widths and exponent digits).
"""

import math
import struct
from decimal import Decimal

_F = struct.Struct('<f')


def to_single(v):
	"""Round a double to single precision (inf on overflow)."""
	try:
		return _F.unpack(_F.pack(v))[0]
	except OverflowError:
		return math.copysign(math.inf, v)


def fpc_round(v):
	"""round(): to nearest, ties to even (the FPU default)."""
	return int(round(v))


def intpower(base, exponent):
	"""math.intpower, step by step as in FPC so results match bit for bit."""
	if base == 0.0 and exponent == 0:
		return 1.0
	i = abs(exponent)
	r = 1.0
	while i > 0:
		while (i & 1) == 0:
			i >>= 1
			base = base * base
		i -= 1
		r = r * base
	if exponent < 0:
		r = 1.0 / r
	return r


def power(base, exponent):
	"""math.power (used by the real ** operator)."""
	if exponent == 0.0:
		return 1.0
	if base == 0.0 and exponent > 0.0:
		return 0.0
	if abs(exponent) <= 2147483647 and exponent == int(exponent):
		return intpower(base, int(exponent))
	return math.exp(exponent * math.log(base))


# float_format profiles: (mantissa digits, exponent digits)
_PROFILE = {False: (17, 3), True: (10, 2)}


def _digits(v, need):
	"""Decimal digits of v > 0 rounded to 'need' significant digits as
	FPC does: returns (digits list, dot_pos)."""
	d = Decimal(v)
	sign, digs, exp = d.as_tuple()
	digs = list(digs)
	# strip leading zeros (none for normal input) and remember the
	# position of the decimal point relative to the first digit
	while len(digs) > 1 and digs[0] == 0:
		digs.pop(0)
	dot = len(digs) + exp
	# integer-part trailing zeros are kept by FPC, fractional ones are not
	if exp < 0:
		while len(digs) > max(dot, 1) and digs[-1] == 0:
			digs.pop()
	if len(digs) > need + 1:
		sticky = any(digs[need + 1:])
		digs = digs[:need + 1] + ([1] if sticky else [])
	if len(digs) > need:
		n, carry = _round(digs, need, True)
		digs = digs[:n]
		dot += carry
	return digs, dot


def _round(buf, n_max, half_even, aggressive=False):
	"""round_digits(): round buf to n_max digits in place.
	Returns (new length, decimal point correction)."""
	n = len(buf)
	dig_round = buf[n_max]
	if aggressive and not half_even and dig_round == 4 and n_max < n - 3 and buf[n - 2] >= 8:
		i = n - 2
		while True:
			i -= 1
			if i == n_max or buf[i] != 9:
				break
		if i == n_max:
			dig_round = 9
	if dig_round < 5:
		return n_max, 0
	if dig_round == 5 and half_even and (n_max == 0 or (buf[n_max - 1] & 1) == 0):
		sticky = 0
		k = n
		while k > n_max + 1 and sticky == 0:
			k -= 1
			sticky = buf[k]
		if sticky == 0:
			return n_max, 0
	k = n_max
	while k > 0:
		k -= 1
		buf[k] += 1
		if buf[k] < 10:
			return k + 1, 0
	buf[0] = 1
	return 1, 1


def real_to_str(v, width=None, prec=None, single=False):
	"""write(v), write(v:width) or write(v:width:prec)."""
	n_req, n_exp = _PROFILE[single]
	min_width = -1 if width is None else max(width, 0)
	min_width = min(min_width, 255)
	frac = -1 if prec is None else min(prec, 216)
	if width is None:
		n_sci = n_req
	else:
		n_sci = min_width - 4 - n_exp
		n_sci = max(2, min(n_sci, n_req))
	minus = math.copysign(1.0, v) < 0
	if math.isnan(v) or math.isinf(v):
		if min_width < 0:
			min_width = n_req + n_exp + 4
		if math.isnan(v):
			s = 'Nan'
		else:
			s = ('-' if minus else '+') + 'Inf'
		return s.rjust(min_width)
	if v == 0.0:
		digs, dot = [], 1
	else:
		digs, dot = _digits(abs(v), n_req)
	if frac >= 0:
		s = _fixed(minus, digs, dot, min_width, frac)
		if s is not None:
			return s
	if len(digs) > n_sci:
		digs = list(digs)
		n, carry = _round(digs, n_sci, False, True)
		digs = digs[:n]
		dot += carry
	return _exponential(minus, digs, n_sci, dot - 1, n_exp, min_width)


def _fixed(minus, digits, dot, min_width, frac):
	n_have = len(digits)
	digits = list(digits)
	cut = dot + frac
	if cut < 0:
		n_have = 0
	elif cut < n_have:
		n_have, carry = _round(digits, cut, False, True)
		dot += carry
	digits = digits[:n_have]
	if dot <= 0 or n_have == 0:
		before = ''
		before_pad = 1
	elif dot > n_have:
		before = digits
		before_pad = dot - n_have
	else:
		before = digits[:dot]
		before_pad = 0
	after_pad0 = -dot if dot < 0 else 0
	after_pad0 = min(after_pad0, frac)
	nb = len(before)
	after = digits[nb:]
	tail = frac - len(after) - after_pad0
	s = ''.join(map(str, before)) + '0' * before_pad
	if frac > 0:
		s += '.' + '0' * after_pad0 + ''.join(map(str, after)) + '0' * tail
	if minus:
		s = '-' + s
	if len(s) > 255:
		return None
	if min_width > len(s):
		s = s.rjust(min(min_width, 255))
	return s


def _exponential(minus, digits, n_req, d_exp, n_exp, min_width):
	e = str(abs(d_exp)).rjust(n_exp, '0')
	m = str(digits[0]) if digits else '0'
	if n_req > 1:
		rest = ''.join(map(str, digits[1:n_req]))
		m += '.' + rest + '0' * (n_req - 1 - len(rest))
	s = ('-' if minus else ' ') + m + 'E' + ('-' if d_exp < 0 else '+') + e
	if min_width > len(s):
		s = s.rjust(min(min_width, 255))
	return s


def val_real(s):
	"""val(s, r, code) for reals; returns (value, code)."""
	n = len(s)
	i = 0
	while i < n and s[i] in ' \t':
		i += 1
	start = i
	if i < n and s[i] in '+-':
		i += 1
	digits = 0
	while i < n and s[i].isdigit():
		i += 1
		digits += 1
	if i < n and s[i] == '.':
		i += 1
		while i < n and s[i].isdigit():
			i += 1
			digits += 1
	if digits == 0:
		return 0.0, i + 1 if i < n else max(i, 1) if n else 1
	if i < n and s[i] in 'eE':
		i += 1
		if i < n and s[i] in '+-':
			i += 1
		ed = i
		while i < n and s[i].isdigit():
			i += 1
		if i == ed:
			return 0.0, i + 1
	if i < n:
		return 0.0, i + 1
	text = s[start:i]
	if text.endswith('.'):
		text += '0'
	if text.startswith(('.', '+.', '-.')):
		text = text.replace('.', '0.', 1)
	try:
		return float(text), 0
	except ValueError:
		return 0.0, 1


def val_int(s, lo, hi):
	"""val(s, n, code) for integers (FPC's fpc_val_sint_shortstr).
	Returns (value, code); the caller range checks the value."""
	n = len(s)
	if n == 0:
		return 0, 1
	code = 0
	while code < n and s[code] in ' \t':
		code += 1
	neg = False
	if code < n and s[code] == '-':
		neg = True
		code += 1
	elif code < n and s[code] == '+':
		code += 1
	base = 10
	if code < n:
		c = s[code]
		if c in '$Xx':
			base = 16
			code += 1
		elif c == '%':
			base = 2
			code += 1
		elif c == '&':
			base = 8
			code += 1
		elif c == '0' and code + 1 < n and s[code + 1] in 'xX':
			base = 16
			code += 2
	while code < n - 1 and s[code] == '0':
		code += 1
	if code >= n:
		return 0, code + 1
	maxval = (1 << 63) - 1 + (1 if neg else 0) if base == 10 else (1 << 64) - 1
	v = 0
	while code < n:
		c = s[code]
		if '0' <= c <= '9':
			u = ord(c) - 48
		elif 'A' <= c <= 'F':
			u = ord(c) - 55
		elif 'a' <= c <= 'f':
			u = ord(c) - 87
		elif c == '\0':
			break
		else:
			u = 16
		if u >= base or v * base + u > maxval:
			return 0, code + 1
		v = v * base + u
		code += 1
	if neg:
		v = -v
	elif base != 10 and v >= 1 << 63:
		v -= 1 << 64
	return v, 0


def val_enum(s, names):
	"""val(s, e, code) for enumerations: case-insensitive name match."""
	sp = 0
	while sp < len(s) and s[sp] == ' ':
		sp += 1
	t = s[sp:].upper()
	for i, nm in enumerate(names):
		if nm.upper() == t:
			return i, 0
	# code: one past the longest matching prefix, as FPC reports it
	best = 1
	for nm in names:
		u = nm.upper()
		k = 0
		while k < len(t) and k < len(u) and t[k] == u[k]:
			k += 1
		best = max(best, k + 1)
	return 0, best + sp
