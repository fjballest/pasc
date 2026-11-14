{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rng3;
type
	T = (Uno, Dos, Tres);
var
	t1: T;
begin
	t1 := Tres;
	writeln(pred(t1));
	writeln(succ(t1));
end.
