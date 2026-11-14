{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program halt1;
begin
	writeln('antes');
	halt(3);
	writeln('despues');
end.
