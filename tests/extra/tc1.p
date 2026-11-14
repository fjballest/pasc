{$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
program tc1;
type
	TP = record a: integer; b: real; end;
	TA = array[1..3] of TP;
const
	P0: TP = (a: 1; b: 2.5);
	AA: TA = ((a: 1; b: 1.0), (a: 2; b: 2.0), (a: 3; b: 3.0));
	N = 3;
	Msg = 'hola';
	X = N * 2 + 1;
	Y: real = X / 2;
	Big = high(integer) div 2;
	Car = 'z';
var
	s: string = 'inicial';
	i: integer = 7;
begin
	writeln(P0.a, ' ', P0.b:0:1, ' ', AA[3].b:0:1, ' ', Msg, ' ', X, ' ', Y:0:2, ' ', Big, ' ', Car);
	writeln(s, ' ', i);
end.
