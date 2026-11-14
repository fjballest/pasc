"""pascdb: run a pasc program step by step and show it in the browser.

A small HTTP server on 127.0.0.1 serves the page (ui.html) and a JSON
API.  The program runs in a background thread on a pasc VM compiled with
LINE instructions; at each one the VM calls Session.hook, which waits
until the browser asks for the next step (or, when playing, until the
chosen delay has passed).
"""

import io
import json
import os
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from pasclib import vm as pvm
from pasclib.errors import Halt
from .snapshot import snapshot, final_snapshot

HERE = os.path.dirname(os.path.abspath(__file__))


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
		vm = self.vm
		with self.cv:
			if self.restart_req:
				raise Restart()
			line = pos[0]
			if self.mode == 'run' and line not in self.breaks:
				return
			if self.mode == 'run':
				self.mode = 'pause'
			self.paused = (pc, fp, sp, pos)
			self.lastpos = pos
			self.highwater = max(self.highwater, sp)
			self.snap = None
			self.status = 'paused'
			self.version += 1
			self.cv.notify_all()
			deadline = time.time() + self.delay
			while True:
				if self.restart_req:
					raise Restart()
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
			elif self.status == 'finished' and self.snap is not None:
				st['snap'] = self.snap
			return st

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
