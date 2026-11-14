{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	P1 = ^integer;
	P2 = ^char;
var
	a: P1;
	b: P2;
begin
	a := b;
end.
