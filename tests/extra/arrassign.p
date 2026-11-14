{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	A1 = array[1..3] of integer;
	A2 = array[1..3] of integer;
var
	x: A1;
	y: A2;
begin
	x := y;
end.
