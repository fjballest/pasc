{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program read4;
var
	c: char;
	n: integer;
	s: string[4];
	d: (Lun, Mar, Mie);
begin
	while not eof do begin
		if eoln then begin
			readln;
			writeln('<eol>');
		end
		else begin
			read(c);
			write('[', ord(c), ']');
		end;
	end;
	writeln;
	read(c);
	writeln(ord(c), eof, eoln);
	read(n);
	writeln(n);
	read(s);
	writeln('[', s, ']', length(s));
	read(d);
	writeln(d);
end.
