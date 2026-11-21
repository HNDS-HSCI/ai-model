"""Core logical representation for the HSCI Mind.

Everything the Mind knows is expressed in a small, uniform first-order language:

* ``Atom(pred, args, neg)`` -- a literal such as ``is(socrates, man)`` or
  ``older than(alice, bob)``. ``neg=True`` is *strong* negation ("Tweety cannot
  fly" is a positive claim about a negative fact, not an absence of knowledge).
* ``Rule(body, head)`` -- a Horn clause. Variables are strings starting with ``?``.

Unary categories (nouns and adjectives) share the binary predicate ``is`` so that
"Rex is a dog" and "Rex is brown" have the same shape, and taxonomies are plain
rules: ``is(?x, dog) -> is(?x, mammal)``.

No predicate, constant or category is special-cased anywhere in the engine: the
vocabulary is whatever the user (or a seed file written in English) teaches.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

IS = "is"  # the copular category predicate

Theta = Dict[str, str]


def is_var(term: str) -> bool:
    return term.startswith("?")


@dataclass(frozen=True)
class Atom:
    pred: str
    args: Tuple[str, ...]
    neg: bool = False

    def negate(self) -> "Atom":
        return Atom(self.pred, self.args, not self.neg)

    def positive(self) -> "Atom":
        return Atom(self.pred, self.args, False)

    def substitute(self, theta: Theta) -> "Atom":
        return Atom(self.pred, tuple(theta.get(a, a) for a in self.args), self.neg)

    def variables(self) -> set:
        return {a for a in self.args if is_var(a)}

    def is_ground(self) -> bool:
        return not self.variables()

    def to_json(self) -> dict:
        return {"pred": self.pred, "args": list(self.args), "neg": self.neg}

    @staticmethod
    def from_json(d: dict) -> "Atom":
        return Atom(d["pred"], tuple(d["args"]), bool(d.get("neg", False)))

    def __str__(self) -> str:
        s = f"{self.pred}({', '.join(self.args)})"
        return f"not {s}" if self.neg else s


@dataclass(frozen=True)
class Rule:
    body: Tuple[Atom, ...]
    head: Atom
    rule_id: str = field(default="", compare=False)
    origin: str = field(default="told", compare=False)  # told | grammar | induced | seed
    source_text: str = field(default="", compare=False)
    confidence: float = field(default=1.0, compare=False)

    def is_safe(self) -> bool:
        """Every head variable must be bound by the body (keeps reasoning finite)."""
        bound = set().union(*(a.variables() for a in self.body)) if self.body else set()
        return self.head.variables() <= bound

    def to_json(self) -> dict:
        return {"body": [a.to_json() for a in self.body], "head": self.head.to_json()}

    @staticmethod
    def from_json(d: dict, **meta) -> "Rule":
        return Rule(tuple(Atom.from_json(a) for a in d["body"]), Atom.from_json(d["head"]), **meta)

    def __str__(self) -> str:
        return f"{' & '.join(map(str, self.body))} -> {self.head}"


def unify(pattern: Atom, fact: Atom, theta: Theta) -> Optional[Theta]:
    """One-way matching of a (possibly non-ground) pattern against a ground fact."""
    if pattern.pred != fact.pred or pattern.neg != fact.neg or len(pattern.args) != len(fact.args):
        return None
    out = dict(theta)
    for p, f in zip(pattern.args, fact.args):
        if is_var(p):
            bound = out.get(p)
            if bound is None:
                out[p] = f
            elif bound != f:
                return None
        elif p != f:
            return None
    return out


def rename_apart(rule: Rule, suffix: str) -> Rule:
    theta = {v: f"{v}_{suffix}" for a in (*rule.body, rule.head) for v in a.variables()}
    return Rule(tuple(a.substitute(theta) for a in rule.body), rule.head.substitute(theta),
                rule.rule_id, rule.origin, rule.source_text, rule.confidence)


def constants(atoms: Iterable[Atom]) -> set:
    return {a for atom in atoms for a in atom.args if not is_var(a)}
