{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program single2; uses math; var i: integer; r: real; begin i := 3; writeln(sin(i*1.0)); writeln(sin(2.0)); writeln(i*1.0 ** 2); writeln(intpower(i*1.0, 2)); r := 0.1; writeln(r = 0.1, ' ', i * 0.1); writeln(-(i*1.5)); writeln(i * 1.5 / 7); writeln(i / 7 * 1.5); 
writeln(16777217 + 0.5); writeln(16777217 * 1.0 = 16777216); writeln(sqr(i * 1.5)); writeln(sqrt(i*1.5)); writeln(abs(-i * 1.5)); end.
