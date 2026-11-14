{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program ptr1;
type
	TNodo = ^TRNodo;
	TRNodo = record
		val: integer;
		sig: TNodo;
	end;
var
	l, p: TNodo;
	i: integer;
procedure push(var l: TNodo; v: integer);
var n: TNodo;
begin
	new(n);
	n^.val := v;
	n^.sig := l;
	l := n;
end;
begin
	l := nil;
	for i := 1 to 5 do
		push(l, i * i);
	p := l;
	while p <> nil do begin
		write(p^.val, ' ');
		p := p^.sig;
	end;
	writeln;
	while l <> nil do begin
		p := l;
		l := l^.sig;
		dispose(p);
	end;
	writeln(l = nil);
	writeln(l^.val);
end.
