{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program accept2;
type
	TM = array[1..2] of array[1..2] of real;
	TP = ^TN;
	TN = record c: char; sig: TP; end;
var
	m: TM;
	p: TP;
	i: integer;
	r: real;
	s: string[10];
	c: char;
function mk(c: char): TP;
begin
	new(result);
	result^.c := c;
	result^.sig := nil;
end;
begin
	m[1][2] := 3; m[2, 1] := 4.5;
	writeln(m[1, 2]:0:1, m[2][1]:5:1);
	p := mk('x');
	new(p^.sig);
	p^.sig^.c := 'y';
	writeln(p^.c, p^.sig^.c);
	writeln(trunc(5), round(7), trunc(2.9), round(-0.5), round(0.5), round(1.5));
	r := 5; i := 7;
	r := i / 2 + r;
	writeln(r:0:2, ' ', sqrt(16), ' ', abs(i - 10));
	s := '';
	if s = '' then writeln('vacio');
	c := 'a';
	s := s + c + c;
	writeln(s, length(s), length(c), length('abc'));
	writeln(ord(s[0]), (r > 1) = true, low(s), high(s));
	writeln(chr(ord('a') + 2), succ('y'), pred(10));
	while not eof do begin
		readln(s);
		writeln('[', s, ']');
	end;
end.
