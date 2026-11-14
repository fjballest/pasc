{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program runs;
type
	TipoColor = (Rojo, Verde);
	TipoNums = array[1..30] of integer;
	TipoCols = array[1..10] of TipoColor;
var
	nums: TipoNums;
	cols: TipoCols;
	i: integer;
begin
	for i := 1 to 30 do
		nums[i] := 0;
	nums[3] := 7;
	nums[30] := 9;
	for i := 1 to 4 do
		cols[i] := Verde;
	stack();
	stack(1);
end.
