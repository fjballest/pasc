{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program file1;
var
	f: text;
	s: string;
	n, total: integer;
begin
	assign(f, 'salida.tmp');
	rewrite(f);
	writeln(f, 'linea uno');
	writeln(f, 10, ' ', 20, ' ', 30);
	write(f, 'sin fin');
	close(f);
	reset(f);
	readln(f, s);
	writeln('[', s, ']');
	total := 0;
	while not eoln(f) do begin
		read(f, n);
		total := total + n;
	end;
	readln(f);
	writeln(total);
	readln(f, s);
	writeln('[', s, '] ', eof(f));
	close(f);
	assign(f, 'noexiste.tmp');
	reset(f);
end.
