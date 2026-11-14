{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}
program stdmathk;

const
	E = 2.5;

begin
	writeln(ln(0), exp(1000), ln(-2));
	writeln(cos(E), arctan(E), exp(E), ln(E), frac(E), int(E));
	writeln(odd(7), pi);
end.
