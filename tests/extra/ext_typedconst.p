{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ext_typedconst;
const
	N: integer = 3;
	M = N * 2;
	Nombre: string = 'abc';
	L = length(Nombre) + M;
type
	T = array[1..N] of integer;
	R = 1..M;
var
	a: T;
	r1: R;
begin
	a[N] := L;
	r1 := M;
	writeln(a[3], ' ', r1, ' ', high(T), ' ', Nombre, ' ', Nombre[2]);
end.
