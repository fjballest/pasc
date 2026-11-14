{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program perf;
const
	N = 20000;
function esprimo(n: integer): boolean;
var
	i: integer;
begin
	result := n > 1;
	i := 2;
	while (i * i <= n) and result do begin
		if n mod i = 0 then
			result := false;
		i := i + 1;
	end;
end;
var
	i, cuantos: integer;
	a: array[1..1000] of integer;
	j, k, aux: integer;
begin
	cuantos := 0;
	for i := 1 to N do
		if esprimo(i) then
			cuantos := cuantos + 1;
	writeln(cuantos);
	for i := 1 to 1000 do
		a[i] := (i * 7919) mod 1000;
	for j := 1 to 999 do
		for k := 1 to 1000 - j do
			if a[k] > a[k+1] then begin
				aux := a[k]; a[k] := a[k+1]; a[k+1] := aux;
			end;
	writeln(a[1], ' ', a[500], ' ', a[1000]);
end.
