import io
import contextlib
import unittest

from nova import NovaRuntimeError, NovaSyntaxError, run
from nova.ast import Node
from nova.lexer import lex
from nova.parser import parse
from nova.cli import main as cli_main
from nova.compiler import NovaCompilerError, find_c_compiler, generate_c


def execute(source):
    output = io.StringIO()
    run(source, output=lambda *values: print(*values, file=output))
    return output.getvalue().splitlines()


class NovaLanguageTests(unittest.TestCase):
    def test_variables_numbers_and_strings(self):
        self.assertEqual(execute('let message = "Nova"\nlet value = 4 + 3 * 2\nprint(message + "!", value)\n'), ["Nova! 10"])

    def test_conditions_and_while_loop(self):
        source = '''let number = 0
while number < 3:
  number = number + 1
end
if number == 3:
  print("done")
else:
  print("wrong")
end
'''
        self.assertEqual(execute(source), ["done"])

    def test_brace_conditions_choose_only_the_matching_branch(self):
        false_branch = '''let age = 15
if age >= 18 {
  print("Adult")
} else {
  print("Under 18")
}
'''
        true_branch = '''let age = 21
if age >= 18 {
  print("Adult")
} else {
  print("Under 18")
}
'''
        self.assertEqual(execute(false_branch), ["Under 18"])
        self.assertEqual(execute(true_branch), ["Adult"])

    def test_brace_conditions_support_comparisons_and_nesting(self):
        source = '''if 3 == 3 {
  if 2 != 3 {
    print("nested")
  } else {
    print("wrong")
  }
}
if 2 < 3 { print("less") }
if 3 > 2 { print("greater") }
if 3 <= 3 { print("at-most") }
if 3 >= 3 { print("at-least") }
'''
        self.assertEqual(execute(source), ["nested", "less", "greater", "at-most", "at-least"])

    def test_functions_return_lists_and_dictionaries(self):
        source = '''func total(values):
  let sum = 0
  for value in values:
    sum = sum + value
  end
  return sum
end
let scores = [2, 3, 4]
let player = {"name": "Dexter", "score": total(scores)}
print(player["name"], player["score"], len(scores))
'''
        self.assertEqual(execute(source), ["Dexter 9 3"])

    def test_elif_and_range(self):
        source = '''let result = 0
for number in range(1, 5):
  result = result + number
end
if result < 10:
  print("low")
elif result == 10:
  print("exact")
else:
  print("high")
end
'''
        self.assertEqual(execute(source), ["exact"])

    def test_syntax_and_runtime_errors_have_locations(self):
        with self.assertRaisesRegex(NovaSyntaxError, "line 1, column"):
            execute("let = 3")
        with self.assertRaisesRegex(NovaRuntimeError, "Undefined variable 'missing'.*line 1, column 7"):
            execute("print(missing)")
        with self.assertRaisesRegex(NovaRuntimeError, "only be used inside a function"):
            execute("return 5")
        with self.assertRaisesRegex(NovaSyntaxError, "Expected ':' or '\\{' after if condition"):
            execute('if true print("missing block")')
        with self.assertRaisesRegex(NovaSyntaxError, "Expected '}' to close if block"):
            execute('if true { print("missing close")')


class NovaFrontEndTests(unittest.TestCase):
    def test_lexer_emits_tokens_with_source_locations(self):
        tokens = lex('# greeting\nlet age = 15\nprint(age >= 18)')
        self.assertEqual(
            [(token.kind, token.value) for token in tokens],
            [
                ("NEWLINE", "\n"), ("LET", "let"), ("IDENTIFIER", "age"),
                ("=", "="), ("NUMBER", 15), ("NEWLINE", "\n"),
                ("IDENTIFIER", "print"), ("(", "("), ("IDENTIFIER", "age"),
                (">=", ">="), ("NUMBER", 18), (")", ")"), ("EOF", ""),
            ],
        )
        self.assertEqual((tokens[1].line, tokens[1].column), (2, 1))
        self.assertEqual((tokens[8].line, tokens[8].column), (3, 7))
        self.assertEqual((tokens[9].line, tokens[9].column), (3, 11))

    def test_parser_builds_ast_and_preserves_operator_precedence(self):
        tree = parse(lex('let result = 1 + 2 * 3'))
        self.assertEqual(len(tree), 1)
        declaration = tree[0]
        self.assertIsInstance(declaration, Node)
        self.assertEqual((declaration.kind, declaration.value), ("let", "result"))
        addition = declaration.children[0]
        self.assertEqual((addition.kind, addition.value), ("binary", "+"))
        self.assertEqual(addition.children[0].value, 1)
        self.assertEqual((addition.children[1].kind, addition.children[1].value), ("binary", "*"))
        self.assertEqual(execute('print(1 + 2 * 3)\nprint((1 + 2) * 3)\n'), ["7", "9"])

    def test_malformed_syntax_reports_line_and_column(self):
        with self.assertRaisesRegex(NovaSyntaxError, r"Expected expression at line 1, column 13"):
            parse(lex("let result ="))
        with self.assertRaisesRegex(NovaSyntaxError, r"Expected ':' or '\{' after if condition at line 1, column 9"):
            parse(lex("if true print(1)"))


class NovaCompilerTests(unittest.TestCase):
    def test_compiler_discovery_finds_installed_clang(self):
        compiler = find_c_compiler()
        if compiler is None:
            self.skipTest("no C compiler installed")
        self.assertIn(compiler[0], {"clang", "gcc", "clang-cl", "cl"})

    def test_c_backend_generates_native_source_for_supported_subset(self):
        tree = parse(lex('let age = 15\nif age >= 18 { print("Adult") } else { print("Under 18") }'))
        c_source = generate_c(tree)
        self.assertIn("#include <stdio.h>", c_source)
        self.assertIn("int main(void)", c_source)
        self.assertIn("nova_order", c_source)
        self.assertIn('nova_string("Adult")', c_source)
        self.assertIn("nova_print(1", c_source)

    def test_build_reports_missing_c_toolchain(self):
        if find_c_compiler() is not None:
            self.skipTest("a C compiler is installed; native compilation is environment-dependent")
        from pathlib import Path
        from nova.compiler import build_file
        with self.assertRaisesRegex(NovaCompilerError, "no C compiler found on PATH"):
            build_file(Path("examples/conditions.nova"))


class NovaCliTests(unittest.TestCase):
    def invoke(self, arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                result = cli_main(arguments)
            except SystemExit as error:
                result = error.code
        return result, stdout.getvalue(), stderr.getvalue()

    def test_run_executes_a_source_file(self):
        result, stdout, stderr = self.invoke(["run", "examples/hello.nova"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout, "Hello, Dexter!\nAge: 15\nFirst skill: Python\n")
        self.assertEqual(stderr, "")

    def test_version_missing_file_and_invalid_command(self):
        result, stdout, stderr = self.invoke(["--version"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout, "Nova 0.1.0\n")
        self.assertEqual(stderr, "")

        result, _, stderr = self.invoke(["run", "missing.nova"])
        self.assertEqual(result, 2)
        self.assertIn("file not found: missing.nova", stderr)

        result, _, stderr = self.invoke(["compile", "hi.nova"])
        self.assertEqual(result, 2)
        self.assertIn("invalid choice", stderr)

        result, _, stderr = self.invoke([])
        self.assertEqual(result, 2)
        self.assertIn("a command is required", stderr)


if __name__ == "__main__":
    unittest.main()
