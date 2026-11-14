{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program fmt1;
const
	A = 2.5; B = 0.1; C = 1.0/3.0; D = -7.25;
var
	r: real;
	i: integer;
begin
	writeln(A); writeln(B); writeln(C); writeln(D); writeln(-A);
	r := 0.0; writeln(r); writeln(r:0:2); writeln(-r:0:2);
	r := 123456789.123; writeln(r); writeln(r:0:3); writeln(r:15:1); writeln(r:5);
	r := 1e-10; writeln(r); writeln(r:0:5); writeln(r:0:12);
	r := 1.5e300; writeln(r); writeln(r * 1e-300:0:4);
	r := 2.0/3.0; writeln(r:0:0, r:0:1, ' ', r:0:16, ' ', r:0:20);
	r := 9.995; writeln(r:0:2); r := 0.045; writeln(r:0:2); r := 0.0049999; writeln(r:0:2);
	r := 99.5; writeln(r:0:0); r := 100.5; writeln(r:0:0); r := -99.5; writeln(r:6:0);
	for i := 1 to 12 do write(r:i, '|'); writeln;
	for i := 0 to 8 do write(3.14159:0:i, ' '); writeln;
	for i := 0 to 8 do write(3.14159:i:i, ' '); writeln;
	r := 1/7; for i := 1 to 25 do write(r:i, ' '); writeln;
	writeln(1e100:0:2);
	writeln(5:3, -5:3, 12345:2, 0:0, ' ', 'ab':5, 'c':3, true:6, false:2);
	writeln(round(2.5), round(3.5), round(-2.5), trunc(-2.7), round(-2.7));
	writeln(sqrt(2.0), sqr(1.5), abs(-3), abs(-3.5), sin(1.0));
	writeln(7 / 2, 7 div 2, -7 div 2, -7 mod 3, 7 mod -3);
end.
