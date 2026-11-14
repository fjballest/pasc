{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rec2;
function fact(n: integer): integer;
begin
	if n <= 1 then
		result := 1
	else
		result := n * fact(n - 1);
end;
function fib(n: integer): integer;
begin
	if n < 2 then
		fib := n
	else
		fib := fib(n - 1) + fib(n - 2);
end;
var
	i: integer;
begin
	for i := 0 to 12 do
		write(fact(i), ' ');
	writeln;
	for i := 0 to 20 do
		write(fib(i), ' ');
	writeln;
	writeln(fact(13));
end.
