{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program case1;
type
	TC = (Rojo, Verde, Azul);
var
	i: integer;
	c: char;
	col: TC;
begin
	for i := -2 to 12 do
		case i of
		0: write('cero ');
		1, 2, 3: write('poco ');
		4..9: write('medio ');
		otherwise write('otro ');
		end;
	writeln;
	for c := 'a' to 'f' do
		case c of
		'a', 'e': write('vocal ');
		'b'..'d': write('cons ');
		else
			write('? ');
			write('! ');
		end;
	writeln;
	for col := Rojo to Azul do
		case col of
		Rojo: writeln('rojo');
		Azul: writeln('azul');
		end;
end.
