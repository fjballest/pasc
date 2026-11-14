{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program single1; var i: integer; r: real; begin i := 16777217; r := i * 2.0; writeln(r:0:1); r := i + 0.5; writeln(r:0:1); writeln(i / 2.0); writeln(i / 2); writeln(i * 1.5);
r := 0.1; writeln(r * 2.0); writeln(sqrt(i)); writeln(-i * 2.0); writeln(abs(i * 2.0)); writeln(sqr(i * 1.0)); writeln(sqrt(i*1.0)); writeln(i * 2.0 + r); writeln(i * 2.0 > 33554433.0);
writeln(trunc(i * 2.0)); writeln(round(i * 1.0)); writeln(i * 2.0 = 33554434); end.
