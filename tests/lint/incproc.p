program incproc;

procedure incr(var x: integer);
begin
	x := x + 1;
end;

procedure incrn(var x: integer; n: integer);
begin
	x := x + n;
end;

procedure doble(var x: integer; n: integer);
begin
	x := 2 * n;
end;

var
	i: integer;
begin
	i := 0;
	incr(i);
	incrn(i, 3);
	doble(i, 3);
	writeln(i);
end.
