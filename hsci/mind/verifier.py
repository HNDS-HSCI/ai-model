"""Independent proof checking with Z3 (the paper's verifier V).

The forward chainer *finds* proofs; this module *checks* them without trusting the
chainer. A proof of ``goal`` is accepted only if

1. its given premises are jointly satisfiable (the proof is not vacuous), and
2. premises + the ground rule instances it used, together with ``not goal``, are
   unsatisfiable -- i.e. the goal is a logical consequence of what was used.

Each ground rule instance is also re-checked against its rule schema, so a bug that
fabricated a step (wrong substitution, wrong rule) is caught here, not shipped.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import z3

from hsci.mind.logic import Atom, Rule, unify
from hsci.mind.reasoner import support


@dataclass
class Verdict:
    verified: bool
    method: str
    detail: str
    premises: int = 0
    steps: int = 0


def _lit(atom: Atom, table: Dict[Atom, z3.BoolRef], ctx: z3.Context) -> z3.BoolRef:
    pos = atom.positive()
    if pos not in table:
        table[pos] = z3.Bool(f"a{len(table)}", ctx)
    v = table[pos]
    return z3.Not(v) if atom.neg else v


def _instance_of(rule: Rule, premises: Tuple[Atom, ...], head: Atom) -> bool:
    if len(premises) != len(rule.body):
        return False
    theta: dict = {}
    for pattern, fact in zip(rule.body, premises):
        theta = unify(pattern, fact, theta)
        if theta is None:
            return False
    return rule.head.substitute(theta) == head


def verify_proof(tree: dict) -> Verdict:
    leaves, steps = support(tree)
    goal: Atom = tree["atom"]
    for rule, premises, head in steps:
        if not _instance_of(rule, premises, head):
            return Verdict(False, "z3", f"step {head} is not a valid instance of rule {rule}")

    ctx = z3.Context()
    table: Dict[Atom, z3.BoolRef] = {}
    s = z3.Solver(ctx=ctx)
    for leaf in leaves:
        s.add(_lit(leaf, table, ctx))
    for _, premises, head in steps:
        s.add(z3.Implies(z3.And(*[_lit(p, table, ctx) for p in premises]), _lit(head, table, ctx)))
    if s.check() != z3.sat:
        return Verdict(False, "z3", "premises are mutually inconsistent", len(leaves), len(steps))
    s.add(z3.Not(_lit(goal, table, ctx)))
    if s.check() == z3.unsat:
        return Verdict(True, "z3", "goal entailed by premises (refutation of negated goal is UNSAT)",
                       len(leaves), len(steps))
    return Verdict(False, "z3", "premises do not entail goal", len(leaves), len(steps))


def verify_all(trees: List[dict]) -> Verdict:
    """Verifies several proofs (e.g. every pairwise step of a superlative answer)."""
    total_p = total_s = 0
    for t in trees:
        v = verify_proof(t)
        total_p += v.premises
        total_s += v.steps
        if not v.verified:
            return v
    return Verdict(True, "z3", f"all {len(trees)} supporting proofs verified", total_p, total_s)
