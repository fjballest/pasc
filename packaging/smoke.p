{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program smoke;
uses math;
var
	r: real;
begin
	r := 2.0 ** 0.5;
	writeln('pasc works: ', r:0:4);
end.
