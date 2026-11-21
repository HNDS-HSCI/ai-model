"""Does understanding come from experience? A learning-curve evaluation.

For phrasings the Mind has never seen, each with a known meaning:

1. **before** -- try K sentences in that phrasing (fresh invented words each time),
2. **teach** -- explain *one* example ("this means that"), exactly as a person would,
3. **after** -- try K *new* sentences in the same phrasing with *different* words.

Each attempt is scored:
    correct  acted on the right meaning
    asked    not confident enough, asked instead of acting (safe)
    wrong    acted on a wrong meaning (the failure that matters most)

Learning from experience shows up as asked/wrong -> correct after one example,
with no code change.

    python -m hsci.mind.understanding.evaluation [--k 8] [--encoder hash|neural]
"""
from __future__ import annotations

import argparse
import random
from typing import Dict, List, Tuple

from hsci.mind.evaluation import Words
from hsci.mind.mind import Mind
from hsci.mind.understanding import meaning as mn
from hsci.mind.understanding.engine import ACT

# (surface phrasing, canonical phrasing). {N},{M} names; {a},{b} adjectives; {c} a category noun.
CONSTRUCTIONS: List[Tuple[str, str]] = [
    ("{N} is known to be {a}.", "{N} is {a}."),
    ("{N} happens to be a {c}.", "{N} is a {c}."),
    ("I wonder if {N} is {a}.", "Is {N} {a}?"),
    ("Please let me know whether {N} is a {c}.", "Is {N} a {c}?"),
    ("{N} has {M} as a friend.", "{N} is a friend of {M}."),
    ("Any {c} you meet is {a}.", "Every {c} is {a}."),
    ("What place is {N} in?", "What is {N} in?"),
    ("Out of everyone, who is {a}?", "Who is {a}?"),
]


def _fill(template: str, slots: Dict[str, str]) -> str:
    return template.format(**slots)


def _slots(w: Words) -> Dict[str, str]:
    return {"N": w.name(), "M": w.name(), "a": w.word(), "b": w.word(), "c": w.word()}


def classify(mind: Mind, surface: str, canonical: str, world: str) -> str:
    ctx = mind._context(world, mind._state(world))
    readings = mind.understanding.understand(surface, ctx)
    want = mn.meanings_to_dicts(mind.parser.parse(canonical, ctx))
    if not readings or readings[0].confidence < ACT:
        return "asked"
    return "correct" if want and mn.key(readings[0].meaning) == mn.key(want) else "wrong"


def run(k: int = 8, seed: int = 0, encoder: str = "hash") -> Dict[str, Dict[str, Dict[str, int]]]:
    rng = random.Random(seed)
    results: Dict[str, Dict[str, Dict[str, int]]] = {}
    for surface_t, canonical_t in CONSTRUCTIONS:
        mind = Mind(encoder=encoder)
        if encoder != "hash":
            mind.understanding.encoders.wait(180)
        w = Words(rng)
        row = {"before": {"correct": 0, "asked": 0, "wrong": 0}, "after": {"correct": 0, "asked": 0, "wrong": 0}}
        for _ in range(k):
            s = _slots(w)
            row["before"][classify(mind, _fill(surface_t, s), _fill(canonical_t, s), "e")] += 1
        s = _slots(w)
        mind.teach(_fill(surface_t, s), _fill(canonical_t, s), "e")        # one example, like a person explaining
        for _ in range(k):
            s = _slots(w)
            row["after"][classify(mind, _fill(surface_t, s), _fill(canonical_t, s), "e")] += 1
        results[surface_t] = row
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--encoder", default="hash", choices=["hash", "neural"])
    args = ap.parse_args()
    res = run(args.k, args.seed, args.encoder)
    print(f"{'phrasing':<44}{'before (ok/ask/wrong)':>24}{'after 1 example':>20}")
    tot = {"before": [0, 0, 0], "after": [0, 0, 0]}
    for phr, row in res.items():
        cells = []
        for phase in ("before", "after"):
            r = row[phase]
            cells.append(f"{r['correct']}/{r['asked']}/{r['wrong']}")
            for i, key in enumerate(("correct", "asked", "wrong")):
                tot[phase][i] += r[key]
        print(f"{phr:<44}{cells[0]:>24}{cells[1]:>20}")
    n = sum(tot["before"])
    for phase in ("before", "after"):
        c, a, wr = tot[phase]
        print(f"{phase:>6}: correct {c / n:.0%}   asked {a / n:.0%}   wrong {wr / n:.0%}")


if __name__ == "__main__":
    main()
