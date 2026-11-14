"""JSON descriptions of a paused pasc VM, for the pascdb browser view."""

import struct

from pasclib.debug import char_repr, str_repr, tname

MAXELEMS = 200		# array elements described
MAXDEPTH = 8		# nesting of records and arrays


class Describer:
	def __init__(self, vm):
		self.vm = vm
		self.mem = vm.mem

	def unpack(self, fmt, addr):
		return struct.unpack_from('<' + fmt, self.mem, addr)[0]

	def ok(self, addr, size):
		return addr is not None and 0 < addr and addr + size <= len(self.mem)

	def value(self, t, addr, depth=0):
		"""A tree describing the value of type t stored at addr."""
		d = {'a': addr, 's': t.size, 't': tname(t)}
		if not self.ok(addr, t.size):
			d.update(k='bad', v='<dirección no válida>', g=True)
			return d
		if t.is_ord:
			v = self.unpack(t.mk, addr)
			g = not (t.lo <= v <= t.hi)
			if t.is_char:
				text = char_repr(v)
			elif t.is_bool:
				text = ('FALSE', 'TRUE')[v] if v in (0, 1) else str(v)
			elif t.is_enum:
				text = t.names[v] if 0 <= v < len(t.names) else str(v)
			else:
				text = str(v)
			d.update(k='scalar', v=text, g=g)
		elif t.is_real:
			v = self.unpack('d', addr)
			d.update(k='scalar', v=repr(v), g=v != v)
		elif t.is_string:
			n = self.mem[addr]
			text = str_repr(bytes(self.mem[addr + 1:addr + 1 + min(n, t.maxlen)]))
			d.update(k='str', v=text, n=n, m=t.maxlen, g=n > t.maxlen)
		elif t.is_array and t.is_chararray():
			d.update(k='str', v=str_repr(bytes(self.mem[addr:addr + t.count])), n=t.count, m=t.count, g=False)
		elif t.is_array:
			items = []
			if depth < MAXDEPTH:
				n = min(t.count, MAXELEMS)
				for i in range(n):
					idx = t.lo + i
					if t.index.is_char:
						label = char_repr(idx)
					elif t.index.is_enum:
						label = t.index.names[idx]
					elif t.index.is_bool:
						label = ('FALSE', 'TRUE')[idx]
					else:
						label = str(idx)
					items.append({'i': label, 'v': self.value(t.elem, addr + i * t.elem.size, depth + 1)})
			d.update(k='array', items=items, more=t.count - len(items), count=t.count)
		elif t.is_record:
			fields = []
			if depth < MAXDEPTH:
				for key, (off, ft, spelling) in t.fields.items():
					fields.append({'n': spelling, 'v': self.value(ft, addr + off, depth + 1)})
			d.update(k='record', f=fields)
		elif t.is_pointer:
			p = self.unpack('Q', addr)
			vm = self.vm
			if p == 0:
				st = 'nil'
			elif p in vm.heap_live:
				st = 'heap'
			elif p in vm.heap_dead:
				st = 'dangling'
			elif 16 <= p < vm.stack_end:
				st = 'mem'
			else:
				st = 'garbage'
			d.update(k='ptr', p=p, st=st)
		elif t.is_file:
			h = self.unpack('Q', addr)
			files = self.vm.files
			if 0 < h < len(files):
				f = files[h]
				text = '%s (%s)' % (f.name, {'closed': 'cerrado', 'input': 'lectura',
					'output': 'escritura'}.get(f.mode, f.mode))
			else:
				text = 'sin asignar'
			d.update(k='scalar', v=text, g=False)
		else:
			d.update(k='scalar', v='?', g=False)
		return d

	def hexbytes(self, addr, size):
		if not self.ok(addr, size):
			return ''
		return bytes(self.mem[addr:addr + size]).hex()


def where_line(prog, pc):
	return prog.lines[pc] if 0 <= pc < len(prog.lines) else 0


def snapshot(vm, pc, fp, sp, pos):
	"""Everything the browser shows, with the VM stopped before line:col pos."""
	prog = vm.prog
	desc = Describer(vm)
	cur = vm.cur_routine
	frames = []
	stack = [(cur, fp, pc - 1, None)] + [(r, rfp, rpc - 1, (rpc, rfp, rsp))
		for (rpc, rfp, rsp, r) in reversed(vm.callstack)]
	# each frame's caller data (return address, saved fp) is stored by the
	# callee's CALL in the 32 bytes just below the callee's frame
	for k, (r, rfp, rpc, saved) in enumerate(stack):
		f = {
			'name': vm.rname(r),
			'routine': r.name,
			'line': where_line(prog, rpc),
			'fp': rfp,
			'size': r.framesize,
			'vars': [],
			'slots': [],
		}
		for name, kind, (wk, off), t in r.vars:
			slot = rfp + off
			if wk == 'r':
				ref = desc.unpack('Q', slot)
				f['slots'].append({'a': slot, 's': 8, 'n': name, 'kind': kind + (
					', pasado por referencia: no se cambia' if kind == 'param' else '') + ' (dirección)',
					'hex': desc.hexbytes(slot, 8), 'v': '-> %d' % ref})
				val = desc.value(t, ref) if desc.ok(ref, t.size) else {'k': 'bad', 'v': '<no válida>', 'g': True,
					'a': ref, 's': t.size, 't': tname(t)}
				f['vars'].append({'n': name, 'kind': kind, 'ref': True, 'v': val})
			else:
				val = desc.value(t, slot)
				f['vars'].append({'n': name, 'kind': kind, 'v': val})
				f['slots'].append({'a': slot, 's': t.size, 'n': name, 'kind': kind,
					'hex': desc.hexbytes(slot, min(t.size, 64)), 'more': max(0, t.size - 64),
					'v': val.get('v', '') if val['k'] in ('scalar', 'str', 'ptr') else
					('(%s)' % val['t'])})
			if val.get('k') == 'ptr':
				f['slots'][-1]['v'] = 'nil' if val['p'] == 0 else '-> %d' % val['p']
		if r is not prog.main:
			hdr = rfp - 32
			f['ret'] = {'a': hdr, 'pc': desc.unpack('Q', hdr), 'line': where_line(prog, desc.unpack('Q', hdr) - 1),
				'savedfp': desc.unpack('Q', hdr + 8)}
		frames.append(f)
	globs = []
	gslots = []
	for name, addr, t in prog.globals:
		val = desc.value(t, addr)
		globs.append({'n': name, 'kind': 'global', 'v': val})
		gslots.append({'a': addr, 's': t.size, 'n': name})
	heap = []
	for addr in sorted(vm.heap_live):
		size, (line, tn) = vm.heap_live[addr]
		t = vm.heap_types.get(addr)
		val = desc.value(t, addr) if t is not None else {'k': 'scalar', 'v': desc.hexbytes(addr, size),
			'a': addr, 's': size, 't': tn, 'g': False}
		heap.append({'a': addr, 's': size, 't': tn, 'line': line, 'v': val})
	return {
		'line': pos[0], 'col': pos[1],
		'frames': frames,
		'globals': globs,
		'gslots': gslots,
		'heap': heap,
		'regions': {
			'globals': [32, prog.globsize],
			'stack': [vm.stack, fp + cur.framesize],
		},
	}


def final_snapshot(vm, pos):
	"""What is left when the program has ended: global variables and heap."""
	prog = vm.prog
	desc = Describer(vm)
	globs = [{'n': name, 'kind': 'global', 'v': desc.value(t, addr)} for name, addr, t in prog.globals]
	heap = []
	for addr in sorted(vm.heap_live):
		size, (line, tn) = vm.heap_live[addr]
		t = vm.heap_types.get(addr)
		val = desc.value(t, addr) if t is not None else {'k': 'scalar', 'v': desc.hexbytes(addr, size),
			'a': addr, 's': size, 't': tn, 'g': False}
		heap.append({'a': addr, 's': size, 't': tn, 'line': line, 'v': val})
	return {'line': pos[0] if pos else 0, 'col': pos[1] if pos else 0, 'frames': [], 'globals': globs,
		'gslots': [{'a': addr, 's': t.size, 'n': name} for name, addr, t in prog.globals],
		'heap': heap, 'final': True, 'regions': {}}
