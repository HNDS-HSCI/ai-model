"""Inductive learning: proposing general rules from examples, and refuting them.

This is the paper's counterexample-guided loop applied to *knowledge* rather than
programs. After every update the learner:

1. **Refutes** standing hypotheses that now have a counterexample in the closure
   (e.g. hypothesis "every bird can fly" + told fact "Pingu is a bird and cannot fly").
2. **Induces** new hypotheses from regularities with enough support and zero
   counterexamples: category implications ("every X I know is also Y") and
   relation symmetry ("whenever a R b, also b R a").

Hypotheses are stored with status ``hypothesis`` and a Laplace-smoothed confidence.
They never feed deductive (verified) answers -- only explicitly-marked "probably"
answers -- so induction can make the system more helpful without making it less
truthful. A user confirming a hypothesis in plain English simply turns it into a
told rule.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from hsci.mind.logic import IS, Atom, Rule
from hsci.mind.reasoner import Closure, Derivation, _join, saturate

MIN_SUPPORT = 2


@dataclass
class Hypothesis:
    rule: Rule
    support: List[str]
    confidence: float
    description: str


@dataclass
class Refutation:
    rule_id: int
    rule: Rule
    counterexample: str


def _individual(term: str) -> bool:
    return not term.startswith("a typical ")


def induce(closure: Closure, rules: Sequence[Rule], known_rule_keys: Set[str]) -> List[Hypothesis]:
    members: Dict[str, Set[str]] = defaultdict(set)
    cats_of: Dict[str, Set[str]] = defaultdict(set)
    for a in closure.atoms():
        if a.pred == IS and not a.neg and len(a.args) == 2 and _individual(a.args[0]):
            members[a.args[1]].add(a.args[0])
            cats_of[a.args[0]].add(a.args[1])

    out: List[Hypothesis] = []
    for a_cat, ents in members.items():
        if len(ents) < MIN_SUPPORT:
            continue
        common = set.intersection(*(cats_of[e] for e in ents)) - {a_cat}
        for b_cat in sorted(common):
            # "big dog" -> "dog" is morphology, not a discovery.
            if set(b_cat.split()) <= set(a_cat.split()) or set(a_cat.split()) <= set(b_cat.split()):
                continue
            rule = Rule((Atom(IS, ("?x", a_cat)),), Atom(IS, ("?x", b_cat)), origin="induced")
            if _key(rule) in known_rule_keys or _entailed(rule, rules):
                continue
            n = len(ents)
            out.append(Hypothesis(rule, sorted(ents), round((n + 1) / (n + 2), 3),
                                  f"every {a_cat} I know of is also {b_cat}"))

    pairs: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
    for a in closure.atoms():
        if a.pred != IS and not a.neg and len(a.args) == 2:
            pairs[a.pred].add(a.args)
    for pred, ps in pairs.items():
        unordered = {frozenset(p) for p in ps if p[0] != p[1]}
        if len(unordered) >= MIN_SUPPORT and all((b, a) in ps for a, b in ps):
            rule = Rule((Atom(pred, ("?a", "?b")),), Atom(pred, ("?b", "?a")), origin="induced")
            if _key(rule) in known_rule_keys or _entailed(rule, rules):
                continue
            n = len(unordered)
            out.append(Hypothesis(rule, sorted(" & ".join(sorted(p)) for p in unordered), round((n + 1) / (n + 2), 3),
                                  f"'{pred}' appears to be symmetric"))
    return out


def refute(closure: Closure, hypotheses: Sequence[Tuple[int, Rule]]) -> List[Refutation]:
    out = []
    for rid, rule in hypotheses:
        for theta in _join(closure, list(rule.body), {}):
            head = rule.head.substitute(theta)
            if head.negate() in closure:
                ce = ", ".join(str(b.substitute(theta)) for b in rule.body) + f" but {head.negate()}"
                out.append(Refutation(rid, rule, ce))
                break
    return out


def _entailed(rule: Rule, rules: Sequence[Rule]) -> bool:
    """Does the existing theory already derive this rule for an arbitrary individual?"""
    fresh = "__probe__"
    theta = {v: f"{fresh}{i}" for i, v in enumerate(sorted({v for a in rule.body for v in a.variables()}))}
    c = Closure()
    saturate(c, rules, [Derivation(b.substitute(theta), None, (), "probe", 0) for b in rule.body], max_facts=20_000)
    return rule.head.substitute(theta) in c


def _key(rule: Rule) -> str:
    import json
    return json.dumps(rule.to_json(), sort_keys=True)
