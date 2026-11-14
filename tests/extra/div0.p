{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program div0;
var
	i, j: integer;
begin
	i := 10; j := 0;
	writeln(i mod 3);
	writeln(i div j);
end.
