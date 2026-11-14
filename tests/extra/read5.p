{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program read5;
var
	n, m: integer;
	s: string;
	d: (Lun, Mar, Mie);
	r: real;
begin
	readln(n, m);
	writeln(n, ' ', m);
	read(n); readln(s);
	writeln(n, '[', s, ']');
	read(d); writeln(d);
	read(d); writeln(ord(d));
	read(r); writeln(r:0:4);
	read(r); writeln(r:0:4);
	read(r); writeln(r:0:4);
	readln(s); writeln('[', s, ']');
	read(n); writeln(n);
	read(d); writeln(d);
end.
