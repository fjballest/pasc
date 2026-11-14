{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
{
	Lista enlazada de palabras leidas de un fichero.
	pascdb lista.p
}
program lista;

const
	MaxPal = 20;

type
	TipoPal = string[MaxPal];
	TipoNodo = ^TipoRNodo;
	TipoRNodo = record
		pal: TipoPal;
		veces: integer;
		sig: TipoNodo;
	end;

procedure leerpal(var f: text; var pal: TipoPal);
var
	c: char;
begin
	pal := '';
	while not eof(f) and not eoln(f) and (length(pal) < MaxPal) do begin
		read(f, c);
		if c <> ' ' then begin
			pal := pal + c;
		end;
	end;
	if not eof(f) then begin
		readln(f);
	end;
end;

procedure insertar(var l: TipoNodo; pal: TipoPal);
var
	n: TipoNodo;
begin
	new(n);
	n^.pal := pal;
	n^.veces := 1;
	n^.sig := l;
	l := n;
end;

function longitud(l: TipoNodo): integer;
begin
	result := 0;
	while l <> nil do begin
		result := result + 1;
		l := l^.sig;
	end;
end;

var
	f: text;
	l: TipoNodo;
	pal: TipoPal;
begin
	assign(f, 'palabras.txt');
	reset(f);
	l := nil;
	while not eof(f) do begin
		leerpal(f, pal);
		insertar(l, pal);
	end;
	close(f);
	writeln('palabras: ', longitud(l));
end.
