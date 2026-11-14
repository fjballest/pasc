{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ficheros;
var
	f, g: text;
	s: string;
begin
	assign(f, 'uno.tmp');
	rewrite(f);
	writeln(f, 'hola');
	close(f);
	assign(g, 'uno.tmp');
	reset(g);
	readln(g, s);
	writeln(s);
end.
