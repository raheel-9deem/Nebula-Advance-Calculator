# 🌌 Nebula — Advanced Scientific Calculator

A striking, fully-functional **Advanced Scientific Calculator** built with **Python + Flask** and a custom **glassmorphism / neon** web UI. No `eval()`, no `exec()` — every expression is parsed by a hand-written recursive-descent parser, so only safe, well-formed math is ever executed.

![tech](https://img.shields.io/badge/Python-3.10+-blue) ![tech](https://img.shields.io/badge/Flask-3.x-black) ![tech](https://img.shields.io/badge/UI-Glassmorphism-violet)

---

## ✨ Features

### Engine
- **Arithmetic:** `+  -  *  /  %  ^` (power, right-associative: `2^3^2 = 2^(3^2)`)
- **Trigonometry:** `sin cos tan`, inverses `asin acos atan`, hyperbolic `sinh cosh tanh asinh acosh atanh`
- **Logarithms:** `ln` (natural), `log` (base-10), `exp`, `10^x`
- **Roots:** `sqrt`, `cbrt`
- **Factorial:** `x!` (e.g. `5!`), **Permutations / Combinations:** `nPr`, `nCr`
- **Sequence operators:** `sum(expr, a, b)`, `prod(expr, a, b)`, and numerical `lim(expr, x0, approach, direction)`
- **Constants:** `pi`, `e`, `tau`, `inf`
- **Absolute value:** `|x|` via `abs()`
- **Degree / Radian mode** toggle (affects all trig functions)
- **Implicit multiplication:** `2pi`, `3(4+1)`, `2sin(30)`
- **Error handling:** divide-by-zero, domain errors, malformed expressions — all surfaced cleanly

### Number Formats (NEW)
After computing a result, tap any format button in the format bar to convert it instantly:
- **DMS** — degrees / minutes / seconds (`45.5` → `45°30'0"`)
- **FRAC** — reduced fraction via continued fractions (`0.5` → `1/2`)
- **HEX / OCT / BIN** — base-N conversion (`255` → `FF` / `377` / `11111111`)
- **ROMAN** — Roman numerals (`2024` → `MMXXIV`)

### UI
- Animated **aurora background** + live **particle constellation**
- **Glassmorphism** calculator shell with neon accent gradients and gradient borders
- Smart **display** with live expression + rainbow-gradient result and inner glow
- **Redesigned keypad** — a clean scientific pad (5-column grid) alongside a phone-style basic numpad
- Color-coded key groups: teal (functions), amber (inverse), cyan (constants), pink (memory), yellow (utilities), blue (operators)
- **Format bar** with DMS / FRAC / HEX / OCT / BIN / ROMAN conversion buttons
- **DEG / RAD** mode switch
- **Memory** functions: `MC MR M+ M−`
- Persistent **history** panel (saved to localStorage, click to reuse a result)
- **Keyboard support** — type expressions directly; `Ctrl/Cmd+C` copies the expression
- Press **=** to compute via Flask API (fetch)
- Fully **responsive & scrollable** — works on desktop and mobile

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or newer

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

---

## 🧭 Usage

| You want to… | Type / click |
|---|---|
| Sine of 30° | `sin(30)` and press `=` |
| 2 to the power 10 | `2^10` |
| Factorial of 6 | `6!` |
| Natural log of 100 | `ln(100)` |
| Square root | `sqrt(144)` |
| Permutations ₈P₃ | `npr(8,3)` |
| Combinations ₈C₃ | `ncr(8,3)` |
| Sum of squares 1..5 | `sum(x^2, 1, 5)` → `55` |
| Use π | `sin(pi/2)` or `2*pi` |
| Modulo | `10%3` |
| Convert 255 to hex | `255` → `=` → tap **HEX** → `FF` |
| Convert 0.5 to fraction | `0.5` → `=` → tap **FRAC** → `1/2` |
| Store 5 in memory | `5` → `M+`, then `MR` to recall |

Switch **DEG / RAD** from the top-right toggle.

---

## 🗂️ Project Structure

```
Advance-Scientific-Calculator-cc/
├── app.py                 # Calculator engine (parser) + Flask web server + format API
├── requirements.txt       # Python dependencies
├── README.md
├── templates/
│   └── index.html         # Calculator UI markup (keypad, format bar, display)
└── static/
    ├── css/
    │   └── style.css      # Glassmorphism/neon theme + responsive layout
    └── js/
        └── app.js         # Keypad logic, history, format calls, particles
```

---

## 🔌 API

The calculator exposes two endpoints.

**`POST /api/calculate`**
```json
{ "expression": "sin(30) + 2^3", "deg": true }
```
Response (success):
```json
{ "success": true, "expression": "sin(30) + 2^3", "result": "3.5", "mode": "DEG" }
```
Response (error):
```json
{ "success": false, "error": "Math error: division by zero" }
```

**`POST /api/format`** — convert a number into DMS / fraction / base-N / Roman
```json
{ "number": 255, "format": "hex", "deg": false }
```
Response:
```json
{ "success": true, "format": "hex", "formatted": "FF", "original": 255.0 }
```

`GET /` serves the UI · `GET /api/health` returns `{ "status": "ok", "engine": "v1.0" }`.

---

## 🛡️ How It Works (no eval)

`app.py` contains a clean **tokenizer → recursive-descent parser** with proper operator precedence:

```
expr   → term (('+'|'-') term)*
term   → factor (('*'|'/'|'%') factor)*
factor → unary ('^' factor)?        # right-assoc power
unary  → ('+'|'-') unary | postfix
postfix→ primary ('!')*              # factorial
primary→ NUMBER | CONST | FUNC '(' args ')' | '(' expr ')' | implicit-mul
```

This guarantees that arbitrary code can **never** be executed through the calculator — only the whitelisted math functions and operators are parsed and evaluated.

---

## 🎨 Design

- **Palette:** deep-space navy backdrop with teal `#5eead4`, violet `#a78bfa`, cyan `#67e8f9`, and pink `#f9a8d4` accents.
- **Typography:** `Orbitron` for headings/results, `JetBrains Mono` for expressions, `Outfit` for body.
- **Motion:** floating aurora blobs + interactive particle network canvas + ripple feedback on every key.

---

## 📝 License

MIT — free to use, modify, and share. Built as a demonstration of a safe Python math engine paired with an eye-catching web front end.

---

<div align="center">

### Made with ❤️ by **Raheel Nadeem**

</div>
