{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program st;
type
	TipoColor = (Rojo, Verde);
	TipoPunto = record
		x, y: integer;
		c: TipoColor;
	end;
	TipoNodo = ^TipoRNodo;
	TipoRNodo = record
		v: integer;
		sig: TipoNodo;
	end;
	TipoNums = array[1..20] of integer;
var
	global: integer;
	lista: TipoNodo;
	nums: TipoNums;
	nombre: string[10];
procedure muestra(p: TipoPunto; var total: integer; s: string);
var
	i: integer;
	r: real;
begin
	r := 2.5;
	i := 7;
	stack();
	total := total + i;
end;
function suma(a, b: integer): integer;
var
	p: TipoPunto;
begin
	p.x := a; p.y := b; p.c := Verde;
	muestra(p, global, 'hola');
	result := a + b;
end;
var
	k: integer;
begin
	global := 1;
	nombre := 'ana';
	new(lista);
	lista^.v := 10;
	new(lista^.sig);
	lista^.sig^.v := 20;
	lista^.sig^.sig := nil;
	for k := 1 to 20 do
		nums[k] := k * k;
	writeln(suma(3, 4));
	new(lista);
end.
