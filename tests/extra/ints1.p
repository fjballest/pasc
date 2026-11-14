{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ints1;
var
	i, j: integer;
	b: 0..10;
	c: char;
begin
	i := high(integer);
	j := i * 2 div 4;
	writeln(j);
	writeln(i + 1);
	writeln(low(integer), ' ', high(integer));
	b := 10;
	writeln(b * 1000);
	c := 'A';
	writeln(ord(c) + 1, chr(ord(c) + 2), succ(c), pred(c));
	writeln(ord(true), ord(false), ord('0'));
	i := 3; j := 4;
	writeln(i and j, ' ', i or j, ' ', i xor j, ' ', not i);
	writeln((i < j) and (j > 0), ' ', not (i = j));
	i := -2147483647;
	writeln(i - 1);
	i := i - 2;
end.
