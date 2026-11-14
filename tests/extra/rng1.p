{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rng1;
type
	TA = array[1..5] of integer;
var
	a: TA;
	i: integer;
begin
	for i := 1 to 5 do
		a[i] := i * i;
	i := 6;
	writeln(a[5]);
	writeln(a[i]);
end.
