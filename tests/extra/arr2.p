{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program arr2;
type
	TM = array[1..3, 1..4] of integer;
	TB = array[boolean] of char;
	TE = array['a'..'c'] of integer;
var
	m: TM;
	b: TB;
	e: TE;
	i, j: integer;
	c: char;
begin
	for i := 1 to 3 do
		for j := 1 to 4 do
			m[i, j] := i * 10 + j;
	for i := 1 to 3 do begin
		for j := 1 to 4 do
			write(m[i][j]:4);
		writeln;
	end;
	b[false] := 'F'; b[true] := 'T';
	writeln(b[1 > 2], b[2 > 1]);
	for c := 'a' to 'c' do e[c] := ord(c);
	writeln(e['b'], low(e), high(e), low(m), high(m));
	j := 5;
	m[2, j] := 0;
end.
