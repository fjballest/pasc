"""Per-user overrides of the limits in limits.py.

A plain text file with one "limit: value" per line overrides the values
in limits.py, so an installed pasc can be tuned without touching it:

	line_length: 120
	loops: 6
	begin_end: off
	enforced: loops, nested_loops

The file is ~/.pasclimits ($HOME/.pasclimits on macOS and Linux,
%USERPROFILE%\\.pasclimits on Windows, e.g. C:\\Users\\ana\\.pasclimits),
or the file named by the PASCLIMITS environment variable (empty: none).
Lines starting with # and blank lines are ignored.  Values are numbers,
on/off (also true/false, yes/no), none, or for 'enforced' a list of limit
names separated by commas.  Mistakes are reported as warnings and the
line is ignored.
"""

import os
import sys


def limits_file():
	path = os.environ.get('PASCLIMITS')
	if path is not None:
		return path or None
	return os.path.join(os.path.expanduser('~'), '.pasclimits')


def parse_value(name, text, limits):
	low = text.strip().lower()
	if name == 'enforced':
		names = tuple(n.strip() for n in low.split(',') if n.strip())
		bad = [n for n in names if n not in limits]
		if bad:
			raise ValueError('unknown limit "%s"' % bad[0])
		return names
	if low in ('on', 'true', 'yes'):
		return True
	if low in ('off', 'false', 'no', 'none'):
		return None
	try:
		return int(low)
	except ValueError:
		raise ValueError('bad value "%s" (use a number, on, off or none)' % text.strip())


def apply(limits, path=None):
	"""Override limits with the user's file, if there is one."""
	path = path or limits_file()
	if not path or not os.path.isfile(path):
		return
	try:
		with open(path, encoding='utf-8', errors='replace') as f:
			lines = f.read().splitlines()
	except OSError as e:
		sys.stderr.write('pasc: %s: %s\n' % (path, e.strerror))
		return
	for i, line in enumerate(lines, 1):
		line = line.strip()
		if not line or line.startswith('#'):
			continue
		name, sep, value = line.partition(':')
		name = name.strip().lower()
		try:
			if not sep:
				raise ValueError('expected "limit: value"')
			if name not in limits:
				raise ValueError('unknown limit "%s"' % name)
			limits[name] = parse_value(name, value, limits)
		except ValueError as e:
			sys.stderr.write('%s:%d: warning: %s; line ignored\n' % (path, i, e))
