{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
function f(x: integer): integer;
var c: char;
begin
	read(c);
	result := x;
end;
begin
	writeln(f(1));
end.
