{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program enum1;
type
	TD = (Lunes, Martes, Miercoles);
	TS = Martes..Miercoles;
var
	d: TD;
	s: TS;
	n, code: integer;
begin
	writeln(Lunes, ' ', ord(Miercoles), ' ', TD(1), ' ', low(TD), ' ', high(TS));
	writeln(Martes:10, '|', Lunes:3, '|');
	val('martes', d, code);
	writeln(d, ' ', code);
	val('  MIERCOLES', d, code);
	writeln(d, ' ', code);
	val('x', d, code);
	writeln(code);
	val('123', n, code); writeln(n, ' ', code);
	val('-0', n, code); writeln(n, ' ', code);
	val('12a', n, code); writeln(n, ' ', code);
	s := Martes;
	d := s;
	writeln(d < Miercoles, d > Lunes);
end.
