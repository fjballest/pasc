program restr_nestif;

var
	a: integer;
begin
	a := 1;
	if a > 0 then begin
		if a > 0 then begin
			if a > 0 then begin
				if a > 0 then begin
					if a > 0 then begin
						if a > 0 then begin
							if a > 0 then begin
								writeln(a);
							end;
						end;
					end;
				end;
			end;
		end;
	end;
end.
