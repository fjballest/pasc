{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program file3;
var
	f: text;
	c: char;
begin
	assign(f, 'datos.txt');
	reset(f);
	while not eof(f) do begin
		read(f, c);
		if c = #10 then
			write('|')
		else
			write(c);
	end;
	writeln;
	close(f);
	close(f);
end.
