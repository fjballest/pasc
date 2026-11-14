{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rng4;
var
	c: char;
	i: integer;
begin
	i := 255;
	c := chr(i);
	writeln(ord(c));
	i := i + 1;
	c := chr(i);
end.
