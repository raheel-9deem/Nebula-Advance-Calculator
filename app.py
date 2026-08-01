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
from typing import Sequence
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Tokens are simple strings. The tokenizer walks the string char by char.

_TOK_TYPES = {
    "NUMBER", "FUNC", "CONST", "OP",
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
    }
    constants = {"pi", "e", "tau", "inf", "nan"}
    keywords = set(functions) | constants

    while i < n:
        c = s[i]

        # whitespace
        if c.isspace():
            i += 1
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
                raise ValueError(f"Unknown identifier: {s[i:j]}")
            i = j
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

    def __init__(self, tokens, deg=False):
        self.tokens = tokens
        self.pos = 0
        self.deg = deg  # trig in degrees if True

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
        raise ValueError(f"Unknown constant: {name}")

    def _deg(self, x):
        """Convert degrees to radians if in degree mode."""
        return math.radians(x) if self.deg else x

    def _rad2deg(self, x):
        """Convert radians to degrees if in degree mode."""
        return math.degrees(x) if self.deg else x

    def _func(self):
        name = self.next()[1]
        self.expect("LPAREN")
        args = [self.expr()]
        while self.peek()[0] == "COMMA":
            self.next()
            args.append(self.expr())
        self.expect("RPAREN")
        return self._apply_func(name, args)

    def _apply_func(self, name, args):
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
            # two-arg
            "npr": lambda n, r: (
                math.factorial(int(n)) / math.factorial(int(n) - int(r))
            ),
            "ncr": lambda n, r: (
                math.factorial(int(n))
                / (math.factorial(int(r)) * math.factorial(int(n) - int(r)))
            ),
            # three-arg
            "sum": lambda expr_fn, a=None, b=None: (
                math.fsum(expr_fn(float(k)) for k in range(int(a), int(b) + 1))
                if a is not None and b is not None else expr_fn(float(a))
                if a is not None else None
            ),
            "prod": lambda expr_fn, a=None, b=None: (
                math.prod(expr_fn(float(k)) for k in range(int(a), int(b) + 1))
                if a is not None and b is not None else expr_fn(float(a))
                if a is not None else None
            ),
        }
        if name not in f:
            raise ValueError(f"Unknown function: {name}")
        # special handling for sum/prod: first arg can be a nested expression fn(x)=...
        if name in ("sum", "prod"):
            if len(args) < 3:
                raise ValueError(
                    f"Function '{name}' requires 3 arguments: fn(x), a, b"
                )
            expr_fn_str, a_str, b_str = (
                str(args[0]), str(args[1]), str(args[2])
            )
            # treat the first arg as a one-argument expression: replace x -> k
            fn = lambda k: self._eval_inline_expr(expr_fn_str.replace("x", str(k))) # type: ignore[return-value]
            a = float(a_str)
            b = float(b_str)
            if int(a) != a or int(b) != b:
                raise ValueError(f"Function '{name}' requires integer bounds")
            if int(a) > int(b):
                raise ValueError(f"Function '{name}' requires a <= b")
            return float(f[name](fn, int(a), int(b)))
        if name == "lim":
            if len(args) != 4:
                raise ValueError(
                    "Function 'lim' requires 4 arguments: fn(x), x0, approach, direction"
                )
            expr_fn_str, x0_str, approach_str, direction_str = (
                str(args[0]), str(args[1]), str(args[2]), str(args[3])
            )
            x0 = float(x0_str)
            approach = float(approach_str)
            direction = str(direction_str).lower()
            # We evaluate the expression numerically for points approaching x0
            fn = lambda k: self._eval_inline_expr(expr_fn_str.replace("x", str(k))) # type: ignore[return-value]
            return float(self._numerical_limit(fn, x0, approach, direction))
        try:
            return float(f[name](*args))
        except TypeError:
            raise ValueError(
                f"Function '{name}' received wrong number of arguments"
            )

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


_FORMATTERS = {
    "dms": _to_dms,
    "frac": _to_fraction,
    "hex": _to_hex,
    "oct": _to_oct,
    "bin": _to_bin,
    "roman": _to_roman,
}


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
    return jsonify({"status": "ok", "engine": "v1.0"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
