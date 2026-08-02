"""Nebula Calculator — converters, currency, and date/time helpers.

Kept in a separate module so app.py stays focused on the math engine.
No third-party dependencies: stdlib only (urllib for the currency fetch).
"""
from __future__ import annotations

import math
import time
import urllib.request
import urllib.error
import json as _json
from datetime import datetime, date, timedelta

# ---------------------------------------------------------------------------
# Unit conversion tables.
#
# Each category maps unit name -> (factor_to_base, canonical_name).
# value_in_base = value * factor_to_base; to convert out: value * (base_factor/factor).
# Temperature is handled specially (offset, not factor).
# ---------------------------------------------------------------------------

UNITS: dict[str, dict[str, float]] = {
    "length": {
        "m": 1.0, "meter": 1.0, "meters": 1.0,
        "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
        "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
        "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
        "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
        "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
        "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
        "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
        "nmi": 1852.0, "nautical mile": 1852.0,
    },
    "mass": {
        "kg": 1.0, "kilogram": 1.0, "kilograms": 1.0,
        "g": 0.001, "gram": 0.001, "grams": 0.001,
        "mg": 1e-6, "milligram": 1e-6,
        "lb": 0.45359237, "pound": 0.45359237, "pounds": 0.45359237,
        "oz": 0.45359237 / 16, "ounce": 0.45359237 / 16, "ounces": 0.45359237 / 16,
        "ton": 1000.0, "tonne": 1000.0, "metric ton": 1000.0,
        "stone": 0.45359237 * 14,
    },
    "time": {
        "s": 1.0, "second": 1.0, "seconds": 1.0,
        "ms": 0.001, "millisecond": 0.001,
        "min": 60.0, "minute": 60.0, "minutes": 60.0,
        "h": 3600.0, "hour": 3600.0, "hours": 3600.0,
        "day": 86400.0, "days": 86400.0,
        "week": 604800.0, "weeks": 604800.0,
        "year": 31557600.0, "years": 31557600.0,  # Julian year
    },
    "area": {
        "m2": 1.0, "sq m": 1.0, "square meter": 1.0,
        "km2": 1e6, "sq km": 1e6,
        "cm2": 1e-4, "mm2": 1e-6,
        "ha": 1e4, "hectare": 1e4,
        "acre": 4046.8564224, "acres": 4046.8564224,
        "ft2": 0.09290304, "sq ft": 0.09290304,
        "in2": 0.00064516, "sq in": 0.00064516,
        "mi2": 2589988.110336, "sq mi": 2589988.110336,
    },
    "volume": {
        "l": 0.001, "liter": 0.001, "liters": 0.001,
        "ml": 1e-6, "milliliter": 1e-6,
        "m3": 1.0, "cubic meter": 1.0,
        "cm3": 1e-6, "cc": 1e-6,
        "gal": 0.003785411784, "gallon": 0.003785411784, "gallons": 0.003785411784,
        "qt": 0.000946352946, "quart": 0.000946352946, "quarts": 0.000946352946,
        "pt": 0.000473176473, "pint": 0.000473176473, "pints": 0.000473176473,
        "cup": 0.0002365882365, "cups": 0.0002365882365,
        "floz": 2.95735295625e-5, "fl oz": 2.95735295625e-5,
    },
    "speed": {
        "m/s": 1.0, "mps": 1.0,
        "km/h": 0.2777777777777778, "kph": 0.2777777777777778,
        "mph": 0.44704, "mi/h": 0.44704,
        "ft/s": 0.3048, "fps": 0.3048,
        "knot": 0.5144444444444445, "kn": 0.5144444444444445,
    },
    "data": {  # base = bytes
        "b": 1.0, "byte": 1.0, "bytes": 1.0,
        "kb": 1000.0, "kilobyte": 1000.0,
        "mb": 1e6, "megabyte": 1e6,
        "gb": 1e9, "gigabyte": 1e9,
        "tb": 1e12, "terabyte": 1e12,
        "kib": 1024.0, "mib": 1024.0 ** 2,
        "gib": 1024.0 ** 3, "tib": 1024.0 ** 4,
    },
}


def convert_unit(category: str, from_unit: str, to_unit: str, value: float) -> float:
    """Convert a value between two units in the same category."""
    cat = UNITS.get(category.lower())
    if not cat:
        raise ValueError(f"Unknown category: {category}")
    f_unit = from_unit.lower().strip()
    t_unit = to_unit.lower().strip()
    if f_unit not in cat:
        raise ValueError(f"Unknown unit in {category}: {from_unit}")
    if t_unit not in cat:
        raise ValueError(f"Unknown unit in {category}: {to_unit}")
    return float(value) * cat[f_unit] / cat[t_unit]


def convert_temperature(from_unit: str, to_unit: str, value: float) -> float:
    """Temperature conversion: C, F, K."""
    f_unit = from_unit.lower().strip()
    t_unit = to_unit.lower().strip()
    v = float(value)
    # normalize to Celsius first
    if f_unit in ("c", "celsius", "degc"):
        c = v
    elif f_unit in ("f", "fahrenheit", "degf"):
        c = (v - 32) * 5.0 / 9.0
    elif f_unit in ("k", "kelvin"):
        c = v - 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")
    if t_unit in ("c", "celsius", "degc"):
        return c
    if t_unit in ("f", "fahrenheit", "degf"):
        return c * 9.0 / 5.0 + 32
    if t_unit in ("k", "kelvin"):
        return c + 273.15
    raise ValueError(f"Unknown temperature unit: {to_unit}")


def categories() -> list[str]:
    """Return the list of unit categories (including temperature)."""
    return list(UNITS.keys()) + ["temperature"]


def units_in(category: str) -> list[str]:
    if category.lower() == "temperature":
        return ["c", "f", "k"]
    cat = UNITS.get(category.lower())
    if not cat:
        return []
    # dedupe aliased names while preserving meaningful short forms first
    seen = set()
    out = []
    for u in cat.keys():
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ---------------------------------------------------------------------------
# Currency conversion (live rates, no API key, 1-hour cache)
# ---------------------------------------------------------------------------

_FX_CACHE: dict[str, tuple[float, float]] = {}  # base_ccy -> (rates_dict, fetched_at)
_FX_TTL = 3600.0  # seconds


def _fetch_rates(base: str) -> dict[str, float]:
    """Fetch live exchange rates relative to `base`. Free, no key."""
    url = f"https://open.er-api.com/v6/latest/{base.upper()}"
    req = urllib.request.Request(url, headers={"User-Agent": "NebulaCalc/2.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        payload = _json.loads(resp.read().decode("utf-8"))
    if not payload.get("rates"):
        raise ValueError("currency service returned no rates")
    return payload["rates"]


def currency_rate(from_ccy: str, to_ccy: str) -> float:
    """Return how many `to_ccy` one unit of `from_ccy` buys. Cached 1h."""
    fc = from_ccy.upper()
    tc = to_ccy.upper()
    if fc == tc:
        return 1.0
    now = time.time()
    cached = _FX_CACHE.get(fc)
    rates = None
    if cached and (now - cached[1]) < _FX_TTL:
        rates = cached[0]
    if rates is None:
        rates = _fetch_rates(fc)
        _FX_CACHE[fc] = (rates, now)
    if tc not in rates:
        raise ValueError(f"No rate for {to_ccy}")
    return float(rates[tc])


def convert_currency(from_ccy: str, to_ccy: str, amount: float) -> float:
    return float(amount) * currency_rate(from_ccy, to_ccy)


# ---------------------------------------------------------------------------
# Date / time helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {s} (use YYYY-MM-DD)")


def date_diff(a: str, b: str) -> dict:
    d1 = _parse_date(a)
    d2 = _parse_date(b)
    delta = (d2 - d1).days
    return {
        "days": abs(delta),
        "weeks": abs(int(delta / 7)),
        "months": int(abs(delta) / 30.4375),
        "years": round(abs(delta) / 365.25, 2),
        "sign": "future" if delta >= 0 else "past",
    }


def add_days(d: str, days: int) -> str:
    base = _parse_date(d)
    return (base + timedelta(days=days)).strftime("%Y-%m-%d")


def weekday(d: str) -> str:
    return _parse_date(d).strftime("%A")


def age(birth: str, on: str | None = None) -> dict:
    b = _parse_date(birth)
    ref = _parse_date(on) if on else date.today()
    years = ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))
    return {"years": years, "days": (ref - b).days}
