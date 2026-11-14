{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program limpio;
const
	NumVeces = 3;
	Saludo: string = 'hola';
type
	TipoPunto = record
		x, y: integer;
	end;
var
	i, total: integer;
	p: TipoPunto;
function sumapunto(p: TipoPunto): integer;
begin
	result := p.x + p.y;
end;
procedure escribe(p: TipoPunto);
begin
	writeln(p.x, ' ', p.y);
end;
procedure fatal(msg: string);
begin
	writeln('error: ', msg);
	halt(1);
end;
function divide(a, b: integer): integer;
begin
	if b = 0 then begin
		fatal('division por cero');
	end;
	result := a div b;
end;
begin
	total := 0;
	for i := 1 to NumVeces do begin
		p.x := i;
		p.y := 2 * i;
		total := total + sumapunto(p);
		escribe(p);
	end;
	writeln(Saludo, ' ', total, ' ', divide(total, 2));
	writeln('a');
	writeln('b');
	writeln('c');
end.
