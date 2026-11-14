{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
{
	Errores tipicos: variable sin inicializar y fuera de rango.
	pasc errores.p
}
program errores;

const
	N = 3;

type
	TipoNums = array[1..N] of integer;

function suma(nums: TipoNums): integer;
var
	i, s: integer;
begin
	for i := 1 to N do begin
		s := s + nums[i];
	end;
	result := s;
end;

var
	nums: TipoNums;
	i: integer;
begin
	for i := 1 to N do begin
		nums[i] := i;
	end;
	writeln(suma(nums));
	i := N + 1;
	writeln(nums[i]);
end.
