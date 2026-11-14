{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program read7;
var
	n: integer;
	c: array[1..3] of char;
	z: array[0..3] of char;
begin
	read(c); writeln('[', c, ']');
	read(c); writeln('[', c, ']');
	readln;
	read(z); writeln('[', z, ']');
	readln(z); writeln('[', z, ']');
	read(n);
	writeln(n);
end.
