"""Runtime evaluator for the Nova AST."""
from .lexer import NovaSyntaxError


class NovaRuntimeError(Exception): pass
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value


class Environment:
    def __init__(self, parent=None): self.values, self.parent = {}, parent
    def get(self, name, token):
        if name in self.values: return self.values[name]
        if self.parent: return self.parent.get(name, token)
        raise NovaRuntimeError(f"Undefined variable '{name}' at {token.location()}")
    def assign(self, name, value, token):
        if name in self.values: self.values[name] = value
        elif self.parent: self.parent.assign(name, value, token)
        else: raise NovaRuntimeError(f"Cannot assign undefined variable '{name}' at {token.location()}")


class NovaFunction:
    def __init__(self, name, parameters, body, closure): self.name, self.parameters, self.body, self.closure = name, parameters, body, closure
    def __call__(self, *arguments):
        if len(arguments) != len(self.parameters): raise NovaRuntimeError(f"Function '{self.name}' expected {len(self.parameters)} arguments, got {len(arguments)}")
        env = Environment(self.closure); env.values.update(zip(self.parameters, arguments))
        try: Interpreter.execute_block(self.body, env)
        except ReturnSignal as returned: return returned.value
        return None
    def __repr__(self): return f"<function {self.name}>"


class Interpreter:
    def __init__(self, output=None):
        self.output = output or print
        self.globals = Environment()
        self.globals.values.update({"print": self.output, "len": len, "range": self.nova_range, "type": self.nova_type})
    @staticmethod
    def nova_range(*args):
        if not 1 <= len(args) <= 3: raise NovaRuntimeError("range expects 1 to 3 arguments")
        if any(not isinstance(x, int) for x in args): raise NovaRuntimeError("range arguments must be integers")
        return list(range(*args))
    @staticmethod
    def nova_type(value):
        if value is None: return "nil"
        if isinstance(value, bool): return "boolean"
        if isinstance(value, (int, float)): return "number"
        if isinstance(value, str): return "string"
        if isinstance(value, list): return "list"
        if isinstance(value, dict): return "dictionary"
        return "function"
    def run(self, statements):
        self.execute_block(statements, self.globals); return self.globals
    @staticmethod
    def execute_block(statements, environment):
        for statement in statements: Interpreter.execute(statement, environment)
    @staticmethod
    def execute(node, env):
        try:
            if node.kind == "let": env.values[node.value] = Interpreter.evaluate(node.children[0], env)
            elif node.kind == "expression": Interpreter.evaluate(node.children[0], env)
            elif node.kind == "assign":
                value, target = Interpreter.evaluate(node.children[0], env), node.value
                if target.kind == "variable": env.assign(target.value, value, target.token)
                else: Interpreter.evaluate(target.children[0], env)[Interpreter.evaluate(target.children[1], env)] = value
            elif node.kind == "if":
                for condition, body in node.value:
                    if Interpreter.evaluate(condition, env): Interpreter.execute_block(body, env); break
                else: Interpreter.execute_block(node.children[0], env)
            elif node.kind == "while":
                while Interpreter.evaluate(node.children[0], env): Interpreter.execute_block(node.children[1], env)
            elif node.kind == "for":
                sequence = Interpreter.evaluate(node.children[0], env)
                for item in sequence:
                    env.values[node.value] = item; Interpreter.execute_block(node.children[1], env)
            elif node.kind == "func":
                name, parameters = node.value; env.values[name] = NovaFunction(name, parameters, node.children[0], env)
            elif node.kind == "return": raise ReturnSignal(Interpreter.evaluate(node.children[0], env) if node.children else None)
        except (NovaRuntimeError, ReturnSignal): raise
        except (TypeError, ValueError, ZeroDivisionError, KeyError, IndexError) as error:
            raise NovaRuntimeError(f"{error} at {node.token.location()}") from error
    @staticmethod
    def evaluate(node, env):
        try:
            if node.kind == "literal": return node.value
            if node.kind == "variable": return env.get(node.value, node.token)
            if node.kind == "list": return [Interpreter.evaluate(x, env) for x in node.children[0]]
            if node.kind == "dict": return {Interpreter.evaluate(k, env): Interpreter.evaluate(v, env) for k, v in node.children[0]}
            if node.kind == "index": return Interpreter.evaluate(node.children[0], env)[Interpreter.evaluate(node.children[1], env)]
            if node.kind == "call":
                fn = Interpreter.evaluate(node.children[0], env); args = [Interpreter.evaluate(x, env) for x in node.children[1]]
                if not callable(fn): raise NovaRuntimeError(f"Can only call functions at {node.token.location()}")
                return fn(*args)
            value = Interpreter.evaluate(node.children[0], env)
            if node.kind == "unary": return -value if node.value == "-" else not value
            right = Interpreter.evaluate(node.children[1], env)
            return {"+": lambda: value + right, "-": lambda: value - right, "*": lambda: value * right, "/": lambda: value / right, "//": lambda: value // right, "%": lambda: value % right, "==": lambda: value == right, "!=": lambda: value != right, "<": lambda: value < right, "<=": lambda: value <= right, ">": lambda: value > right, ">=": lambda: value >= right, "AND": lambda: value and right, "OR": lambda: value or right}[node.value]()
        except NovaRuntimeError: raise
        except (TypeError, ValueError, ZeroDivisionError, KeyError, IndexError) as error:
            raise NovaRuntimeError(f"{error} at {node.token.location()}") from error


def run(source: str, output=None):
    from .lexer import lex
    from .parser import parse
    try:
        return Interpreter(output).run(parse(lex(source)))
    except ReturnSignal as error:
        raise NovaRuntimeError("'return' can only be used inside a function") from error
