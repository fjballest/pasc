{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program booleanos;
var
	b, c: boolean;
	n: integer;
function espar(n: integer): boolean;
begin
	if n mod 2 = 0 then
		result := true
	else
		result := false;
end;
function esimpar(n: integer): boolean;
begin
	if n mod 2 = 0 then begin
		esimpar := false;
	end
	else begin
		esimpar := true;
	end;
end;
begin
	n := 3;
	if espar(n) = True then
		writeln('par');
	if esimpar(n) <> false then
		writeln('impar');
	b := esimpar(n) = false;
	if n > 2 then
		c := true
	else
		c := false;
	writeln(b, c, b = c);
end.
