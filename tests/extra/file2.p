{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program file2;
var
	f: text;
begin
	assign(f, 'x.tmp');
	writeln(f, 'hola');
end.
