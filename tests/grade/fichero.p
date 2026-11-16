program fichero;

var
	f: text;
	n: integer;
begin
	assign(f, 'entrada.txt');
	reset(f);
	readln(f, n);
	close(f);
	writeln('doble: ', 2 * n);
end.
