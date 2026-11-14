{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	T = string[10];
var
	s: T;
procedure q(var x: string);
begin
end;
begin
	q(s);
end.
