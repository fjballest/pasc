{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program grupos;
var
	a, b: integer;
begin
	a := 1;
	b := a + 1; a := b * 2;
	b := a + 1; a := b * 2;
	b := a + 1; a := b * 2;
	writeln(a);
end.
