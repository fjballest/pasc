{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ptr2;
type
	PP = ^TP;
	TP = record
		nombre: string[10];
		edad: integer;
		sig: PP;
	end;
	PI = ^integer;
var
	l, q: PP;
	a, b: PI;
	x: integer;
procedure ins(var l: PP; n: string; e: integer);
var p: PP;
begin
	new(p);
	p^.nombre := n;
	p^.edad := e;
	p^.sig := l;
	l := p;
end;
function busca(l: PP; n: string): PP;
begin
	result := l;
	while (result <> nil) and (result^.nombre <> n) do
		result := result^.sig;
end;
begin
	l := nil;
	ins(l, 'ana', 20);
	ins(l, 'luis', 30);
	ins(l, 'eva', 25);
	q := busca(l, 'luis');
	writeln(q^.nombre, ' ', q^.edad);
	writeln(busca(l, 'pepe') = nil);
	q^.edad := q^.edad + 1;
	writeln(busca(l, 'luis')^.edad);
	x := 5;
	a := @x;
	b := a;
	b^ := b^ * 2;
	writeln(x, ' ', a = b, ' ', a^);
	new(a);
	a^ := 1;
	writeln(a <> b, ' ', a^, ' ', b^);
	dispose(a);
	q := busca(l, 'pepe');
	writeln(q^.edad);
end.
