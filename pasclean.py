#!/usr/bin/env python3
"""pasclean: cleans up the submissions downloaded from Moodle.

usage: pasclean -c CALIFICACIONES.csv [dir | entregas.zip]

Moodle's "Descargar todas las entregas" gives a folder per student, named
like "NOMBRE APELLIDOS_12345_assignsubmission_file", with the student's
files inside.  pasclean (a replacement for cleanlabs) leaves, for each
student, one NAME.p with the program, its carriage returns removed, and
removes the folder.  NAME is the student's name in lower case, without
accents or other characters that need quoting in the shell, with dots
instead of blanks (josé ñúñez → jose.nunez.p).

The students' names are looked up in CALIFICACIONES.csv, the gradebook
exported from Moodle as "Texto plano" (tab separated), with the columns
Nombre, Apellido(s) and "Número de ID".  pasclean writes a file IDS with
one line per program, NAME.p, a tab, and the student's "Número de ID"; then
pasgrade adds an id column to NOTAS and pasnotas uses it to put the grades
back in the CSV.  Names it cannot find are reported and get no id.

Given a .zip, pasclean extracts it into dir (by default, a folder named
after the zip without ".zip") first.  Only .p and .pas files are kept; if a
student sent several, the largest one is kept and the others are reported.
"""

import csv
import os
import shutil
import sys
import unicodedata
import zipfile

SOURCES = ('.p', '.pas', '.pp')


def usage():
	sys.stderr.write('usage: pasclean -c calificaciones.csv [dir | entregas.zip]\n')
	sys.exit(2)


def ascii_words(s):
	"""s in lower case ASCII letters and digits, as a list of words."""
	s = unicodedata.normalize('NFKD', s)
	s = ''.join(c for c in s if not unicodedata.combining(c))
	s = s.lower().replace('ñ', 'n')
	out = ''.join(c if ('a' <= c <= 'z') or ('0' <= c <= '9') else ' ' for c in s)
	return out.split()


def cleanname(s):
	return '.'.join(ascii_words(s)) or 'sin.nombre'


def readcsv(path):
	"""(header, rows) of a Moodle export, tab or comma separated."""
	with open(path, encoding='utf-8-sig', newline='') as f:
		text = f.read()
	delim = '\t' if text.split('\n', 1)[0].count('\t') > 0 else ','
	rows = list(csv.reader(text.splitlines(), delimiter=delim))
	return delim, rows[0], rows[1:]


def column(header, *names):
	"""index of the first column whose name contains one of names."""
	for n in names:
		for i, h in enumerate(header):
			if n.lower() in h.lower():
				return i
	return -1


def students(path):
	"""{name key: (Número de ID, full name)} from the gradebook CSV."""
	delim, header, rows = readcsv(path)
	cn, ca, ci = column(header, 'Nombre'), column(header, 'Apellido'), column(header, 'mero de ID', 'ID number')
	if min(cn, ca, ci) < 0:
		sys.exit('pasclean: %s: no Nombre, Apellido(s) or Número de ID column' % path)
	who = {}
	for r in rows:
		if len(r) <= max(cn, ca, ci):
			continue
		full = r[cn] + ' ' + r[ca]
		who[' '.join(ascii_words(full))] = (r[ci], full)
	return who


def find(who, folder):
	"""(Número de ID, full name) of the student who owns the folder, or None."""
	name = folder.split('_')[0]
	key = ' '.join(ascii_words(name))
	if key in who:
		return who[key]
	words = sorted(key.split())
	for k, v in who.items():		# same words in another order
		if sorted(k.split()) == words:
			return v
	return None


def cleanup(d, who):
	ids, missing, notes = [], [], []
	used = set(os.listdir(d))
	for f in sorted(os.listdir(d)):
		path = os.path.join(d, f)
		if f.startswith('._'):
			os.remove(path)
			continue
		if not os.path.isdir(path) or '_assignsubmission' not in f:
			continue
		st = find(who, f)
		name = cleanname(st[1] if st else f.split('_')[0])
		dest, k = name + '.p', 2
		while dest in used:
			dest, k = '%s.%d.p' % (name, k), k + 1
		srcs = []
		for root, _, files in os.walk(path):
			srcs += [os.path.join(root, x) for x in files
				if x.lower().endswith(SOURCES) and not x.startswith('._')]
		if not srcs:
			notes.append('%s: no Pascal file, left as it is' % f)
			continue
		srcs.sort(key=os.path.getsize, reverse=True)
		if len(srcs) > 1:
			notes.append('%s: kept %s, ignored %s' % (dest, os.path.basename(srcs[0]),
				', '.join(os.path.basename(s) for s in srcs[1:])))
		with open(srcs[0], 'rb') as src:
			data = src.read().replace(b'\r', b'')
		with open(os.path.join(d, dest), 'wb') as out:
			out.write(data)
		used.add(dest)
		shutil.rmtree(path)
		if st:
			ids.append((dest, st[0]))
		else:
			missing.append('%s: %s not in the CSV, no id' % (dest, f.split('_')[0]))
	return ids, missing, notes


def main(argv):
	csvpath, target = None, '.'
	i = 0
	while i < len(argv):
		if argv[i] == '-c' and i + 1 < len(argv):
			csvpath = argv[i + 1]
			i += 1
		elif argv[i].startswith('-'):
			usage()
		else:
			target = argv[i]
		i += 1
	if csvpath is None:
		usage()
	who = students(csvpath)
	d = target
	if target.lower().endswith('.zip'):
		d = target[:-4]
		if os.path.exists(d):
			sys.exit('pasclean: %s already exists' % d)
		with zipfile.ZipFile(target) as z:
			for m in z.infolist():
				if m.filename.startswith('/') or '..' in m.filename.split('/'):
					sys.exit('pasclean: bad name in the zip: %s' % m.filename)
			z.extractall(d)
	ids, missing, notes = cleanup(d, who)
	idspath = os.path.join(d, 'IDS')
	old = {}
	if os.path.exists(idspath):
		with open(idspath) as f:
			old = dict(l.rstrip('\n').split('\t', 1) for l in f if '\t' in l)
	old.update(ids)
	with open(idspath, 'w') as f:
		for prog in sorted(old):
			f.write('%s\t%s\n' % (prog, old[prog]))
	for m in notes + missing:
		sys.stderr.write('pasclean: %s\n' % m)
	sys.stderr.write('pasclean: %d programs in %s; %d without id; wrote %s\n' % (len(ids) + len(missing),
		d, len(missing), idspath))
	return 1 if missing else 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
