{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	R = record a: integer; end;
var
	r1: R;
begin
	writeln(r1);
end.
