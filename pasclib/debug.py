"""Debugging aids for students: the stack() builtin and the leak report."""

import struct
import sys

MAXLINE = 200		# characters shown for one variable
MAXELEMS = 12		# array elements shown


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
			items = []
			n = min(t.count, MAXELEMS)
			for i in range(n):
				items.append(self.value(t.elem, addr + i * t.elem.size, depth + 1))
			if t.count > n:
				items.append('... %d more' % (t.count - n))
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


def dump_stack(vm, pc, fp, out=None):
	out = out or sys.stderr
	vm.flush_all()
	prog = vm.prog
	f = Formatter(vm)
	frames = [(vm.cur_routine, fp, pc - 1)]
	for (rpc, rfp, rsp, r) in reversed(vm.callstack):
		frames.append((r, rfp, rpc - 1))
	lines = ['--- stack() at %s ---' % vm.where(pc - 1)]
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
				if kind == 'result':
					kind = 'result'
				else:
					kind = 'var param'
				if not (16 <= addr < len(vm.mem)):
					addr = None
			else:
				addr = rfp + off
			lines.append(f.var_line(name, kind, t, addr))
	if prog.globals:
		lines.append('   global variables')
		for name, addr, t in prog.globals:
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
