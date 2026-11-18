#!/usr/bin/env python3
"""pasnotas: puts the grades of a NOTAS file into the gradebook CSV.

usage: pasnotas -c CALIFICACIONES.csv -t TAREA [-n NOTAS] [-o SALIDA.csv] [dir]

CALIFICACIONES.csv is the gradebook exported from Moodle as "Texto plano"
(tab separated).  TAREA is part of the name of its column for the task,
such as "Primer ejercicio enero".  NOTAS (default NOTAS, else
NOTAS.pasgrade) is the table in dir (default .) with the grades in its
first column, nota, and the program in its who column.  The student's
"Número de ID" comes from the id column of NOTAS or, if it has none, from
the IDS file pasclean wrote in dir.

pasnotas writes SALIDA.csv (by default the CSV's name with ".notas" before
".csv"), a copy of the CSV with the grades in the task's column, to import
in Moodle (Calificaciones > Importar > Archivo CSV, separator: tab; map
"Número de ID" to the ID number and the task's column to the task).  Only
numeric grades are copied, with a decimal comma; '-', '*' and the like are
left empty, and are reported, as are grades with no student.
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pasclean import readcsv, column		# noqa: E402


def usage():
	sys.stderr.write('usage: pasnotas -c calificaciones.csv -t tarea [-n notas] [-o salida.csv] [dir]\n')
	sys.exit(2)


def readnotas(path):
	"""[(nota, who, id)] from a NOTAS file ('Tab 8', a header, rows)."""
	with open(path, encoding='utf-8', errors='replace') as f:
		lines = [l.rstrip('\n') for l in f]
	k = 0
	while k < len(lines) and 'nota' not in lines[k].split('\t'):
		k += 1
	if k == len(lines):
		sys.exit('pasnotas: %s: no header with a nota column' % path)
	header = lines[k].split('\t')
	cn, cw = header.index('nota'), header.index('who') if 'who' in header else len(header) - 1
	ci = header.index('id') if 'id' in header else -1
	rows = []
	for l in lines[k + 1:]:
		r = l.split('\t')
		if len(r) != len(header):		# moss report, commands...
			continue
		rows.append((r[cn].strip(), r[cw].strip(), r[ci].strip() if ci >= 0 else ''))
	return rows


def grade(s):
	"""the grade with a decimal comma, or None if s is not a number."""
	try:
		v = float(s.replace(',', '.'))
	except ValueError:
		return None
	return ('%g' % v).replace('.', ',')


def main(argv):
	csvpath, task, notas, out, d = None, None, None, None, '.'
	i = 0
	while i < len(argv):
		a = argv[i]
		if a in ('-c', '-t', '-n', '-o') and i + 1 < len(argv):
			i += 1
			if a == '-c':
				csvpath = argv[i]
			elif a == '-t':
				task = argv[i]
			elif a == '-n':
				notas = argv[i]
			else:
				out = argv[i]
		elif a.startswith('-'):
			usage()
		else:
			d = a
		i += 1
	if csvpath is None or task is None:
		usage()
	if notas is None:
		notas = 'NOTAS' if os.path.exists(os.path.join(d, 'NOTAS')) else 'NOTAS.pasgrade'
	if not os.path.isabs(notas):
		notas = os.path.join(d, notas)
	if out is None:
		out = csvpath[:-4] + '.notas.csv' if csvpath.lower().endswith('.csv') else csvpath + '.notas'
	if os.path.abspath(out) == os.path.abspath(csvpath):
		sys.exit('pasnotas: will not overwrite %s' % csvpath)
	delim, header, rows = readcsv(csvpath)
	ct = column(header, task)
	cid = column(header, 'mero de ID', 'ID number')
	if ct < 0:
		sys.exit('pasnotas: no column for "%s" in %s' % (task, csvpath))
	if cid < 0:
		sys.exit('pasnotas: no Número de ID column in %s' % csvpath)
	ids = {}
	idspath = os.path.join(d, 'IDS')
	if os.path.exists(idspath):
		with open(idspath) as f:
			ids = dict(l.rstrip('\n').split('\t', 1) for l in f if '\t' in l)
	byid = {}
	problems = []
	for nota, who, sid in readnotas(notas):
		sid = sid if sid not in ('', '-') else ids.get(who, '')
		g = grade(nota)
		if not sid:
			problems.append('%s: no Número de ID (not in IDS)' % who)
		elif g is None:
			problems.append('%s: grade "%s" is not a number, left empty' % (who, nota))
		else:
			byid[sid] = g
	done = 0
	for r in rows:
		if len(r) > max(ct, cid) and r[cid] in byid:
			r[ct] = byid.pop(r[cid])
			done += 1
	for sid in sorted(byid):
		problems.append('id %s: not in %s' % (sid, csvpath))
	with open(out, 'w', encoding='utf-8', newline='') as f:
		w = csv.writer(f, delimiter=delim, lineterminator='\n')
		w.writerow(header)
		w.writerows(rows)
	for p in problems:
		sys.stderr.write('pasnotas: %s\n' % p)
	sys.stderr.write('pasnotas: %d grades in column "%s"; wrote %s\n' % (done, header[ct], out))
	return 1 if problems else 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
