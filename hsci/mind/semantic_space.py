"""Sub-symbolic layer: learned vector representations over the symbolic knowledge.

Two representations, both learned from data rather than written by hand:

* **Lexical (character n-gram) vectors** give perception tolerance to typos and
  inflection ("mamal" -> "mammal"), so grounding does not fail on surface noise.
* **Distributional concept embeddings** are factorised (PPMI + truncated SVD) from
  the knowledge closure itself: symbols that take part in similar facts and rules
  end up close together. They power "what is similar to X?" and suggestions for
  unknown terms.

Neither layer ever decides truth. They only propose candidates (which symbol was
meant, which concepts are related); every answer still has to be proven by the
reasoner and checked by the verifier. This is the "neural proposes, symbolic
disposes" contract of the architecture. The interface is deliberately small so a
pretrained sentence encoder can replace these vectors later without touching the
reasoning core.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from hsci.mind.logic import IS, Rule


def _grams(word: str, n: int = 3) -> Counter:
    w = f"#{word.lower()}#"
    return Counter(w[i:i + n] for i in range(max(1, len(w) - n + 1)))


def lexical_similarity(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    inter = sum((ga & gb).values())
    return 2 * inter / max(1, sum(ga.values()) + sum(gb.values()))


def fuzzy_match(word: str, vocabulary: Iterable[str], threshold: float = 0.72) -> Optional[Tuple[str, float]]:
    best: Optional[Tuple[str, float]] = None
    for v in vocabulary:
        if v == word or abs(len(v) - len(word)) > max(3, len(word) // 2):
            continue
        s = lexical_similarity(word, v)
        if s >= threshold and (best is None or s > best[1]):
            best = (v, s)
    return best


class ConceptSpace:
    """PPMI + SVD embedding of every symbol in a knowledge closure."""

    def __init__(self, atoms: Iterable, rules: Sequence[Rule], dim: int = 32) -> None:
        contexts: Dict[str, Counter] = defaultdict(Counter)
        for a in atoms:
            if a.args and a.args[0].startswith("a typical "):
                continue
            sign = "not " if a.neg else ""
            if a.pred == IS and len(a.args) == 2:
                contexts[a.args[0]][f"{sign}is:{a.args[1]}"] += 1
                contexts[a.args[1]][f"{sign}has-member:{a.args[0]}"] += 1
            elif len(a.args) == 2:
                contexts[a.args[0]][f"{sign}{a.pred}->:{a.args[1]}"] += 1
                contexts[a.args[1]][f"{sign}<-{a.pred}:{a.args[0]}"] += 1
            elif len(a.args) == 1:
                contexts[a.args[0]][f"{sign}{a.pred}"] += 1
        for r in rules:
            for b in r.body:
                if b.pred == IS and r.head.pred == IS and len(b.args) == 2 and not b.args[1].startswith("?"):
                    head = r.head.args[1]
                    contexts[b.args[1]][f"sub-of:{head}"] += 1
                    contexts[head][f"super-of:{b.args[1]}"] += 1
        self.symbols = sorted(contexts)
        self.vectors: Optional[np.ndarray] = None
        if len(self.symbols) < 3:
            return
        feats = sorted({f for c in contexts.values() for f in c})
        fi = {f: i for i, f in enumerate(feats)}
        m = np.zeros((len(self.symbols), len(feats)))
        for i, s in enumerate(self.symbols):
            for f, n in contexts[s].items():
                m[i, fi[f]] = n
        total = m.sum()
        pr = m.sum(axis=1, keepdims=True) / total
        pc = m.sum(axis=0, keepdims=True) / total
        with np.errstate(divide="ignore", invalid="ignore"):
            pmi = np.log((m / total) / (pr @ pc))
        ppmi = np.nan_to_num(np.maximum(pmi, 0.0), nan=0.0, posinf=0.0, neginf=0.0)
        k = max(1, min(dim, min(ppmi.shape) - 1))
        u, s, _ = np.linalg.svd(ppmi, full_matrices=False)
        vec = u[:, :k] * np.sqrt(s[:k])
        norms = np.linalg.norm(vec, axis=1, keepdims=True)
        self.vectors = vec / np.where(norms == 0, 1, norms)
        self._index = {s: i for i, s in enumerate(self.symbols)}

    def similar(self, symbol: str, k: int = 5) -> List[Tuple[str, float]]:
        if self.vectors is None or symbol not in self._index:
            return []
        sims = self.vectors @ self.vectors[self._index[symbol]]
        order = np.argsort(-sims)
        return [(self.symbols[i], round(float(sims[i]), 3)) for i in order
                if self.symbols[i] != symbol and sims[i] > 0.05][:k]
