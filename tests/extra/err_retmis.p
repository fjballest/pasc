{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
function f: integer;
begin
	result := 'x';
end;
begin
	writeln(f);
end.
