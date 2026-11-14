{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program recinf;
procedure r(n: integer);
begin
	r(n + 1);
end;
begin
	r(0);
end.
