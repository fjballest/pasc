"""pascdb: run a pasc program step by step and show it in the browser.

A small HTTP server on 127.0.0.1 serves the page (ui.html) and a JSON
API.  The program runs in a background thread on a pasc VM compiled with
LINE instructions; at each one the VM calls Session.hook, which waits
until the browser asks for the next step (or, when playing, until the
chosen delay has passed).
"""

import io
import json
import struct
import os
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from pasclib import vm as pvm
from pasclib import code as C
from pasclib.errors import Halt
from .snapshot import snapshot, final_snapshot

HERE = os.path.dirname(os.path.abspath(__file__))


def value_text(v):
	"""An operand stack value as text."""
	if isinstance(v, (bytes, bytearray)):
		return "'" + bytes(v).decode('latin-1') + "'"
	if isinstance(v, float):
		return repr(v)
	return str(v)


def encode(arg):
	"""An instruction's argument as bytes, for showing code as memory."""
	if arg is None:
		return b''
	if isinstance(arg, bool):
		return bytes([int(arg)])
	if isinstance(arg, int):
		if -2**31 <= arg < 2**32:
			return struct.pack('<I', arg & 0xffffffff)
		return struct.pack('<Q', arg & 0xffffffffffffffff)
	if isinstance(arg, float):
		return struct.pack('<d', arg)
	if isinstance(arg, (bytes, bytearray)):
		return bytes([len(arg) & 0xff]) + bytes(arg)
	if isinstance(arg, str):
		b = arg.encode('latin-1', 'replace')
		return b if len(b) == 1 else bytes([len(b) & 0xff]) + b
	if isinstance(arg, (tuple, list)):
		return b''.join(encode(x) for x in arg)
	name = getattr(arg, 'name', None) or type(arg).__name__
	return encode(str(name))


class Restart(BaseException):
	"""Raised inside the VM thread to abandon a run."""


class Sink:
	"""Collects the program's output (and pasc's messages) for the page."""
	def __init__(self, session, kind):
		self.session = session
		self.kind = kind

	def write(self, b):
		if isinstance(b, str):
			b = b.encode('utf-8', 'replace')
		with self.session.cv:
			self.session.output.append((self.kind, bytes(b).decode('latin-1')))
			self.session.version += 1
		return len(b)

	def flush(self):
		pass


class Session:
	def __init__(self, prog, source):
		self.prog = prog
		self.source = source
		self.cv = threading.Condition()
		self.version = 0
		self.mode = 'pause'		# pause step play run
		self.delay = 0.6
		self.permits = 0
		self.ipermits = 0
		self.icount = None		# instructions to run before stopping (stepi)
		self.atinstr = False
		self.breaks = set()
		self.thread = None
		self.start()

	# the program thread
	def start(self):
		with self.cv:
			self.output = []
			self.status = 'starting'
			self.exitcode = None
			self.paused = None
			self.snap = None
			self.waiting_input = False
			self.restart_req = False
			self.lastpos = None
			self.highwater = 0
			self.vm = pvm.VM(self.prog)
			vm = self.vm
			vm.out.out = Sink(self, 'out')
			vm.out.tty = True
			r, w = os.pipe()
			self.inr, self.inw = r, w
			vm.inp.fd = r
			vm.inp.buf = b''
			vm.inp.pos = 0
			vm.inp.flushout = vm.out.flush
			orig = vm.inp.fill

			def fill():
				if vm.inp.pos < len(vm.inp.buf):
					return True
				with self.cv:
					self.waiting_input = True
					self.version += 1
				try:
					return orig()
				finally:
					with self.cv:
						self.waiting_input = False
						self.version += 1
			vm.inp.fill = fill
			vm.hook = self.hook
			vm.ihook = self.ihook
			self.icount = None
			self.version += 1
		self.thread = threading.Thread(target=self.run, args=(vm,), daemon=True)
		self.thread.start()

	def run(self, vm):
		err = Sink(self, 'err')
		code = None
		try:
			saved = sys.stderr
			sys.stderr = err
			try:
				code = vm.run()
			finally:
				sys.stderr = saved
		except Restart:
			return
		except Exception:
			err.write(traceback.format_exc())
			code = -1
		with self.cv:
			if vm is not self.vm:
				return
			self.status = 'finished'
			self.exitcode = code
			self.snap = final_snapshot(vm, self.lastpos, self.highwater)
			self.version += 1
			self.cv.notify_all()

	def hook(self, pc, fp, sp, pos):
		"""Called by the VM at each LINE instruction."""
		with self.cv:
			if self.restart_req:
				raise Restart()
			line = pos[0]
			self.lastpos = pos
			if self.mode == 'stepi':		# going instruction by instruction
				return
			if self.mode == 'run' and line not in self.breaks:
				return
			if self.mode == 'run':
				self.mode = 'pause'
			self.wait(pc, fp, sp, pos, False)

	def ihook(self, pc, fp, sp):
		"""Called by the VM before every instruction; it stops only after a
		stepi.  The quick test keeps the program fast the rest of the time."""
		c = self.icount
		if c is None:
			return
		if c > 0:
			self.icount = c - 1
			return
		with self.cv:
			self.icount = None
			if self.restart_req:
				raise Restart()
			pos = self.lastpos or (self.prog.lines[pc], 1)
			self.wait(pc, fp, sp, pos, True)

	def wait(self, pc, fp, sp, pos, atinstr):
		"""Stop with the VM about to run instruction pc until the page says
		how to go on.  Called with self.cv held."""
		self.paused = (pc, fp, sp, pos)
		self.atinstr = atinstr
		self.highwater = max(self.highwater, sp)
		self.snap = None
		self.status = 'paused'
		self.version += 1
		self.cv.notify_all()
		deadline = time.time() + self.delay
		while True:
			if self.restart_req:
				raise Restart()
			if self.mode == 'stepi' and self.ipermits > 0:
				self.ipermits = 0
				# from a LINE pause the next instruction is the one shown,
				# from an instruction pause it has just been shown: run one
				self.icount = 0 if atinstr else 1
				break
			if self.mode == 'step' and self.permits > 0:
				self.permits -= 1
				if self.permits == 0:
					self.mode = 'pause'
				break
			if self.mode == 'run':
				break
			if self.mode == 'play':
				left = deadline - time.time()
				if left <= 0:
					break
				self.cv.wait(left)
				continue
			self.cv.wait(0.5)
		self.status = 'running'
		self.paused = None
		self.version += 1

	# commands from the page
	def command(self, cmd, args):
		with self.cv:
			if cmd == 'step':
				self.mode = 'step'
				self.permits += 1
			elif cmd == 'stepi':
				self.mode = 'stepi'
				self.ipermits = 1
				self.permits = 0
			elif cmd == 'play':
				self.mode = 'play'
			elif cmd == 'pause':
				self.mode = 'pause'
			elif cmd == 'run':
				self.mode = 'run'
			elif cmd == 'speed':
				self.delay = max(0.0, min(5.0, float(args.get('delay', 0.6))))
			elif cmd == 'break':
				line = int(args.get('line', 0))
				if line in self.breaks:
					self.breaks.discard(line)
				else:
					self.breaks.add(line)
			elif cmd == 'input':
				text = args.get('text', '') + '\n'
				if self.inw is not None:
					try:
						os.write(self.inw, text.encode('latin-1', 'replace'))
						self.output.append(('in', text))
					except OSError:
						pass
			elif cmd == 'eof':
				self.close_fd('inw')
			elif cmd == 'restart':
				self.restart_req = True
				self.mode = 'pause'
				self.permits = 0
				self.ipermits = 0
			self.version += 1
			self.cv.notify_all()
		if cmd == 'restart':
			self.close_fd('inw')		# a program waiting for input gets eof
			self.thread.join(2)
			old = self.vm
			old.inp.fd = None		# never read that descriptor again
			self.close_fd('inr')
			self.start()

	def close_fd(self, name):
		"""Close a pipe end once: a descriptor closed twice could by then
		belong to one of the server's sockets."""
		fd = getattr(self, name)
		setattr(self, name, None)
		if fd is not None:
			try:
				os.close(fd)
			except OSError:
				pass

	def state(self, since):
		"""The page's view; waits up to 1 s for something new."""
		with self.cv:
			if self.version == since:
				self.cv.wait(1.0)
			st = {
				'version': self.version,
				'status': 'quit' if getattr(self, 'quitting', False) else
					('input' if self.waiting_input else self.status),
				'mode': self.mode,
				'exitcode': self.exitcode,
				'breaks': sorted(self.breaks),
				'delay': self.delay,
				'output': ''.join(t for k, t in self.output if k in ('out', 'in')),
				'messages': ''.join(t for k, t in self.output if k == 'err'),
			}
			if self.paused is not None:
				if self.snap is None:
					self.snap = snapshot(self.vm, *self.paused, highwater=self.highwater)
				st['snap'] = self.snap
				st['machine'] = self.machine()
			elif self.status == 'finished' and self.snap is not None:
				st['snap'] = self.snap
			return st

	def machine(self):
		"""The VM's registers and operand stack while it is stopped."""
		pc, fp, sp, pos = self.paused
		vm = self.vm
		ops = vm.opstack[-32:]
		return {
			'pc': pc, 'fp': fp, 'sp': sp,
			'kind': vm.cur_routine.kind,
			'routine': vm.cur_routine.name,
			'atinstr': self.atinstr,
			'stack': [value_text(v) for v in ops],
			'depth': len(vm.opstack),
		}

	def code(self):
		"""The bytecode, one row per instruction: [line, op, argument, hex].
		pasc's VM keeps each instruction as an opcode and a Python value;
		hex is how a real machine could store it in bytes: the opcode, then
		the argument (integers in 4 bytes, little endian, reals in 8, kinds
		and strings as their characters)."""
		prog = self.prog
		rows = []
		for pc, (op, arg) in enumerate(zip(prog.ops, prog.args)):
			if arg is None:
				a = ''
			elif op == C.CALL:
				a = prog.routines[arg].name
			else:
				a = repr(arg)
			rows.append([prog.lines[pc], C.OPS[op], a, (bytes([op]) + encode(arg)).hex()])
		starts = {r.entry: {'kind': r.kind, 'routine': r.name} for r in prog.routines if r.entry is not None}
		return {'rows': rows, 'starts': starts}

	def memory(self, addr, size):
		with self.cv:
			mem = self.vm.mem
			addr = max(0, min(addr, len(mem)))
			size = max(0, min(size, 4096, len(mem) - addr))
			return {'a': addr, 'hex': bytes(mem[addr:addr + size]).hex()}


def make_handler(session, token):
	class Handler(BaseHTTPRequestHandler):
		def log_message(self, *args):
			pass

		def send(self, code, body, ctype='application/json'):
			if isinstance(body, str):
				body = body.encode('utf-8')
			self.send_response(code)
			self.send_header('Content-Type', ctype)
			self.send_header('Content-Length', str(len(body)))
			self.send_header('Cache-Control', 'no-store')
			self.end_headers()
			self.wfile.write(body)

		def do_GET(self):
			u = urlparse(self.path)
			q = {k: v[0] for k, v in parse_qs(u.query).items()}
			if q.get('t') != token:
				return self.send(403, 'forbidden', 'text/plain')
			if u.path == '/':
				with open(os.path.join(HERE, 'ui.html'), 'rb') as f:
					return self.send(200, f.read(), 'text/html; charset=utf-8')
			if u.path == '/api/source':
				return self.send(200, json.dumps({'fname': session.prog.fname,
					'lines': session.source.split('\n')}))
			if u.path == '/api/code':
				return self.send(200, json.dumps(session.code()))
			if u.path == '/api/state':
				return self.send(200, json.dumps(session.state(int(q.get('since', -1)))))
			if u.path == '/api/mem':
				return self.send(200, json.dumps(session.memory(int(q.get('addr', 0)), int(q.get('len', 256)))))
			if u.path == '/api/quit':
				self.send(200, '{}')
				with session.cv:
					session.quitting = True
					session.version += 1
					session.cv.notify_all()
				threading.Thread(target=self.server.shutdown, daemon=True).start()
				return
			if u.path.startswith('/api/'):
				session.command(u.path[5:], q)
				return self.send(200, '{}')
			self.send(404, 'not found', 'text/plain')

	return Handler


def serve(prog, source, open_browser=True, port=0):
	session = Session(prog, source)
	token = os.urandom(8).hex()
	httpd = ThreadingHTTPServer(('127.0.0.1', port), make_handler(session, token))
	url = 'http://127.0.0.1:%d/?t=%s' % (httpd.server_address[1], token)
	print('pascdb: %s' % url)
	print('pascdb: open that address in a browser if it does not open by itself; Ctrl+C ends pascdb')
	sys.stdout.flush()
	if open_browser:
		threading.Timer(0.3, lambda: webbrowser.open(url)).start()
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	print('pascdb: done')
	return 0
