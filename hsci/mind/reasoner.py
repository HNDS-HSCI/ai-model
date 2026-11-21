"""Deductive engine: semi-naive forward chaining with full proof recording.

Every atom in a ``Closure`` carries the ``Derivation`` that produced it -- either
a told fact (with its source sentence) or a rule application (with the premises
it consumed). Proofs are therefore first-class data: they are what the verifier
re-checks with Z3 and what the explainer turns back into English.

The language is function-free Datalog with strong negation, so saturation always
terminates; ``max_facts`` is only a guard against pathological inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from hsci.mind.logic import Atom, Rule, Theta, unify


@dataclass(frozen=True)
class Derivation:
    atom: Atom
    rule: Optional[Rule]           # None => given (told / hypothetical) fact
    premises: Tuple[Atom, ...]
    source: str                    # source sentence for given facts
    depth: int


class Closure:
    """The set of everything entailed by a world's facts and rules."""

    def __init__(self) -> None:
        self.derivations: Dict[Atom, Derivation] = {}
        self._index: Dict[Tuple[str, bool, int], List[Atom]] = {}

    def __contains__(self, atom: Atom) -> bool:
        return atom in self.derivations

    def __len__(self) -> int:
        return len(self.derivations)

    def add(self, d: Derivation) -> bool:
        if d.atom in self.derivations:
            return False
        self.derivations[d.atom] = d
        self._index.setdefault(_key(d.atom), []).append(d.atom)
        return True

    def candidates(self, pattern: Atom) -> List[Atom]:
        return self._index.get(_key(pattern), [])

    def match(self, pattern: Atom, theta: Optional[Theta] = None) -> List[Theta]:
        out = []
        for fact in self.candidates(pattern):
            t = unify(pattern, fact, theta or {})
            if t is not None:
                out.append(t)
        return out

    def get(self, atom: Atom) -> Optional[Derivation]:
        return self.derivations.get(atom)

    def contradictions(self) -> List[Tuple[Atom, Atom]]:
        return [(a.positive(), a) for a in self.derivations if a.neg and a.positive() in self.derivations]

    def copy(self) -> "Closure":
        c = Closure()
        c.derivations = dict(self.derivations)
        c._index = {k: list(v) for k, v in self._index.items()}
        return c

    def atoms(self) -> Iterable[Atom]:
        return self.derivations.keys()


def _key(a: Atom) -> Tuple[str, bool, int]:
    return (a.pred, a.neg, len(a.args))


class SaturationLimit(RuntimeError):
    pass


def saturate(closure: Closure, rules: Sequence[Rule], new_facts: Iterable[Derivation],
             max_facts: int = 200_000) -> Closure:
    """Adds ``new_facts`` to ``closure`` and forward-chains to a fixed point (in place).

    Semi-naive: each round only fires rules that use at least one atom from the
    previous round's delta, so incremental updates cost proportional to what changed.
    """
    delta = [d.atom for d in new_facts if closure.add(d)]
    while delta:
        next_delta: List[Atom] = []
        delta_index: Dict[Tuple[str, bool, int], List[Atom]] = {}
        for a in delta:
            delta_index.setdefault(_key(a), []).append(a)
        for rule in rules:
            for i, trigger in enumerate(rule.body):
                for fact in delta_index.get(_key(trigger), ()):
                    theta = unify(trigger, fact, {})
                    if theta is None:
                        continue
                    rest = [b for j, b in enumerate(rule.body) if j != i]
                    for full in _join(closure, rest, theta):
                        head = rule.head.substitute(full)
                        if not head.is_ground() or head in closure:
                            continue
                        premises = tuple(b.substitute(full) for b in rule.body)
                        depth = 1 + max(closure.derivations[p].depth for p in premises)
                        closure.add(Derivation(head, rule, premises, "", depth))
                        next_delta.append(head)
                        if len(closure) > max_facts:
                            raise SaturationLimit(f"closure exceeded {max_facts} facts")
        delta = next_delta
    return closure


def saturate_all(rules: Sequence[Rule], given: Iterable[Derivation], max_facts: int = 200_000) -> Closure:
    """Strict closure, then default rules (generics such as "Birds fly").

    A default conclusion is added only if its negation is not derivable and adding
    it (plus its strict consequences) creates no contradiction -- so "Pingu cannot
    fly" silently blocks "birds fly" for Pingu instead of making the theory
    inconsistent. Strict knowledge always wins over defaults.
    """
    strict = [r for r in rules if r.origin != "default"]
    defaults = [r for r in rules if r.origin == "default"]
    closure = saturate(Closure(), strict, given, max_facts)
    if not defaults:
        return closure
    blocked: set = set()
    changed = True
    while changed:
        changed = False
        for rule in defaults:
            for theta in list(_join(closure, list(rule.body), {})):
                head = rule.head.substitute(theta)
                if not head.is_ground() or head in closure or head in blocked or head.negate() in closure:
                    continue
                premises = tuple(b.substitute(theta) for b in rule.body)
                depth = 1 + max(closure.derivations[p].depth for p in premises)
                trial = closure.copy()
                before = len(trial.contradictions())
                saturate(trial, strict, [Derivation(head, rule, premises, "", depth)], max_facts)
                if len(trial.contradictions()) > before:
                    blocked.add(head)
                    continue
                closure = trial
                changed = True
    return closure


def uses_default(tree: dict) -> bool:
    if tree.get("rule") is not None and tree["rule"].origin == "default":
        return True
    return any(uses_default(p) for p in tree.get("premises", []))


def _join(closure: Closure, atoms: List[Atom], theta: Theta):
    if not atoms:
        yield theta
        return
    # Most-bound-first ordering keeps joins selective.
    atoms = sorted(atoms, key=lambda a: -sum(1 for x in a.args if x in theta or not x.startswith("?")))
    first, rest = atoms[0], atoms[1:]
    for t in closure.match(first.substitute(theta), theta):
        yield from _join(closure, rest, t)


def proof_tree(closure: Closure, atom: Atom, _seen: Optional[set] = None) -> dict:
    """Recursively expands the recorded derivation of ``atom`` into a JSON-able tree."""
    seen = _seen or set()
    d = closure.get(atom)
    if d is None:
        return {"atom": atom, "missing": True}
    node = {"atom": atom, "rule": d.rule, "source": d.source, "depth": d.depth, "premises": []}
    if atom in seen:
        return node
    seen = seen | {atom}
    node["premises"] = [proof_tree(closure, p, seen) for p in d.premises]
    return node


def support(tree: dict) -> Tuple[List[Atom], List[Tuple[Rule, Tuple[Atom, ...], Atom]]]:
    """Leaves (given facts) and ground rule instances used by a proof tree."""
    leaves: List[Atom] = []
    steps: List[Tuple[Rule, Tuple[Atom, ...], Atom]] = []

    def walk(n: dict) -> None:
        if n.get("rule") is None:
            if n["atom"] not in leaves:
                leaves.append(n["atom"])
            return
        steps.append((n["rule"], tuple(p["atom"] for p in n["premises"]), n["atom"]))
        for p in n["premises"]:
            walk(p)

    walk(tree)
    return leaves, steps
