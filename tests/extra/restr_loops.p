program restr_loops;

var
	i, n: integer;
begin
	n := 0;
	for i := 1 to 3 do begin
		n := n + 1;
	end;
	for i := 1 to 3 do begin
		n := n + 1;
	end;
	while n > 0 do begin
		n := n - 1;
	end;
	repeat
		n := n + 1;
	until n = 3;
	for i := 1 to 3 do begin
		n := n + 1;
	end;
	writeln(n);
end.
