{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program read1;
var
	a, b: integer;
	r: real;
	c: char;
	s: string[5];
	t: string;
begin
	read(a, b);
	writeln(a + b);
	read(r);
	writeln(r:0:3);
	read(c);
	writeln('[', c, ']', ord(c));
	readln(s);
	writeln('[', s, ']');
	readln(t);
	writeln('[', t, ']');
	readln;
	read(c);
	writeln('[', c, '] ', eoln, ' ', eof);
	readln(a);
	writeln(a, ' ', eof);
	readln(t);
	writeln('[', t, '] ', eof, eoln);
	read(c);
	writeln(ord(c));
	read(a);
	writeln(a);
end.
