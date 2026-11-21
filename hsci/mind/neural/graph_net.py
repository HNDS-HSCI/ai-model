"""Neural intuition over the concept graph (System 1 next to the reasoner's System 2).

Everything the Mind knows -- told facts, derived conclusions, taxonomy rules -- is
turned into a typed concept graph:

    (rex, is, dog)   (alice, older than, bob)   (dog, subclass of, mammal)
    (tweety, can fly, YES)  for one-place predicates

A small relational graph neural network (R-GCN encoder with basis-decomposed
relation weights, DistMult decoder) learns a vector for every concept by link
prediction: with part of the graph hidden, predict the hidden links back. Trained
on the Mind's own knowledge, on CPU, in about a second for thousands of links; no
outside data.

What it is for: when deduction cannot settle a question, the network can still
say "probably" -- because Fep is a dax, and daxes in general tend to be brave. It
proposes; it never proves. Its outputs are always labelled as intuition and never
marked verified.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from hsci.mind.logic import IS, Atom, Rule

YES = "__yes__"
SUBCLASS = "subclass of"

Triple = Tuple[str, str, str]


def atom_to_triple(a: Atom) -> Optional[Triple]:
    if a.pred == IS and len(a.args) == 2:
        return (a.args[0], IS, a.args[1])
    if len(a.args) == 2:
        return (a.args[0], a.pred, a.args[1])
    if len(a.args) == 1:
        return (a.args[0], a.pred, YES)
    return None


def _skip(term: str) -> bool:
    return term.startswith("?") or term.startswith("a typical") or term.startswith("__probe")


def graph_from_knowledge(atoms: Iterable[Atom], rules: Sequence[Rule]) -> Tuple[List[Triple], List[Triple]]:
    """Positive links (true facts + taxonomy) and explicit negative links (strong negation)."""
    pos, neg = set(), set()
    for a in atoms:
        t = atom_to_triple(a.positive())
        if t is None or _skip(t[0]) or _skip(t[2]):
            continue
        (neg if a.neg else pos).add(t)
    for r in rules:
        if (len(r.body) == 1 and r.body[0].pred == IS and r.head.pred == IS and not r.head.neg
                and r.origin != "induced" and r.body[0].args[0] == r.head.args[0]):
            pos.add((r.body[0].args[1], SUBCLASS, r.head.args[1]))
    return sorted(pos), sorted(neg)


class RGCNDistMult(nn.Module):
    def __init__(self, n_nodes: int, n_rel: int, dim: int = 32, bases: int = 4, layers: int = 2) -> None:
        super().__init__()
        self.n_rel = n_rel
        self.emb = nn.Embedding(n_nodes, dim)
        # Two layers let information travel entity -> its class -> the class's other members.
        self.bases = nn.ParameterList([nn.Parameter(torch.randn(bases, dim, dim) * (1.0 / dim ** 0.5)) for _ in range(layers)])
        self.coef = nn.ParameterList([nn.Parameter(torch.randn(2 * n_rel, bases) * 0.5) for _ in range(layers)])
        self.self_loop = nn.ModuleList([nn.Linear(dim, dim) for _ in range(layers)])
        self.rel = nn.Embedding(n_rel, dim)
        nn.init.normal_(self.emb.weight, std=0.3)
        nn.init.normal_(self.rel.weight, mean=1.0, std=0.1)

    def encode(self, src: torch.Tensor, rel: torch.Tensor, dst: torch.Tensor) -> torch.Tensor:
        h = self.emb.weight
        if src.numel() == 0:
            return h
        s = torch.cat([src, dst])
        d = torch.cat([dst, src])
        r = torch.cat([rel, rel + self.n_rel])
        deg = torch.zeros(h.shape[0]).index_add_(0, d, torch.ones(d.shape[0])).clamp(min=1).unsqueeze(1)
        for bases, coef, loop in zip(self.bases, self.coef, self.self_loop):
            w = torch.einsum("rb,bij->rij", coef, bases)
            msg = torch.bmm(h[s].unsqueeze(1), w[r]).squeeze(1)
            agg = torch.zeros_like(h).index_add_(0, d, msg)
            h = h + torch.tanh(loop(h) + agg / deg)
        return h

    def score(self, h: torch.Tensor, s: torch.Tensor, r: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        return (h[s] * self.rel(r) * h[o]).sum(-1)


@dataclass
class TrainReport:
    links: int
    nodes: int
    relations: int
    epochs: int
    final_loss: float


class ConceptGraphNet:
    """Trains on a knowledge graph and answers 'how plausible is this link?'."""

    def __init__(self, dim: int = 32, epochs: int = 300, negatives: int = 4, edge_dropout: float = 0.5,
                 seed: int = 0) -> None:
        self.dim, self.epochs, self.negatives, self.edge_dropout, self.seed = dim, epochs, negatives, edge_dropout, seed
        self.nodes: Dict[str, int] = {}
        self.rels: Dict[str, int] = {}
        self.model: Optional[RGCNDistMult] = None
        self._h: Optional[torch.Tensor] = None
        self._edges: Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = None
        self._tails_by_rel: Dict[int, List[int]] = {}
        self.report: Optional[TrainReport] = None

    def fit(self, positives: Sequence[Triple], negatives: Sequence[Triple] = ()) -> "ConceptGraphNet":
        torch.manual_seed(self.seed)
        rng = random.Random(self.seed)
        for s, r, o in list(positives) + list(negatives):
            self.nodes.setdefault(s, len(self.nodes))
            self.nodes.setdefault(o, len(self.nodes))
            self.rels.setdefault(r, len(self.rels))
        if not positives or len(self.nodes) < 3:
            return self
        P = torch.tensor([[self.nodes[s], self.rels[r], self.nodes[o]] for s, r, o in positives])
        N_explicit = torch.tensor([[self.nodes[s], self.rels[r], self.nodes[o]] for s, r, o in negatives]) \
            if negatives else torch.zeros((0, 3), dtype=torch.long)
        for s, r, o in P.tolist():
            self._tails_by_rel.setdefault(r, []).append(o)
        self.model = RGCNDistMult(len(self.nodes), len(self.rels), self.dim)
        opt = torch.optim.Adam(self.model.parameters(), lr=0.02, weight_decay=1e-5)
        loss_v = 0.0
        for _ in range(self.epochs):
            self.model.train()
            keep = torch.rand(P.shape[0]) > self.edge_dropout          # hide links -> must generalise
            E = P[keep] if keep.any() else P
            h = self.model.encode(E[:, 0], E[:, 1], E[:, 2])
            neg = self._corrupt(P, rng)
            batch = torch.cat([P, neg, N_explicit])
            y = torch.cat([torch.ones(P.shape[0]), torch.zeros(neg.shape[0] + N_explicit.shape[0])])
            logits = self.model.score(h, batch[:, 0], batch[:, 1], batch[:, 2])
            # balance true vs. false examples so scores read as probabilities, not 'mostly no'
            n_pos, n_neg = float(P.shape[0]), float(neg.shape[0] + N_explicit.shape[0])
            weight = torch.where(y > 0, torch.tensor(n_neg / n_pos), torch.tensor(1.0))
            loss = F.binary_cross_entropy_with_logits(logits, y, weight=weight)
            opt.zero_grad()
            loss.backward()
            opt.step()
            loss_v = float(loss)
        self.model.eval()
        with torch.no_grad():
            self._h = self.model.encode(P[:, 0], P[:, 1], P[:, 2])
        self.report = TrainReport(P.shape[0], len(self.nodes), len(self.rels), self.epochs, round(loss_v, 4))
        return self

    def _corrupt(self, P: torch.Tensor, rng: random.Random) -> torch.Tensor:
        """Negative samples: same head and relation, a tail of the right *type* (seen with that relation)."""
        out = []
        n = len(self.nodes)
        for s, r, o in P.tolist():
            pool = self._tails_by_rel.get(r) or list(range(n))
            for _ in range(self.negatives):
                t = rng.choice(pool) if rng.random() < 0.8 else rng.randrange(n)
                if rng.random() < 0.5:
                    out.append([s, r, t])
                else:
                    out.append([rng.randrange(n), r, o])
        return torch.tensor(out)

    def plausibility(self, triple: Triple) -> Optional[float]:
        """Probability-like score in [0, 1], or None if a concept/relation is unknown to the network."""
        if self.model is None or self._h is None:
            return None
        s, r, o = triple
        if s not in self.nodes or o not in self.nodes or r not in self.rels:
            return None
        with torch.no_grad():
            logit = self.model.score(self._h, torch.tensor([self.nodes[s]]), torch.tensor([self.rels[r]]),
                                     torch.tensor([self.nodes[o]]))
        return float(torch.sigmoid(logit)[0])

    def similar(self, concept: str, k: int = 5) -> List[Tuple[str, float]]:
        if self._h is None or concept not in self.nodes:
            return []
        h = F.normalize(self._h, dim=1)
        sims = h @ h[self.nodes[concept]]
        names = {i: n for n, i in self.nodes.items()}
        order = torch.argsort(sims, descending=True).tolist()
        return [(names[i], round(float(sims[i]), 3)) for i in order
                if names[i] != concept and names[i] != YES][:k]
