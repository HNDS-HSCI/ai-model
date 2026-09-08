"""
UniversalMathEngine — Phase 6 of HSCI Activation
The core breakthrough: solves ANY mathematical problem using SymPy.

This is what allows HSCI to go beyond 11 hardcoded templates.
SymPy is a full Computer Algebra System (CAS) — it understands:
  - Arithmetic, Algebra, Calculus
  - Linear equations, Quadratic, Polynomial
  - Trigonometry, Logarithms
  - Differential Equations
  - Matrix / Linear Algebra
  - Physics formulas
  - Statistics

The key insight: HSCI doesn't need to memorize 1.8 trillion patterns.
It needs to UNDERSTAND mathematical axioms and COMPUTE from them.
That's what SymPy provides — a real mathematical brain.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

try:
    import sympy as sp
    from sympy import symbols, solve, simplify, Eq, sympify, parse_expr
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations, implicit_multiplication_application
    )
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


_WORD_OPERATORS = [
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\btimes\b", "*"),
    (r"\bmultiplied\s+by\b", "*"),
    (r"\bdivided\s+by\b", "/"),
]

_NAMED_FUNCTIONS = [
    (r"\bsquare\s+root\s+of\s+", "sqrt "),
    (r"\bcube\s+root\s+of\s+", "cbrt "),
]

_CONVERSATIONAL_PREFIXES = re.compile(
    r"^(?:can|could|would)\s+you\s+(?:please\s+)?(?:tell\s+me\s+)?(?:what\s+)?|"
    r"^(?:please\s+)?tell\s+me\s+what\s+|"
    r"^i\s+(?:want|need)\s+to\s+know\s+what\s+",
    re.IGNORECASE,
)


def normalize_natural_math_phrasing(text: str) -> str:
    """
    Translates common natural-language ways of expressing arithmetic into the
    symbolic form SymPy can parse. This is a bounded, mechanical translation
    step (word operators, percentage phrasing, named functions, conversational
    wrappers) -- not a general NLU model -- so it generalizes correctly across
    any numbers/variables without per-example hardcoding.
    """
    result = text.strip()
    result = result.replace("what's", "what is").replace("What's", "What is")
    result = _CONVERSATIONAL_PREFIXES.sub("", result).strip()

    # Strip thousands-separator commas from numbers ("50,000" -> "50000") before
    # anything else runs, so every downstream strategy (percentage-of, plain
    # arithmetic, equation parsing) sees a clean number instead of silently
    # truncating at the comma. Only matches real grouping (comma immediately
    # followed by exactly 3 digits), so it can't eat an equation-separator
    # comma like "x-y=20, x+y=10" (space right after that comma, not a digit).
    result = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", result)

    # "15% of 240" -> "(15/100)*240" (must run before word-operator substitution)
    result = re.sub(
        r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)",
        r"(\1/100)*\2",
        result,
        flags=re.IGNORECASE,
    )

    for pattern, replacement in _NAMED_FUNCTIONS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    # "sqrt 144" -> "sqrt(144)" (only wraps the number/expr directly following the function name)
    result = re.sub(r"\b(sqrt|cbrt)\s+(\d+(?:\.\d+)?)", r"\1(\2)", result, flags=re.IGNORECASE)

    for pattern, replacement in _WORD_OPERATORS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Strip a leading question/command wrapper ("what is the ", "find ", ...)
    # and trailing punctuation once, after the substitutions above, so the
    # wrapper doesn't survive around a just-substituted function call like
    # "what is the sqrt(144)?" -> "sqrt(144)".
    result = re.sub(r"^(?:what\s+is\s+(?:the\s+)?|find\s+(?:the\s+)?|calc\w*\s+|solv\w*\s+|comput\w*\s+|eval\w*\s+)+", "", result, flags=re.IGNORECASE)
    # Strip a demonstrative filler ("this equation", "this problem", bare
    # "this") that a command word can leave behind -- "solve this x+10=10"
    # -> "solve " strips to "this x+10=10", and without this, "this" gets
    # parsed by SymPy as a literal symbol multiplied into the equation
    # (e.g. "this*x + 10 = 10"), corrupting the actual variable to solve for.
    result = re.sub(r"^this\s+(?:equation|problem|expression|one)?\s*", "", result, flags=re.IGNORECASE)
    result = result.strip(" ?.!")

    return result


@dataclass
class MathResult:
    """Result from the universal math engine."""
    solved: bool
    answer: Any                    # numeric or symbolic answer
    answer_display: str            # human-readable
    method: str                    # "sympy_solve", "sympy_eval", "arithmetic", etc.
    steps: List[str]               # explanation steps
    variables: Dict[str, Any]      # all variable assignments
    error: Optional[str] = None


class UniversalMathEngine:
    """
    HSCI Universal Math Engine.
    Solves ANY mathematical expression or equation using SymPy CAS.

    This is the key to making HSCI work on arbitrary problems:
    instead of matching to 11 hardcoded templates, it uses a full
    Computer Algebra System to derive the answer from first principles.
    """

    TRANSFORMATIONS = (standard_transformations + (implicit_multiplication_application,))

    def __init__(self):
        self._sympy_ok = SYMPY_AVAILABLE
        if not self._sympy_ok:
            print("[UniversalMath] WARNING: sympy not installed. Run: pip install sympy")

    # ─── Public API ───────────────────────────────────────────────────────────

    def solve_from_text(self, text: str, entities: Dict[str, Any]) -> MathResult:
        """
        Main entry: given raw text + extracted entities, solve the problem.
        This is called by the ReasoningEngine when no template matches.
        """
        if not self._sympy_ok:
            return MathResult(False, None, "", "unavailable", [], {}, "sympy not installed")

        text = normalize_natural_math_phrasing(text)

        # Strategy 0: Multiple equations ("x+y=10 and x-y=20") must be solved
        # as a system, not fed whole into the single-equation path below --
        # that path assumes exactly one "=" relates exactly one unknown, and
        # silently mis-solving (or crashing on SymPy's multi-symbol solve()
        # return shape) is worse than just checking for this case first.
        if self._count_equations(text) >= 2:
            result = self._try_system_solve(text, entities)
            if result.solved:
                return result

        # Strategy 1: Try to extract and solve an equation from the text
        result = self._try_equation_solve(text, entities)
        if result.solved:
            return result

        # Strategy 2: Try to evaluate a pure arithmetic expression
        result = self._try_arithmetic_eval(text, entities)
        if result.solved:
            return result

        # Strategy 3: Substitute known values and solve for unknown
        result = self._try_substitution_solve(text, entities)
        if result.solved:
            return result

        return MathResult(
            solved=False, answer=None, answer_display="",
            method="none", steps=["Could not parse a solvable mathematical expression."],
            variables={},
            error="No mathematical structure found in input"
        )

    def solve_expression(self, expr_str: str) -> MathResult:
        """
        Solve or evaluate a single expression string.
        Examples:
          "x**2 + 5*x + 6 = 0"  → {x: -2, x: -3}
          "2 + 3 * 4"            → 14
          "sin(pi/2)"            → 1
        """
        if not self._sympy_ok:
            return MathResult(False, None, "", "unavailable", [], {})

        expr_str = expr_str.strip()

        # Equation (contains = sign, not ==)
        if "=" in expr_str and "==" not in expr_str:
            return self._solve_equation(expr_str)

        # Pure expression to evaluate
        return self._evaluate_expression(expr_str)

    # ─── Strategy 1: Equation Solving ────────────────────────────────────────

    def _try_equation_solve(self, text: str, entities: Dict[str, Any]) -> MathResult:
        """Extract equations from text and solve them."""
        # Direct equation check (e.g. "x+2=2" or "calcaute x+2=2")
        if "=" in text and "==" not in text:
            clean_eq = re.sub(r"^(?:calc\w*|solv\w*|comput\w*|eval\w*|find\s+result\s+for|what\s+is)\s+", "", text.strip(), flags=re.IGNORECASE)
            result = self._solve_equation(clean_eq)
            if result.solved:
                return result

        # Patterns that hint at equations
        equation_patterns = [
            # "solve x^2 + 5x + 6 = 0"
            r'(?:solve|find|calculate|calc\w*)\s+(.+?=.+?)(?:\s+for\s+(\w+))?$',
            # "x + y = 10, x - y = 2"
            r'([a-zA-Z]\s*[\+\-\*\/]\s*[a-zA-Z0-9\s]+\s*=\s*[0-9]+)',
            # "2x + 3 = 11"
            r'(\d*[a-zA-Z]\s*[\+\-]\s*\d+\s*=\s*\d+)',
        ]

        text_lower = text.lower()
        for pattern in equation_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                eq_str = match.group(1).strip()
                target_var = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else None
                result = self._solve_equation(eq_str, target_var)
                if result.solved:
                    return result

        return MathResult(False, None, "", "no_equation", [], {})

    # ─── Strategy 0: Systems of Equations ────────────────────────────────────

    @staticmethod
    def _split_equation_segments(text: str) -> List[str]:
        """Splits on and/;/newlines/commas, except a comma directly between two
        digits ("50,000"), which is a thousands separator, not a boundary
        between two equations ("x-y=20, x+y=10")."""
        return re.split(r"\band\b|[;\n]|,(?!\d)", text, flags=re.IGNORECASE)

    def _count_equations(self, text: str) -> int:
        """Counts distinct '<expr>=<expr>' segments (split on and/;/,/newlines)."""
        segments = self._split_equation_segments(text)
        return sum(1 for seg in segments if "=" in seg and "==" not in seg)

    def _try_system_solve(self, text: str, entities: Dict[str, Any]) -> MathResult:
        """Solves N simultaneous equations in N unknowns via SymPy's list-form solve()."""
        segments = self._split_equation_segments(text)
        eq_strs = [s.strip() for s in segments if "=" in s and "==" not in s]
        if len(eq_strs) < 2:
            return MathResult(False, None, "", "not_a_system", [], {})

        try:
            equations = []
            all_symbols = set()
            for eq_str in eq_strs:
                eq_str = eq_str.replace("^", "**")
                eq_str = re.sub(r"^(?:solv\w*|calc\w*|find)\s+", "", eq_str, flags=re.IGNORECASE).strip()
                parts = eq_str.split("=", 1)
                if len(parts) != 2:
                    return MathResult(False, None, "", "bad_equation_in_system", [], {})
                lhs = parse_expr(parts[0].strip(), transformations=self.TRANSFORMATIONS)
                rhs = parse_expr(parts[1].strip(), transformations=self.TRANSFORMATIONS)
                eq = Eq(lhs, rhs)
                equations.append(eq)
                all_symbols.update(eq.free_symbols)

            if not all_symbols:
                return MathResult(False, None, "", "no_unknowns_in_system", [], {})

            sorted_symbols = sorted(all_symbols, key=lambda s: s.name)
            solution = solve(equations, sorted_symbols)

            if not solution:
                return MathResult(False, None, "", "system_no_solution", [], {})

            # solve() on a list of symbols returns a dict {sym: value} for a
            # unique solution, or a list of dicts/tuples for multiple branches
            # (e.g. a nonlinear system) -- normalize to one solution dict.
            if isinstance(solution, dict):
                sol_dict = solution
            elif isinstance(solution, list) and solution and isinstance(solution[0], dict):
                sol_dict = solution[0]
            elif isinstance(solution, list) and solution:
                first = solution[0]
                values = first if isinstance(first, (list, tuple)) else solution
                sol_dict = dict(zip(sorted_symbols, values))
            else:
                return MathResult(False, None, "", "unrecognized_system_solution_shape", [], {})

            variables: Dict[str, Any] = {}
            display_parts = []
            for sym, val in sol_dict.items():
                val_float = float(val.evalf()) if hasattr(val, "evalf") else float(val)
                variables[str(sym)] = val_float
                display_parts.append(f"{sym} = {val_float}")
            display = ", ".join(display_parts)

            steps = [
                f"System of {len(equations)} equations: {'; '.join(eq_strs)}",
                f"Solved simultaneously for {[str(s) for s in sorted_symbols]}",
                f"Solution: {display}",
            ]

            return MathResult(
                solved=True, answer=variables, answer_display=display,
                method="sympy_system_solve", steps=steps, variables=variables
            )
        except Exception as e:
            return MathResult(False, None, "", "system_solve_error", [], {}, str(e))

    def _solve_equation(self, eq_str: str, target_var: str = None) -> MathResult:
        """Solve a single equation string using SymPy."""
        try:
            eq_str = eq_str.replace("^", "**")

            if "=" in eq_str and "==" not in eq_str:
                parts = eq_str.split("=", 1)
                lhs = parse_expr(parts[0].strip(), transformations=self.TRANSFORMATIONS)
                rhs = parse_expr(parts[1].strip(), transformations=self.TRANSFORMATIONS)
                equation = Eq(lhs, rhs)
            else:
                equation = parse_expr(eq_str, transformations=self.TRANSFORMATIONS)

            # Find all unknowns
            free_vars = list(equation.free_symbols) if hasattr(equation, 'free_symbols') else []
            if not free_vars:
                # Pure numeric
                val = float(simplify(equation))
                return MathResult(
                    solved=True, answer=val, answer_display=str(val),
                    method="sympy_eval", steps=[f"Evaluated: {eq_str} = {val}"],
                    variables={"result": val}
                )

            # Prefer the target variable if specified
            if target_var:
                solve_for = [v for v in free_vars if v.name == target_var]
                solve_for = solve_for[0] if solve_for else free_vars[0]
            else:
                solve_for = free_vars[0]

            solution = solve(equation, solve_for)

            if not solution:
                return MathResult(False, None, "", "sympy_no_solution", [], {})

            # Format solution
            if len(solution) == 1:
                ans = solution[0]
                ans_float = float(ans.evalf()) if hasattr(ans, 'evalf') else float(ans)
                display = f"{solve_for.name} = {ans_float}"
            else:
                ans = solution
                display = f"{solve_for.name} = {[str(s) for s in solution]}"
                ans_float = [float(s.evalf()) for s in solution if hasattr(s, 'evalf')]

            steps = [
                f"Equation: {eq_str}",
                f"Variable to find: {solve_for.name}",
                f"SymPy solution: {display}",
            ]

            return MathResult(
                solved=True, answer=ans, answer_display=display,
                method="sympy_solve", steps=steps,
                variables={str(solve_for): ans_float}
            )

        except Exception as e:
            return MathResult(False, None, "", "sympy_error", [], {}, str(e))

    # ─── Strategy 2: Arithmetic Evaluation ───────────────────────────────────

    def _try_arithmetic_eval(self, text: str, entities: Dict[str, Any]) -> MathResult:
        """Extract and evaluate pure arithmetic from text."""
        # Clean text of commands
        clean = re.sub(r'^(?:calculate|compute|what is|find|solve)\s+', '', text, flags=re.IGNORECASE).strip()
        # Remove trailing question marks or punctuation
        clean = re.sub(r'[\?\.\s]+$', '', clean)
        
        # Check if the clean text consists only of numbers, operators, parentheses, and spaces
        if re.match(r'^[\d\.\s\+\-\*\/\(\)\^\%]+$', clean):
            return self._evaluate_expression(clean)
            
        # Fallback to finding simple sub-expressions if whole string is not pure arithmetic
        arith_pattern = r'(\d+(?:\.\d+)?\s*(?:[\+\-\*\/\^]\s*\d+(?:\.\d+)?)+)'
        match = re.search(arith_pattern, text)
        if match:
            expr = match.group(1).strip()
            return self._evaluate_expression(expr)

        # Last resort: a known function call like "sqrt(144)" is valid SymPy but
        # contains letters, so it fails the pure-digits-and-operators regex above.
        # _evaluate_expression already fails safely (caught exception) on garbage,
        # so it's safe to just attempt it directly here.
        if re.match(r'^(?:sqrt|cbrt|sin|cos|tan|log|ln|abs)\(', clean, re.IGNORECASE):
            return self._evaluate_expression(clean)

        return MathResult(False, None, "", "no_arithmetic", [], {})

    def _evaluate_expression(self, expr_str: str) -> MathResult:
        """Evaluate a pure math expression using SymPy."""
        try:
            expr_str = expr_str.replace("^", "**")
            result = parse_expr(expr_str, transformations=self.TRANSFORMATIONS)
            val = float(result.evalf())
            return MathResult(
                solved=True, answer=val, answer_display=str(val),
                method="sympy_eval", steps=[f"{expr_str} = {val}"],
                variables={"result": val}
            )
        except Exception as e:
            return MathResult(False, None, "", "eval_error", [], {}, str(e))

    # ─── Strategy 3: Substitution Solve ──────────────────────────────────────

    def _try_substitution_solve(self, text: str, entities: Dict[str, Any]) -> MathResult:
        """
        Given known entity values, build and solve the implied formula.
        Example: distance=100, time=5 → velocity = distance/time = 20
        """
        if not entities:
            return MathResult(False, None, "", "no_entities", [], {})

        # Build known values dict
        known = {}
        unknown_name = "result"

        for name, ev in entities.items():
            from hsci.core.data_types import EntityValue
            if isinstance(ev, EntityValue):
                if ev.known and ev.value is not None:
                    try:
                        known[name] = float(ev.value)
                    except (ValueError, TypeError):
                        pass
                else:
                    unknown_name = name
            else:
                if ev is not None:
                    try:
                        known[name] = float(ev)
                    except (ValueError, TypeError):
                        pass

        if len(known) < 2:
            return MathResult(False, None, "", "insufficient_entities", [], {})

        # Try common formula patterns based on entity name semantics
        formula = self._infer_formula(text.lower(), known, unknown_name)
        if formula:
            try:
                result = float(formula)
                steps = [
                    f"Known values: {known}",
                    f"Inferred formula for '{unknown_name}'",
                    f"Result: {result}"
                ]
                return MathResult(
                    solved=True, answer=result,
                    answer_display=f"{unknown_name} = {result}",
                    method="substitution", steps=steps,
                    variables={unknown_name: result}
                )
            except Exception:
                pass

        return MathResult(False, None, "", "substitution_failed", [], {})

    def _infer_formula(self, text: str, known: Dict[str, float], unknown: str) -> Optional[float]:
        """
        Infer a formula from context + entity names.
        This is concept-guided substitution — the key to generalizing beyond templates.
        """
        vals = list(known.values())

        # Physics: distance = rate * time
        if any(w in text for w in ["velocity", "speed", "rate"]) and any(w in text for w in ["time", "hours", "seconds"]):
            if any(w in text for w in ["distance", "far", "km", "miles"]):
                return vals[0] * vals[1]  # d = v * t
            else:
                # velocity = distance / time
                return vals[0] / vals[1] if vals[1] != 0 else None

        # Finance: simple percentage
        if any(w in text for w in ["percent", "rate", "tax", "discount", "interest"]):
            base = max(vals)
            rate = min(vals)
            if rate > 1:
                return base * (rate / 100)
            else:
                return base * rate

        # Area: l * w
        if any(w in text for w in ["area", "rectangle", "square"]):
            return vals[0] * vals[1]

        # Default: try addition, then multiplication
        if "sum" in text or "total" in text or "add" in text:
            return sum(vals)
        if "product" in text or "multiply" in text:
            result = 1
            for v in vals:
                result *= v
            return result

        return None

    def can_solve(self, text: str) -> bool:
        """Quick check if this engine can likely solve the given text."""
        normalized = normalize_natural_math_phrasing(text)
        math_indicators = [
            r'\d+\s*[\+\-\*\/\^]\s*\d+',  # arithmetic
            r'[a-zA-Z]\s*[\+\-\*\/]\s*[a-zA-Z0-9]',  # algebra
            r'solve|calculate|compute|find|what is',  # intent
            r'=\s*\d',  # equation
            r'\bsqrt\(|\bcbrt\(',  # named functions, post-normalization
        ]
        for pattern in math_indicators:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False
