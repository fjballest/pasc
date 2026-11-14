{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rng2;
var
	s: string[5];
	i: integer;
begin
	s := 'abc';
	i := 5;
	s[i] := 'x';
	writeln(length(s), s);
	i := 6;
	s[i] := 'y';
end.
