# 🌌 Nebula — Advanced Scientific Calculator

A striking, fully-functional **Advanced Scientific Calculator** built with **Python + Flask** and a custom **glassmorphism / neon** web UI. No `eval()`, no `exec()` — every expression is parsed by a hand-written recursive-descent parser, so only safe, well-formed math is ever executed.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![UI](https://img.shields.io/badge/UI-Glassmorphism_neon+violet)
![Version](https://img.shields.io/badge/Version-v2.0-green)

---

## 🚀 What's New in v2

| Area | Highlights |
|---|---|
| **Calculus** | `diff(sin(x),0)` → derivative · `integrate(x^2,0,1)` → Simpson's-rule integral |
| **Statistics** | `mean(2,4,6,8)`, `std(1,2,3,4,5)`, `median`, `var`, `min`, `max` |
| **Number Theory** | `gcd(12,18)` → 6 · `lcm(4,6)` → 12 · `isprime(17)` → 1 · `primefac(60)` |
| **Base-N Input** | `0xFF + 0b1` → 256 · `0o17` → 15 · `0b1010` → 10 |
| **Named Variables** | `sto("a",5)` → `recall("a")*2` → 10 |
| **Equation Solver** | Quadratic formula, complex roots, 2×2 / 3×3 linear systems |
| **Matrices** | add, sub, mul, det, inverse, transpose, solve (pure Python) |
| **Unit Converter** | length, mass, temperature, time, area, volume, speed, data |
| **Currency** | Live exchange rates (free API, 1-hour cache) |
| **Date/Time** | Date difference, add days, day-of-week, age calculator |
| **Graph Plotter** | Interactive canvas — zoom (scroll), pan (drag), hover crosshair |
| **Tools Drawer** | Tabbed panel: Convert · Currency · DateTime · Stats · Solve · Matrix · Base |
| **Themes** | Dark → Light toggle, accent persisted in localStorage |
| **Voice Input** | Speech-to-text → math tokens (graceful fallback on unsupported browsers) |
| **History** | CSV export, re-edit original expressions |
| **Formats** | Added SCI, ENG, DEC (engineering notation, grouped decimal) |

---

## ✨ Features

### Engine

- **Arithmetic:** `+  -  *  /  %  ^` (power, right-associative: `2^3^2 = 2^(3^2)`)
- **Trigonometry:** `sin cos tan`, inverses `asin acos atan`, hyperbolic `sinh cosh tanh asinh acosh atanh`
- **Logarithms:** `ln` (natural), `log` (base-10), `exp`, `10^x`
- **Roots:** `sqrt`, `cbrt`
- **Factorial:** `x!` (e.g. `5!`), **Permutations / Combinations:** `npr`, `nCr`
- **Sequence / Calculus:** `sum(expr, a, b)`, `prod(expr, a, b)`, `lim(expr, x0, approach, direction)`, `diff(expr, x0)`, `integrate(expr, a, b)`
- **Statistics:** `mean(...)`, `median(...)`, `var(...)`, `std(...)`, `min(...)`, `max(...)`, `sum2(...)`, `range2(...)`
- **Number Theory:** `gcd(a,b)`, `lcm(a,b)`, `isprime(n)`, `primefac(n)`, `modpow(b,e,m)`
- **Rounding:** `floor(x)`, `ceil(x)`, `round2(x)`
- **Constants:** `pi`, `e`, `tau`, `phi` (golden ratio)
- **Absolute value:** `|x|` via `abs()`
- **Base-N Literals:** `0xFF` (hex), `0b1010` (binary), `0o17` (octal)
- **Named Variables:** `sto("name", value)`, `recall("name")`, `clrvars()`
- **BMI / Percentage:** `bmi(weight,height)`, `pct(part,whole)`, `pctchange(old,new)`, `hypot(x,y)`
- **Degree / Radian mode** toggle (affects all trig functions)
- **Implicit multiplication:** `2pi`, `3(4+1)`, `2sin(30)`
- **Error handling:** divide-by-zero, domain errors, malformed expressions — all surfaced cleanly

### Number Formats

After computing a result, tap any format button in the format bar to convert it instantly:

| Format | Example |
|---|---|
| **DMS** | `45.5` → `45°30'0"` |
| **FRAC** | `0.5` → `1/2` (continued fractions) |
| **HEX** | `255` → `FF` |
| **OCT** | `255` → `377` |
| **BIN** | `255` → `11111111` |
| **ROMAN** | `2024` → `MMXXIV` |
| **SCI** | `1234567` → `1.234567e+06` |
| **ENG** | `1234567` → `1.234567 M` (engineering prefix) |
| **DEC** | `1234567` → `1,234,567` (grouped) |

### UI

- Animated **aurora background** + live **particle constellation**
- **Glassmorphism** calculator shell with neon accent gradients and gradient borders
- **Color-coded key groups:** teal (functions), amber (inverse), cyan (constants), pink (memory), violet (tools), yellow (utilities), blue (operators)
- **Format bar** with DMS / FRAC / HEX / OCT / BIN / ROMAN / SCI / ENG / DEC
- **DEG / RAD** mode switch
- **Memory:** `MC MR M+ M-`
- **Named variables panel** (sidebar) — click to recall stored values
- **Persistent history** (localStorage) — click to reuse a result, ✎ to edit the original expression, CSV export
- **Keyboard support** — type expressions directly; `Ctrl/Cmd+C` copies the expression
- **Graph plotter** — scroll to zoom, drag to pan, hover to read (x, y)
- **Tools drawer** — tabbed panel: Convert · Currency · DateTime · Stats · Solve · Matrix · Base
- **Theme toggle** — Dark ↔ Light, persisted in localStorage
- **Voice input** — speech-to-text → math tokens (graceful degradation)
- Fully **responsive & scrollable** — works on desktop and mobile

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or newer
- A modern browser (Chrome / Edge / Firefox / Safari)

### Install & Run

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. launch the app
python app.py
```

Then open **http://localhost:5000** in your browser.

**No third-party dependencies required** beyond Flask — all math, matrices, converters, and solvers are stdlib / pure Python.

---

## 🧭 Usage

### Expression Examples

| You want to… | Type / click |
|---|---|
| Sine of 30° | `sin(30)` → `=` |
| 2 to the power 10 | `2^10` → `1024` |
| Factorial of 6 | `6!` → `720` |
| Natural log of 100 | `ln(100)` |
| Square root | `sqrt(144)` → `12` |
| Permutations ₈P₃ | `npr(8,3)` |
| Combinations ₈C₃ | `ncr(8,3)` |
| Sum of squares 1..5 | `sum(x^2, 1, 5)` → `55` |
| Product 2..5 | `prod(x, 2, 5)` → `120` |
| Numerical limit | `lim(1/x,0,1,1)` → `1048576` |
| Numerical derivative | `diff(sin(x), 0)` → `1` |
| Numerical integral | `integrate(x^2, 0, 1)` → `0.333…` |
| Mean of dataset | `mean(2, 4, 4, 4, 5, 5, 7, 9)` → `5` |
| Standard deviation | `std(1, 2, 3, 4, 5)` → `1.581…` |
| GCD | `gcd(12, 18)` → `6` |
| LCM | `lcm(4, 6)` → `12` |
| Primality test | `isprime(17)` → `1` (true) |
| Hex + binary | `0xFF + 0b1` → `256` |
| Store / recall variable | `sto("a",5)` then `recall("a")*2` → `10` |
| Golden ratio | `phi` → `1.618…` |
| BMI | `bmi(70,170)` → BMI value |

### Switch DEG / RAD from the top-right toggle.

---

## 🛠️ Tools

All tools live in a slide-up **tools drawer** (open via the gear icon ⚙ on the header, or the **TOOLS** key on the scientific pad).

### 📐 Unit Converter

Supports 8 categories: **length, mass, time, area, volume, speed, data, temperature**.

Example: Convert `1 km` → `1000 m`

### 💱 Currency

Live exchange rates via a free API (no key required). 1-hour in-memory cache.

Example: `1 USD → 0.87 EUR` (approx)

### 📅 Date / Time

- **Difference** between two dates (days, weeks, months, years)
- **Add days** to a date
- **Day of week** for any date
- **Age calculator** (birth date → years, days)

### 📊 Stats (Dataset)

Post a list of numbers → get back **mean, median, mode, variance, std, min, max, range, quartiles, sum, count**.

### 🔢 Equation Solver

- **Polynomial** — quadratic formula with discriminant and complex-root support
- **Linear System** — 2×2 / 3×3 via Gaussian elimination

### 🧮 Matrix

Operations: **det, inverse, transpose, multiply, add, solve (Ax=b)** — pure Python, no numpy.

### 🔤 Base Converter

Input any format (`255`, `0xFF`, `0b1010`, `0o377`, `FF`) → get all four bases (decimal, hex, oct, binary).

### 📈 Graph Plotter

Open the graph panel from the header. Enter `sin(x)`, set x range, and click **Plot**.

- **Scroll** to zoom · **Drag** to pan · **Hover** to read (x, y)
- Toggle DEG / RAD per-plot

---

## 🗂️ Project Structure

```
Advance-Scientific-Calculator-cc/
├── app.py                 # Calculator engine (tokenizer + parser) + Flask routes
├── converters.py          # Unit conversion tables, currency fetch/cache, date/time helpers
├── requirements.txt       # Python dependencies (Flask only)
├── README.md              # You are here
├── templates/
│   └── index.html         # Calculator UI (keypad, format bar, graph panel, tools drawer, display)
└── static/
    ├── css/
    │   └── style.css      # Glassmorphism / neon theme + responsive layout
    └── js/
        └── app.js         # Keypad, history, graph plotter, tools drawer, themes, voice
```

---

## 🔌 API

All API endpoints accept and return JSON. The root path (`/`) serves the HTML UI.

### `POST /api/calculate`

Evaluate a mathematical expression.

```json
{ "expression": "sin(30) + 2^3", "deg": true }
```

**Success response:**
```json
{
  "success": true,
  "expression": "sin(30) + 2^3",
  "result": "3.5",
  "mode": "DEG"
}
```

**Error response:**
```json
{ "success": false, "error": "Math error: division by zero" }
```

### `POST /api/format`

Convert a number into a formatted string.

```json
{ "value": 255, "format": "hex" }
```

**Response:**
```json
{ "success": true, "format": "hex", "formatted": "FF", "original": 255.0 }
```

Supported formats: `dms`, `frac`, `hex`, `oct`, `bin`, `roman`, `sci`, `eng`, `dec`

### `POST /api/plot`

Sample a function for graphing.

```json
{ "expr": "sin(x)", "xMin": -6.28, "xMax": 6.28, "n": 600 }
```

**Response:**
```json
{ "success": true, "points": [[-6.28, -0.02], [-6.2, 0.12], …] }
```

### `POST /api/convert`

Unit conversion.

```json
{ "category": "length", "from": "km", "to": "m", "value": 1 }
```

**Response:** `{ "success": true, "result": 1000.0 }`

### `GET /api/units`

List all unit categories and their units.

```json
{ "success": true, "categories": ["length", "mass", "time", "area", "volume", "speed", "data", "temperature"] }
```

### `POST /api/currency`

Live currency conversion.

```json
{ "from": "USD", "to": "EUR", "amount": 1 }
```

**Response:** `{ "success": true, "result": 0.8687 }` (rate × amount)

On network failure: `{ "success": false, "error": "Currency service unreachable" }`

### `POST /api/datetime`

Date math operations.

```json
{ "op": "diff", "a": "2024-01-01", "b": "2024-02-01" }
```

**Response:** `{ "success": true, "result": { "days": 31, "weeks": 4, … } }`

Operations: `diff`, `add`, `weekday`, `age`

### `POST /api/stats`

Dataset statistics.

```json
{ "data": [2, 4, 4, 4, 5, 5, 7, 9] }
```

**Response:** `{ "success": true, "result": { "mean": 5.0, "median": 4.5, "mode": 4.0, … } }`

### `POST /api/solve`

Solve equations.

**Polynomial (degree 1 or 2):**
```json
{ "type": "poly", "coeffs": [1, -3, 2] }
```
→ `{ "success": true, "roots": [2.0, 1.0], "discriminant": 1 }`

**Linear system (Ax = b):**
```json
{ "type": "system", "A": [[2, 1], [1, -1]], "b": [5, 1] }
```
→ `{ "success": true, "roots": [2.0, 1.0] }`

### `POST /api/matrix`

Matrix operations.

```json
{ "op": "det", "a": [[1, 2], [3, 4]] }
```
→ `{ "success": true, "result": -2.0 }`

Operations: `add`, `sub`, `mul`, `det`, `inv`, `transpose`, `solve`

### `POST /api/base`

Parse and convert between bases.

```json
{ "value": "0xFF" }
```
→ `{ "success": true, "dec": 255, "hex": "FF", "oct": "377", "bin": "11111111" }`

### `GET /api/health`

```json
{ "status": "ok", "engine": "v2.0" }
```

---

## 🛡️ How It Works (no eval)

`app.py` contains a clean **tokenizer → recursive-descent parser** with proper operator precedence:

```
expr   → term (('+'|'-') term)*
term   → factor (('*'|'/'|'%') factor)*
factor → unary ('^' factor)?        # right-assoc power
unary  → ('+'|'-') unary | postfix
postfix→ primary ('!')*              # factorial
primary→ NUMBER | CONST | VAR | FUNC '(' args ')' | '(' expr ')' | implicit-mul
```

This guarantees that arbitrary code can **never** be executed through the calculator — only the whitelisted math functions, operators, and user-defined numeric constants (variables) are parsed and evaluated. The security guarantee holds even with named variables and the tools drawer.

---

## 🎨 Design

- **Palette:** deep-space navy backdrop with teal `#5eead4`, violet `#a78bfa`, cyan `#67e8f9`, and pink `#f9a8d4` accents.
- **Typography:** `Orbitron` for headings/results, `JetBrains Mono` for expressions, `Outfit` for body.
- **Motion:** floating aurora blobs + interactive particle network canvas + ripple feedback on every key.
- **Themes:** Dark (default) and Light — persisted via localStorage.

---

## 📝 License

MIT — free to use, modify, and share. Built as a demonstration of a safe Python math engine paired with an eye-catching web front end.

---

<div align="center">

### Made with ❤️ by **Raheel Nadeem**

</div>
