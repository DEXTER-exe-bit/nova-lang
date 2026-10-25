# Nova language specification (0.1.0)

## Source format

Programs are UTF-8 text. Statements end at a newline. Whitespace is cosmetic and `#` starts a comment. Blocks begin with `:` and end with `end`; indentation is encouraged but not significant.

## Values and variables

`number` values are integers or floating-point values. Nova also has `string`, `boolean` (`true` and `false`), `nil`, `list`, `dictionary`, and function values.

```nova
let name = "Nova"
let active = true
let records = [1, 2, 3]
let person = {"name": name, "active": active}
name = "Nova Lang"
```

Variables must be introduced with `let`; later writes use `=`. Lists and dictionaries use zero-based indexing and bracket access: `records[0]`, `person["name"]`. A bracket target may be assigned, for example `records[0] = 99`.

## Expressions

Operators, in highest-to-lowest precedence order, are unary `-` and `not`; `* / // %`; `+ -`; comparisons `< <= > >=`; equality `== !=`; then `and`, `or`. Parentheses group expressions. `/` produces a floating-point quotient and `//` a floor quotient.

Strings support `\n`, `\t`, `\r`, escaped quote, and escaped backslash. Both single and double quotes are accepted.

## Control flow

```nova
if score >= 90:
  print("A")
elif score >= 70:
  print("C")
else:
  print("Try again")
end

while count < 3:
  count = count + 1
end

for item in ["a", "b"]:
  print(item)
end
```

Conditions may alternatively use braces, which do not need an `end` terminator:

```nova
if score >= 90 {
  print("A")
} else {
  print("Try again")
}
```

Both forms support nesting. An `if` condition must be followed by either `:` or `{`; an unterminated brace block is a syntax error.

`for` iterates any iterable runtime value, including lists, dictionaries (their keys), and `range` results.

## Functions and built-ins

```nova
func add(left, right):
  return left + right
end
```

Functions close over their surrounding scope and return `nil` when no `return` executes. Built-ins are `print(...)`, `len(value)`, `range(stop)`, `range(start, stop[, step])`, and `type(value)`. `type` returns one of `nil`, `boolean`, `number`, `string`, `list`, `dictionary`, or `function`.

## Errors

Invalid source raises a syntax error with line and column. Runtime failures such as unknown variables, invalid indexing, type mismatches, and division by zero report a Nova runtime error with source location where available.
