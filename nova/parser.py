"""Recursive-descent parser producing Nova AST nodes."""

from .ast import Node
from .lexer import NovaSyntaxError


class Parser:
    def __init__(self, tokens: list[Token]): self.tokens, self.current = tokens, 0
    def peek(self): return self.tokens[self.current]
    def previous(self): return self.tokens[self.current - 1]
    def check(self, *kinds): return self.peek().kind in kinds
    def advance(self):
        if not self.check("EOF"): self.current += 1
        return self.previous()
    def match(self, *kinds):
        if self.check(*kinds): return self.advance()
        return None
    def require(self, kind, message):
        if self.check(kind): return self.advance()
        raise NovaSyntaxError(f"{message} at {self.peek().location()}")
    def skip_newlines(self):
        while self.match("NEWLINE"): pass

    def parse(self):
        statements = []; self.skip_newlines()
        while not self.check("EOF"):
            statements.append(self.statement()); self.skip_newlines()
        return statements

    def block(self, stop):
        self.require("NEWLINE", "Expected a new line after ':'")
        self.skip_newlines(); result = []
        while not self.check(*stop, "EOF"):
            result.append(self.statement()); self.skip_newlines()
        return result

    def brace_block(self, description):
        """Parse a statement block enclosed in braces.

        Braces already serve dictionary literals in expressions. At this point the
        parser has completed an `if` condition, so a brace unambiguously starts a
        statement block.
        """
        self.require("{", f"Expected '{{' to start {description}")
        self.skip_newlines(); result = []
        while not self.check("}", "EOF"):
            result.append(self.statement()); self.skip_newlines()
        self.require("}", f"Expected '}}' to close {description}")
        return result

    def statement(self):
        if token := self.match("LET"):
            name = self.require("IDENTIFIER", "Expected variable name")
            self.require("=", "Expected '=' after variable name")
            return Node("let", token, name.value, (self.expression(),))
        if token := self.match("IF"):
            condition = self.expression()
            if self.match(":"):
                branches = [(condition, self.block(("ELIF", "ELSE", "END")))]
                while self.match("ELIF"):
                    condition = self.expression(); self.require(":", "Expected ':' after elif condition")
                    branches.append((condition, self.block(("ELIF", "ELSE", "END"))))
                otherwise = []
                if self.match("ELSE"):
                    self.require(":", "Expected ':' after else")
                    otherwise = self.block(("END",))
                self.require("END", "Expected 'end' to close if")
                return Node("if", token, branches, (otherwise,))
            if self.check("{"):
                branches = [(condition, self.brace_block("if block"))]
                self.skip_newlines()
                while self.match("ELIF"):
                    condition = self.expression()
                    branches.append((condition, self.brace_block("elif block")))
                    self.skip_newlines()
                otherwise = []
                if self.match("ELSE"):
                    otherwise = self.brace_block("else block")
                    self.skip_newlines()
                return Node("if", token, branches, (otherwise,))
            raise NovaSyntaxError(f"Expected ':' or '{{' after if condition at {self.peek().location()}")
        if token := self.match("WHILE"):
            condition = self.expression(); self.require(":", "Expected ':' after while condition")
            body = self.block(("END",)); self.require("END", "Expected 'end' to close while")
            return Node("while", token, None, (condition, body))
        if token := self.match("FOR"):
            name = self.require("IDENTIFIER", "Expected loop variable")
            self.require("IN", "Expected 'in' after loop variable")
            sequence = self.expression(); self.require(":", "Expected ':' after for expression")
            body = self.block(("END",)); self.require("END", "Expected 'end' to close for")
            return Node("for", token, name.value, (sequence, body))
        if token := self.match("FUNC"):
            name = self.require("IDENTIFIER", "Expected function name")
            self.require("(", "Expected '(' after function name"); parameters = []
            if not self.check(")"):
                while True:
                    parameters.append(self.require("IDENTIFIER", "Expected parameter name").value)
                    if not self.match(","): break
            self.require(")", "Expected ')' after parameters"); self.require(":", "Expected ':' after function signature")
            body = self.block(("END",)); self.require("END", "Expected 'end' to close function")
            return Node("func", token, (name.value, parameters), (body,))
        if token := self.match("RETURN"):
            return Node("return", token, None, () if self.check("NEWLINE", "END", "EOF") else (self.expression(),))
        expression = self.expression()
        if self.match("="):
            if expression.kind not in {"variable", "index"}: raise NovaSyntaxError(f"Invalid assignment target at {expression.token.location()}")
            return Node("assign", expression.token, expression, (self.expression(),))
        return Node("expression", expression.token, None, (expression,))

    def expression(self): return self.or_expr()
    def or_expr(self): return self.binary(self.and_expr, ("OR",))
    def and_expr(self): return self.binary(self.equality, ("AND",))
    def equality(self): return self.binary(self.comparison, ("==", "!="))
    def comparison(self): return self.binary(self.term, ("<", "<=", ">", ">="))
    def term(self): return self.binary(self.factor, ("+", "-"))
    def factor(self): return self.binary(self.unary, ("*", "/", "//", "%"))
    def binary(self, lower, kinds):
        node = lower()
        while op := self.match(*kinds): node = Node("binary", op, op.kind, (node, lower()))
        return node
    def unary(self):
        if op := self.match("-", "NOT"): return Node("unary", op, op.kind, (self.unary(),))
        return self.call()
    def call(self):
        node = self.primary()
        while True:
            if self.match("("):
                args = []
                if not self.check(")"):
                    while True:
                        args.append(self.expression())
                        if not self.match(","): break
                self.require(")", "Expected ')' after arguments"); node = Node("call", node.token, None, (node, args))
            elif self.match("["):
                key = self.expression(); self.require("]", "Expected ']' after index")
                node = Node("index", node.token, None, (node, key))
            else: break
        return node
    def primary(self):
        if token := self.match("NUMBER", "STRING"): return Node("literal", token, token.value)
        if token := self.match("TRUE"): return Node("literal", token, True)
        if token := self.match("FALSE"): return Node("literal", token, False)
        if token := self.match("NIL"): return Node("literal", token, None)
        if token := self.match("IDENTIFIER"): return Node("variable", token, token.value)
        if token := self.match("("):
            node = self.expression(); self.require(")", "Expected ')' after expression"); return node
        if token := self.match("["):
            values = []
            if not self.check("]"):
                while True:
                    values.append(self.expression())
                    if not self.match(","): break
            self.require("]", "Expected ']' after list"); return Node("list", token, None, (values,))
        if token := self.match("{"):
            pairs = []
            if not self.check("}"):
                while True:
                    key = self.expression(); self.require(":", "Expected ':' between dictionary key and value")
                    pairs.append((key, self.expression()))
                    if not self.match(","): break
            self.require("}", "Expected '}' after dictionary"); return Node("dict", token, None, (pairs,))
        raise NovaSyntaxError(f"Expected expression at {self.peek().location()}")


def parse(tokens: list[Token]): return Parser(tokens).parse()
