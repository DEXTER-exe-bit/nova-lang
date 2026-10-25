# Nova

Nova is an experimental, general-purpose interpreted language implemented in pure Python. Its syntax combines familiar Python-style colons with explicit Lua-style `end` block terminators, so indentation is optional.

The project is prepared for its first public GitHub repository. The Python interpreter and CLI are the reference implementation; the native C backend is experimental and remains unverified on this Windows machine.

## Install and run on Windows PowerShell

Nova runs natively in Windows PowerShell with Python 3.10+ (tested with Python 3.14.4). From the project directory, install the command in editable mode:

```powershell
cd E:\nova-lang
python --version
python -m ensurepip --upgrade
python -m pip install -e .
nova --version
nova run examples\hello.nova
python -m unittest discover -s tests -v
```

After installation, `nova` is available from other directories too. Use an absolute or relative source path:

```powershell
cd $HOME
nova run E:\nova-lang\examples\collections_and_loops.nova
```

Use `nova --help` for command help. `nova run FILE.nova` exits with code 1 for a Nova syntax/runtime error, or code 2 for invalid arguments and unreadable files. The older `python main.py examples\hello.nova` form is still supported from the project root.

Run the included programs directly:

```powershell
nova run examples\hello.nova
nova run examples\conditions.nova
nova run examples\collections_and_loops.nova
```

The test suite has no third-party dependencies:

```powershell
python -m unittest discover -s tests -v
```

## Native compiler backend

Nova includes an initial C11 backend:

~~~powershell
nova build examples\conditions.nova -o examples\conditions.exe --emit-c examples\conditions.c
examples\conditions.exe
~~~

This requires a C compiler and its platform headers/libraries: LLVM clang, MinGW gcc, or cl.exe from an MSVC Developer Command Prompt. Nova discovers clang on PATH and the standard installation at C:/Program Files/LLVM/bin/clang.exe. For clang targeting x86_64-pc-windows-msvc, the Windows SDK and MSVC/Visual C++ Build Tools libraries are also required; clang alone is not enough. On the current machine, clang is installed but those SDK/MSVC libraries are missing, so native executable generation is not verified. The command is intended to generate a native Windows executable from Nova's AST and does not use Python as the generated program's runtime. If prerequisites are missing, nova build reports the compiler diagnostics. Use --emit-c to keep the generated C source.

Check the toolchain before building:

~~~powershell
& 'C:/Program Files/LLVM/bin/clang.exe' --version
Get-Command clang -ErrorAction SilentlyContinue
~~~

The first backend supports scalar let and assignment, numeric/string/boolean/nil expressions, arithmetic, comparisons, and/or/not, print(...), and nested if/elif/else. Lists, dictionaries, indexing, while, for, user functions, return, and built-ins other than print remain interpreter-only and are rejected by nova build. In particular, the current examples\\hello.nova uses a list, so it is expected to remain interpreter-only until list support is added to the backend.

## Example

```nova
func square(number):
  return number * number
end

let values = [1, 2, 3]
for value in values:
  print(square(value))
end
```

## Conditions

Nova supports brace-delimited `if`/`else` blocks. Only the branch whose condition is true is executed:

```nova
let age = 15

if age >= 18 {
  print("Adult")
} else {
  print("Under 18")
}
```

The comparison operators are `==`, `!=`, `<`, `>`, `<=`, and `>=`. Conditions can be nested. Nova also continues to support its original colon/`end` block syntax for compatibility.

## Project layout

- `nova/` — lexer, parser, interpreter, and public API
- `nova/cli.py` — packaged `nova` command-line interface
- `main.py` — backwards-compatible command-line runner
- `examples/` — executable Nova programs
- `tests/` — automated standard-library tests
- `LANGUAGE_SPEC.md` — syntax and built-ins reference
- `vscode-extension/` — local VS Code language extension, icon theme, and Nova Night color theme
- `.github/workflows/tests.yml` — Windows GitHub Actions test workflow

Nova currently has no third-party dependencies. See [LANGUAGE_SPEC.md](LANGUAGE_SPEC.md) for the complete initial language definition and [CHANGELOG.md](CHANGELOG.md) for release notes.

## Front-end architecture

Nova keeps source processing in distinct stages:

1. `nova/lexer.py` converts UTF-8 source text into source-located tokens. It recognizes only Nova's implemented literals, identifiers, keywords, operators, punctuation, and `#` comments.
2. `nova/parser.py` applies recursive-descent grammar rules to those tokens and builds the AST nodes defined in `nova/ast.py`. Nodes retain their originating token for line/column diagnostics.
3. `nova/interpreter.py` evaluates the AST. The CLI in `nova/cli.py` loads a file and reports front-end/runtime errors.

The C11 backend is experimental. It generates C for a scalar subset, but native executable generation is unverified on the current Windows machine because the Windows SDK/MSVC libraries are missing.

## VS Code extension

The published [DexterNova Nova Language extension](https://marketplace.visualstudio.com/items?itemName=DexterNova.nova-language-dex) provides `.nova` language recognition, syntax highlighting, the Nova file icon theme, and the Nova Night theme. Its source and packaging instructions are in `vscode-extension/`.
