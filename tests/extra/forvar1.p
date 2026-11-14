{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program forv1; var i: integer; procedure p; begin for i := 1 to 3 do write(i); end; begin p; writeln; end.
