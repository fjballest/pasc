{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
var
	x: integer;
procedure incr();
begin
	x := x + 1;
end;
begin
	x := 1;
	incr();
end.
