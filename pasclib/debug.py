"""Debugging aids for students: the stack() builtin and the leak report."""

import struct
import sys

MAXLINE = 200		# characters shown for one variable
MAXELEMS = 12		# array elements shown
MAXSCAN = 4000		# array elements examined to find runs of equal values
RUN = 3			# longer runs of equal (or garbage) elements are abbreviated


def is_garbage(text):
	return '<garbage' in text or '<out of range' in text or '<invalid' in text or '<dangling' in text


def runs(keys):
	"""Group consecutive equal keys (garbage counts as equal to garbage).
	Yields (start, end) index ranges, end exclusive."""
	i = 0
	n = len(keys)
	while i < n:
		j = i + 1
		k = 'garbage' if is_garbage(keys[i]) else keys[i]
		while j < n and ('garbage' if is_garbage(keys[j]) else keys[j]) == k:
			j += 1
		yield i, j
		i = j


def abbreviate(keys):
	"""Indexes to show: runs longer than RUN show their first two elements,
	'...' (None) and the last one."""
	out = []
	for i, j in runs(keys):
		if j - i > RUN:
			out += [i, i + 1, None, j - 1]
		else:
			out += list(range(i, j))
	return out



def char_repr(c):
	if 32 <= c < 127 and c != 39:
		return "'%s'" % chr(c)
	if c == 39:
		return "''''"
	return '#%d' % c


def str_repr(b):
	"""Pascal-like literal for the bytes b: 'abc'#10'de'."""
	out = []
	quoted = False
	for c in b:
		if 32 <= c < 127:
			if not quoted:
				out.append("'")
				quoted = True
			out.append("''" if c == 39 else chr(c))
		else:
			if quoted:
				out.append("'")
				quoted = False
			out.append('#%d' % c)
	if quoted:
		out.append("'")
	return ''.join(out) or "''"


FRIENDLY = {'LongInt': 'integer', 'ShortString': 'string', 'Real': 'real', 'Char': 'char',
	'Boolean': 'boolean', 'Text': 'text'}


def tname(t):
	return FRIENDLY.get(t.name, t.name)


class Formatter:
	def __init__(self, vm):
		self.vm = vm
		self.mem = vm.mem

	def value(self, t, addr, depth=0):
		mem = self.mem
		if addr < 0 or addr + t.size > len(mem):
			return '<invalid address>'
		if t.is_ord:
			v = struct.unpack_from('<' + t.mk, mem, addr)[0]
			if t.is_char:
				return char_repr(v)
			if t.is_bool:
				return ('FALSE', 'TRUE')[v] if v in (0, 1) else '<garbage %d>' % v
			if t.is_enum:
				if 0 <= v < len(t.names):
					return t.names[v]
				return '<garbage %d>' % v
			if not (t.lo <= v <= t.hi):
				return '%d <out of range %d..%d>' % (v, t.lo, t.hi)
			return str(v)
		if t.is_real:
			v = struct.unpack_from('<d', mem, addr)[0]
			return repr(v)
		if t.is_string:
			n = mem[addr]
			s = str_repr(bytes(mem[addr + 1:addr + 1 + min(n, t.maxlen)]))
			if n > t.maxlen:
				return '%s <garbage length %d>' % (s, n)
			return s
		if t.is_array:
			if t.is_chararray():
				return str_repr(bytes(mem[addr:addr + t.count]))
			if depth > 3:
				return '[...]'
			scan = min(t.count, MAXSCAN)
			vals = [self.value(t.elem, addr + i * t.elem.size, depth + 1) for i in range(scan)]
			items = []
			for i in abbreviate(vals):
				if len(items) >= MAXELEMS:
					items.append('... %d more' % (t.count - i if i is not None else 0))
					break
				items.append('...' if i is None else vals[i])
			else:
				if t.count > scan:
					items.append('... %d more' % (t.count - scan))
			return '[' + ', '.join(items) + ']'
		if t.is_record:
			if depth > 3:
				return '(...)'
			parts = []
			for key, (off, ft, spelling) in t.fields.items():
				parts.append('%s: %s' % (spelling, self.value(ft, addr + off, depth + 1)))
			return '(' + '; '.join(parts) + ')'
		if t.is_pointer:
			p = struct.unpack_from('<Q', mem, addr)[0]
			return self.pointer(p, t, depth)
		if t.is_file:
			h = struct.unpack_from('<Q', mem, addr)[0]
			files = self.vm.files
			if 0 < h < len(files):
				f = files[h]
				return '<text %s, %s>' % (f.name, f.mode)
			return '<text, not assigned>'
		return '?'

	def pointer(self, p, t, depth):
		vm = self.vm
		if p == 0:
			return 'nil'
		if p in vm.heap_live:
			if depth > 1 or t.target is None:
				return '^heap@%d' % p
			return '^' + self.value(t.target, p, depth + 2)
		if p in vm.heap_dead:
			return '<dangling pointer: memory was disposed>'
		if 16 <= p < vm.stack_end:
			return '^@%d' % p
		return '<garbage pointer>'

	def var_line(self, name, kind, t, addr):
		if kind == 'var param':
			if addr is None:
				val = '<invalid>'
			else:
				val = self.value(t, addr)
			text = '%s: %s = %s' % (name, tname(t), val)
			label = 'var parameter'
		else:
			text = '%s: %s = %s' % (name, tname(t), self.value(t, addr))
			label = {'param': 'parameter', 'local': 'local', 'result': 'function result'}.get(kind, kind)
		if len(text) > MAXLINE:
			text = text[:MAXLINE - 3] + '...'
		return '      %s  {%s}' % (text, label)


class Pretty:
	"""stack(level) for level >= 1: one line per field or element, indented.
	Structures nest up to level + 1 deep, pointers are followed level times
	and arrays show up to 8 * level elements."""

	def __init__(self, f, level):
		self.f = f
		self.level = level
		self.maxdepth = level + 1
		self.maxelems = 8 * level

	def lines(self, prefix, t, addr, ind, depth=0, ptrs=0, seen=None):
		"""Lines showing 'prefix' followed by the value of type t at addr."""
		f = self.f
		pad = '      ' + '    ' * ind
		seen = seen or set()
		if addr is None or addr < 0 or addr + t.size > len(f.mem):
			return [pad + prefix + '<invalid address>']
		if t.is_record and depth < self.maxdepth:
			out = [pad + prefix + '(']
			for key, (off, ft, spelling) in t.fields.items():
				out += self.lines(spelling + ': ', ft, addr + off, ind + 1, depth + 1, ptrs, seen)
			return out + [pad + ')']
		if t.is_array and not t.is_chararray() and depth < self.maxdepth:
			out = [pad + prefix + '[']
			scan = min(t.count, MAXSCAN)
			keys = [f.value(t.elem, addr + i * t.elem.size, depth + 1) for i in range(scan)]
			shown = 0
			for i in abbreviate(keys):
				if shown >= self.maxelems:
					out.append(pad + '    ... %d more' % (t.count - (i if i is not None else scan)))
					break
				if i is None:
					out.append(pad + '    ...')
					continue
				shown += 1
				idx = t.lo + i
				if t.index.is_char:
					label = char_repr(idx)
				elif t.index.is_enum:
					label = t.index.names[idx]
				elif t.index.is_bool:
					label = ('FALSE', 'TRUE')[idx]
				else:
					label = str(idx)
				out += self.lines('[%s] = ' % label, t.elem, addr + i * t.elem.size, ind + 1, depth + 1, ptrs, seen)
			else:
				if t.count > scan:
					out.append(pad + '    ... %d more' % (t.count - scan))
			return out + [pad + ']']
		if t.is_pointer and t.target is not None:
			p = struct.unpack_from('<Q', f.mem, addr)[0]
			vm = f.vm
			if p in vm.heap_live and ptrs < self.level:
				if p in seen:
					return [pad + prefix + '^heap@%d (already shown above)' % p]
				return self.lines(prefix + '^heap@%d -> ' % p, t.target, p, ind, depth, ptrs + 1, seen | {p})
		text = pad + prefix + f.value(t, addr, depth)
		if len(text) > MAXLINE + len(pad):
			text = text[:MAXLINE + len(pad) - 3] + '...'
		return [text]

	def var(self, name, kind, t, addr):
		label = {'param': 'parameter', 'local': 'local', 'result': 'function result',
			'var param': 'var parameter', 'global': 'global'}.get(kind, kind)
		out = self.lines('%s: %s = ' % (name, tname(t)), t, addr, 0)
		if kind != 'global':
			out[0] += '  {%s}' % label
		return out


def dump_stack(vm, pc, fp, level=0, out=None):
	out = out or sys.stderr
	vm.flush_all()
	prog = vm.prog
	f = Formatter(vm)
	frames = [(vm.cur_routine, fp, pc - 1)]
	for (rpc, rfp, rsp, r) in reversed(vm.callstack):
		frames.append((r, rfp, rpc - 1))
	pretty = Pretty(f, level) if level > 0 else None
	lines = ['--- stack(%d) at %s ---' % (level, vm.where(pc - 1)) if level else '--- stack() at %s ---' % vm.where(pc - 1)]
	shown = frames if len(frames) <= 12 else frames[:8] + [None] + frames[-3:]
	for fr in shown:
		if fr is None:
			lines.append('   ... %d more calls ...' % (len(frames) - 11))
			continue
		r, rfp, rpc = fr
		lines.append('   %s, line %d' % (vm.rname(r), prog.lines[rpc] if 0 <= rpc < len(prog.lines) else 0))
		for name, kind, where, t in r.vars:
			wk, off = where
			if wk == 'r':
				addr = struct.unpack_from('<Q', vm.mem, rfp + off)[0]
				if kind not in ('result', 'param'):
					kind = 'var param'
				if not (16 <= addr < len(vm.mem)):
					addr = None
			else:
				addr = rfp + off
			if pretty:
				lines += pretty.var(name, kind, t, addr)
			else:
				lines.append(f.var_line(name, kind, t, addr))
	if prog.globals:
		lines.append('   global variables')
		for name, addr, t in prog.globals:
			if pretty:
				lines += pretty.var(name, 'global', t, addr)
			else:
				lines.append(f.var_line(name, 'global', t, addr).replace('  {global}', ''))
	n = len(vm.heap_live)
	lines.append('   heap: %d block%s in use (%d bytes)' % (n, '' if n == 1 else 's',
		sum(sz for sz, _ in vm.heap_live.values())))
	lines.append('---')
	out.write('\n'.join(lines) + '\n')
	out.flush()


def leak_report(vm, out=None):
	if not vm.heap_live:
		return
	out = out or sys.stderr
	sites = {}
	total = 0
	for addr, (size, site) in vm.heap_live.items():
		k = site
		sites.setdefault(k, [0, 0])
		sites[k][0] += 1
		sites[k][1] += size
		total += size
	n = len(vm.heap_live)
	lines = ['Memory leak: %d block%s (%d bytes) allocated with new %s never disposed:'
		% (n, '' if n == 1 else 's', total, 'was' if n == 1 else 'were')]
	for (line, tname), (count, size) in sorted(sites.items()):
		lines.append('  %d x %s (%d bytes) allocated at %s:%d' % (count, tname, size, vm.prog.fname, line))
	vm.flush_all()
	out.write('\n'.join(lines) + '\n')
	out.flush()
