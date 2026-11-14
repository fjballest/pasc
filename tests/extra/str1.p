{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program str1;
type
	TS = string[10];
	TC = array[1..4] of char;
var
	s: TS;
	t: string;
	c: TC;
	i: integer;
begin
	s := 'hola';
	t := s + ' mundo' + '!';
	writeln(t, ' ', length(t));
	s := t;
	writeln(s, ' ', length(s));
	writeln('abc' < 'abd', ' ', 'ab' < 'abc', ' ', 'b' > 'abc', ' ', s = 'hola mundo');
	c := 'xy';
	t := c;
	writeln(length(t));
	c := s;
	writeln(c);
	setlength(t, 3);
	writeln(t);
	t := '';
	for i := 1 to 300 do
		t := t + 'z';
	writeln(length(t));
	writeln(t[255], t[1]);
	s := 'a';
	s := s + 'b';
	writeln(s, ord(s[0]));
	t := 'it''s';
	writeln(t, #65, 'x'#66'y');
	case s of
	'ab': writeln('es ab');
	'cd': writeln('es cd');
	end;
	writeln(high(s), low(s));
end.
