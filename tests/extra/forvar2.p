{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program forv2; procedure p(var i: integer); begin for i := 1 to 3 do write(i); end; procedure q(i: integer); begin for i := 1 to 3 do write(i); end; var k: integer; begin p(k); q(k); writeln; end.
