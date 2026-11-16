program estructura;

procedure muchos(n: integer);
var
	i, j, k: integer;
begin
	for i := 1 to n do begin
		for j := 1 to n do begin
			for k := 1 to n do begin
				writeln(i, j, k);
			end;
		end;
	end;
	i := 0;
	while i < n do begin
		i := i + 1;
	end;
	repeat
		i := i - 1;
	until i = 0;
end;

procedure anidados(a, b, c, d, e, f: integer);
begin
	if a > 0 then begin
		if b > 0 then begin
			case c of
				1: begin
					if d > 0 then begin
						if e > 0 then begin
							if f > 0 then begin
								if a > b then begin
									writeln('profundo');
								end;
							end;
						end;
					end;
				end;
			end;
		end;
	end;
end;

procedure cadena(x: integer);
begin
	if x = 1 then begin
		writeln(1);
	end else if x = 2 then begin
		writeln(2);
	end else if x = 3 then begin
		writeln(3);
	end else if x = 4 then begin
		writeln(4);
	end else if x = 5 then begin
		writeln(5);
	end else if x = 6 then begin
		writeln(6);
	end else if x = 7 then begin
		writeln(7);
	end;
end;

procedure seguidos(x: integer);
begin
	if x = 1 then begin
		writeln(1);
	end;
	if x = 2 then begin
		writeln(2);
	end;
	if x = 3 then begin
		writeln(3);
	end;
	if x = 4 then begin
		writeln(4);
	end;
	if x = 5 then begin
		writeln(5);
	end;
	if x = 6 then begin
		writeln(6);
	end;
	if x = 7 then begin
		writeln(7);
	end;
end;

begin
	muchos(1);
	anidados(1, 1, 1, 1, 1, 1);
	cadena(3);
	seguidos(3);
end.
