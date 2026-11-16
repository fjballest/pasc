program tipos;

const
	N = 3;
	Primos: array[1..N] of integer = (2, 3, 5);

type
	TipoNums = array[1..N] of integer;
	TipoLetras = array['a'..'z'] of integer;
	TipoMal = array[(Uno, Dos)] of integer;
	TipoTabla = array[1..N] of array[1..N] of char;
	TipoNodo = record
		nums: TipoNums;
		otros: array[1..N] of integer;
		nombre: string[10];
		sig: ^TipoNodo;
		color: (Rojo, Verde);
		ok: boolean;
	end;

var
	nums: TipoNums;
	cuenta: array[1..N] of integer;
	dia: 1..31;
begin
	nums[1] := Primos[1];
	cuenta[1] := 0;
	dia := 1;
	writeln(nums[1], cuenta[1], dia);
end.
