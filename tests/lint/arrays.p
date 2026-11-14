{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program arrays;
const
	Max = 10;
type
	TipoNums = array[1..Max] of integer;
var
	nums: TipoNums;
	n, i: integer;
	esta: boolean;
procedure escribe(nums: TipoNums; i: integer);
begin
	writeln(nums[i]);
end;
function suma(nums: TipoNums; n: integer): integer;
var
	k: integer;
begin
	result := 0;
	for k := 1 to n do begin
		result := result + nums[k];
	end;
end;
function busca(nums: TipoNums; n, x: integer): boolean;
var
	k: integer;
begin
	k := 1;
	result := false;
	while (k <= n) and not result do begin
		result := nums[k] = x;
		k := k + 1;
	end;
end;
begin
	n := 3;
	for i := 1 to n do
		nums[i] := i;
	esta := false;
	for i := 1 to n do begin
		if nums[i] = 2 then begin
			esta := true;
		end;
	end;
	if esta then
		escribe(nums, 2)
	else begin
		writeln(suma(nums, n), busca(nums, n, 2));
	end;
end.
