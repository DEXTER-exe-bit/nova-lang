"""Tokenization for Nova source code."""

from dataclasses import dataclass


class NovaSyntaxError(Exception):
    """Raised when Nova source cannot be parsed."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    line: int
    column: int

    def location(self) -> str:
        return f"line {self.line}, column {self.column}"


KEYWORDS = {
    "let": "LET", "if": "IF", "elif": "ELIF", "else": "ELSE", "end": "END",
    "while": "WHILE", "for": "FOR", "in": "IN", "func": "FUNC", "return": "RETURN",
    "true": "TRUE", "false": "FALSE", "nil": "NIL", "and": "AND", "or": "OR", "not": "NOT",
}


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line, column = 1, 1

    def add(kind: str, value: object, start_line: int, start_column: int) -> None:
        tokens.append(Token(kind, value, start_line, start_column))

    while i < len(source):
        char = source[i]
        if char in " \t\r":
            i += 1; column += 1
        elif char == "\n":
            add("NEWLINE", "\n", line, column)
            i += 1; line += 1; column = 1
        elif char == "#":
            while i < len(source) and source[i] != "\n":
                i += 1; column += 1
        elif char.isdigit():
            start_line, start_column, start = line, column, i
            while i < len(source) and source[i].isdigit(): i += 1; column += 1
            if i < len(source) and source[i] == "." and i + 1 < len(source) and source[i + 1].isdigit():
                i += 1; column += 1
                while i < len(source) and source[i].isdigit(): i += 1; column += 1
            text = source[start:i]
            add("NUMBER", float(text) if "." in text else int(text), start_line, start_column)
        elif char.isalpha() or char == "_":
            start_line, start_column, start = line, column, i
            while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                i += 1; column += 1
            text = source[start:i]
            add(KEYWORDS.get(text, "IDENTIFIER"), text, start_line, start_column)
        elif char in "\"'":
            quote, start_line, start_column = char, line, column
            i += 1; column += 1; value = ""
            while i < len(source) and source[i] != quote:
                if source[i] == "\\":
                    if i + 1 >= len(source): raise NovaSyntaxError(f"Unterminated string at line {start_line}, column {start_column}")
                    escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "\"": "\"", "'": "'"}
                    i += 1; column += 1
                    value += escapes.get(source[i], source[i])
                else:
                    if source[i] == "\n": raise NovaSyntaxError(f"Unterminated string at line {start_line}, column {start_column}")
                    value += source[i]
                i += 1; column += 1
            if i >= len(source): raise NovaSyntaxError(f"Unterminated string at line {start_line}, column {start_column}")
            i += 1; column += 1
            add("STRING", value, start_line, start_column)
        else:
            start_line, start_column = line, column
            two = source[i:i + 2]
            if two in {"==", "!=", "<=", ">=", "//"}:
                add(two, two, line, column); i += 2; column += 2
            elif char in "+-*/%()[]{}:,.=<>":
                add(char, char, line, column); i += 1; column += 1
            else:
                raise NovaSyntaxError(f"Unexpected character {char!r} at line {line}, column {column}")
    tokens.append(Token("EOF", "", line, column))
    return tokens
