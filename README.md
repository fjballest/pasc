# pasc

<img src="branding/logo.svg" alt="pasc logo" width="120">

`pasc` runs programs written in the restricted Free Pascal dialect used in
the course sources (the `.p` files in `../src`). It is pure
Python 3 (3.7 or later), has no dependencies, and runs the same way on
macOS, Linux and Windows.

## Documentation

* [docs/userguide.md](docs/userguide.md) ([PDF](docs/userguide.pdf)): how to use pasc and pascdb, with pascdb screenshots.
* [docs/design.md](docs/design.md) ([PDF](docs/design.pdf)): design and internals, for whoever changes pasc or pascdb.
* `docs/build.sh` regenerates both PDFs (`-s` also retakes the screenshots with `docs/shots.py`).

## Installing

Students: see [INSTALAR.md](INSTALAR.md), a step-by-step guide in Spanish. Each release also carries it as a PDF (`pasc-VERSION-INSTALAR.pdf`), and every installer and zip includes it as `INSTALAR.pdf`; the workflow builds it with `packaging/docs/build-pdf.py`.

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
pasc -w prog.p           # do not report style warnings (see below)
pasc -z prog.p           # uninitialised memory is zero, not random
pasc -g prog.p           # allow global variables before procedures
pasc -L prog.p           # do not enforce the limits on loops and nesting
pasc -R prog.p           # relaxed: the course rules (indentation, limits...) are warnings
pasc --datos prog.p      # every file the program opens is datos.txt (for grading)
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
* **Global variables last.** Global variables must be declared after all
  procedures and functions, just before the main program, so they work as
  the main program's locals and routines cannot use them. `-g` (for pasc
  and pascdb) allows them earlier.
* **Typed constants are constants.** Their value can be used in later
  constant declarations and types (`const N: integer = 3; type T =
  array[1..N] of real;`), and they cannot be assigned. fpc allows neither.
* **Memory leaks.** When the program ends, every block allocated with `new`
  and never disposed is reported, grouped by the line that allocated it.
* **`stack()`** prints, on standard error, every active procedure and
  function with its parameters (and what `var` parameters refer to), its
  locals and its result, then the global variables and the heap in use.
  It shows records, arrays, strings, enumerations and pointers by value,
  and marks garbage values. `stack(1)`, `stack(2)`, ... print more: one
  line per field or array element, indented, with structures nested one
  level deeper, pointers followed one more step and more array elements
  for each level. `stack()` is `stack(0)`. Runs of more than three equal
  (or garbage) array elements show only the first two, `...` and the last.
* **Functions must not do input/output.** Using `read`, `eof`, files,
  etc. in a function, or calling a procedure that does, is a compile
  error. `write` and `writeln` (directly or through a procedure that only
  writes) are allowed for debugging, with a warning. Writing an error
  message right before `halt`, as in a `fatal` procedure, gets no warning.
* **No `ord` to compare characters.** `ord(c) >= ord('a')` is a compile
  error: write `c >= 'a'`.
* **"should be a function".** A procedure that does no input/output and
  only assigns a value to its single `var` parameter gets a warning.
* **Indentation.** A badly indented program does not compile: the
  statements of a block are indented more than the line that opens it and
  start at the same column, and `end`, `else` and `until` line up with the
  line that opened them (tabs count as 8 columns). Indenting with spaces
  in a file that also uses tabs gets a warning suggesting tabs.
* **Limits on loops and nesting.** A procedure, function or main program
  with more than 4 loops, loops nested more than 2 deep, control
  structures (`if`, `case`, `while`, `repeat`, `for`) nested more than 6
  deep (an `else if` does not nest), or more than 6 `if` statements in a
  row (an `if ... else if ...` chain counts as one) does not compile. The
  numbers are in `pasclib/limits.py`, whose `enforced` entry lists which
  limits are errors. `-L` (pasc and pascdb) turns them into style
  warnings.
* **Named types.** A type written in place (anonymous) in a variable, a
  typed constant, a record field or an array element is an error: declare
  it with a name (`TipoNums = array[1..N] of integer;`) and use the name.
  Array indexes may be subranges written in place, and `string[n]` and
  `^T` may be written anywhere. This is an enforced
  limit too (`named_types` in `limits.py`; `-L` makes it a warning).
* **Files.** When the program ends, files still open are reported, and so
  is opening the same file a second time.
* **Big parameters.** An array or record value parameter that the routine
  never changes is passed by reference internally, so passing large data
  by value does not copy it (or overflow the stack).

### Style warnings

pasc (and pascdb) report these style warnings unless run with `-w`:

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
* bodies of `if`, `else`, `while` and `for` not written between `begin` and
  `end`;
* `end else` on one line (`else` goes on its own line, right under the
  `end`), `begin` and `end` of a block on the same line (except the
  statements of a `case` branch), and `begin` on a line of its own after
  `then`, `do` or `else` (it goes at the end of that line);
* a `for` loop that sets a boolean when it finds something but keeps going
  (it should be a `while` or `repeat` that stops);
* a routine taking an array and an index used only as `a[i]` (pass the
  element instead);
* a routine taking an array and the number of elements used in it (keep
  both in a record);
* naming style: constants, enumeration values and types start with an
  uppercase letter; variables, parameters, fields, procedures and functions
  are all lowercase; a name is always written as it was declared.

All the limits are in one table, `pasclib/limits.py`. Change a number there,
or set an entry to `None` to turn that check off.

### Per-user limits (`~/.pasclimits`)

An installed pasc can be tuned without touching `limits.py`: a plain text
file `.pasclimits` in the home directory (`$HOME/.pasclimits` on macOS and
Linux, `%USERPROFILE%\.pasclimits`, e.g. `C:\Users\ana\.pasclimits`, on
Windows) overrides its values, one `limit: value` per line:

```
# my limits
line_length: 120
loops: 6
begin_end: off
enforced: loops, nested_loops
```

Values are numbers, `on`/`off` (or `true`/`false`, `yes`/`no`), `none`,
and, for `enforced`, a list of limit names. Lines starting with `#` are
ignored, and a wrong line is reported as a warning and ignored. The
environment variable `PASCLIMITS` names another file instead (empty: no
file); the test suites set it empty.

## pascdb: watching a program run

```
pascdb prog.p
```

compiles the program and opens a page in the browser (pascdb is a small
local web server; the Salir button or Ctrl+C in the terminal ends it). The page shows:

* the source, with the statement about to run highlighted (line and
  column), and breakpoints set by clicking line numbers;
* **Datos**: a `var` parameter is shown as a dashed arrow to the argument
  it refers to (it is not a copy); when that argument was itself a `var`
  parameter of the caller, the arrow goes to it, and from there on to the
  original variable. A button switches to drawing `var` parameters as faded copies
  of their argument instead. Strings longer than 40 characters are cut
  (click one to see it whole). The program's data are drawn as boxes: one frame per active
  procedure or function with its parameters, locals and result, the global
  variables, and the blocks allocated with `new`. Records and arrays can
  be collapsed and expanded by clicking their headers, and pointers are
  arrows, so linked lists appear as chains. Garbage values are marked;
* **Pila**: the stack as it is in memory, with addresses, sizes and bytes
  of every slot, plus each call's return address and saved frame pointer;
* **Memoria**: one hex dump of all the memory in use (globals and stack,
  then the heap), with each variable's bytes shaded and named; picking a
  variable, slot or heap block in the list scrolls to it. The stack is
  shown as far as it has grown: bytes above the stack pointer (marked
  `sp ▶`) are dimmed, since they are no longer in use but still there;
* **Ficheros**: every text file open for reading (and the standard
  input), with what has been read dimmed and the next character to read
  highlighted;
* the program's output, and an input line for what it reads (EOF button
  for end of file).

After every step (also while playing), what the step changed is
highlighted: values in Datos (or the header of a collapsed structure that
contains them, and new heap blocks), slots in Pila and bytes in Memoria. Each panel scrolls so the
change is visible.

The **EN**/**ES** button switches the page between English and Spanish
(remembered by the browser).

Each of Datos, Pila, Memoria and Ficheros has a ⧉ button that opens it in its own
window, and **Juntos** shows them side by side. All the windows
follow the same run, and a variable picked in one is shown in Memoria in
all of them.

**Paso** (Enter) runs one source line, entering every procedure and
function. **Reproducir** (Space) runs the program slowly on its own at the
chosen speed, and **Continuar** runs to the next breakpoint or the end.
**Reiniciar** starts again, and **Salir** ends pascdb. pascdb uses pasc's compiler and VM (compiled
with extra LINE instructions); pasc itself does not need pascdb. It needs
only Python and a browser, and the installers include it.

## pasgrade: a first pass at grading (teachers only)

`pasgrade` lives in this repository but is left out of the releases
(`.gitattributes`); install it with `packaging/install-local.sh`.

```
pasgrade [-t secs] [-i datos.txt] [-r result.txt] [-o NOTAS.pasgrade] [-p] [-z] dir
```

compiles and runs every `NAME.p` in `dir` and writes `NOTAS.pasgrade` (never
`NOTAS`), tab separated, with the columns `nota clean burr works modok comp
warn who`. `comp` is `y`, `r` (only compiles with `pasc -R`: valid Pascal
that breaks the course rules) or `n`; `warn` says whether there are
warnings. Each program runs in a scratch directory with the input file as
`datos.txt` and as standard input, under `pasc --datos` (so whatever file
name it opens, it reads `datos.txt`), and is stopped after `secs` seconds
(endless loop). Its messages and output go to `NAME.p.out`. If `result.txt`
exists, `works` is `y` when each of its lines appears in the output, in
order, ignoring blank space, empty lines and case (`-p`: punctuation too),
`m` when only its words appear in order, mixed with other text, and `n`
otherwise. `-z` runs with zeroed memory, as fpc. The other columns are for
the teacher.

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
  string selectors and, unlike Pascal, several statements in a branch
  without `begin`/`end`), `while`, `repeat`, `for ... to/downto`,
  `for ... in` over an ordinal type, compound statements, and procedure
  calls.
* Operators: `+ - * / div mod and or xor not shl shr = <> < > <= >= @ ^`.
  With `uses math` you also get `**` and `mod` on reals.
* Routines: `write writeln read readln eof eoln assign reset rewrite
  close halt ord chr succ pred low high length setlength val new dispose
  stack`, `input`, `output`; the standard math functions `abs sqr sqrt sin
  cos arctan exp ln frac int trunc round odd pi random randomize` (`random`
  gives the same numbers as fpc's for the same seed); and `intpower` from
  `math`.

Anything else is a compile error, even where fpc would accept it. That
includes sets, dynamic and open arrays, nested routines, `exit`, `break`,
`inc`, `with`, `const` parameters, units other than `math`, and assigning
text variables. As in fpc, `and` and `or` short-circuit.

## Known differences from fpc

* Floating-point division by zero is error 200 and invalid operations are
  207, as fpc reports them on x86-64 and Windows. fpc on arm64 macOS
  reports 216 for both.
* `arctan` is fpc's own routine (fdlibm's), so it gives the same result on
  every system; the other transcendental functions (`sin`, `cos`, `exp`,
  `ln`) use the C library. Their last (17th) digit may differ from fpc's,
  as fpc's own results differ between processors.
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
| `pasclib/indent.py` | indentation checks |
| `pascdb.py`, `pascdblib/` | the browser-based stepper (server, snapshots, `ui.html`) |
| `packaging/install-local.sh` | installs the checkout for the current user (no root) |

## Tests

```
python3 tests/run_tests.py     # every program in the course directory (../src)
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
