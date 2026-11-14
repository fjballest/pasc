# pasc

`pasc` runs programs written in the restricted Free Pascal dialect used in
the course sources (the `.p` files in the parent directory). It is pure
Python 3 (3.7 or later), has no dependencies, and runs the same way on
macOS, Linux and Windows.

## Installing

Students: see [INSTALAR.md](INSTALAR.md), a step-by-step guide in Spanish.

Download an installer from the
[releases page](https://github.com/fjballest/pasc/releases). None of them
needs Python:

* **Windows 7 or later:** run `pasc-VERSION-windows-setup.exe`. It needs no
  administrator rights and adds `pasc` to the PATH; open a new terminal
  afterwards. `pasc-VERSION-windows-portable.zip` is the same without
  installing.
* **macOS 10.13 or later** (Intel and Apple silicon): open
  `pasc-VERSION-macos.pkg`. It installs `/usr/local/bin/pasc`. The package is
  not signed, so if macOS refuses to open it, right-click it and choose Open.
* **Linux x86_64** (any distribution from 2017 on): unpack
  `pasc-VERSION-linux-x86_64.tar.gz` and run `./install.sh`. It installs
  in `~/.local/bin`; `sudo ./install.sh /usr/local` installs for everyone.
* **Anywhere with Python 3.7 or later:** unzip `pasc-VERSION-source.zip`
  and run `python3 pasc.py prog.p`.

To make a new release, set `VERSION` in `pasclib/__init__.py` and push a
tag such as `v1.1`. The workflow in `.github/workflows/release.yml` tests
pasc, builds the installers with PyInstaller on GitHub and publishes them.
Running the workflow by hand only builds them; they appear as artifacts
of the run.

## Using it

```
./pasc prog.p            # from the source: macOS / Linux   (or: python3 pasc.py prog.p)
pasc prog.p              # Windows, using pasc.bat (needs the py launcher)
pasc -c prog.p           # only compile (check) the program
pasc -S prog.p           # print the bytecode
pasc --stack 64 prog.p   # stack size in MB (default 16)
pasc -w prog.p           # also report style warnings (see below)
pasc -z prog.p           # uninitialised memory is zero, not random
pasc --seed 7 prog.p     # repeatable random contents for uninitialised memory
```

The source is compiled into an in-memory bytecode. Compile errors stop
compilation and are reported as `file:line:col: error: message`, using
fpc's wording where it applies. The bytecode then runs on a stack VM.
The exit status is the program's `halt` code, or the FPC run-time error
number after a message such as

```
Runtime error 201 at 27b.diasem.p:34: Range check error
  in main program
```

## Teaching aids

These deliberately go beyond (or against) fpc, to help students learn:

* **Uninitialised memory is random.** Global and local variables, function
  results and blocks from `new` start with garbage, so a program that
  forgets to initialise something misbehaves visibly. fpc zeroes global
  variables; `-z` makes all of it zero. `--seed N` repeats a run.
* **Typed constants are constants.** Their value can be used in later
  constant declarations and types (`const N: integer = 3; type T =
  array[1..N] of real;`), and they cannot be assigned. fpc allows neither.
* **Memory leaks.** When the program ends, every block allocated with `new`
  and never disposed is reported, grouped by the line that allocated it.
* **`stack()`** prints, on standard error, every active procedure and
  function with its parameters (and what `var` parameters refer to), its
  locals and its result, then the global variables and the heap in use.
  It shows records, arrays, strings, enumerations and pointers by value,
  and marks garbage values.
* **Functions must not do input/output.** Using `read`, `eof`, files,
  etc. in a function, or calling a procedure that does, is a compile
  error. `write` and `writeln` (directly or through a procedure that only
  writes) are allowed for debugging, with a warning. Writing an error
  message right before `halt`, as in a `fatal` procedure, gets no warning.
* **No `ord` to compare characters.** `ord(c) >= ord('a')` is a compile
  error: write `c >= 'a'`.
* **"should be a function".** A procedure that does no input/output and
  only assigns a value to its single `var` parameter gets a warning.

### Style warnings (`-w`)

`-w` reports:

* lines that are too long;
* procedure, function and main program bodies that are too long (the
  problem is not split into subproblems);
* routines with too many parameters (records or arrays would be better);
* two routines with the same body, up to the names of their parameters and
  locals;
* the same statement, or group of statements, written several times in a
  row, perhaps instead of a loop or a procedure (numbers may differ between
  the copies);
* `x = True`, `x <> False` and the like, where the comparison is not needed;
* `if c then x := true else x := false` (or `result := ...`), which should
  assign or return `c` or `not c` directly;
* naming style: constants, enumeration values and types start with an
  uppercase letter; variables, parameters, fields, procedures and functions
  are all lowercase; a name is always written as it was declared.

All the limits are in one table, `pasclib/limits.py`. Change a number there,
or set an entry to `None` to turn that check off.

## Semantics

Programs behave as if built by fpc 3.2 for a 64-bit target with

    {$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}

whether or not the file has that line (directives are accepted and
ignored). In detail:

* `integer` is 32 bits. Integer arithmetic is done in 64 bits, as fpc does
  on 64-bit CPUs, with overflow checks (error 215). Range checks (201)
  apply when a value is stored in a smaller type, and also to array and
  string indexes, `succ`, `pred` and `chr`.
* `real` (and `float` from `math`) is a double. Real constants that fit
  exactly in a single, like `2.5`, are singles, as in fpc. This shows in
  `writeln(5.0/2)`, which prints ` 2.500000000E+00`, and in constant
  folding.
* `write` and `writeln` format numbers with fpc's algorithm: the default
  `E` notation, `:w`, `:w:d` and the rounding rules. Enumerations print
  their names and booleans print `TRUE`/`FALSE`.
* `string` is a shortstring (`string[255]`), and `s[0]` is its length
  byte. `string[n]`, `array of char` and the conversions between them
  work as in fpc. `var` string parameters must match exactly ($V+).
* `read` and `readln` follow fpc's rules: blanks are skipped before
  numbers and enumeration names, and reading a real at end of file is
  error 106 while reading an integer gives 0. `eof`, `eoln` and `val`
  behave the same way.
* Text files use fpc's 256-byte buffer: a file that is never closed loses
  its last partial buffer, as with fpc.
* `@x` has the typed pointer type ($T+). `new` and `dispose` use a heap;
  dereferencing `nil` is error 216.
* As in fpc, a program with `uses math` (which brings in sysutils) reports
  run-time errors as unhandled exceptions (`ERangeError: Range check
  error`, ...) and exits with status 217.
* Files without the `{$mode objfpc}...` line still get these semantics.
  fpc would compile them in its default mode, where `integer` is 16 bits.

## The subset

pasc implements only what the course programs use:

* Types: `integer`, `char`, `boolean`, `real`, `string`, `string[n]`,
  `text`, enumerations, subranges, arrays (indexed by any ordinal type;
  `a[i, j]` works too), records, pointers, and `float` with `uses math`.
* Declarations: `const` (plain and typed, including record and array
  initialisers), `type`, `var` (including initialised variables),
  procedures and functions with value and `var` parameters, and `result`
  or the function name to set the result.
* Statements: assignment, `if`, `case` (with ranges, `else`/`otherwise`,
  and string selectors), `while`, `repeat`, `for ... to/downto`,
  `for ... in` over an ordinal type, compound statements, and procedure
  calls.
* Operators: `+ - * / div mod and or xor not shl shr = <> < > <= >= @ ^`.
  With `uses math` you also get `**` and `mod` on reals.
* Routines: `write writeln read readln eof eoln assign reset rewrite
  close halt ord chr succ pred low high length setlength val sqr sqrt abs
  sin trunc round new dispose stack`, `input`, `output`, and `intpower` from
  `math`.

Anything else is a compile error, even where fpc would accept it. That
includes sets, dynamic and open arrays, nested routines, `exit`, `break`,
`inc`, `with`, `const` parameters, units other than `math`, and assigning
text variables. As in fpc, `and` and `or` short-circuit.

## Known differences from fpc

* Floating-point division by zero is error 200 and invalid operations are
  207, as fpc reports them on x86-64 and Windows. fpc on arm64 macOS
  reports 216 for both.
* Infinite recursion ends with error 202 (stack overflow) instead of a
  crash.
* `pasc` is an interpreter, so it is much slower than native code (a few
  million bytecode instructions per second). That is plenty for the course
  programs.

## Layout

| File | Purpose |
|---|---|
| `pasc.py` | command line driver |
| `pasclib/lexer.py`, `parser.py`, `ast.py` | tokens and syntax tree |
| `pasclib/types.py`, `compiler.py` | type checking and bytecode generation |
| `pasclib/code.py` | the bytecode (opcodes and disassembler) |
| `pasclib/vm.py` | the virtual machine and run-time library |
| `pasclib/textio.py`, `fmt.py` | text files, number formatting, `val` |
| `pasclib/debug.py` | `stack()` and the leak report |
| `pasclib/lint.py`, `limits.py` | style warnings and their limits |

## Tests

```
python3 tests/run_tests.py     # every program in the course directory
python3 tests/difftest.py      # tests/extra: edge cases and compile errors
python3 tests/lint_test.py     # tests/lint: the warnings
python3 tests/features_test.py # stack(), leak report, random memory
```

The fpc comparisons run pasc with `-z`. With `RANDOM_MEM=1`,
`run_tests.py` uses random memory instead, which shows the course programs
that read uninitialised data (`44.arrys.p` and `53.str.p`).

`run_tests.py` compares each course program's output and exit status with
fpc's, recorded in `tests/expected/`. `gen_expected.py` regenerates those
results and needs fpc. Each program runs in a scratch directory, so the
course sources and data files are never modified. `difftest.py` runs
`tests/extra/*.p` through fpc and through pasc and compares the results.
fpc's results are cached in `tests/extra/expected/`, so neither script
needs fpc to run. Files named `restr_*.p` are programs that fpc accepts
but that fall outside the subset, so pasc must reject them. Files named
`ext_*.p` use a pasc extension that fpc rejects; they must print `X.out`.
