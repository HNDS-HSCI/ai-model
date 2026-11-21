"""Quantitative reasoning: formulas, quantities, arithmetic and equation solving.

Formulas are *knowledge*, taught in English ("force equals mass times acceleration")
or symbols ("F = m * a"); nothing about physics is in this code. To answer "what is
the force?" the solver chains any formulas whose unknowns can be filled from known
quantities (forward search over equations), solves each step with SymPy, then
verifies the whole chain by substituting every value back into every equation used.

User text never reaches ``eval``: expressions are tokenised, every name is mapped to
an opaque ``v<N>`` placeholder, and the result is checked against a strict character
whitelist before SymPy parses it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                        parse_expr, standard_transformations)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_SAFE = re.compile(r"^[0-9v\s\.\+\-\*/\^\(\)]*$")
_NUMBER = r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?"

# Ordered longest-first so "divided by" wins over "by", etc.
_OP_WORDS = [
    (r"\bto the power of\b", "^"), (r"\braised to\b", "^"), (r"\bmultiplied by\b", "*"),
    (r"\bdivided by\b", "/"), (r"\btimes\b", "*"), (r"\bplus\b", "+"), (r"\bminus\b", "-"),
    (r"\bover\b", "/"), (r"\bsquared\b", "^2"), (r"\bcubed\b", "^3"),
    (r"\bhalf of\b", "0.5*"), (r"\bhalf\b", "0.5*"), (r"\btwice\b", "2*"), (r"\bthe product of\b", ""),
    (r"\b(?:the\s+)?square root of\b", "sqrt"),
]
_FILLER = {"the", "a", "an", "its", "their", "his", "her", "and"}
_EDGE_FILLER = _FILLER | {"of"}   # "of" is kept inside names ("speed of light") but not at the edges
_QUESTION_LEAD = re.compile(
    r"^(?:what\s+is|what's|whats|calculate|compute|evaluate|work\s+out|find|solve(?:\s+for\s+[a-z])?|"
    r"simplify|how\s+much\s+is)\s+", re.I)


def words_to_ops(text: str) -> str:
    out = text
    for pat, sym in _OP_WORDS:
        out = re.sub(pat, f" {sym} ", out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def norm_name(name: str) -> str:
    words = [w.split("'")[0] for w in re.findall(r"[a-z][a-z0-9_']*", name.lower()) if w not in _FILLER]
    while words and words[0] in _EDGE_FILLER:
        words.pop(0)
    while words and words[-1] in _EDGE_FILLER:
        words.pop()
    return " ".join(words)


@dataclass
class Formula:
    target: str
    expr: str                    # RHS with names wrapped as {name}
    names: List[str]
    text: str = ""
    formula_id: int = 0

    @property
    def variables(self) -> List[str]:
        return [self.target] + [n for n in self.names if n != self.target]

    def sympy_eq(self, symbols: Dict[str, sympy.Symbol]) -> sympy.Eq:
        rhs = _compile(self.expr, symbols)
        symbols.setdefault(self.target, sympy.Symbol(re.sub(r"\W+", "_", self.target) or "q"))
        return sympy.Eq(symbols[self.target], rhs)


@dataclass
class Quantity:
    name: str
    value: float
    unit: Optional[str] = None
    source: str = ""


@dataclass
class SolveStep:
    quantity: str
    value: float
    unit: Optional[str]
    formula: Formula
    inputs: Dict[str, float]


@dataclass
class QuantityAnswer:
    name: str
    value: float
    unit: Optional[str]
    steps: List[SolveStep] = field(default_factory=list)
    given: bool = False
    verified: bool = False
    residual: float = 0.0
    givens_used: List[Quantity] = field(default_factory=list)


def _compile(expr: str, symbols: Dict[str, sympy.Symbol]):
    """Compiles an expression whose names are written as {name} into SymPy, safely."""
    mapping: Dict[str, sympy.Symbol] = {}

    def sub(m: re.Match) -> str:
        key = f"v{len(mapping)}"
        name = m.group(1)
        symbols.setdefault(name, sympy.Symbol(re.sub(r"\W+", "_", name) or "q"))
        mapping[key] = symbols[name]
        return f" {key} "

    placeholder = re.sub(r"\{([^{}]+)\}", sub, expr)
    if not _SAFE.match(placeholder) or len(placeholder) > 400:
        raise ValueError(f"unsafe or unsupported expression: {expr!r}")
    return parse_expr(placeholder, local_dict=dict(mapping), global_dict=_GLOBALS, transformations=_TRANSFORMS)


_GLOBALS = {"Integer": sympy.Integer, "Float": sympy.Float, "Rational": sympy.Rational,
            "Symbol": sympy.Symbol, "Mul": sympy.Mul, "Add": sympy.Add, "Pow": sympy.Pow}


def _tokenise_rhs(rhs: str) -> Optional[Tuple[str, List[str]]]:
    """Turns 'mass * acceleration' into ('{mass} * {acceleration}', [names])."""
    rhs = words_to_ops(rhs)
    parts = re.split(r"([\+\-\*/\^\(\)])", rhs)
    out, names = [], []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        if p in "+-*/^()":
            out.append(p)
        elif re.fullmatch(_NUMBER, p):
            out.append(p)
        else:
            m = re.fullmatch(rf"({_NUMBER})\s*([a-zA-Z].*)", p)  # "0.5 mass" / "2x"
            coef = None
            if m:
                coef, p = m.group(1), m.group(2)
            name = norm_name(p)
            if not name:
                return None
            if coef:
                out.extend([coef, "*"])
            out.append("{" + name + "}")
            if name not in names:
                names.append(name)
    return " ".join(out), names


def parse_formula(text: str) -> Optional[Formula]:
    """'force equals mass times acceleration' / 'speed = distance / time' / 'F = m*a'."""
    t = text.strip().rstrip(".!")
    m = re.match(r"^(.+?)\s*(?:=|\bequals\b|\bis equal to\b|\bis defined as\b|\bis\b)\s*(.+)$", t, re.I)
    if not m:
        return None
    lhs, rhs = m.group(1), m.group(2)
    if re.search(r"\d", lhs) or not re.search(r"[\+\-\*/\^]|\b(?:times|divided by|multiplied by|plus|minus|over|squared|cubed|half|twice|to the power of)\b", rhs, re.I):
        return None
    if re.search(rf"^\s*{_NUMBER}\s*[a-zA-Z/]*\s*$", rhs):  # "mass is 10 kg" is a quantity
        return None
    target = norm_name(lhs)
    tok = _tokenise_rhs(rhs)
    if not target or not tok:
        return None
    expr, names = tok
    if not names or len(target.split()) > 4 or any(len(n.split()) > 4 for n in names):
        return None
    # A formula needs two operands written by the user: "klat plus 8" is one, but
    # "Bob is half asleep" (a lone name plus an implied coefficient) is not.
    operands = len(names) + len(re.findall(_NUMBER, rhs))
    if operands < 2 and not re.search(r"\b(?:squared|cubed)\b|\^", rhs):
        return None
    f = Formula(target, expr, names, text=text.strip())
    try:
        f.sympy_eq({})
    except Exception:
        return None
    return f


_UNIT = r"(?:[a-zA-Z°µ][a-zA-Z°µ0-9/\^\*\.\-]*)"


def parse_quantity(text: str) -> Optional[Quantity]:
    """'The mass is 10 kg' / 'mass = 10' / 'the car has a mass of 1200 kg'."""
    t = text.strip().rstrip(".!?")
    patterns = [
        rf"^(.+?)\s*(?:=|\bequals\b|\bis\b|\bwas\b|\bof\b)\s*({_NUMBER})\s*({_UNIT})?$",
        rf"^.+?\b(?:has|have|had)\s+(?:a|an)\s+(.+?)\s+of\s+({_NUMBER})\s*({_UNIT})?$",
    ]
    for p in patterns:
        m = re.match(p, t, re.I)
        if m:
            raw_name = m.group(1)
            if "'s" in raw_name:
                raw_name = raw_name.split("'s", 1)[1]
            name = norm_name(raw_name)
            if not name or len(name.split()) > 4 or re.search(r"[\+\*/\^=]", raw_name):
                return None
            unit = m.group(3)
            if unit and unit.lower() in {"and", "if", "then", "what", "is"}:
                return None
            return Quantity(name, float(m.group(2)), unit, text.strip())
    return None


def _unit_expr(unit: Optional[str], symbols: Dict[str, sympy.Symbol]):
    if not unit:
        return None
    u = re.sub(r"([a-zA-Z]+)(\d+)", r"\1^\2", unit)  # s2 -> s^2
    expr = re.sub(r"[a-zA-Zµ°]+", lambda m: "{" + m.group(0) + "}", u)
    try:
        return _compile(expr, symbols)
    except Exception:
        return None


def _fmt_unit(expr) -> Optional[str]:
    if expr is None or expr.free_symbols == set():
        return None
    _, core = expr.as_coeff_Mul()
    if isinstance(core, sympy.Add):
        return None
    return str(core).replace("**", "^")


def solve_for(target: str, formulas: List[Formula], knowns: Dict[str, Quantity]) -> Optional[QuantityAnswer]:
    """Forward-chains over formulas until ``target`` is known, then verifies the chain."""
    if target in knowns:
        q = knowns[target]
        return QuantityAnswer(target, q.value, q.unit, given=True, verified=True, givens_used=[q])
    values: Dict[str, float] = {k: q.value for k, q in knowns.items()}
    units: Dict[str, Optional[str]] = {k: q.unit for k, q in knowns.items()}
    steps: List[SolveStep] = []
    progress = True
    while progress and target not in values:
        progress = False
        for f in formulas:
            unknown = [v for v in f.variables if v not in values]
            if len(unknown) != 1:
                continue
            u = unknown[0]
            syms: Dict[str, sympy.Symbol] = {}
            try:
                eq = f.sympy_eq(syms)
                sols = sympy.solve(eq.subs({syms[k]: values[k] for k in f.variables if k in values}), syms[u])
            except Exception:
                continue
            real = [complex(s) for s in sols if s.is_number]
            real = [r.real for r in real if abs(r.imag) < 1e-12]
            if not real:
                continue
            val = max(real) if len(real) > 1 else real[0]  # physical quantities: prefer the positive root
            values[u] = val
            units[u] = _derive_unit(f, u, units)
            steps.append(SolveStep(u, val, units[u], f, {k: values[k] for k in f.variables if k != u}))
            progress = True
            if u == target:
                break
    if target not in values:
        return None
    used = {k for s in steps for k in s.inputs}
    residual = _check(steps, values)
    return QuantityAnswer(target, values[target], units.get(target), steps, verified=residual < 1e-6,
                          residual=residual, givens_used=[q for k, q in knowns.items() if k in used])


def _derive_unit(f: Formula, unknown: str, units: Dict[str, Optional[str]]) -> Optional[str]:
    syms: Dict[str, sympy.Symbol] = {}
    try:
        eq = f.sympy_eq(syms)
        subs = {}
        for v in f.variables:
            if v == unknown:
                continue
            ue = _unit_expr(units.get(v), {})
            if ue is None:
                return None
            subs[syms[v]] = ue
        sol = sympy.solve(eq.subs(subs), syms[unknown])
        return _fmt_unit(sympy.simplify(sol[0])) if sol else None
    except Exception:
        return None


def _check(steps: List[SolveStep], values: Dict[str, float]) -> float:
    """Max relative residual after substituting all values into every formula used."""
    worst = 0.0
    for s in steps:
        syms: Dict[str, sympy.Symbol] = {}
        eq = s.formula.sympy_eq(syms)
        lhs = float(eq.lhs.subs({syms[k]: values[k] for k in s.formula.variables}))
        rhs = float(eq.rhs.subs({syms[k]: values[k] for k in s.formula.variables}))
        worst = max(worst, abs(lhs - rhs) / max(1.0, abs(lhs)))
    return worst


# --------------------------------------------------------------------- arithmetic

@dataclass
class MathResult:
    kind: str                 # "evaluate" | "solve"
    expression: str
    answer: str
    values: List[str]
    verified: bool
    detail: str = ""


def detect_math(text: str) -> Optional[str]:
    """Returns the bare math expression if the sentence is pure arithmetic/algebra."""
    t = text.strip().rstrip("?.!")
    t = _QUESTION_LEAD.sub("", t)
    t = words_to_ops(t)
    t = t.replace("×", "*").replace("÷", "/").replace("−", "-")
    if not re.search(r"\d", t) or not re.search(r"[\+\-\*/\^=]|sqrt", t):
        return None
    if re.search(r"[a-z]{2,}", t.lower().replace("sqrt", "")):
        return None
    if not re.fullmatch(r"[0-9a-z\s\.\+\-\*/\^\(\)=]+", t.lower().replace("sqrt", "")):
        return None
    return t


def _parse_algebra(expr: str):
    letters = sorted(set(re.findall(r"[a-z]", expr.replace("sqrt", ""))))
    local = {ch: sympy.Symbol(ch) for ch in letters}
    local["sqrt"] = sympy.sqrt
    if not re.fullmatch(r"[0-9a-z\s\.\+\-\*/\^\(\)]+", expr) or len(expr) > 300:
        raise ValueError("unsupported expression")
    return parse_expr(expr, local_dict=local, global_dict=_GLOBALS, transformations=_TRANSFORMS), local


def _fmt(v) -> str:
    v = sympy.nsimplify(v, rational=False) if isinstance(v, sympy.Float) else v
    if v.is_Integer:
        return str(int(v))
    if v.is_Rational:
        return f"{v} (≈ {float(v):.6g})"
    if v.is_number:
        c = complex(v)
        return f"{c.real:.10g}" if abs(c.imag) < 1e-12 else str(sympy.N(v, 8))
    return str(v)


def solve_math(expr: str) -> MathResult:
    expr = expr.lower()
    if "=" in expr:
        lhs_s, rhs_s = expr.split("=", 1)
        lhs, local = _parse_algebra(lhs_s)
        rhs, local2 = _parse_algebra(rhs_s)
        syms = sorted((lhs - rhs).free_symbols, key=lambda s: s.name)
        if not syms:
            ok = sympy.simplify(lhs - rhs) == 0
            return MathResult("check", expr, "true" if ok else "false", [], True)
        var = sympy.Symbol("x") if sympy.Symbol("x") in syms else syms[0]
        sols = sympy.solve(sympy.Eq(lhs, rhs), var)
        verified = all(sympy.simplify((lhs - rhs).subs(var, s)) == 0 for s in sols) if sols else False
        vals = [_fmt(s) for s in sols]
        ans = f"{var} = " + (" or ".join(vals) if vals else "no solution")
        return MathResult("solve", expr, ans, vals, verified,
                          "each solution substituted back into the equation gives 0 = 0" if verified else "")
    e, _ = _parse_algebra(expr)
    val = sympy.simplify(e)
    return MathResult("evaluate", expr, _fmt(val), [_fmt(val)], True, "exact symbolic evaluation")
