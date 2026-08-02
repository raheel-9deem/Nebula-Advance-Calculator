""" Advance Scientific Calculator - Core Engine + Flask Web App
============================================================

A robust, safe scientific calculator engine exposed via a small Flask
web server. The engine evaluates mathematical expressions using a
hand-written recursive-descent parser (no eval / no exec) so that only
safe, well-formed math expressions are ever executed.

Features
--------
- Basic arithmetic: + - * / % ^
- Parentheses and operator precedence
- Scientific functions: sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh
- log ln exp sqrt cbrt abs
- ln (natural), log (base-10)
- Power, factorial (!), square root, cube root
- Constants: pi, e, tau, inf, nan
- Degree / Radian mode toggle
- Memory functions handled client-side
- Permutations nPr and combinations nCr
- Sequence ops: sum/prod over a range, numerical lim()
- Formats: DMS, fraction, HEX/OCT/BIN, Roman numerals (via /api/format)
"""
from __future__ import annotations

import math
import os
import statistics as _stats
from typing import Sequence
from flask import Flask, jsonify, render_template, request
import urllib.error

import converters as _conv

# ---------------------------------------------------------------------------
# Persistent user variables (named memory)
# ---------------------------------------------------------------------------

USER_VARS: dict[str, float] = {}

# Every known function/constant name (used to detect the free iteration
# variable in lambda-taking functions). Mirrors the sets in _tokenize.
_ALL_KNOWN_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "log", "ln", "exp", "sqrt", "cbrt", "abs",
    "npr", "ncr", "sum", "prod", "lim", "diff", "integrate",
    "mean", "median", "mode", "var", "variance", "std", "stddev", "pstdev",
    "vmin", "vmax", "vrange", "vsum", "vcount", "q1", "q3",
    "gcd", "lcm", "isprime", "primefac", "modpow",
    "floor", "ceil", "round2", "round_", "sign", "trunc", "hypot",
    "sto", "recall", "clrvars", "bmi", "pct", "pctchange",
    "pi", "e", "tau", "inf", "nan", "phi",
}

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Tokens are simple strings. The tokenizer walks the string char by char.

_TOK_TYPES = {
    "NUMBER", "FUNC", "CONST", "VAR", "STRING", "OP",
    "LPAREN", "RPAREN", "COMMA", "EOF",
}


def _tokenize(s: str) -> list[tuple[str, object]]:
    """Convert an expression string into a list of (type, value) tokens."""
    tokens: list[tuple[str, object]] = []
    i, n = 0, len(s)

    functions = {
        "sin", "cos", "tan", "asin", "acos", "atan",
        "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
        "log", "ln", "exp", "sqrt", "cbrt", "abs",
        "npr", "ncr",
        "sum", "prod", "lim",
        # calculus (numerical)
        "diff", "integrate",
        # statistics (variadic)
        "mean", "median", "mode", "var", "variance", "std", "stddev", "pstdev",
        "vmin", "vmax", "vrange", "vsum", "vcount", "q1", "q3",
        # number theory / integer ops
        "gcd", "lcm", "isprime", "primefac", "modpow",
        "floor", "ceil", "round2", "round_", "sign", "trunc",
        # persistent named variables
        "sto", "recall", "clrvars",
        # everyday helpers
        "bmi", "pct", "pctchange", "hypot",
    }
    constants = {"pi", "e", "tau", "inf", "nan", "phi"}
    keywords = set(functions) | constants

    while i < n:
        c = s[i]

        # whitespace
        if c.isspace():
            i += 1
            continue

        # base-N integer literals: 0x.. (hex), 0b.. (binary), 0o.. (octal)
        if c == "0" and i + 1 < n and s[i + 1] in "xXbBoO":
            prefix = s[i + 1].lower()
            j = i + 2
            if prefix == "x":
                while j < n and s[j] in "0123456789abcdefABCDEF":
                    j += 1
                if j == i + 2:
                    raise ValueError("Malformed hex literal")
                tokens.append(("NUMBER", float(int(s[i:j], 16))))
            elif prefix == "b":
                while j < n and s[j] in "01":
                    j += 1
                if j == i + 2:
                    raise ValueError("Malformed binary literal")
                tokens.append(("NUMBER", float(int(s[i:j], 2))))
            else:  # octal
                while j < n and s[j] in "01234567":
                    j += 1
                if j == i + 2:
                    raise ValueError("Malformed octal literal")
                tokens.append(("NUMBER", float(int(s[i:j], 8))))
            i = j
            continue

        # number: integer or float, support scientific notation
        if c.isdigit() or c == ".":
            j = i
            seen_dot = False
            while j < n and (s[j].isdigit() or s[j] == "."):
                if s[j] == ".":
                    if seen_dot:
                        break
                    seen_dot = True
                j += 1
            # scientific notation e.g. 1.5e10, 2e-3
            if j < n and s[j] in "eE":
                j += 1
                if j < n and s[j] in "+-":
                    j += 1
                while j < n and s[j].isdigit():
                    j += 1
            tokens.append(("NUMBER", float(s[i:j])))
            i = j
            continue

        # identifiers (functions / constants / sequence ops)
        if c.isalpha() or c == "_":
            j = i
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            name = s[i:j].lower()
            if name in constants:
                tokens.append(("CONST", name))
            elif name in functions:
                tokens.append(("FUNC", name))
            else:
                # Unknown alpha identifier. Treating it as a variable token
                # lets lambda-taking functions (sum/prod/diff/...) hold a free
                # variable like 'x', and lets user variables referenced inline
                # resolve at evaluation time. Resolution & validity are checked
                # by the parser (USER_VARS) or rejected for bare unknowns.
                tokens.append(("VAR", name))
            i = j
            continue

        # string literal (used for variable names, e.g. sto("a", 5))
        if c == '"' or c == "'":
            quote = c
            j = i + 1
            while j < n and s[j] != quote:
                j += 1
            if j >= n:
                raise ValueError("Unterminated string literal")
            tokens.append(("STRING", s[i + 1:j].lower()))
            i = j + 1
            continue

        # operators
        if c in "+-*/^%!":
            tokens.append(("OP", c))
            i += 1
            continue

        if c == "(":
            tokens.append(("LPAREN", c))
            i += 1
            continue
        if c == ")":
            tokens.append(("RPAREN", c))
            i += 1
            continue
        if c == ",":
            tokens.append(("COMMA", c))
            i += 1
            continue

        raise ValueError(f"Unexpected character: {c!r}")

    tokens.append(("EOF", None))
    return tokens


# Operators that round-trip to themselves. Powers use '^'.
_OP_TEXT = {"+": "+", "-": "-", "*": "*", "/": "/", "%": "%", "^": "^", "!": "!"}


def _tokens_to_source(span) -> str:
    """Rebuild a source string from a slice of tokens (without the closing
    comma/paren). This lets lambda-taking functions re-parse an inner
    expression with a bound variable instead of evaluating it eagerly."""
    out = []
    prev = None
    for ttype, tval in span:
        if ttype == "EOF":
            break
        piece = ""
        if ttype == "NUMBER":
            # preserve integer-ness vs float if integral
            if isinstance(tval, float) and tval == int(tval) and abs(tval) < 1e15:
                piece = str(int(tval))
            else:
                piece = repr(tval)
        elif ttype in ("FUNC", "CONST", "VAR"):
            piece = tval
        elif ttype == "OP":
            piece = _OP_TEXT.get(tval, str(tval))
        elif ttype == "LPAREN":
            piece = "("
        elif ttype == "RPAREN":
            piece = ")"
        elif ttype == "COMMA":
            piece = ","
        # insert spacing only between two adjacent alphanumerics to avoid fusing
        if piece and prev and out and piece[:1].isalnum() and prev[:1].isalnum():
            out.append(" ")
        if piece:
            out.append(piece)
            prev = piece
    return "".join(out)


# ---------------------------------------------------------------------------
# Module-level math helpers
# ---------------------------------------------------------------------------

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _prime_factors(n: int) -> int:
    """Return the count of prime factors with multiplicity.

    Returned as a float so it composes with the math engine. (Used mainly as a
    yes/no + magnitude check, e.g. primefac(60) -> 4 factors.)
    """
    n = abs(n)
    count = 0
    d = 2
    while d * d <= n:
        while n % d == 0:
            count += 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        count += 1
    return float(count)


def _quantile(data: list[float], q: float) -> float:
    """Linear-interpolation quantile of a sorted dataset."""
    if not data:
        raise ValueError("empty dataset")
    s = sorted(data)
    if len(s) == 1:
        return float(s[0])
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(s[int(pos)])
    frac = pos - lo
    return float(s[lo] * (1 - frac) + s[hi] * frac)


def _simpson(fn, a: float, b: float, n: int) -> float:
    """Composite Simpson's 1/3 rule for numerical integration."""
    if n % 2 == 1:
        n += 1
    h = (b - a) / n
    total = fn(a) + fn(b)
    for i in range(1, n):
        x = a + i * h
        total += (4 if i % 2 == 1 else 2) * fn(x)
    return (h / 3.0) * total


def _detect_var_name(expr: str) -> str:
    """Find the lone 'free' identifier in an inner expression to use as the
    iteration variable. Defaults to 'x'. Known functions/constants are ignored,
    so an expression like 'exp(x)+log(2)' correctly resolves to 'x'."""
    import re
    names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    free = [nm.lower() for nm in names if nm.lower() not in _ALL_KNOWN_NAMES]
    if "x" in free:
        return "x"
    if free:
        return free[0]
    return "x"


# ---------------------------------------------------------------------------
# Parser (recursive descent) - evaluates inline
# ---------------------------------------------------------------------------

class _Parser:
    """Recursive-descent parser with full precedence.

    Grammar (lowest -> highest precedence):
    expr := term (('+' | '-') term)*
    term := factor (('*' | '/' | '%') factor)*
    factor := unary ('^' unary)*  # right associative power
    unary := ('-' | '+') unary | postfix
    postfix := primary ('!')*      # factorial
    primary := NUMBER | CONST | FUNC '(' expr (',' expr)* ')' |
               '(' expr ')' | primary primary | '[' expr (',' expr)* ']'
    """

    def __init__(self, tokens, deg=False, variables=None):
        self.tokens = tokens
        self.pos = 0
        self.deg = deg  # trig in degrees if True
        self.vars = variables  # dict of named values for this parse

    def peek(self):
        return self.tokens[self.pos]

    def next(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.next()
        if tok[0] != type_:
            raise ValueError(f"Expected {type_} but got {tok[0]}")
        return tok

    def parse(self):
        result = self.expr()
        if self.peek()[0] != "EOF":
            raise ValueError(f"Unexpected token after expression: {self.peek()}")
        return result

    def expr(self):
        value = self.term()
        while self.peek()[0] == "OP" and self.peek()[1] in "+-":
            op = self.next()[1]
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self):
        value = self.factor()
        while self.peek()[0] == "OP" and self.peek()[1] in "*/%":
            op = self.next()[1]
            rhs = self.factor()
            if op == "*":
                value = value * rhs
            elif op == "/":
                if rhs == 0:
                    raise ZeroDivisionError("Division by zero")
                value = value / rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("Modulo by zero")
                value = math.fmod(value, rhs)
        return value

    def factor(self):
        # exponentiation is RIGHT associative: 2^3^2 = 2^(3^2)
        base = self.unary()
        if self.peek()[0] == "OP" and self.peek()[1] == "^":
            self.next()
            exp = self.factor()
            return math.pow(base, exp)
        return base

    def unary(self):
        if self.peek()[0] == "OP" and self.peek()[1] in "+-":
            op = self.next()[1]
            val = self.unary()
            return -val if op == "-" else val
        return self.postfix()

    def postfix(self):
        value = self.primary()
        while self.peek()[0] == "OP" and self.peek()[1] == "!":
            self.next()
            value = self._factorial(value)
        return value

    def _factorial(self, n):
        if n < 0 or n != int(n):
            raise ValueError("Factorial requires a non-negative integer")
        if n > 170:
            raise OverflowError("Factorial overflow")
        return float(math.factorial(int(n)))

    def primary(self):
        tok = self.peek()

        if tok[0] == "NUMBER":
            self.next()
            value = tok[1]
            value = self._implicit_mul(value)
            return value

        if tok[0] == "CONST":
            self.next()
            value = self._const(tok[1])
            return self._implicit_mul(value)

        if tok[0] == "FUNC":
            return self._func()

        if tok[0] == "VAR":
            self.next()
            if tok[1] not in (USER_VARS or {}):
                # Evaluate lazily only matters for lambda capture which uses the
                # raw token stream, never this branch. A bare unknown identifier
                # in a normal expression is an error.
                raise ValueError(f"Unknown identifier: {tok[1]}")
            value = float(USER_VARS.get(tok[1], 0.0))
            return self._implicit_mul(value)

        if tok[0] == "LPAREN":
            self.next()
            value = self.expr()
            self.expect("RPAREN")
            return self._implicit_mul(value)

        raise ValueError(f"Unexpected token: {tok}")

    def _implicit_mul(self, left):
        """Handle implicit multiplication after a value: 2pi, 2(3), 3sin(0)."""
        nxt = self.peek()
        if nxt[0] in ("NUMBER", "CONST", "FUNC", "LPAREN"):
            right = self.factor()
            return left * right
        return left

    def _const(self, name):
        if name == "pi":
            return math.pi
        if name == "e":
            return math.e
        if name == "tau":
            return math.tau
        if name == "inf":
            return math.inf
        if name == "nan":
            return math.nan
        if name == "phi":
            return (1 + math.sqrt(5)) / 2
        raise ValueError(f"Unknown constant: {name}")

    def _deg(self, x):
        """Convert degrees to radians if in degree mode."""
        return math.radians(x) if self.deg else x

    def _rad2deg(self, x):
        """Convert radians to degrees if in degree mode."""
        return math.degrees(x) if self.deg else x

    # Functions whose first argument is a lambda expression string (captured raw).
    _LAMBDA_FUNCS = {"sum", "prod", "lim", "diff", "integrate"}
    # Functions whose first argument is a bare/quoted NAME (captured raw).
    _NAME_FUNCS = {"sto", "recall"}

    def _func(self):
        name = self.next()[1]
        self.expect("LPAREN")
        # For lambda functions, capture the first argument as a RAW source
        # substring (so an unknown variable like x is never evaluated eagerly).
        if name in self._LAMBDA_FUNCS:
            arg0_src, arg0_val = self._capture_raw_arg()
            args = [arg0_src if arg0_src is not None else arg0_val]
            while self.peek()[0] == "COMMA":
                self.next()
                args.append(self.expr())
            self.expect("RPAREN")
            return self._apply_func(name, args)
        # For name-taking functions (sto/recall), capture the first arg as a
        # bare/quoted name string, then evaluate the rest normally.
        if name in self._NAME_FUNCS:
            name_tok = self.peek()
            raw_name = None
            if name_tok[0] == "VAR":
                self.next()
                raw_name = name_tok[1]
            elif name_tok[0] == "STRING":
                self.next()
                raw_name = name_tok[1]
            else:
                raise ValueError(f"Function '{name}' expects a variable name")
            args = [raw_name]
            while self.peek()[0] == "COMMA":
                self.next()
                args.append(self.expr())
            self.expect("RPAREN")
            return self._apply_func(name, args)
        if self.peek()[0] == "RPAREN":
            self.next()
            return self._apply_func(name, [])
        args = [self.expr()]
        while self.peek()[0] == "COMMA":
            self.next()
            args.append(self.expr())
        self.expect("RPAREN")
        return self._apply_func(name, args)

    def _capture_raw_arg(self):
        """Capture one balanced argument as a raw source substring.

        Returns (raw_string, None). Falls back to (None, value) if the argument
        cannot be captured as text (defensive). Uses the token spans to rebuild
        the source — we reconstruct from tokens by their original text.
        """
        start = self.pos
        depth = 0
        while True:
            tok = self.peek()
            if tok[0] == "EOF":
                raise ValueError("Unexpected end inside function argument")
            if tok[0] == "LPAREN":
                depth += 1
            elif tok[0] == "RPAREN":
                if depth == 0:
                    break
                depth -= 1
            elif tok[0] == "COMMA" and depth == 0:
                break
            self.next()
        # slice the captured tokens (start..pos)
        span = self.tokens[start:self.pos]
        raw = _tokens_to_source(span)
        return raw, None

    def _apply_func(self, name, args):
        # ---- Lambda-taking functions: first arg is a raw expression string ----
        if name in self._LAMBDA_FUNCS:
            return self._apply_lambda_func(name, args)

        # ---- Variadic statistics over raw numeric args ----
        STAT_VARIADIC = {
            "mean", "median", "mode", "var", "variance", "std", "stddev",
            "pstdev", "vmin", "vmax", "vrange", "vsum", "vcount", "q1", "q3",
        }
        if name in STAT_VARIADIC:
            return self._apply_stat_func(name, args)

        # ---- Pers household helpers: sto / recall / clrvars ----
        if name in ("sto", "recall", "clrvars"):
            return self._apply_var_func(name, args)

        # ---- Single-arg math familiars + two-arg + small helpers ----
        f = {
            "sin": lambda x: math.sin(self._deg(x)),
            "cos": lambda x: math.cos(self._deg(x)),
            "tan": lambda x: math.tan(self._deg(x)),
            "asin": lambda x: self._rad2deg(math.asin(x)),
            "acos": lambda x: self._rad2deg(math.acos(x)),
            "atan": lambda x: self._rad2deg(math.atan(x)),
            "sinh": lambda x: math.sinh(x),
            "cosh": lambda x: math.cosh(x),
            "tanh": lambda x: math.tanh(x),
            "asinh": lambda x: math.asinh(x),
            "acosh": lambda x: math.acosh(x),
            "atanh": lambda x: math.atanh(x),
            "ln": lambda x: math.log(x),
            "log": lambda x: math.log10(x),
            "exp": lambda x: math.exp(x),
            "sqrt": lambda x: math.sqrt(x),
            "cbrt": lambda x: math.copysign(abs(x) ** (1.0 / 3.0), x),
            "abs": lambda x: abs(x),
            "floor": lambda x: float(math.floor(x)),
            "ceil": lambda x: float(math.ceil(x)),
            "round2": lambda x, n=0: float(round(x, int(n))),
            "round_": lambda x, n=0: float(round(x, int(n))),
            "sign": lambda x: float((x > 0) - (x < 0)),
            "trunc": lambda x: float(math.trunc(x)),
            "hypot": lambda a, b: math.hypot(a, b),
            # two-arg
            "npr": lambda n, r: (
                math.factorial(int(n)) / math.factorial(int(n) - int(r))
            ),
            "ncr": lambda n, r: (
                math.factorial(int(n))
                / (math.factorial(int(r)) * math.factorial(int(n) - int(r)))
            ),
            # number theory
            "gcd": lambda a, b: float(math.gcd(int(a), int(b))),
            "lcm": lambda a, b: float(math.lcm(int(a), int(b))),
            "isprime": lambda n: 1.0 if _is_prime(int(n)) else 0.0,
            "primefac": lambda n: float(_prime_factors(int(n))),
            "modpow": lambda b, e, m: float(pow(int(b), int(e), int(m))),
            # everyday helpers
            "bmi": lambda w, h: w / (h * h),
            "pct": lambda part, whole: (part / whole * 100.0) if whole else float("nan"),
            "pctchange": lambda old, new: ((new - old) / abs(old) * 100.0) if old else float("nan"),
        }
        if name not in f:
            raise ValueError(f"Unknown function: {name}")
        try:
            return float(f[name](*args))
        except TypeError as e:
            raise ValueError(
                f"Function '{name}' received wrong number of arguments"
            )

    def _apply_lambda_func(self, name, args):
        """Handle sum/prod/lim/diff/integrate whose first arg is a raw expr."""
        if not args:
            raise ValueError(f"Function '{name}' requires arguments")
        expr_str = str(args[0])
        # variable name: default 'x'; named via an optional leading "var:" not
        # supported to keep syntax simple -> always bind 'x'. We also accept
        # any single unknown identifier as the variable by scanning tokens.
        var_name = _detect_var_name(expr_str)

        if name in ("sum", "prod"):
            if len(args) != 3:
                raise ValueError(
                    f"Function '{name}' requires 3 arguments: fn(x), a, b"
                )
            a = float(args[1])
            b = float(args[2])
            if int(a) != a or int(b) != b:
                raise ValueError(f"Function '{name}' requires integer bounds")
            if int(a) > int(b):
                raise ValueError(f"Function '{name}' requires a <= b")
            runner = lambda k: self._eval_with_var(expr_str, var_name, k)
            if name == "sum":
                return float(math.fsum(
                    runner(float(k)) for k in range(int(a), int(b) + 1)
                ))
            return float(math.prod(
                runner(float(k)) for k in range(int(a), int(b) + 1)
            ))

        if name == "lim":
            if len(args) != 4:
                raise ValueError(
                    "Function 'lim' requires 4 arguments: fn(x), x0, approach, direction"
                )
            x0 = float(args[1])
            approach = float(args[2])
            # direction: numeric (1/-1) or stringified '+'/'-'
            dir_raw = args[3]
            try:
                dir_num = float(dir_raw)
                direction = "+" if dir_num >= 0 else "-"
            except (TypeError, ValueError):
                direction = str(dir_raw).strip().lower().strip("'\"")
                if direction not in ("+", "-"):
                    raise ValueError("lim direction must be 1, -1, '+' or '-'")
            fn = lambda k: self._eval_with_var(expr_str, var_name, k)
            return float(self._numerical_limit(fn, x0, approach, direction))

        if name == "diff":
            if len(args) not in (2, 3):
                raise ValueError(
                    "Function 'diff' requires 2 or 3 arguments: fn(x), x0, [h]"
                )
            x0 = float(args[1])
            h = float(args[2]) if len(args) == 3 else 1e-6
            fn = lambda k: self._eval_with_var(expr_str, var_name, k)
            return float((fn(x0 + h) - fn(x0 - h)) / (2 * h))

        if name == "integrate":
            if len(args) != 3:
                raise ValueError(
                    "Function 'integrate' requires 3 arguments: fn(x), a, b"
                )
            a = float(args[1])
            b = float(args[2])
            fn = lambda k: self._eval_with_var(expr_str, var_name, k)
            return float(_simpson(fn, a, b, 1000))
        raise ValueError(f"Unknown lambda function: {name}")

    def _apply_stat_func(self, name, args):
        """Variadic statistics over raw numeric arguments."""
        data = [float(a) for a in args]
        n = len(data)
        if n == 0:
            raise ValueError(f"Function '{name}' requires at least one argument")
        if name == "mean":
            return float(_stats.mean(data))
        if name == "median":
            return float(_stats.median(data))
        if name == "mode":
            return float(_stats.mode(data))
        if name in ("var", "variance"):
            return float(_stats.variance(data))
        if name in ("std", "stddev"):
            return float(_stats.stdev(data))
        if name == "pstdev":
            return float(_stats.pstdev(data))
        if name == "vmin":
            return float(min(data))
        if name == "vmax":
            return float(max(data))
        if name == "vrange":
            return float(max(data) - min(data))
        if name == "vsum":
            return float(math.fsum(data))
        if name == "vcount":
            return float(n)
        if name == "q1":
            return float(_quantile(data, 0.25))
        if name == "q3":
            return float(_quantile(data, 0.75))
        raise ValueError(f"Unknown statistics function: {name}")

    def _apply_var_func(self, name, args):
        """Persistent named-variable operations (sto / recall / clrvars)."""
        if name == "sto":
            if len(args) != 2:
                raise ValueError("Function 'sto' requires 2 arguments: name, value")
            vname = str(args[0]).strip().strip("'\"").lower()
            if not vname.replace("_", "").isalnum():
                raise ValueError("Invalid variable name")
            value = float(args[1])
            USER_VARS[vname] = value
            return value
        if name == "recall":
            if len(args) != 1:
                raise ValueError("Function 'recall' requires 1 argument: name")
            vname = str(args[0]).strip().strip("'\"").lower()
            if vname not in USER_VARS:
                raise ValueError(f"Undefined variable: {vname}")
            return float(USER_VARS[vname])
        if name == "clrvars":
            USER_VARS.clear()
            return 0.0
        raise ValueError(f"Unknown variable function: {name}")

    def _eval_with_var(self, expr: str, var_name: str, value: float) -> float:
        """Evaluate an inner expression with a single variable bound to a value.

        Uses a temporary USER_VARS entry so the tokenizer/recognise it as a VAR
        — no string replacement, so identifiers such as 'exp'/'max' are safe.
        """
        existed = var_name in USER_VARS
        old = USER_VARS.get(var_name)
        # bind for this evaluation, also stash any user var of the same name
        USER_VARS[var_name] = value
        try:
            return self._eval_inline_expr(expr)
        finally:
            if existed:
                USER_VARS[var_name] = old
            else:
                USER_VARS.pop(var_name, None)

    def _eval_inline_expr(self, expr: str) -> float:
        try:
            toks = _tokenize(expr)
            p = _Parser(toks, deg=self.deg)
            val = p.parse()
            if isinstance(val, float):
                return val
            return float(val)
        except Exception as e:  # pragma: no cover - safety net
            raise ValueError(f"Invalid inner expression '{expr}': {e}")

    def _numerical_limit(self, fn, x0, approach, direction):
        # Very simple numerical limit using a sequence of points approaching x0
        #  - if x0 is finite: points = x0 +/- (approach / 2^n)
        #  - if x0 is infinity: points = approach + n
        pts = []
        if direction == "+":
            if math.isinf(x0) and x0 > 0:
                pts = [approach + k for k in (1, 10, 100, 1000, 10000)]
            else:
                pts = [x0 + (approach if approach != 0 else 1) / (2 ** k) for k in range(1, 21)]
        elif direction == "-":
            if math.isinf(x0) and x0 < 0:
                pts = [approach - k for k in (1, 10, 100, 1000, 10000)]
            else:
                pts = [x0 - (approach if approach != 0 else 1) / (2 ** k) for k in range(1, 21)]
        else:
            raise ValueError("Direction must be '+' or '-'")
        vals = []
        for t in pts:
            try:
                vals.append(fn(t))
            except Exception:
                pass
        if not vals:
            return float("nan")
        return vals[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate(expression: str, deg: bool = False) -> dict:
    """Evaluate a math expression and return a result dict.

    Parameters
    ----------
    expression : str
        The mathematical expression, e.g. "sin(30) + 2^3".
    deg : bool
        If True, trigonometric functions expect degrees.

    Returns
    -------
    dict with keys: expression, result, mode, success, error (on failure)
    """
    if not expression or not expression.strip():
        return {"success": False, "error": "Empty expression"}

    # friendly substitutions
    expr = (expression
            .replace("×", "*").replace("÷", "/").replace("−", "-")
            .replace("√", "sqrt").replace("π", "pi").replace("τ", "tau")
            .replace("^", "^"))  # ^ stays, used for powers

    try:
        tokens = _tokenize(expr)
        parser = _Parser(tokens, deg=deg)
        result = parser.parse()

        # pretty result formatting
        if isinstance(result, float):
            if math.isinf(result):
                text = "∞" if result > 0 else "-∞"
            elif math.isnan(result):
                text = "NaN"
            elif result == int(result) and abs(result) < 1e15:
                text = str(int(result))
            else:
                text = f"{result:.10g}"
        else:
            text = str(result)

        return {
            "success": True,
            "expression": expression,
            "result": text,
            "mode": "DEG" if deg else "RAD",
        }
    except ZeroDivisionError as e:
        return {"success": False, "error": f"Math error: {e}"}
    except (ValueError, OverflowError, ArithmeticError) as e:
        return {"success": False, "error": f"{e}"}
    except Exception as e:  # pragma: no cover - defensive
        return {"success": False, "error": f"Unexpected error: {e}"}


# ---------------------------------------------------------------------------
# Formatting helpers (DMS, fraction, base-N, roman)
# ---------------------------------------------------------------------------

def _to_dms(value: float, deg_mode: bool = True) -> str:
    """Convert a number to degrees/minutes/seconds notation.

    If deg_mode is True, the value is assumed to already be in degrees.
    If deg_mode is False, the value is in radians and converted first.
    """
    if deg_mode is False:
        value = math.degrees(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    d = int(value)
    rem = (value - d) * 60
    m = int(rem)
    s = (rem - m) * 60
    # round to avoid float noise like 19.999999
    s = round(s, 4)
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    if abs(s - int(s)) < 1e-6:
        s_str = f"{int(s)}\""
    else:
        s_str = f'{s:g}"'
    return f"{sign}{d}°{m}'{s_str}"


def _to_fraction(value: float, max_den: int = 1000000) -> str:
    """Approximate a float as a reduced fraction using continued fractions."""
    if math.isinf(value) or math.isnan(value):
        return "∞" if value > 0 else "NaN"
    if value == int(value):
        return f"{int(value)}"
    sign = "-" if value < 0 else ""
    x = abs(value)
    # continued fraction expansion
    h0, h1 = 0, 1
    k0, k1 = 1, 0
    approx = x
    for _ in range(32):
        whole = int(approx)
        h = whole * h1 + h0
        k = whole * k1 + k0
        if k > max_den:
            break
        h0, h1 = h1, h
        k0, k1 = k1, k
        if abs(h / k - x) < 1e-12:
            break
        if approx == whole:
            break
        approx = 1.0 / (approx - whole)
    num, den = h1, k1
    if den == 1:
        return f"{sign}{num}"
    return f"{sign}{num}/{den}"


def _to_hex(value: float) -> str:
    n = int(round(value))
    if n < 0:
        return "-" + format(-n, "X")
    return format(n, "X")


def _to_oct(value: float) -> str:
    n = int(round(value))
    if n < 0:
        return "-" + format(-n, "o")
    return format(n, "o")


def _to_bin(value: float) -> str:
    n = int(round(value))
    if n < 0:
        return "-" + format(-n, "b")
    return format(n, "b")


_ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"),
    (1, "I"),
]


def _to_roman(value: float) -> str:
    n = int(round(value))
    if n <= 0:
        raise ValueError("Roman numerals require a positive integer")
    out = []
    for v, sym in _ROMAN:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def _to_engineering(value: float) -> str:
    """Engineering notation — exponent is a multiple of 3."""
    if value == 0 or math.isinf(value) or math.isnan(value):
        return f"{value:g}"
    exp = math.floor(math.log10(abs(value)))
    exp -= exp % 3  # snap to multiple of 3
    mant = value / (10 ** exp)
    return f"{mant:.10g}e{exp:+03d}"


def _to_grouped(value: float, digits: int = 10) -> str:
    """Decimal notation grouped with commas."""
    if math.isinf(value) or math.isnan(value):
        return f"{value:g}"
    s = f"{value:.{digits}g}"
    # split integer/decimal parts
    if "." in s:
        intpart, frac = s.split(".", 1)
    else:
        intpart, frac = s, ""
    neg = intpart.startswith("-")
    if neg:
        intpart = intpart[1:]
    intpart = f"{int(intpart):,}" if intpart.isdigit() else intpart
    return ("-" if neg else "") + intpart + (("." + frac) if frac else "")


_FORMATTERS = {
    "dms": _to_dms,
    "frac": _to_fraction,
    "hex": _to_hex,
    "oct": _to_oct,
    "bin": _to_bin,
    "roman": _to_roman,
    "sci": lambda v: f"{v:.10g}" if (math.isinf(v) or math.isnan(v)) else format(v, ".10E").replace("E", "e"),
    "eng": _to_engineering,
    "dec": _to_grouped,
}


# ---------------------------------------------------------------------------
# Linear algebra (pure Python, no numpy) + equation solving
# ---------------------------------------------------------------------------

def _clean(x):
    """JSON-safe float: None for non-finite so jsonify never emits NaN/Infinity."""
    x = float(x)
    return x if math.isfinite(x) else None


def _mat_shape(m):
    if not m or not isinstance(m, list):
        raise ValueError("Matrix must be a non-empty list of rows")
    cols = len(m[0])
    for row in m:
        if not isinstance(row, list) or len(row) != cols:
            raise ValueError("Matrix rows must have equal length")
    return len(m), cols


def _mat_add(a, b):
    ra, ca = _mat_shape(a)
    rb, cb = _mat_shape(b)
    if ra != rb or ca != cb:
        raise ValueError("Matrices must have the same shape to add")
    return [[a[i][j] + b[i][j] for j in range(ca)] for i in range(ra)]


def _mat_sub(a, b):
    ra, ca = _mat_shape(a)
    rb, cb = _mat_shape(b)
    if ra != rb or ca != cb:
        raise ValueError("Matrices must have the same shape to subtract")
    return [[a[i][j] - b[i][j] for j in range(ca)] for i in range(ra)]


def _mat_mul(a, b):
    ra, ca = _mat_shape(a)
    rb, cb = _mat_shape(b)
    if ca != rb:
        raise ValueError(
            f"Cannot multiply {ra}x{ca} by {rb}x{cb} matrices"
        )
    return [[sum(a[i][k] * b[k][j] for k in range(ca)) for j in range(cb)]
            for i in range(ra)]


def _mat_transpose(a):
    r, c = _mat_shape(a)
    return [[a[i][j] for i in range(r)] for j in range(c)]


def _mat_det(a):
    n, m = _mat_shape(a)
    if n != m:
        raise ValueError("Determinant requires a square matrix")
    # copy to avoid mutating input
    M = [row[:] for row in a]
    det = 1.0
    for col in range(n):
        # partial pivot
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            return 0.0
        if pivot != col:
            M[col], M[pivot] = M[pivot], M[col]
            det = -det
        det *= M[col][col]
        for r in range(col + 1, n):
            factor = M[r][col] / M[col][col]
            for c in range(col, n):
                M[r][c] -= factor * M[col][c]
    return det


def _mat_inv(a):
    n, m = _mat_shape(a)
    if n != m:
        raise ValueError("Inverse requires a square matrix")
    # augmented [A | I] then Gaussian elimination
    M = [list(a[i]) + [1.0 if i == j else 0.0 for j in range(n)]
         for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            raise ValueError("Matrix is singular (not invertible)")
        if pivot != col:
            M[col], M[pivot] = M[pivot], M[col]
        piv = M[col][col]
        M[col] = [v / piv for v in M[col]]
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col]
            M[r] = [M[r][k] - factor * M[col][k] for k in range(2 * n)]
    return [row[n:] for row in M]


def _mat_solve(a, b):
    """Solve Ax = b for x (b as a column vector). Returns a flat list."""
    inv = _mat_inv(a)
    n = len(a)
    if len(b) != n:
        raise ValueError("RHS length must match matrix rows")
    return [sum(inv[i][j] * b[j] for j in range(n)) for i in range(n)]


def _solve_poly(coeffs):
    """Solve ax + b = 0 (coeffs [a,b]) or ax^2 + bx + c = 0 (coeffs [a,b,c]).
    Returns a dict with roots and metadata."""
    coeffs = [float(c) for c in coeffs]
    if len(coeffs) == 2:
        a, b = coeffs
        if a == 0:
            if b == 0:
                return {"roots": [], "note": "Identity: infinitely many solutions"}
            return {"roots": [], "note": "No solution (inconsistent)"}
        return {"roots": [(-b / a)], "discriminant": None}
    if len(coeffs) == 3:
        a, b, c = coeffs
        if a == 0:
            return _solve_poly([b, c])
        disc = b * b - 4 * a * c
        if disc >= 0:
            sq = math.sqrt(disc)
            r1 = (-b + sq) / (2 * a)
            r2 = (-b - sq) / (2 * a)
            return {"roots": sorted([r1, r2], reverse=True), "discriminant": disc}
        # complex
        re = -b / (2 * a)
        im = math.sqrt(-disc) / (2 * a)
        roots = [f"{re:.10g} + {im:.10g}i", f"{re:.10g} - {im:.10g}i"]
        return {"roots": roots, "discriminant": disc, "complex": True}
    raise ValueError("Only degree-1 and degree-2 polynomials are supported")


def _solve_system(A, b):
    """Solve a linear system Ax = b via inverse. A is n x n, b is length n."""
    return _mat_solve(A, b)


# ---------------------------------------------------------------------------
# Base literal parser (for /api/base)
# ---------------------------------------------------------------------------

def _parse_any_base(text: str):
    """Parse a numeric string in any of: 0x, 0b, 0o, decimal, or hex digits."""
    s = text.strip().lower()
    if not s:
        raise ValueError("empty value")
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if s.startswith("0x"):
        val = int(s, 16)
    elif s.startswith("0b"):
        val = int(s, 2)
    elif s.startswith("0o"):
        val = int(s, 8)
    else:
        try:
            val = int(s)
        except ValueError:
            # try as bare hex
            val = int(s, 16)
    if neg:
        val = -val
    return val


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json(silent=True) or {}
    expression = str(data.get("expression", "")).strip()
    deg = bool(data.get("deg", False))
    return jsonify(calculate(expression, deg=deg))


@app.route("/api/format", methods=["POST"])
def api_format():
    """Format a numeric value in DMS / fraction / base-N / roman."""
    data = request.get_json(silent=True) or {}
    try:
        number = float(data.get("number", "nan"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid number"})
    fmt = str(data.get("format", "")).lower()
    deg = bool(data.get("deg", False))
    if fmt not in _FORMATTERS:
        return jsonify({"success": False, "error": f"Unknown format: {fmt}"})
    try:
        if fmt == "dms":
            formatted = _FORMATTERS[fmt](number, deg_mode=deg)
        else:
            formatted = _FORMATTERS[fmt](number)
    except (ValueError, OverflowError) as e:
        return jsonify({"success": False, "error": str(e)})
    return jsonify({
        "success": True,
        "format": fmt,
        "formatted": formatted,
        "original": number,
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "engine": "v2.0"})


@app.route("/api/solve", methods=["POST"])
def api_solve():
    """Solve polynomials or linear systems.

    Body for a polynomial: { "type": "poly", "coeffs": [a, b, (c)] }
      degree-1 coeffs [a, b] solves a x + b = 0
      degree-2 coeffs [a, b, c] solves a x^2 + b x + c = 0
    Body for a linear system: { "type": "system", "A": [[...]], "b": [...] }
    """
    data = request.get_json(silent=True) or {}
    stype = str(data.get("type", "")).lower()
    try:
        if stype in ("poly", "polynomial", ""):
            coeffs = data.get("coeffs") or data.get("c") or []
            if not isinstance(coeffs, list) or not coeffs:
                return jsonify({"success": False, "error": "coeffs list required"})
            res = _solve_poly(coeffs)
            res["success"] = True
            return jsonify(_jsonsafe(res))
        if stype == "system":
            A = data.get("A")
            b = data.get("b")
            if not isinstance(A, list) or not isinstance(b, list):
                return jsonify({"success": False, "error": "A (matrix) and b (vector) required"})
            x = _mat_solve(A, _to_float_list(b))
            return jsonify({"success": True, "roots": _jsonsafe(x), "note": "Ax = b solution"})
        return jsonify({"success": False, "error": "type must be 'poly' or 'system'"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/matrix", methods=["POST"])
def api_matrix():
    """Matrix operations. Body: { "op": "...", "a": [[..]], "b": [[..]] }.

    ops: add, sub, mul, det, inv, transpose, solve (a * x = b, b as vector)
    """
    data = request.get_json(silent=True) or {}
    op = str(data.get("op", "")).lower()
    a = data.get("a")
    b = data.get("b")
    try:
        if op == "add":
            res = _mat_add(a, b)
        elif op == "sub":
            res = _mat_sub(a, b)
        elif op == "mul":
            res = _mat_mul(a, b)
        elif op == "transpose":
            res = _mat_transpose(a)
        elif op == "det":
            return jsonify({"success": True, "result": _clean(_mat_det(a))})
        elif op == "inv":
            res = _mat_inv(a)
        elif op == "solve":
            roots = _mat_solve(a, _to_float_list(b))
            return jsonify({"success": True, "result": _jsonsafe(roots), "shape": None})
        else:
            return jsonify({"success": False, "error": f"unknown op: {op}"})
        shape = f"{len(res)}x{len(res[0])}" if res else "0x0"
        return jsonify({"success": True, "result": _jsonsafe(res), "shape": shape})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/base", methods=["POST"])
def api_base():
    """Convert a value between decimal, hex, octal, and binary.

    Body: { "value": "0xFF" | 255 | "FF" ... }
    """
    data = request.get_json(silent=True) or {}
    raw = str(data.get("value", ""))
    try:
        v = _parse_any_base(raw)
        return jsonify({
            "success": True,
            "dec": int(v),
            "hex": format(v, "X"),
            "oct": format(v, "o"),
            "bin": format(v, "b"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/convert", methods=["POST"])
def api_convert():
    """Unit conversion. Body: { "category", "from", "to", "value" }.

    Temperature is its own category (offset-based) handled specially.
    """
    data = request.get_json(silent=True) or {}
    try:
        category = str(data.get("category", "")).lower()
        from_u = str(data.get("from", ""))
        to_u = str(data.get("to", ""))
        value = float(data.get("value", 0))
        if category == "temperature":
            result = _conv.convert_temperature(from_u, to_u, value)
        else:
            result = _conv.convert_unit(category, from_u, to_u, value)
        return jsonify({
            "success": True,
            "result": _clean(result),
            "category": category,
            "from": from_u,
            "to": to_u,
            "input": value,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/units", methods=["GET"])
def api_units():
    """List available conversion categories and their units."""
    out = {}
    for cat, table in _conv.UNITS.items():
        out[cat] = list(table.keys())
    out["temperature"] = ["c", "f", "k"]
    return jsonify({"success": True, "categories": out})


@app.route("/api/currency", methods=["POST"])
def api_currency():
    """Live currency conversion. Body: { "from", "to", "amount" }.

    Rates are cached for 1 hour. Fails gracefully if the rate service is
    unreachable (no 500 — returns a clear success:false message).
    """
    data = request.get_json(silent=True) or {}
    try:
        fc = str(data.get("from", "")).upper()
        tc = str(data.get("to", "")).upper()
        amount = float(data.get("amount", 1))
        if not fc or not tc:
            return jsonify({"success": False, "error": "from and to required"})
        rate = _conv.currency_rate(fc, tc)
        return jsonify({
            "success": True,
            "rate": _clean(rate),
            "from": fc,
            "to": tc,
            "amount": _clean(amount),
            "result": _clean(amount * rate),
        })
    except urllib.error.URLError:
        return jsonify({"success": False, "error": "Currency service unreachable. Try again later."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/datetime", methods=["POST"])
def api_datetime():
    """Date/time math. Body determines the operation:

    { "op": "diff", "a": "...", "b": "..." } -> difference between dates
    { "op": "add", "date": "...", "days": n } -> date + n days
    { "op": "weekday", "date": "..." } -> day of week
    { "op": "age", "birth": "...", "on": "..." } -> age
    """
    data = request.get_json(silent=True) or {}
    try:
        op = str(data.get("op", "diff")).lower()
        if op == "diff":
            res = _conv.date_diff(str(data.get("a", "")), str(data.get("b", "")))
        elif op == "add":
            res = {"date": _conv.add_days(str(data.get("date", "")), int(data.get("days", 0)))}
        elif op == "weekday":
            res = {"weekday": _conv.weekday(str(data.get("date", "")))}
        elif op == "age":
            res = _conv.age(str(data.get("birth", "")), data.get("on"))
        else:
            return jsonify({"success": False, "error": f"unknown op: {op}"})
        return jsonify({"success": True, "result": _jsonsafe(res)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stats", methods=["POST"])
def api_stats():
    """Dataset statistics on a posted list of numbers.

    Body: { "data": [1, 2, 3, ...] }
    Returns mean, median, mode, variance, std, min, max, range, quartiles.
    """
    data = request.get_json(silent=True) or {}
    try:
        arr = data.get("data")
        if not isinstance(arr, list) or not arr:
            return jsonify({"success": False, "error": "data list required"})
        nums = [float(v) for v in arr]
        import statistics as st
        out = {
            "count": len(nums),
            "sum": _clean(math.fsum(nums)),
            "mean": _clean(st.mean(nums)),
            "median": _clean(st.median(nums)),
            "min": _clean(min(nums)),
            "max": _clean(max(nums)),
            "range": _clean(max(nums) - min(nums)),
            "variance": _clean(st.variance(nums)) if len(nums) > 1 else None,
            "std": _clean(st.stdev(nums)) if len(nums) > 1 else None,
            "q1": _clean(_quantile(nums, 0.25)),
            "q3": _clean(_quantile(nums, 0.75)),
        }
        try:
            out["mode"] = _clean(st.mode(nums))
        except st.StatisticsError:
            out["mode"] = None
        return jsonify({"success": True, "result": out})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plot", methods=["POST"])
def api_plot():
    """Sample a function y = f(x) over a range for plotting.

    Body: { "expr": "sin(x)", "xMin": -6.28, "xMax": 6.28, "n": 200, "deg": false }
    Returns { "points": [[x, y], ...] } with y=None for evaluation failures.
    """
    data = request.get_json(silent=True) or {}
    try:
        expr = str(data.get("expr", "")).strip()
        if not expr:
            return jsonify({"success": False, "error": "expr required"})
        x_min = float(data.get("xMin", -10))
        x_max = float(data.get("xMax", 10))
        n = int(data.get("n", 200))
        deg = bool(data.get("deg", False))
        if n < 2:
            n = 200
        if n > 2000:
            n = 2000
        if x_max <= x_min:
            return jsonify({"success": False, "error": "xMax must exceed xMin"})
        var_name = _detect_var_name(expr)
        # use a throwaway parser to run _eval_with_var for each sample
        toks = _tokenize("__noop__") if False else _tokenize("0")
        parser = _Parser(toks, deg=deg)
        step = (x_max - x_min) / (n - 1)
        points = []
        for i in range(n):
            x = x_min + i * step
            try:
                y = parser._eval_with_var(expr, var_name, x)
                points.append([_clean(x), _clean(y)])
            except Exception:
                points.append([_clean(x), None])
        return jsonify({"success": True, "points": points, "n": n})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def _to_float_list(x):
    if not isinstance(x, list):
        raise ValueError("expected a list")
    return [float(v) for v in x]


def _jsonsafe(obj):
    """Recursively make a structure JSON-safe (no NaN/Infinity)."""
    if isinstance(obj, dict):
        return {k: _jsonsafe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonsafe(v) for v in obj]
    if isinstance(obj, (int,)):
        return obj
    if isinstance(obj, float):
        return _clean(obj)
    return obj


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
