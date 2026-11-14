{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	R = record a: integer; end;
var
	r: R;
begin
	r.b := 1;
end.
