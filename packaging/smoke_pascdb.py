#!/usr/bin/env python3
"""Check a pascdb command end to end: start it on a program, step through
a few lines over HTTP and look at the reported state.
usage: smoke_pascdb.py PASCDB-COMMAND... prog.p"""
import json, re, subprocess, sys, time, urllib.request, os
os.environ['PASCLIMITS'] = ''	# ignore the user's ~/.pasclimits

cmd = sys.argv[1:]
p = subprocess.Popen(cmd[:-1] + ['--no-browser', '-g', '-L', cmd[-1]], stdout=subprocess.PIPE, text=True)
try:
	url = None
	for line in p.stdout:
		m = re.search(r'(http://127\.0\.0\.1:\d+)/\?t=(\w+)', line)
		if m:
			base, tok = m.group(1), m.group(2)
			break
	else:
		sys.exit('pascdb did not start')

	def get(path, **q):
		q['t'] = tok
		qs = '&'.join('%s=%s' % kv for kv in q.items())
		with urllib.request.urlopen('%s/api/%s?%s' % (base, path, qs), timeout=10) as r:
			return json.loads(r.read())

	assert get('source')['lines']
	lines = []
	for i in range(4):
		get('step')
		time.sleep(0.3)
		st = get('state')
		if st.get('snap'):
			lines.append(st['snap']['line'])
	print('pascdb stopped at lines', lines)
	assert lines, 'no snapshot'
	assert 'frames' in st['snap'] and 'heap' in st['snap']
	# the machine view: registers, bytecode and one instruction at a time
	code = get('code')
	assert code['rows'] and code['starts'], 'no bytecode'
	m = st['machine']
	pcs = [m['pc']]
	for i in range(5):
		get('stepi')
		time.sleep(0.3)
		st = get('state')
		m = st['machine']
		assert m['atinstr'], 'stepi did not stop at an instruction'
		pcs.append(m['pc'])
	print('stepi went through pcs', pcs)
	assert all(a != b for a, b in zip(pcs, pcs[1:])), 'stepi did not advance'
	get('step')
	time.sleep(0.3)
	st = get('state')
	assert not st['machine']['atinstr'], 'step after stepi did not stop at a line'
	get('run')
	time.sleep(1)
	st = get('state')
	assert st['status'] == 'finished', st['status']
	print('pascdb ok; program output:', repr(st['output'][:60]))
finally:
	p.kill()
