{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program fbuf;
var f: text; g: text; i: integer; s: string;
begin
	assign(f, 'zz.tmp'); rewrite(f); writeln(f, 'hola');
	assign(g, 'zz2.tmp'); rewrite(g); for i := 1 to 100 do writeln(g, 'linea ', i);
	assign(f, 'zz2.tmp'); reset(f); i := 0;
	while not eof(f) do begin readln(f, s); i := i + 1; end;
	writeln(i, ' ', s);
end.
