{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program loops1;
type
	TL = 'c'..'g';
	TD = (Lun, Mar, Mie);
var
	i, n: integer;
	c: char;
	d: TD;
	b: boolean;
begin
	n := 0;
	for i := 10 downto 1 do
		n := n + i;
	writeln(n, ' ', i);
	for c in TL do write(c);
	writeln(' ', c);
	for d := Mie downto Lun do write(d, ' ');
	writeln;
	for b := false to true do write(b, ' ');
	writeln;
	i := 0;
	repeat
		i := i + 3;
	until i > 10;
	writeln(i);
	while i > 0 do
		i := i - 4;
	writeln(i);
	for i := 5 to 1 do writeln('nunca');
	writeln(i);
end.
