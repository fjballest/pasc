{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program p;
var
	c: char;
begin
	c := 'x';
	if ord(c) >= ord('a') then
		writeln(c);
end.
