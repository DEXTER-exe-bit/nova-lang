"""C11 backend for the currently supported scalar subset of Nova."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .ast import Node
from .lexer import lex
from .parser import parse


class NovaCompilerError(Exception):
    """Raised when C generation or native compilation cannot proceed."""


RUNTIME = r'''
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef enum { NOVA_NIL, NOVA_NUMBER, NOVA_BOOL, NOVA_STRING } NovaKind;
typedef struct { NovaKind kind; double number; int boolean; const char *string; } NovaValue;
static NovaValue nova_nil(void) { NovaValue v={NOVA_NIL,0,0,NULL}; return v; }
static NovaValue nova_number(double n) { NovaValue v={NOVA_NUMBER,n,0,NULL}; return v; }
static NovaValue nova_bool(int b) { NovaValue v={NOVA_BOOL,0,b!=0,NULL}; return v; }
static NovaValue nova_string(const char *s) { NovaValue v={NOVA_STRING,0,0,s}; return v; }
static void nova_fail(const char *m,int l,int c) { fprintf(stderr,"Nova runtime error: %s at line %d, column %d\n",m,l,c); exit(EXIT_FAILURE); }
static NovaValue nova_require(NovaValue v,int ok,int l,int c) { if(!ok) nova_fail("undefined variable",l,c); return v; }
static int nova_truthy(NovaValue v) { if(v.kind==NOVA_NIL)return 0; if(v.kind==NOVA_BOOL)return v.boolean; if(v.kind==NOVA_NUMBER)return v.number!=0; if(v.kind==NOVA_STRING)return v.string[0]!='\0'; return 1; }
static NovaValue nova_add(NovaValue a,NovaValue b,int l,int c) { if(a.kind==NOVA_NUMBER&&b.kind==NOVA_NUMBER)return nova_number(a.number+b.number); if(a.kind==NOVA_STRING&&b.kind==NOVA_STRING){size_t n=strlen(a.string)+strlen(b.string)+1;char *s=(char*)malloc(n);if(!s)nova_fail("out of memory",l,c);strcpy(s,a.string);strcat(s,b.string);return nova_string(s);} nova_fail("operator '+' requires two numbers or two strings",l,c); return nova_nil(); }
static NovaValue nova_numeric(NovaValue a,NovaValue b,char op,int l,int c) { if(a.kind!=NOVA_NUMBER||b.kind!=NOVA_NUMBER)nova_fail("arithmetic operator requires numbers",l,c); if((op=='/'||op=='%'||op=='d')&&b.number==0)nova_fail("division by zero",l,c); if(op=='+')return nova_number(a.number+b.number);if(op=='-')return nova_number(a.number-b.number);if(op=='*')return nova_number(a.number*b.number);if(op=='/')return nova_number(a.number/b.number);if(op=='%')return nova_number(fmod(a.number,b.number));return nova_number(floor(a.number/b.number)); }
static NovaValue nova_equal(NovaValue a,NovaValue b) { if(a.kind!=b.kind)return nova_bool(0);if(a.kind==NOVA_NIL)return nova_bool(1);if(a.kind==NOVA_NUMBER)return nova_bool(a.number==b.number);if(a.kind==NOVA_BOOL)return nova_bool(a.boolean==b.boolean);return nova_bool(strcmp(a.string,b.string)==0); }
static NovaValue nova_order(NovaValue a,NovaValue b,const char *op,int l,int c) { int r; if(a.kind==NOVA_NUMBER&&b.kind==NOVA_NUMBER){if(strcmp(op,"<")==0)r=a.number<b.number;else if(strcmp(op,"<=")==0)r=a.number<=b.number;else if(strcmp(op,">")==0)r=a.number>b.number;else r=a.number>=b.number;}else if(a.kind==NOVA_STRING&&b.kind==NOVA_STRING){int q=strcmp(a.string,b.string);if(strcmp(op,"<")==0)r=q<0;else if(strcmp(op,"<=")==0)r=q<=0;else if(strcmp(op,">")==0)r=q>0;else r=q>=0;}else{nova_fail("comparison requires two numbers or two strings",l,c);return nova_bool(0);}return nova_bool(r); }
static NovaValue nova_and(NovaValue a,NovaValue b){return nova_truthy(a)?b:a;} static NovaValue nova_or(NovaValue a,NovaValue b){return nova_truthy(a)?a:b;} static NovaValue nova_not(NovaValue v){return nova_bool(!nova_truthy(v));}
static NovaValue nova_neg(NovaValue v,int l,int c){if(v.kind!=NOVA_NUMBER)nova_fail("unary '-' requires a number",l,c);return nova_number(-v.number);}
static void nova_print_value(NovaValue v){if(v.kind==NOVA_NIL)fputs("None",stdout);else if(v.kind==NOVA_NUMBER)printf("%.15g",v.number);else if(v.kind==NOVA_BOOL)fputs(v.boolean?"True":"False",stdout);else fputs(v.string,stdout);}
static void nova_print(int n,...){va_list ap;va_start(ap,n);for(int i=0;i<n;i++){if(i)putchar(' ');nova_print_value(va_arg(ap,NovaValue));}va_end(ap);putchar('\n');}
'''


def _c_name(name: str) -> str:
    return "nova_v_" + "".join(c if re.match(r"[A-Za-z0-9_]", c) else f"_u{ord(c):x}_" for c in name)


class CGenerator:
    def __init__(self, statements):
        self.statements = statements
        self.variables = set()
        self.collect(statements)

    def collect(self, statements):
        for node in statements:
            if node.kind == "let":
                self.variables.add(node.value)
            elif node.kind == "if":
                for _, body in node.value:
                    self.collect(body)
                self.collect(node.children[0])

    def error(self, node, message):
        raise NovaCompilerError(f"{message} at {node.token.location()}")

    def generate(self):
        declarations = "\n".join(
            f"    NovaValue {_c_name(n)}=nova_nil(); int nova_i_{_c_name(n)[7:]}=0;"
            for n in sorted(self.variables)
        )
        body = "\n".join(self.statement(n, 1) for n in self.statements)
        return RUNTIME + f"\nint main(void) {{\n{declarations}\n{body}\n    return 0;\n}}\n"

    def statement(self, node, level):
        pad = "    " * level
        if node.kind == "let":
            return f"{pad}{self.assign(node.value, node.children[0])}"
        if node.kind == "assign":
            if node.value.kind != "variable":
                self.error(node, "native build does not support indexed assignment")
            if node.value.value not in self.variables:
                self.error(node, f"Cannot assign undefined variable '{node.value.value}'")
            return f"{pad}{self.assign(node.value.value, node.children[0])}"
        if node.kind == "expression":
            expr = node.children[0]
            if expr.kind == "call" and self.is_print(expr):
                return f"{pad}{self.print_call(expr)}"
            self.error(node, "native build supports only print(...) expression statements")
        if node.kind == "if":
            lines = []
            for i, (condition, body) in enumerate(node.value):
                lines.append(f"{pad}{'if' if i == 0 else 'else if'} (nova_truthy({self.expression(condition)})) {{")
                lines.extend(self.statement(child, level + 1) for child in body)
                lines.append(f"{pad}}}")
            if node.children[0]:
                lines.append(f"{pad}else {{")
                lines.extend(self.statement(child, level + 1) for child in node.children[0])
                lines.append(f"{pad}}}")
            return "\n".join(lines)
        self.error(node, f"native build does not support '{node.kind}' statements")

    def assign(self, name, value):
        prefix = _c_name(name)
        return f"{prefix}={self.expression(value)}; nova_i_{prefix[7:]}=1;"

    def is_print(self, node):
        return node.children[0].kind == "variable" and node.children[0].value == "print"

    def print_call(self, node):
        if not self.is_print(node):
            self.error(node, "native build supports only print(...) calls")
        args = ", ".join(self.expression(a) for a in node.children[1])
        return f"nova_print({len(node.children[1])}{', ' if args else ''}{args});"

    def expression(self, node):
        if node.kind == "literal":
            if node.value is None: return "nova_nil()"
            if isinstance(node.value, bool): return f"nova_bool({int(node.value)})"
            if isinstance(node.value, (int, float)): return f"nova_number({node.value!r})"
            return f"nova_string({json.dumps(node.value)})"
        if node.kind == "variable":
            if node.value not in self.variables:
                self.error(node, f"Undefined variable '{node.value}'")
            p = _c_name(node.value)
            return f"nova_require({p},nova_i_{p[7:]},{node.token.line},{node.token.column})"
        if node.kind == "unary":
            value = self.expression(node.children[0])
            return f"nova_neg({value},{node.token.line},{node.token.column})" if node.value == "-" else f"nova_not({value})"
        if node.kind == "binary":
            left, right, op = self.expression(node.children[0]), self.expression(node.children[1]), node.value
            if op == "+": return f"nova_add({left},{right},{node.token.line},{node.token.column})"
            if op in {"-","*","/","//","%"}:
                code = "d" if op == "//" else op
                return f"nova_numeric({left},{right},'{code}',{node.token.line},{node.token.column})"
            if op in {"==","!="}:
                value = f"nova_equal({left},{right})"
                return value if op == "==" else f"nova_not({value})"
            if op in {"<","<=",">",">="}: return f"nova_order({left},{right},{json.dumps(op)},{node.token.line},{node.token.column})"
            if op == "AND": return f"nova_and({left},{right})"
            if op == "OR": return f"nova_or({left},{right})"
        self.error(node, f"native build does not support '{node.kind}' expressions")


def generate_c(statements):
    return CGenerator(statements).generate()


def find_c_compiler():
    explicit = (
        Path(r"C:\Program Files\LLVM\bin\clang.exe"),
        Path(r"C:\Program Files\LLVM\bin\clang-cl.exe"),
    )
    for path in explicit:
        if path.is_file():
            return ("clang" if path.name == "clang.exe" else "clang-cl"), str(path)
    for name in ("clang", "gcc", "clang-cl", "cl"):
        path = shutil.which(name)
        if path:
            return name, path
    return None


def build_file(source_path: Path, output=None, emit_c=None):
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as error:
        raise NovaCompilerError(f"could not read '{source_path}': {error}") from error
    generated = generate_c(parse(lex(source)))
    compiler = find_c_compiler()
    if compiler is None:
        if emit_c:
            emit_c.write_text(generated, encoding="utf-8")
        raise NovaCompilerError("no C compiler found on PATH; install LLVM/clang, MinGW gcc, or use an MSVC Developer Command Prompt, then retry nova build" + (f" (C source written to {emit_c})" if emit_c else ""))
    target = (output or source_path.with_suffix(".exe")).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    if emit_c:
        c_path = emit_c.resolve()
        c_path.parent.mkdir(parents=True, exist_ok=True)
        c_path.write_text(generated, encoding="utf-8")
    else:
        temporary = tempfile.TemporaryDirectory(prefix="nova-build-")
        c_path = Path(temporary.name) / "program.c"
        c_path.write_text(generated, encoding="utf-8")
    name, executable = compiler
    command = [executable, "/nologo", "/O2", f"/Fe:{target}", str(c_path)] if name == "cl" else [executable, "-std=c11", "-O2", str(c_path), "-o", str(target)]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    finally:
        if temporary:
            temporary.cleanup()
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        if any(marker in details for marker in ("math.h' file not found", "libcmt.lib", "oldnames.lib")):
            details += " Windows SDK and MSVC/Visual C++ runtime libraries are required for clang's x86_64-pc-windows-msvc target."
        raise NovaCompilerError(f"C compiler failed ({name}): {details}")
    if not target.exists():
        raise NovaCompilerError(f"C compiler reported success but did not create '{target}'")
    return target
