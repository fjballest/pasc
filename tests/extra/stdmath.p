{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}
program fns;

type
	Big = 0..2000000000000;

var
	i: integer;
	x: real;
	n: Big;
begin
	writeln(cos(0), ' ', cos(1.5));
	writeln(arctan(1) * 4, ' ', pi);
	writeln(exp(1), ' ', ln(10), ' ', ln(exp(2)));
	writeln(frac(3.75), ' ', frac(-3.75), ' ', int(-3.75), ' ', int(2.5));
	writeln(odd(3), ' ', odd(-3), ' ', odd(4), ' ', odd(0));
	writeln(pi:0:5, ' ', pi * 2:10:3);
	x := 2;
	writeln(cos(x), ' ', arctan(x):0:12, ' ', exp(x), ' ', ln(x), ' ', frac(x / 3), ' ', int(x * 1.6));
	i := 7;
	writeln(odd(i), ' ', exp(i):0:4);
	for i := 1 to 10 do begin
		write(random(100), ' ');
	end;
	writeln();
	for i := 1 to 3 do begin
		writeln(random);
	end;
	writeln(random(-10));
	n := 1000000000000;
	writeln(random(n));
	writeln(random(0));
end.
