{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program estilo;
const
	maxNotas = 3;
	Limite: integer = 10;
type
	tipoNota = 1..Limite;
	TipoP = record
		X: integer;
	end;
	TipoC = (rojo, Verde);
var
	Total: integer;
	n: integer;
procedure Escribe(a, b, c, d, e, f, g, h: integer);
begin
	writeln(a + b + c + d + e + f + g + h);
end;
function doble(x: integer): integer;
var
	aux: integer;
begin
	aux := x * 2;
	result := aux + 0 * x + 0 * x + 0;
end;
function otro(y: integer): integer;
var
	z: integer;
begin
	z := y * 2;
	result := z + 0 * y + 0 * y + 0;
end;
procedure calcula(n: integer; var r: integer);
begin
	r := n * n;
end;
begin
	n := 1;
	writeln('una linea demasiado larga para el limite de cien columnas de este programa, que sigue y sigue un poco mas');
	writeln(doble(1));
	writeln(doble(2));
	writeln(doble(3));
	N := N + 1;
	Total := 0;
	Escribe(1, 2, 3, 4, 5, 6, 7, 8);
	calcula(3, total);
	writeln(otro(1), maxNotas);
end.
