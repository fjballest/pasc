{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program depura;
procedure traza(x: integer);
begin
	writeln('traza ', x);
end;
function f(x: integer): integer;
begin
	writeln('f ', x);
	traza(x);
	result := x * 2;
end;
begin
	writeln(f(1));
end.
