program restr_nestloops;

var
	i, j, k: integer;
begin
	for i := 1 to 2 do begin
		for j := 1 to 2 do begin
			for k := 1 to 2 do begin
				writeln(i, j, k);
			end;
		end;
	end;
end.
