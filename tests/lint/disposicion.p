program disposicion;

var
	i: integer;
begin
	i := 1;
	if i > 0 then begin
		writeln(1);
	end else begin
		writeln(2);
	end;
	if i > 0 then begin writeln(3); end;
	while i > 0 do
	begin
		i := i - 1;
	end;
	case i of
	0:
		begin
			writeln(4);
			writeln(5);
		end;
	1: begin writeln(6); writeln(7); end;
	end;
end.
