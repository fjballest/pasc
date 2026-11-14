{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program sc1;
var
	a: array[1..3] of integer;
	i, llamadas: integer;
function f(x: integer): boolean;
begin
	llamadas := llamadas * 10 + x + 5;
	result := x > 0;
end;
begin
	a[1] := 1; a[2] := 2; a[3] := 3;
	i := 4;
	if (i <= 3) and (a[i] = 2) then
		writeln('si')
	else
		writeln('no');
	llamadas := 0;
	if f(1) or f(2) then
		writeln('or ok ', llamadas);
	llamadas := 0;
	if f(-1) and f(3) then
		writeln('and?');
	writeln(llamadas);
end.
