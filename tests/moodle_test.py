#!/usr/bin/env python3
"""Checks pasclean and pasnotas on a made up Moodle download and gradebook."""
import os, subprocess, sys, shutil, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
fail = 0

def check(what, cond):
	global fail
	print(('ok   ' if cond else 'FAIL ') + what)
	fail += not cond

def run(tool, *args):
	return subprocess.run([sys.executable, os.path.join(TOP, tool + '.py')] + list(args),
		capture_output=True, text=True)

PROG = b"program p;\r\nbegin\r\n\twriteln('hola');\r\nend.\r\n"
CSV = ('Nombre\tApellido(s)\t"Número de ID"\tInstitución\tDepartamento\t"Dirección de correo"\t'
	'"Tarea: Primer ejercicio enero (Real)"\t"Tarea: Practica enero (Real)"\n'
	'JOSÉ\tÑÚÑEZ PÉREZ\tj.nunez.2024\t\t\tj@x\t-\t-\n'
	'MARÍA\tDE LA O\tm.delao.2023\t\t\tm@x\t-\t-\n'
	'ANA\tLÓPEZ\ta.lopez.2025\t\t\ta@x\t-\t-\n')

d = tempfile.mkdtemp()
try:
	csvp = os.path.join(d, 'calif.csv')
	with open(csvp, 'w', encoding='utf-8') as f:
		f.write(CSV)
	zp = os.path.join(d, 'entregas.zip')
	with zipfile.ZipFile(zp, 'w') as z:
		z.writestr('JOSÉ ÑÚÑEZ PÉREZ_111_assignsubmission_file/ej.p', PROG)
		z.writestr('MARÍA DE LA O_222_assignsubmission_file/a.pas', PROG)
		z.writestr('MARÍA DE LA O_222_assignsubmission_file/viejo.p', b'x')
		z.writestr('PEPE DESCONOCIDO_333_assignsubmission_file/p.p', PROG)
	r = run('pasclean', '-c', csvp, zp)
	e = os.path.join(d, 'entregas')
	files = sorted(os.listdir(e))
	check('clean names', files == ['IDS', 'jose.nunez.perez.p', 'maria.de.la.o.p', 'pepe.desconocido.p'])
	check('carriage returns removed', b'\r' not in open(os.path.join(e, 'jose.nunez.perez.p'), 'rb').read())
	check('largest file kept', open(os.path.join(e, 'maria.de.la.o.p'), 'rb').read() == PROG.replace(b'\r', b''))
	ids = open(os.path.join(e, 'IDS')).read()
	check('IDS', ids == 'jose.nunez.perez.p\tj.nunez.2024\nmaria.de.la.o.p\tm.delao.2023\n')
	check('unknown student reported', 'pepe.desconocido.p' in r.stderr and r.returncode == 1)

	# pasgrade adds the id column (no moss in tests)
	subprocess.run([sys.executable, os.path.join(TOP, 'pasgrade.py'), '-M', e], capture_output=True)
	notas = open(os.path.join(e, 'NOTAS.pasgrade')).read().splitlines()
	check('NOTAS id column', notas[1].split('\t')[-1] == 'id' and notas[2].split('\t')[-1] == 'j.nunez.2024')

	# the teacher's grades
	with open(os.path.join(e, 'NOTAS'), 'w') as f:
		f.write('Tab 8\nnota\tclean\twho\n7.5\t-\tjose.nunez.perez.p\n*\t-\tmaria.de.la.o.p\n'
			'5\t-\tpepe.desconocido.p\n\nmoss *.p\n')
	r = run('pasnotas', '-c', csvp, '-t', 'Primer ejercicio enero', e)
	out = open(os.path.join(d, 'calif.notas.csv'), encoding='utf-8').read().splitlines()
	check('grade with decimal comma', out[1].split('\t')[6] == '7,5' and out[1].split('\t')[7] == '-')
	check('non numeric grade left alone', out[2].split('\t')[6] == '-')
	check('problems reported', 'maria.de.la.o.p' in r.stderr and 'pepe.desconocido.p' in r.stderr)
	check('header kept', out[0].split('\t')[2] == 'Número de ID')
finally:
	shutil.rmtree(d)
sys.exit(1 if fail else 0)
