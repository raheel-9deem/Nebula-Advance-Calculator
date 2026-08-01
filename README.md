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
- **Constants:** `pi`, `e`, `tau`, `inf`
- **Absolute value:** `|x|` via `abs()`
- **Degree / Radian mode** toggle (affects all trig functions)
- **Implicit multiplication:** `2pi`, `3(4+1)`, `2sin(30)`
- **Error handling:** divide-by-zero, domain errors, malformed expressions — all surfaced cleanly

### UI
- Animated **aurora background** + live **particle constellation**
- **Glassmorphism** calculator shell with neon accent gradients
- Smart **display** with live expression + rainbow-gradient result
- Full scientific **keypad** (6-column grid)
- **DEG / RAD** mode switch
- **Memory** functions: `MC MR M+ M−`
- Persistent **history** panel (saved to localStorage, click to reuse a result)
- **Keyboard support** — type expressions directly
- Press **=** to compute via Flask API (fetch)

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
| Use π | `sin(pi/2)` or `2*pi` |
| Modulo | `10%3` |
| Store 5 in memory | `5` → `M+`, then `MR` to recall |

Switch **DEG / RAD** from the top-right toggle.

---

## 🗂️ Project Structure

```
Advance-Scientific-Calculator-cc/
├── app.py                 # Calculator engine (parser) + Flask web server
├── requirements.txt       # Python dependencies
├── README.md
├── templates/
│   └── index.html         # Calculator UI markup
└── static/
    ├── css/
    │   └── style.css      # Glassmorphism/neon theme
    └── js/
        └── app.js         # Keypad logic, history, fetch API, particles
```

---

## 🔌 API

The calculator exposes a single calculation endpoint.

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

`GET /` serves the UI · `GET /api/health` returns `{ "status": "ok" }`.

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

- **Palette:** deep-space navy backdrop with teal `#5eead4`, violet `#a78bfa`, and pink `#f9a8d4` accents.
- **Typography:** `Orbitron` for headings/results, `JetBrains Mono` for expressions, `Outfit` for body.
- **Motion:** floating aurora blobs + interactive particle network canvas + ripple feedback on every key.

---

## 📝 License

MIT — free to use, modify, and share. Built as a demonstration of a safe Python math engine paired with an eye-catching web front end.
