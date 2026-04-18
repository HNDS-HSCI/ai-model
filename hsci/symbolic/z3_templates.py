import z3
from typing import Callable, Dict, Any

# Version 3.0 Z3 Templates
# Lambdas must accept keyword arguments corresponding to their parameters.

Z3_TEMPLATES: Dict[str, Callable] = {
    "ADDITION": lambda a, b, result: result == a + b,
    "SUBTRACTION": lambda a, b, result: result == a - b,
    "MULTIPLICATION": lambda a, b, result: result == a * b,
    "DIVISION": lambda a, b, result: z3.And(result == a / b, b != 0),
    "PERCENTAGE": lambda base, rate, result: result == base * (rate / 100),
    "PERCENTAGE_DECIMAL": lambda base, rate, result: result == base * rate,
    "PERCENTAGE_SUBTRACTION": lambda base, rate, result: result == base - (base * rate),
    "LINEAR_EQUATION": lambda a, b, c, x: a * x + b == c,
    "AREA_RECTANGLE": lambda l, w, area: area == l * w,
    "AREA_TRIANGLE": lambda base, h, area: area == (base * h) / 2,
    "SIMPLE_INTEREST": lambda p, r, t, i: i == p * r * t,
    "LOOP_INVARIANT": lambda inv, i: z3.ForAll([i], z3.Implies(inv(i), z3.And(inv(i+1), i >= 0))),
    "DISTANCE_RATE_TIME": lambda d, r, t: d == r * t,
    "FORCE_MASS_ACCEL": lambda f, m, a: f == m * a,
}

# Metadata for Concept Library seeding
Z3_METADATA = {
    "ADDITION": {"template": "result = a + b", "domain": "arithmetic", "entities": ["a", "b"]},
    "SUBTRACTION": {"template": "result = a - b", "domain": "arithmetic", "entities": ["a", "b"]},
    "MULTIPLICATION": {"template": "result = a * b", "domain": "arithmetic", "entities": ["a", "b"]},
    "DIVISION": {"template": "result = a / b", "domain": "arithmetic", "entities": ["a", "b"]},
    "PERCENTAGE": {"template": "result = base * (rate / 100)", "domain": "arithmetic", "entities": ["base", "rate"]},
    "PERCENTAGE_DECIMAL": {"template": "result = base * rate", "domain": "arithmetic", "entities": ["base", "rate"]},
    "PERCENTAGE_SUBTRACTION": {"template": "result = base - (base * rate)", "domain": "arithmetic", "entities": ["base", "rate"]},
    "LINEAR_EQUATION": {"template": "a*x + b = c", "domain": "algebra", "entities": ["a", "x", "b", "c"]},
    "AREA_RECTANGLE": {"template": "area = l * w", "domain": "geometry", "entities": ["l", "w"]},
    "DISTANCE_RATE_TIME": {"template": "d = r * t", "domain": "physics", "entities": ["r", "t"]},
    "FORCE_MASS_ACCEL": {"template": "f = m * a", "domain": "physics", "entities": ["m", "a"]},
}
