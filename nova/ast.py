"""Nova's compiler-front-end AST nodes.

The parser creates these nodes and the interpreter consumes them. A future
compiler can consume the same tree without coupling itself to either module.
"""

from dataclasses import dataclass

from .lexer import Token


@dataclass
class Node:
    """A deliberately small, source-located AST node.

    ``kind`` identifies the grammar production, ``value`` stores names or
    operators, and ``children`` stores nested nodes. The originating token is
    retained so diagnostics can report line and column information.
    """

    kind: str
    token: Token
    value: object = None
    children: tuple = ()
