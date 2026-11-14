{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
{
	Puntos en el plano: registros, arrays y parametros var.
	pascdb puntos.p
}
program puntos;

const
	MaxPuntos = 5;

type
	TipoPunto = record
		x, y: integer;
	end;
	TipoPuntos = array[1..MaxPuntos] of TipoPunto;
	TipoNube = record
		puntos: TipoPuntos;
		npuntos: integer;
	end;

procedure mover(var p: TipoPunto; dx, dy: integer);
begin
	p.x := p.x + dx;
	p.y := p.y + dy;
end;

procedure moverpuntos(var nube: TipoNube; dx, dy: integer);
var
	i: integer;
begin
	for i := 1 to nube.npuntos do begin
		mover(nube.puntos[i], dx, dy);
	end;
end;

procedure anadir(var nube: TipoNube; x, y: integer);
begin
	nube.npuntos := nube.npuntos + 1;
	nube.puntos[nube.npuntos].x := x;
	nube.puntos[nube.npuntos].y := y;
end;

var
	nube: TipoNube;
begin
	nube.npuntos := 0;
	anadir(nube, 1, 2);
	anadir(nube, 3, 4);
	moverpuntos(nube, 10, 20);
	writeln(nube.puntos[1].x, ' ', nube.puntos[2].y);
end.
