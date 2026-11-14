{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program forv3; type R = record x: integer; end; var r1: R; begin for r1.x := 1 to 3 do write(r1.x); end.
