{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program rec1;
type
	TP = record x, y: integer; end;
	TArr = array[1..3] of TP;
	TR = record nombre: string[20]; pts: TArr; n: integer; end;
function mk(x, y: integer): TP;
begin
	result.x := x;
	result.y := y;
end;
procedure muta(p: TP);
begin
	p.x := 99;
	writeln('dentro ', p.x);
end;
procedure mutav(var p: TP);
begin
	p.x := 77;
end;
function suma(r: TR): integer;
var i: integer;
begin
	result := 0;
	for i := 1 to r.n do
		result := result + r.pts[i].x + r.pts[i].y;
end;
var
	r, r2: TR;
	p: TP;
	i: integer;
begin
	r.nombre := 'figura';
	r.n := 3;
	for i := 1 to 3 do
		r.pts[i] := mk(i, 10 * i);
	r2 := r;
	r2.pts[1].x := 1000;
	writeln(suma(r), ' ', suma(r2));
	p := mk(1, 2);
	muta(p);
	writeln(p.x);
	mutav(p);
	writeln(p.x);
	mutav(r.pts[2]);
	writeln(r.pts[2].x, ' ', mk(5, 6).y);
end.
