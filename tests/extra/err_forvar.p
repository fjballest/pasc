{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
var
	i: integer;
procedure inc2(var x: integer);
begin
	x := x + 2;
end;
begin
	for i := 1 to 3 do
		inc2(i);
end.
