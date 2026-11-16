program ext_casemulti;

type
	TipoColor = (Rojo, Verde, Azul);

var
	c: TipoColor;
	i: integer;
begin
	for c := Rojo to Azul do begin
		case c of
		Rojo:
			writeln('rojo');
			writeln(ord(c): 3);
		Verde, Azul:
			i := ord(c);
			writeln('otro ', i);
			if i > 1 then begin
				writeln('azul');
			end;
		end;
	end;
	for i := 1 to 4 do begin
		case i of
		1..2:
			write('a');
			write('b');
		3:
			begin
				write('c');
			end;
		else
			write('d');
			writeln();
		end;
	end;
end.
