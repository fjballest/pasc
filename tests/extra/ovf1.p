{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ovf1;
var
	i, j: integer;
begin
	i := 2147483647;
	writeln(i * i);
	writeln(i * i * 2);
	j := i * i div i;
	writeln(j);
	writeln(i * i * i);
end.
