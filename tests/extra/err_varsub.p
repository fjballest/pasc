{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	T = 1..10;
var
	t1: T;
procedure q(var x: integer);
begin
end;
begin
	q(t1);
end.
