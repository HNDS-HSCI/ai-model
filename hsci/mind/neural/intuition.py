"""Intuition: a "probably" when proof is silent, from two learned sources.

* **Category statistics** (transparent counting): "5 of the 6 daxes I know are
  brave". Strong for class-typical properties; blind to relational patterns.
* **Concept-graph network** (R-GCN, ``graph_net.py``): learned vectors over the
  whole graph. Weaker on simple class-typical facts, but sees relational patterns
  counting cannot ("people who like a member of X tend to be Y").

Measured on held-out facts (``neural/evaluation.py``): class-typical AUC 0.98
(counting) vs 0.93 (network); relational AUC 0.50 (counting) vs 0.95 (network).
Each judgement uses counting when it has enough class evidence and the network
otherwise, averaging them when both speak.

Intuition only ever produces explicitly-labelled "probably" answers: never verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from hsci.mind.lexicon import pluralize
from hsci.mind.logic import IS, Atom, Rule
from hsci.mind.neural.graph_net import ConceptGraphNet, atom_to_triple, graph_from_knowledge

MIN_CLASSMATES = 3
MIN_LINKS = 40        # the network needs this much experience before its intuition counts
MIN_DEGREE = 2        # ... and must have seen both concepts in at least this many links
YES_AT = 0.80
NO_AT = 0.15


@dataclass
class Judgement:
    probability: float
    source: str           # statistics | network | statistics+network
    reason: str


class Intuition:
    def __init__(self, atoms: Sequence[Atom], rules: Sequence[Rule], seed: int = 0) -> None:
        self.pos, self.neg = graph_from_knowledge(atoms, rules)
        self.facts: Set[Tuple[str, str, str]] = set(self.pos)
        self.false: Set[Tuple[str, str, str]] = set(self.neg)
        self.classes: Dict[str, Set[str]] = {}
        self.members: Dict[str, Set[str]] = {}
        for s, r, o in self.pos:
            if r == IS:
                self.classes.setdefault(s, set()).add(o)
                self.members.setdefault(o, set()).add(s)
        self.degree: Dict[str, int] = {}
        for s, _, o in self.pos:
            self.degree[s] = self.degree.get(s, 0) + 1
            self.degree[o] = self.degree.get(o, 0) + 1
        # Train only when there is enough experience to learn from.
        self.net = ConceptGraphNet(dim=16, seed=seed)
        if len(self.pos) >= MIN_LINKS:
            self.net.fit(self.pos, self.neg)

    def judge(self, atom: Atom) -> Optional[Judgement]:
        t = atom_to_triple(atom.positive())
        if t is None or t in self.facts or t in self.false:
            return None
        stat = self._statistics(t)
        net_p = self.net.plausibility(t) if self._experienced(t) else None
        if stat and net_p is not None:
            p = (stat[0] + net_p) / 2
            j = Judgement(p, "statistics+network", f"{stat[1]}; the concept-graph network rates it {net_p:.2f}")
        elif stat:
            j = Judgement(stat[0], "statistics", stat[1])
        elif net_p is not None:
            j = Judgement(net_p, "network", f"the concept-graph network, trained on {len(self.pos)} links, rates it {net_p:.2f}")
        else:
            return None
        if atom.neg:
            j.probability = 1 - j.probability
        return j

    def _experienced(self, t: Tuple[str, str, str]) -> bool:
        if len(self.pos) < MIN_LINKS:
            return False
        return all(self.degree.get(x, 0) >= MIN_DEGREE for x in (t[0], t[2]))

    def _statistics(self, t: Tuple[str, str, str]) -> Optional[Tuple[float, str]]:
        s, r, o = t
        best: Optional[Tuple[float, str, int]] = None
        for c in self.classes.get(s, ()):
            if c == o:
                continue
            mates = self.members.get(c, set()) - {s}
            # unmentioned counts as weak evidence against: intuition is about how typical something is
            told = list(mates)
            if len(told) < MIN_CLASSMATES:
                continue
            yes = sum((m, r, o) in self.facts for m in told)
            p = (yes + 0.5) / (len(told) + 1)             # smoothed frequency
            if best is None or abs(p - 0.5) > abs(best[0] - 0.5):
                best = (p, f"{yes} of the {len(told)} {pluralize(c)} I know about {'are' if r == IS else r} {o}", len(told))
        return (best[0], best[1]) if best else None

    def similar(self, concept: str, k: int = 5) -> List[Tuple[str, float]]:
        return self.net.similar(concept, k)
