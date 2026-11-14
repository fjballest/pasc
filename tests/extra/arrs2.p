{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program arrs;
type A1 = array[1..3] of char; A2 = array[1..3] of char;
var c: A1; d: A2; s: string;
procedure q(var z: A1); begin z[1] := 'q'; end;
procedure q2(z: A1); begin writeln(z); end;
begin c := 'abcd'; writeln(c); s := 'xyzw'; c := s; writeln(c); d := c; q(d); writeln(d); q2(d); q2('ab'); q2('x'); end.
