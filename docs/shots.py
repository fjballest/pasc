#!/usr/bin/env python3
"""Make the pascdb screenshots used by the user guide (docs/img/*.png).

Each shot starts pascdb on an example program (docs/examples), drives it
through its HTTP API to the wanted point, and photographs the page with
headless Chrome.  usage: python3 docs/shots.py [shot names...]
(CHROME=path overrides the browser.)
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, 'examples')
IMG = os.path.join(HERE, 'img')
PASCDB = os.path.join(os.path.dirname(HERE), 'pascdb.py')

# name: (program, input lines, actions, page settings, window size)
# actions: ('break', line) ('run',) ('step', n) ('input', text)
SHOTS = {
	'start': ('lista.p', [], [], 'lang=en', (1400, 820)),
	'list': ('lista.p', [], [('break', 44), ('run',), ('run',), ('run',)], 'lang=en', (1400, 820)),
	'files': ('lista.p', [], [('break', 26), ('run',), ('step', 6)], 'lang=en&tab=files', (1400, 820)),
	'varparams': ('puntos.p', [], [('break', 24), ('run',), ('run',)], 'lang=en', (1400, 820)),
	'varcopies': ('puntos.p', [], [('break', 24), ('run',), ('run',)], 'lang=en&refs=copy', (1400, 820)),
	'stack': ('puntos.p', [], [('break', 24), ('run',), ('run',)], 'lang=en&tab=stack', (1400, 820)),
	'memory': ('puntos.p', [], [('break', 24), ('run',), ('run',), ('step', 1)], 'lang=en&tab=mem', (1400, 820)),
	'together': ('lista.p', [], [('break', 44), ('run',), ('run',)], 'lang=en&together=1', (2300, 900)),
	'spanish': ('lista.p', [], [('break', 44), ('run',), ('run',)], 'lang=es', (1400, 820)),
	'finished': ('lista.p', [], [('run',)], 'lang=en', (1400, 820)),
}


def chrome():
	if os.environ.get('CHROME'):
		return os.environ['CHROME']
	for c in ('google-chrome', 'chromium', 'chromium-browser',
			'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'):
		p = shutil.which(c) or (c if os.path.exists(c) else None)
		if p:
			return p
	sys.exit('shots: Chrome not found (set CHROME)')


def wait_stop(api):
	"""Wait until the program pauses again (or ends)."""
	v = api('state')['version']
	for _ in range(20):
		st = api('state', since=v)
		v = st['version']
		if st['status'] in ('paused', 'finished', 'input', 'error'):
			return st
	return st


def shot(name):
	prog, inp, actions, settings, (w, h) = SHOTS[name]
	p = subprocess.Popen([sys.executable, PASCDB, '--no-browser', prog], cwd=EX,
		stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
	try:
		for line in p.stdout:
			m = re.search(r'(http://127\.0\.0\.1:\d+)/\?t=(\w+)', line)
			if m:
				base, tok = m.groups()
				break

		def api(path, **q):
			q['t'] = tok
			url = '%s/api/%s?%s' % (base, path, '&'.join('%s=%s' % (k, urllib.request.quote(str(v)))
				for k, v in q.items()))
			return json.loads(urllib.request.urlopen(url, timeout=10).read())

		time.sleep(0.5)
		for text in inp:
			api('input', text=text)
		for a in actions:
			if a[0] == 'break':
				api('break', line=a[1])
			elif a[0] == 'run':
				api('run')
				wait_stop(api)
			elif a[0] == 'step':
				for _ in range(a[1]):
					api('step')
					time.sleep(0.25)
			elif a[0] == 'input':
				api('input', text=a[1])
		time.sleep(0.5)
		out = os.path.join(IMG, name + '.png')
		url = '%s/?t=%s&once=1&%s' % (base, tok, settings)
		subprocess.run([chrome(), '--headless', '--disable-gpu', '--hide-scrollbars',
			'--force-device-scale-factor=1', '--window-size=%d,%d' % (w, h),
			'--virtual-time-budget=5000', '--screenshot=' + out, url],
			check=True, capture_output=True, timeout=60)
		print('wrote', out)
	finally:
		p.kill()


os.makedirs(IMG, exist_ok=True)
for n in sys.argv[1:] or SHOTS:
	shot(n)
