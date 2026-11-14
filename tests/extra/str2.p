{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program str2;
type
	TS3 = string[3];
	TC = array[0..4] of char;
var
	s: string;
	t: TS3;
	z: TC;
	i: integer;
function corta(s: string): TS3;
begin
	result := s;
end;
function rep(c: char; n: integer): string;
var i: integer;
begin
	result := '';
	for i := 1 to n do
		result := result + c;
end;
procedure p(s: TS3);
begin
	writeln('<', s, '>');
end;
begin
	s := 'abcdef';
	t := corta(s);
	writeln(t, length(t));
	p(s);
	p('xy');
	writeln(rep('-', 10), rep('x', 0), '|');
	s[0] := chr(3);
	writeln(s, length(s));
	s := 'a' + #0 + 'b';
	writeln(length(s), s < 'a', s > 'a', 'a' + 'b' = 'ab');
	z := 'hi';
	writeln('[', z, ']');
	s := z;
	writeln(length(s));
	writeln('x':0, 'abc':2, 'abc':5, '|');
	s := '';
	writeln(s = '', length(s), 'a' < 'B', 'Z' < 'a');
	for i := 1 to 3 do
		s := s + chr(ord('a') + i);
	writeln(s);
	case s of
	'bcd': writeln('ok');
	else writeln('no');
	end;
	t := 'abc';
	t[3] := 'z';
	writeln(t);
end.
