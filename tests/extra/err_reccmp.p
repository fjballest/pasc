{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
type
	R = record a: integer; end;
var
	r1, r2: R;
begin
	if r1 = r2 then
		writeln('x');
end.
