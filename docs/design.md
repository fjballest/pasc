# pasc and pascdb: design and internals

This document is for whoever has to change pasc or pascdb. It explains how
the code is organised, how a program travels from source text to a running
VM, what every module does and why it is written the way it is, and how
to test and release a change. Read sections 1 to 3 first. After that, the
rest of the document can be read in any order, as a reference.

The user's view (options, messages, the pascdb page) is in the
[user guide](userguide.md).

## 1. What the programs are

**pasc** runs programs written in the restricted Free Pascal dialect of
the course. It is a pure Python 3 program (3.7 or later, no dependencies).
It compiles the source into an in-memory bytecode, reporting errors as
`file:line:col: error: message`, and then runs the bytecode on a virtual
machine. The goal is that a course program behaves exactly as when built
with fpc 3.2.2 for a 64-bit target with

    {$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}

including output formatting, run-time error numbers and exit statuses,
plus a set of teaching aids that fpc lacks (random uninitialised memory,
leak reports, `stack()`, style warnings, indentation errors, ...).

**pascdb** is a stepper that runs on top of pasc. It compiles the program
with pasc's compiler (adding `LINE` instructions), runs it on pasc's VM in
a background thread, and shows it in a browser page served by a small
local HTTP server: the source with the current statement, the data as
boxes and arrows, the stack, the raw memory and the input files.

Two rules shaped everything:

1. **Only what the course uses.** pasc implements the features that the
   course programs (`../src/*.p`) use, and rejects the rest with a compile
   error, even if fpc would accept it. Sets, dynamic arrays, nested
   routines, `exit`, `break`, `inc`, `with`, `const` parameters and units
   other than `math` are rejected on purpose. Before adding a feature,
   check that the course needs it.
2. **fpc is the oracle.** Whenever pasc and fpc could differ, fpc is right
   unless the difference is a deliberate teaching aid or one of the known
   differences in section 13. The test suites compare pasc against fpc's
   recorded results.

## 2. Layout of the repository

| Path | What it is |
|---|---|
| `pasc.py` | command-line driver of pasc |
| `pascdb.py` | command-line driver of pascdb |
| `pasgrade.py` | first pass at grading a directory of programs (runs `pasc.py`) |
| `pasc`, `pascdb`, `pasc.bat`, `pascdb.bat` | launchers to run from a checkout |
| `pasclib/__init__.py` | `VERSION` (the one place the version is set) |
| `pasclib/lexer.py` | source text to tokens |
| `pasclib/parser.py` | tokens to syntax tree (recursive descent) |
| `pasclib/ast.py` | syntax tree node classes |
| `pasclib/types.py` | Pascal types, sizes, compatibility |
| `pasclib/compiler.py` | type checker and bytecode generator |
| `pasclib/code.py` | opcodes, `Program`, `RoutineInfo`, disassembler |
| `pasclib/vm.py` | the virtual machine and the run-time library |
| `pasclib/textio.py` | Pascal text files with FPC's reading rules |
| `pasclib/fmt.py` | FPC's real formatting, `val`, `round`, powers |
| `pasclib/errors.py` | `CompileError`, `RunError`, `Halt`, FPC error names |
| `pasclib/debug.py` | `stack()` output and the leak report |
| `pasclib/indent.py` | indentation errors and the tabs warning |
| `pasclib/lint.py` | style warnings (on unless `-w`) |
| `pasclib/limits.py` | the table of limits for the style warnings |
| `pasclib/userlimits.py` | `~/.pasclimits`: per-user overrides of the limits |
| `pascdblib/server.py` | pascdb's HTTP server and the session driving the VM |
| `pascdblib/snapshot.py` | JSON description of a paused VM |
| `pascdblib/ui.html` | the whole pascdb page (HTML, CSS and JavaScript) |
| `tests/` | test suites (section 15) |
| `packaging/` | installers, local install, PDF tools, pascdb smoke test |
| `.github/workflows/release.yml` | CI: tests, installers, GitHub release |
| `docs/` | this document, the user guide, examples, screenshots |
| `README.md`, `INSTALAR.md` | overview; installation guide for students (Spanish) |

pasc never imports pascdb. pascdb imports pasclib and adds only
`pascdblib`. The source files use tabs for indentation, and so does every
example and test program.

## 3. The pipeline at a glance

```
prog.p --lexer--> tokens --parser--> AST --indent--> (indentation errors)
                                      |
                                      +--compiler--> code.Program --vm--> run
                                      |       (type check, bytecode, warnings)
                                      +--lint (unless -w)-----> style warnings
```

`pasc.py` does, in `compile_file()` and `main()`:

1. read the file as Latin-1 (so every byte is a char, as in fpc);
2. `parse(src, fname)` (parser.py), which tokenizes and builds the AST;
3. `compile_program(tree, fname, lint, debug, early_globals)`
   (compiler.py), which runs the indentation check, compiles, and, with
   `lint=True` (the default; `-w` turns it off), runs the linter; it returns a `code.Program` with
   `prog.warnings` sorted by position;
4. print the warnings; with `-S` print `prog.disassemble()`; with `-c`
   stop;
5. `vm.run(prog, stack_size, randomize, seed)`, whose result is the exit
   status.

Every compile error is a `CompileError(fname, line, col, msg)` raised at
the first problem: there is no error recovery, as in fpc's usual
behaviour for these programs. The messages use fpc's wording where fpc
has an equivalent message (the tests check the line of the first error
against fpc's).

## 4. Lexer (`pasclib/lexer.py`)

`tokenize(src, fname)` returns a list of `Token(kind, value, text, line,
col)`. Kinds are `id`, `kw`, `int`, `real`, `str`, `sym` and `eof`.

* Identifiers and keywords are case-insensitive: `value` is the lowercase
  key used for lookups and `text` is the spelling, kept for messages and
  for the naming-style checks.
* `KEYWORDS` is the set of words reserved in objfpc mode, so a program
  cannot use, for example, `object` or `class` as a name, as in fpc.
* Comments are `{ }` (nesting), `(* *)` and `//`. Directives `{$...}` are
  skipped: pasc always uses the semantics of the `{$mode objfpc}...` line.
* Strings are `'...'` with `''` for a quote and `#65` / `#$41` char codes
  glued to them; their value is `bytes`.
* Columns count characters, with a tab counting as one; the indentation
  checker converts to visual columns itself (tabs every 8).

The token list is stored on the tree (`tree.tokens`) because the linter
compares token sequences (duplicate bodies, repeated statements).

## 5. Parser and syntax tree (`parser.py`, `ast.py`)

The parser is a plain recursive-descent parser over the token list
(`Parser.next`, `peek`, `expect_kw`, `expect_sym`, `expect_id`). There is
one method per construct: `parse_program`, `parse_decls`, `parse_consts`,
`parse_types`, `parse_vars`, `parse_routine`, `parse_type`, `parse_init`
(typed constant initialisers), `parse_stmt1`, `parse_case`, `parse_expr`,
`parse_simple`, `parse_term`, `parse_power`, `parse_factor`, and the
postfix forms (`a[i]`, `r.f`, `p^`, calls).

Nodes are classes made by `ast.node(name, fields)`. Every node has `line`
and `col` (its start). Names are pairs `(key, text)` or `Name(name,
text)` nodes. Some nodes record extra positions used by the indentation
checker and pascdb, such as `endline` on compound statements and
`endpos` on the program. The node list in `ast.py` is short and
readable: it is the best summary of the language pasc accepts.

A `case` branch may hold several statements without `begin`/`end`
(`parse_branch()`): they end at `end`, `else`, `otherwise` or the start
of the next label list, which `branch_ends()` recognises by scanning
constants, ranges and commas up to a `:` (there are no goto labels, so
no statement looks like that). They are kept as a `Compound` with
`bare = True`, which `indent.py` checks as a list under the label.

Things the parser rejects directly (because they are outside the subset)
produce errors there: nested routines, open array and `const` parameters,
procedure directives, variant records, dynamic arrays, sets, unsupported
statements (`with`, `goto`, ...) and operators.
Things that need types (such as an `exit` that is really a call) are left
to the compiler.

## 6. Types (`pasclib/types.py`)

Types are objects, compared by identity except where `same_type()` says
otherwise.

| Class | Pascal types | Size | Notes |
|---|---|---|---|
| `OrdType` | integer, int64, char, boolean, enumerations, subranges | 1, 2, 4 or 8 | `kind` is int/char/bool/enum; `lo`, `hi`; `base` is the host type of a subrange; `root()` decides assignment compatibility; `mk` is the struct letter used to load/store it |
| `RealType` | real (double), single | 8 or 4 | real constants that are exact in single precision are typed single, as fpc does |
| `StringType` | string, string[n] | n+1 | shortstring: length byte then chars |
| `ArrayType` | arrays | count * elem | `index` is an OrdType; `lo`, `hi`, `count`; `is_chararray()` |
| `RecordType` | records | sum of fields | `fields`: key -> (offset, type, spelling), in order; no padding (FPC packs these records the same way for the course's types) |
| `PointerType` | `^T` | 8 | `target` may be resolved later (forward pointer types) |
| `NilType` | the type of `nil` | 8 | |
| `FileType` | text | 8 | holds a VM file handle (an index in `vm.files`) |

Sizes follow FPC on 64-bit targets: `integer` is 32 bits (objfpc mode),
a subrange takes the smallest of 1/2/4/8 bytes that holds it, enumerations
take 4 bytes, pointers 8. Getting the sizes right matters: they show in
`sizeof`-like behaviour, in pascdb's memory view and in range checks on
stores.

The `mk` letters are those of Python's `struct` module: `b B h H i I q Q`
(8 to 64 bits, signed/unsigned), `d` for a double, `f` for a single.

## 7. The compiler (`pasclib/compiler.py`)

The compiler is a single class, `Compiler`, that checks types and emits
code in one walk over the tree. It is the largest module (about 1900
lines) and the one most changes touch.

### 7.1 Main data structures

* **`Sym`**: a symbol table entry. `kind` is `const`, `var`, `type`,
  `routine`, `builtin`, `program` or `unit`. Variables carry `where`:
  `('g', addr)` for a global (absolute address), `('l', off)` for a local
  or value parameter (offset from the frame pointer), or `('r', off)` for
  a reference: a slot in the frame holding the address of the variable
  (var parameters, unchanged array/record parameters, structured function
  results). Typed constants are variables with `typedconst = True` and,
  when simple, a `value` usable in constant expressions. For-loop control
  variables are `locked` while the loop runs.
* **Scopes**: `self.scopes` is a list of dicts from lowercase key to
  `Sym`: the system scope (`init_system()`: predefined types, `true`,
  `false`, built-in routines, `input` and `output`), the `math` scope if
  the program uses `math`, the global scope and, while compiling a
  routine, its scope. `lookup()` searches from the innermost; `use()` is
  `lookup()` plus the consistent-case style check; `declare()` reports
  duplicates and runs the naming checks.
* **`Ex`**: the result of checking an expression: its `type`, its folded
  constant `const` (or `None`), `vcode` (instructions that push the value;
  for structured types, the address) and `acode` (instructions that push
  the address, for designators). `assignable`, `sym`, `istype` and
  `isproc` complete it. Code is always a Python list of `(op, arg, line)`
  tuples, so expressions are compiled bottom-up by concatenating lists.
* **`Routine`**: the context of the routine being compiled: frame
  allocation (`alloc()`, `frame`, `maxframe`, temporaries above
  `tempmark`), the result symbol, whether the result was set, and the
  data used by the teaching checks: `io` (first input/output done), `wio`
  (first write), `uses` and `whole` (how var parameters are used, for the
  "should be a function" warning).
* **`code.Program`** (output): `ops`, `args` and `lines` (three parallel
  lists, one entry per instruction), `routines` (a `RoutineInfo` per
  routine; index 0 is the main program), `globsize`, `image` (initial
  contents of global memory), `init_ranges` (the parts of the image that
  must be copied: initialised variables and typed constants), `globals`
  (name, address, type: used by `stack()` and pascdb), `warnings` and
  `uses_math`.
* **`RoutineInfo`**: `entry` (pc), `framesize`, `params` (how the VM
  pops arguments into the new frame: `('val', off, mk)`, `('ref', off,
  None)`, `('str', off, maxlen)`, `('copy', off, size)`, in pop order),
  `result` (`('val', off, mk)`, `('str', off, None)` or `('none', ...)`),
  `line`, and `vars` (name, kind, where, type) for `stack()` and pascdb.

### 7.2 Order of work

`compile_program()` runs `check_indentation()` (indent.py) first, then
`Compiler.program()`:

1. `uses`: only `math` is accepted.
2. The main program's `RoutineInfo` is created (index 0).
3. Unless `-g`, a `var` section before the last routine is an error
   (global variables must come after all routines; constants and types
   may come anywhere).
4. `declarations()` walks the declarations in order: `const_decl`,
   `type_section` (resolves a group of types, including forward pointer
   targets), `var_decl` and `routine`. Each routine is compiled
   completely (its code is appended to `self.code`) when it is reached.
5. The main body is compiled, followed by `PUSH 0; HALT`, and put first.
6. `assemble()` runs the peephole optimiser, resolves labels to pcs, and
   fills in the `Program`.

Labels are pseudo instructions `(LABEL, n, line)` (with `LABEL = -1`)
inside the code lists; jumps carry the label number until `assemble()`
replaces it with the pc.

### 7.3 Expressions

`expr(e)` dispatches to `x_<NodeClass>` (`x_IntLit`, `x_Name`,
`x_Field`, `x_Index`, `x_Deref`, `x_Call`, `x_Unary`, `x_Binary`, ...).
Each returns an `Ex`. Constant folding happens as part of checking:
`fold_int`, `fold_real` and `fold_ipow` compute constant results with
fpc's rules (including overflow and range errors at compile time), and
an `Ex` with `const` set gets `vcode = [PUSH const]`.

* Integer arithmetic is done on 64 bits: `ADD`, `SUB`, `MUL` raise error
  215 when the result does not fit in an int64 (as fpc with `$Q+` on a
  64-bit CPU). Narrowing happens only on stores, with `CHK lo, hi`
  (error 201), and in a few places where fpc's arithmetic is 32 bits.
* Reals are Python floats. Single precision is simulated with `SGL`
  (round to single) where fpc would hold a single.
* Strings are `bytes` on the operand stack; `CONCAT` cuts at 255.
  Characters are ints, converted with `C2S` when a string is needed.
* Comparisons push 1 or 0. `and`/`or` on booleans short-circuit with
  `JZK`/`JNZK` (jump keeping the value on the stack if it decides).
* `compare_checks()` holds teaching checks on comparisons: `x = True`
  style warnings and the error for `ord(c) >= ord('a')`.
* `coerce(x, t, node)` is assignment compatibility: it returns the code
  that pushes `x` converted to `t` (integer to real, char to string,
  string to `string[n]`, range check of ordinals), or raises fpc's
  "Incompatible types" error.

### 7.4 Designators, loads and stores

`var_code(sym)` gives the address code of a variable: `GADDR addr`,
`LADDR off` or, for references, `LDL ('Q', off)` (load the stored
address). `load_code(acode, t)` turns an address into a value: `LDG`/
`LDL` directly for globals and locals, `LD mk` otherwise, `LDS` for
strings, and nothing for arrays and records (they are handled by
address). Fields add `ADDI offset`; indexes use `INDEX (lo, hi, elemsize,
check)` (error 201 if out of range); `p^` emits `DEREF`, which checks for
nil (error 216).

`s_Assign` and `store()` emit the store: `STG`/`STL`/`ST mk` for scalars
(after `CHK` when the target is narrower than the value), `STS maxlen` for
strings (truncating), `COPY size` for arrays and records, `STCA` for char
arrays.

### 7.5 Routines and calls

`routine(r)` builds the routine's frame. Offsets are assigned in
parameter order, then the result, then locals, then temporaries. How a
parameter is passed:

| Parameter | Frame slot | `params` entry |
|---|---|---|
| `var` parameter | 8-byte address | `ref` |
| value array/record never changed by the routine | 8-byte address | `ref` (see below) |
| value string | `maxlen + 1` bytes | `str` |
| value array/record that may change | its size | `copy` |
| scalar | its size | `val` |

`unchanged_params()` finds array and record value parameters that the
body never assigns, never passes as a `var` argument and never takes the
address of. Those are passed by reference internally: the meaning is the
same and big arrays are neither copied nor able to overflow the stack.

Functions return scalars and strings through a result slot read by `RET`;
a structured result is written through a hidden reference parameter that
points to a temporary in the caller (`call()` emits `LADDR tmp; CALL;
LADDR tmp`).

`call()` checks the arguments (`var` arguments must be assignable and of
the same type, `$V+` for strings) and pushes them in order; the VM pops
them in reverse (`info.params` is reversed for that).

### 7.6 Statements

`stmt(s)` dispatches to `s_<NodeClass>`. Temporaries allocated while
compiling a statement are released when it ends (`self.rt.frame = mark`).
With `debug=True` (pascdb), every statement except compound statements
and loops gets a `LINE (line, col)` instruction in front of it, and each
routine and the program get one at their final `end`.

Loops: `while` and `repeat` are the usual test-and-jump patterns; `for`
evaluates the bounds once, stores the limit in a temporary, locks the
control variable (assigning to it, or passing it as `var`, is an error)
and leaves it with fpc's final value. `for ... in` iterates over an
ordinal type. `case` compiles to a chain of comparisons (ranges and
strings included) with `else`/`otherwise`.

### 7.7 Built-in routines

`builtin(name, e, args)` compiles every predefined routine. Most become
one of:

* `WR (spec, haswidth, hasprec)` and `WRLN`: write a value to the file
  whose address is pushed first; `spec` says how (`('i',)` integer,
  `('r', single)` real, `('c',)`, `('s',)`, `('b',)`, `('e', names)` ...).
* `RD spec` and `RDLN`: read into an address.
* `FN name`: math functions (`sqrt`, `sin`, `trunc`, `round`, ...), with
  fpc's error numbers for invalid arguments.
* `SYS name` or `SYS (name, ...)`: `eof`, `eoln`, `assign`, `reset`,
  `rewrite`, `close`, `new`, `dispose`, `setlength`, `val`, `stack`.

`ord`, `chr`, `succ`, `pred`, `low`, `high`, `length`, `sqr`, `abs` are
mostly folded or open-coded with range checks.

### 7.8 Teaching checks in the compiler

* **I/O in functions** (`io()`): input/output in a function is an error;
  `write`/`writeln` (directly or through a procedure that only writes) is
  a warning, and output right before `halt` (a `fatal` procedure) is
  ignored. Each routine `Sym` records `does_io` and `does_write` so calls
  propagate the property.
* **"should be a function"**: at the end of `routine()`, a procedure with
  no I/O and a single `var` parameter whose every use is a whole
  assignment gets a warning.
* **Function result not set**: warning, as in fpc.
* **Naming style** (`check_name`, `check_case`): only when style warnings are on; they add
  to `self.lints`.
* **Typed constants**: read-only, and usable in constant expressions and
  types (fpc allows neither).
* **Global variables last** (section 7.2).

### 7.9 Peephole optimiser

`peephole()` fuses common pairs into single instructions, which matters
because each VM instruction costs a Python loop iteration: `PUSH k; ADD`
to `ADDK k`, compare-and-jump pairs to `JNEQ`, `JNLT`, ... , `INDEX; LD`
to `LDX`, and `x := x + k` on a global or local scalar to `INCG`/`INCL`
(with the range check folded in). New fusions must keep the error
behaviour identical (same error, same pc for the line number).

## 8. The bytecode (`pasclib/code.py`)

The VM is a stack machine. Operand stack values are Python ints (ordinals,
addresses, pointers), floats (reals) and bytes (strings). Arrays and
records are never on the operand stack: their addresses are.

| Group | Instructions |
|---|---|
| stack | `NOP PUSH k`, `POP`, `DUP`, `SWAP` |
| addresses | `GADDR a` (push absolute address), `LADDR off` (fp+off), `ADDI k`, `INDEX (lo,hi,size,chk)`, `DEREF` |
| loads/stores | `LDG (mk,a)`, `STG (mk,a)`, `LDL (mk,off)`, `STL (mk,off)`, `LD mk`, `ST mk`, `LDS`, `STS max`, `LDCA (n,zb)`, `STCA n`, `COPY n` |
| integers | `ADD SUB MUL DIV MOD NEG`, `CHK (lo,hi)`, `AND OR XOR NOT BNOT SHL SHR` |
| reals | `FADD FSUB FMUL FDIV FNEG I2F SGL` |
| comparisons | `EQ NE LT LE GT GE` (work for ints, floats and bytes) |
| strings | `CONCAT`, `C2S` |
| jumps | `JMP`, `JZ`, `JNZ`, `JZK`, `JNZK` |
| calls | `CALL r` (routine index), `RET r`, `HALT` |
| run time library | `FN name`, `WR spec`, `WRLN`, `RD spec`, `RDLN`, `SYS name` |
| fused | `ADDK k`, `LDX`, `JNEQ JNNE JNLT JNLE JNGT JNGE`, `INCG`, `INCL` |
| debugging | `LINE (line,col)`: calls `vm.hook` (pascdb only) |

`pasc -S prog.p` prints the code with pc, source line, opcode and
argument, routine by routine. It is the quickest way to see what the
compiler generates for a construct.

To add an instruction: append its name to `OPS` in `code.py` (the
numbering is automatic), emit it in the compiler, and implement it in
the VM: in `VM.loop()` if it is frequent, otherwise in `VM.slow()`.

## 9. The virtual machine (`pasclib/vm.py`)

### 9.1 Memory

All of the program's data live in one `bytearray`, `vm.mem`, so that
addresses, pointers, `@x`, garbage and the memory views behave as in a
real machine:

```
0      16        32                 stack                 stack_end         len(mem)
| nil  | output, |  global variables  |  frames (16 MB by    |  heap (grows      |
|      | input   |  (prog.globsize)   |  default, --stack)   |  with new)        |
```

* `[0, 16)` is reserved so that address 0 is nil.
* `[16, 24)` and `[24, 32)` hold the handles of `output` and `input`.
* Globals start at 32 and end at `prog.globsize`; the stack starts at the
  next multiple of 16 (`vm.stack`).
* The heap starts at `stack_end` and grows by extending the bytearray.
  Blocks are rounded up to 8 bytes; freed blocks go to per-size free
  lists (`heap_free`); `heap_live` maps a block to (requested size,
  (line, type name)) for the leak report, and `heap_dead` remembers
  disposed blocks so a dangling pointer can be told apart from garbage.
  Disposing something that is not a live block is error 204.

Values are stored little-endian with `struct` (`STRUCTS[mk]`).

### 9.2 Random uninitialised memory

Unless `-z`, the VM fills everything that a real program would not
initialise with random bytes: all of global memory except
`init_ranges`, every new frame on `CALL` (and the main frame), and every
block returned by `new`. `garbage(n)` takes slices of a 1 MB random pool
made once from `random.Random(seed)`, which keeps it fast and makes
`--seed N` repeatable. With `-z`, memory is zero, as fpc leaves global
variables. The fpc comparison tests use `-z`.

### 9.3 Frames and calls

`fp` points at the current frame and `sp` at its end. `CALL r`:

1. reserves 32 bytes at `sp` for the call header (as a real call would
   keep registers there): the return pc at `sp` and the caller's `fp` at
   `sp+8`;
2. the new frame starts at `nfp = sp + 32` and is `r.framesize` long;
   overflowing `stack_end` is error 202; the frame is filled with garbage;
3. arguments are popped into their slots following `r.params`;
4. `(pc, fp, sp, cur)` is pushed on `vm.callstack` (a Python list, used
   for speed and for error reports), and execution continues at
   `r.entry`.

`RET` pushes the function result (from its slot) and restores the saved
registers from `callstack`. The header bytes in memory are only for
display (pascdb's Stack pane and `stack()`), so they always match what
`callstack` holds.

### 9.4 The interpreter loop

`VM.loop()` is a single `while True` with an `if/elif` chain. The most
frequent instructions come first, and everything (`mem`, `stack.append`,
the `struct` functions, opcode numbers) is bound to local variables:
this is the main performance trick of a Python interpreter, and the
reason for the fused instructions. Rare instructions are in
`VM.slow()`, which returns the new `(pc, fp, sp)`.

Errors are Python exceptions: `RunError(code)` carries an FPC run-time
error number, `Halt(code)` ends the program. `struct.error` on a store
means a value out of range (201); `IndexError` or `ValueError` means a
bad address (216). The loop saves `self.pc` before re-raising, so the
report can name the line.

### 9.5 Ending a run

`VM.run()` maps the outcome to an exit status:

* normal end or `halt(n)`: `n & 0xff`; then the output is flushed, the
  leak report is printed (`debug.leak_report`) and files left open are
  reported (`files_report`);
* `RunError`: the output is flushed and `report()` prints
  `Runtime error N at file:line: Name`, the routine and the call chain
  (the last 20 calls). With `uses math`, fpc's sysutils turns errors into
  exceptions, so pasc prints `An unhandled exception occurred at ...`,
  the exception class and message (`errors.EXCEPTIONS`), and exits with
  217;
* `RecursionError` (Python) is reported as 202, Ctrl+C exits with 130.

### 9.6 Files

`text` variables hold an index into `vm.files` (0 means "not assigned":
error 102). `files[1]` is output and `files[2]` is input.
`textio.TextFile` implements a Pascal text file with the rules of FPC's
`rtl/inc/text.inc`: `read` of numbers skips blanks and stops at
separators, `eof`/`eoln` look ahead the same way, `readln` skips to the
next line, and output uses a 256-byte buffer, so a file that is never
closed loses its last partial buffer, exactly as with fpc. Standard input
is read lazily from file descriptor 0 (so interactive programs work and
pascdb can feed a pipe); standard output is flushed before reading from
input and when it is a terminal.

The VM warns when a file is opened a second time (`note_open`) and when
files are left open at the end (`files_report`).

### 9.7 Number formatting and conversions (`pasclib/fmt.py`)

`real_to_str(v, width, prec, single)` reproduces `str_real()` from FPC's
`rtl/inc/flt_core.inc`: shortest digits, the default
` d.ddddddddddE+ddd` notation with 17 significant digits for doubles and
fewer for singles, fixed notation with `:w:d`, round half up, and the
aggressive round-up of `...4999` tails that fpc does. `val_int`,
`val_real` and `val_enum` implement `val` and the parsing used by
`read`. `fpc_round`, `intpower` and `power` match fpc's results.

When output differs from fpc, look first at the RTL sources (installed at
`/usr/local/share/fpcsrc/rtl/inc`: `text.inc`, `flt_core.inc`,
`sstrings.inc`) and add a case to `tests/extra`.

### 9.8 The hook

`vm.hook` is `None` for pasc. pascdb sets it, and the `LINE` instruction
calls `hook(pc, fp, sp, (line, col))` before each statement. The hook
may block (that is how pascdb pauses the program) and may raise an
exception to abandon the run. pasc never emits `LINE`, so the hook costs
nothing there.

## 10. Debugging aids (`pasclib/debug.py`)

* **`stack()`** compiles to `SYS 'stack'` with the level on the operand
  stack and calls `dump_stack(vm, pc, fp, level)`. It walks
  `vm.callstack` from the current routine outwards, printing each
  routine's `info.vars` (parameters, result, locals; for references it
  follows the stored address), then `prog.globals` and the live heap
  blocks. `Formatter` turns a value into one line (level 0); `Pretty`
  prints one line per field or element, deeper with each level.
  `plan()` and `runs()` compress long arrays: runs of more than `RUN`
  equal (or garbage) elements become `... N more, the same`.
* **Garbage detection** is heuristic: an ordinal outside its type's range,
  an invalid enumeration, a string longer than its maximum, a pointer
  that is not nil and not a live heap block or a valid address is
  garbage; a record is garbage when its first field is, an array when
  its first element is.
* **`leak_report(vm)`** groups the blocks left in `heap_live` by
  allocation site and type, and prints them on standard error.

## 11. Indentation and style checks

### 11.1 `pasclib/indent.py`

`check_indentation(tree, fname)` runs before compiling. It uses the
tokens' positions (tabs expanded to multiples of 8) and the tree: the
statements of a block must be indented more than the line that opened
it and must all start at the same column, and `end`, `else` and
`until` must line up with the line that opened them. Only statements and
keywords that start a line are checked. A violation is a compile error.
`tabs_warning()` returns a warning when lines are indented with spaces in
a file that also indents with tabs.

### 11.2 `pasclib/lint.py` and `limits.py`

With `lint=True` (unless `-w`), `lint_program(tree, prog)` runs a list of independent checks
over the tree and returns `(line, col, message)` triples:
`lines_check` (line length), `size_check` and `body_check` (routine and
body sizes, parameter count), `duplicates_check` (same normalised body),
`repeat_check` (repeated statements or groups), `boolean_if_check`,
`begin_end_check`, `search_loop_check`, `layout_check` (where `begin`,
`end` and `else` go, from the tokens and the compound statements) and
`array_param_checks` (array plus index, array plus count). `structure_check` (number of loops,
nesting of loops and of control structures, ifs in a row; an `else if`
continues its `if` instead of nesting) is described below. `walk()` iterates over every node with its
parent.

The limits on loops and nesting (`structure_check()`, collected by
`structure_findings()`) and the ban on anonymous types
(`anonymous_types()`) are special: `compile_program()` turns the ones
listed in `LIMITS['enforced']` into a `CompileError`, unless
`enforce=False` (`-L` in pasc and pascdb); not enforced, they are style
warnings. The test suites pass `-L` so the course programs are compared
with fpc whatever their structure, and `tests/extra/restr_*` cases check
that each enforced limit rejects a program.

Every threshold and on/off switch is in `LIMITS` (`limits.py`). At the
end of `limits.py`, `userlimits.apply()` overrides them with the user's
`~/.pasclimits` (or the file in `$PASCLIMITS`), lines of `limit: value`;
the test suites set `PASCLIMITS` empty so a local file cannot change
their results. A check
reads its entry with `LIMITS.get(name)` and does nothing when it is
`None` or `False`. To add a style check: add an entry to `LIMITS` with a
comment, write a function in `lint.py` that appends to `found`, call it
from `lint_program()`, document it in the README and the user guide, and
add a case to `tests/lint`. Francisco tunes the values in `limits.py`
himself; keep them when editing the file.

## 12. pascdb

### 12.1 Architecture

```
browser page (ui.html) --HTTP GET /api/...--> ThreadingHTTPServer (server.py)
        ^                                         |
        |  JSON state with snapshot               | Session.command()
        +-----------------------------------------+
                                                  | threading.Condition
                       VM thread: vm.run() --LINE--> Session.hook() (blocks)
```

`pascdb.py` reads and compiles the program with
`compile_program(..., debug=True)` and calls `serve(prog, source)`.
`serve()` creates a `Session`, a random 16-hex-digit token, an HTTP
server on `127.0.0.1` (port 0, chosen by the system, unless `--port`),
prints the URL `http://127.0.0.1:PORT/?t=TOKEN` and opens the browser.
Every request must carry the token (otherwise 403), so other users of
the machine cannot drive the session. Ctrl+C or `/api/quit` stops the
server.

### 12.2 The session (`pascdblib/server.py`)

`Session` holds the state shared between the HTTP threads and the VM
thread, protected by one `threading.Condition` (`self.cv`). Every change
increments `self.version` and calls `notify_all()`.

* **`start()`** builds a fresh `VM` (random memory, as pasc), replaces
  its output with a `Sink` that appends to `self.output`, connects
  standard input to an `os.pipe()` (the page's input line writes to it),
  wraps `inp.fill` to know when the program waits for input, sets
  `vm.hook = self.hook`, and runs `vm.run()` in a daemon thread.
  Restarting creates a new VM; the old thread is abandoned by raising
  `Restart` from the hook.
* **`hook()`** runs in the VM thread at every `LINE`. In mode `run`
  (Continue) it returns at once unless the line has a breakpoint. Else it
  records the paused position (`self.paused = (pc, fp, sp, pos)`), marks
  the snapshot as stale, and waits on the condition until the mode lets
  it go on: `step` with a permit (one per Step press), `run`, or `play`
  after `self.delay` seconds.
* **`command()`** handles `step`, `play`, `pause`, `run`, `speed`,
  `break` (toggle a line), `input` (write a line to the pipe), `eof`
  (close the pipe's write end), and `restart`.
* **`state(since)`** is a long poll: it waits up to one second for
  `version` to change and returns the status, mode, breakpoints, delay,
  output, pasc's messages and, when paused or finished, the snapshot. The
  snapshot is computed lazily, once per pause.
* **`close_fd()`** closes each pipe end exactly once. A descriptor closed
  twice could already belong to one of the server's sockets; this was a
  real bug.
* When the run ends, `final_snapshot()` describes the globals and the
  heap as they were left, with `lastpos` (the last `LINE` reached).

### 12.3 HTTP API

All requests are `GET` with `t=TOKEN`:

| Path | Result |
|---|---|
| `/` | `ui.html` |
| `/api/source` | `{fname, lines}` |
| `/api/state?since=V` | the state (long poll) |
| `/api/mem?addr=A&len=N` | `{a, hex}`: up to 4096 bytes of memory |
| `/api/step`, `/api/play`, `/api/pause`, `/api/run`, `/api/restart`, `/api/eof` | commands |
| `/api/break?line=N` | toggle a breakpoint |
| `/api/speed?delay=S` | seconds between steps when playing |
| `/api/input?text=...` | send a line to the program |
| `/api/quit` | end pascdb |

`docs/shots.py` and `packaging/smoke_pascdb.py` drive pascdb through this
API, which makes them good examples.

### 12.4 Snapshots (`pascdblib/snapshot.py`)

`snapshot(vm, pc, fp, sp, pos, highwater)` returns a JSON-able dict:

* `line`, `col`: the statement about to run;
* `frames`: one per active call, innermost first, each with `name`,
  `kind`, `routine`, `line`, `fp`, `size`, `vars` (for the Data pane) and
  `slots` (for the Stack pane: address, size, name, kind, hex bytes), and
  `ret` (address of the call header, return pc and line, saved fp);
* `globals` and `gslots`; `heap` (live blocks with address, size, type,
  allocation line and value);
* `files`: the input files with the text around the read position
  (`input_files`);
* `regions`: the address ranges of globals, stack, the stack pointer
  (`sp`), the part of the stack ever used (`used`, from `highwater`) and
  the heap, for the Memory pane.

Values are trees made by `Describer.value(t, addr)`: `{a, s, t, k, ...}`
with `k` one of `scalar`, `str`, `array` (`items` with index labels,
`more`), `record` (`f`), `ptr` (`p`, and `st`: `nil`, `heap`,
`dangling`, `mem` or `garbage`), `file`, or `bad`; `g` marks garbage.
Arrays are cut at 200 elements and nesting at 8 levels.

For var parameters, `label_index()` maps every (address, type) to a
readable name such as `nube.puntos[2]`, and `ref_targets()` resolves
what each var parameter refers to. If the argument was itself (part of) a
var parameter of a caller, the target is that parameter, so the page can
draw a chain of arrows that ends at the real variable.

### 12.5 The page (`pascdblib/ui.html`)

The page is one file with no external dependencies: HTML, CSS and plain
JavaScript. The installers ship it as data (`--add-data`).

* **Layout**: a toolbar; on the left the source (`#source`), the output
  and the input line (`#io`); on the right the tabs Data (`#data`), Stack
  (`#stack`), Memory (`#mem`) and Files (`#files`), each in a `.pane`.
* **Polling**: `poll()` loops on `api('state', {since: version})`. When
  the snapshot changes, `diff(old, new)` computes what changed and
  `renderAll()` redraws the visible panes. `renderStatus()` and
  `markSource()` update the toolbar status, output and current line.
* **Data pane**: `renderData()` builds frames, globals and heap blocks
  with `varNode()` and `valueNode()`; `drawArrows()` draws pointers and
  var-parameter references as SVG paths on `#arrows`, after layout.
  Structures can be collapsed (`closed` map, keyed by path). `refCopies`
  switches var parameters between arrows and faded copies. Strings
  longer than `MAXSTR` are cut.
* **Stack pane**: `renderStack()` lists each frame's slots, header
  (return address and saved fp) and bytes, using `frames[].slots` and
  `ret`.
* **Memory pane**: one virtual-scrolled hex dump of all the memory in
  use (`memLayout()`, `drawDump()`), fetched in 4 KB chunks with
  `/api/mem`; bytes above `sp` are dimmed; variables are shaded and
  named; picking an item scrolls to it (`memScrollTo()`).
* **Files pane**: `renderFiles()` shows each input file with what has
  been read dimmed and the next character highlighted.
* **Change highlighting**: `diff()` compares the leaves of both
  snapshots (keyed by address and type), new heap blocks and stack slots,
  and computes byte ranges for the dump; panes scroll to the change.
* **Languages**: interface strings are written in Spanish and passed
  through `L(text, args...)`, which looks them up in the `EN` dictionary
  when the language is English (`{0}` placeholders). Static texts use
  `data-t`, `data-tt` (tooltips) and `data-tp` (placeholders) attributes,
  applied by `applyLang()`. The choice is kept in `localStorage`. **Any
  new user-visible string must go through `L()` and get an `EN` entry.**
* **Several windows**: the ⧉ buttons open a pane alone with `?view=NAME`.
  Windows of the same session talk through a `BroadcastChannel` named
  after the token: the selected variable, the language and quitting are
  shared. Juntos (`together`) shows all panes side by side.
* **URL parameters**: `t` (token), `lang` (`es`/`en`), `view` (pop-out),
  `tab` (`data`, `stack`, `mem`, `files`), `together=1`, `refs=copy` or
  `refs=arrow`, and `once=1`, which renders the current state and stops
  polling (used for screenshots, since headless Chrome would otherwise
  wait forever for the long poll).

## 13. Semantics decisions and known differences

* Programs get the semantics of the `{$mode objfpc}...` line even when
  the file lacks it (fpc would use its default mode, with 16-bit
  integers).
* Integer arithmetic in 64 bits with overflow checks (215); range checks
  (201) on stores, indexes, `succ`, `pred`, `chr`.
* Real constants exact in single precision are singles (fpc does this),
  which shows in output such as `writeln(5.0/2)`.
* Floating-point division by zero is 200 and invalid operations 207, as
  fpc on x86-64 and Windows; fpc on arm64 macOS says 216.
* Infinite recursion ends with 202 instead of a crash.
* Reading uninitialised or disposed heap memory gives pasc's garbage, not
  fpc's (the course test `64a.ptrint.p` is a known difference).
* Teaching aids that reject programs fpc accepts: global variables after
  routines (unless `-g`), indentation errors, no I/O in functions, no
  `ord` to compare chars.

## 14. Recipes

**Support a new built-in routine.** Add its name to the list in
`init_system()`; compile it in `builtin()` (check argument count and
types, emit code, often `SYS (name, ...)` or `FN name`); implement it in
`VM.sys()` or `VM.fn()`; if it does I/O add it to `IO_BUILTINS`; add a
`tests/extra` case and run `difftest.py -r name` with fpc installed;
document it in the README's subset list.

**Support a new statement or expression form.** Add a node to `ast.py`;
parse it in `parser.py`; check and compile it in an `s_` or `x_` method;
teach `indent.py` its layout if it has a body; let `lint.walk()` see its
children; add tests.

**Change an error message.** Messages are in the compiler (`error()`
calls), the parser, `indent.py` and `errors.RTE_NAMES`. The lint tests
compare full warning texts (`tests/lint/*.expected`); the fpc tests
compare only the line of the first compile error.

**Change what pascdb shows.** Data comes from `snapshot.py`; display is
in `ui.html`. Add fields to the snapshot only if the page cannot compute
them. Remember `L()` and `EN` for new strings, and check pop-out windows
and Juntos. Then regenerate the screenshots (`python3 docs/shots.py`)
if the guide's captures change.

**Make pasc faster.** Profile a long program (`python3 -m cProfile
pasc.py prog.p`), look at the code for the hot loop with `-S`, and
consider a fused instruction in `peephole()` plus its case near the top
of `VM.loop()`.

**Debug the VM itself.** `PASC_DEBUG=1` makes Python `IndexError`/`ValueError`
exceptions inside the VM propagate (with a traceback) instead of becoming
error 216.

## 15. Tests

Run them from the checkout, after every change:

```
python3 tests/run_tests.py       # every course program in ../src vs fpc's results
python3 tests/difftest.py        # tests/extra edge cases vs fpc (results cached)
python3 tests/lint_test.py       # tests/lint/X.p vs X.expected (warnings)
python3 tests/features_test.py   # stack(), leaks, random memory, file warnings
python3 packaging/smoke_pascdb.py python3 pascdb.py tests/features/stack1.p
```

* `run_tests.py` runs each `../src/*.p` in a scratch directory (so the
  course files are never touched) with `-g -z` and compares output, exit
  status and, for programs fpc rejects, the line of the first error with
  `tests/expected/` (made by `gen_expected.py`, which needs fpc). `KNOWN`
  lists the deliberate differences. `RANDOM_MEM=1` runs with random
  memory, which reveals programs that read uninitialised data.
* `difftest.py` compiles `tests/extra/*.p` with fpc and pasc (input from
  `X.in` if present). fpc's results are cached as JSON keyed by the
  source's SHA-1, so CI runs without fpc; `-r` refreshes. `restr_*.p` are
  programs fpc accepts that pasc must reject; `ext_*.p` use pasc
  extensions and must print `X.out`; `err_*.p` are compile errors.
* `lint_test.py` runs `pasc -c` on `tests/lint/X.p` and compares the
  warnings with `X.expected`.
* `features_test.py` checks `stack()` output, the leak report, the seed
  and `-z`, and the file warnings.
* `smoke_pascdb.py` starts pascdb without a browser, sets breakpoints,
  steps, and checks the output through the API.

## 16. Packaging, releases and documentation

* **Local install** (Francisco's Mac): `packaging/install-local.sh`
  copies the checkout to `~/.local/lib/pasc` and writes `pasc` and
  `pascdb` launchers to `/usr/local/bin` (or `~/.local/bin`). Run it
  after each change.
* **Installers**: `.github/workflows/release.yml` runs on tags `v*` (or
  by hand). Jobs: `test`; `docs` (INSTALAR.pdf from INSTALAR.md with
  `packaging/docs/build-pdf.py`); `windows` (PyInstaller one-dir builds of
  pasc and pascdb, then Inno Setup with `packaging/windows/pasc.iss`, and
  a portable zip); `macos` (universal2 Python, PyInstaller,
  `packaging/macos/build-pkg.sh`); `linux` (PyInstaller in an old
  Debian 9 Python container, glibc 2.24, so the build runs on old and new
  distributions, plus
  `packaging/linux/install.sh`); `source` (a zip of the sources); and
  `release` (publishes everything on GitHub). PyInstaller needs
  `--hidden-import` for modules imported lazily (`pasclib.lint`,
  `pasclib.debug`, `pasclib.indent`) and `--add-data` for `ui.html`.
* **Releasing**: set `VERSION` in `pasclib/__init__.py`, commit, tag
  `vX.Y.Z` and push the branch and the tag. Pushing workflow changes
  needs a token with the `workflow` scope (`gh auth git-credential`).
* **Documents**: `packaging/docs/md2pdf file.md` turns any Markdown file
  into a PDF (a single shell script; it makes a private Python venv with
  markdown-it-py once and prints with headless Chrome). `docs/build.sh`
  regenerates this document's and the user guide's PDFs, and
  `docs/shots.py` regenerates the pascdb captures in `docs/img` from the
  example programs in `docs/examples`.
