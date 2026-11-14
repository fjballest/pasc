{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program mathops;
uses math;
var
	r, s: real;
	i: integer;
	b: boolean;
begin
	r := 6.28; s := 2.0;
	writeln(r mod s, ' ', 7.5 mod 2, ' ', -7.5 mod 2.0, ' ', 10 mod 3);
	writeln(2 ** 10, ' ', 2.0 ** 0.5, ' ', 3 ** 0, ' ', 2 ** -1, ' ', 1.5 ** 2);
	i := 3;
	writeln(intpower(2, i), ' ', intpower(1.5, -2), ' ', i ** 3);
	writeln(r:300:2);
	b := 1 = 1 = true;
	writeln(b, ' ', (i < 4) = (i > 2));
	writeln(i ** 40);
end.
