"""How well does the *learned* parser understand sentences it has never seen?

The neural parser trains only on the Mind's experience memory. It is then tested on
new sentences built from invented words, in many sentence shapes. The grammar is
used only to provide the correct answer for scoring -- never to help the network.

    python -m hsci.mind.understanding.neural_eval [--k 10] [--seed 0]
"""
from __future__ import annotations

import argparse
import random
import time
from typing import Dict, List, Tuple

from hsci.mind.evaluation import Words
from hsci.mind.lexicon import pluralize
from hsci.mind.parser import ParseContext, SemanticParser, Unparsed
from hsci.mind.understanding import meaning as mn
from hsci.mind.understanding.engine import dialogue_lexicon, utterance_tokens
from hsci.mind.understanding.neural_parser import NeuralSemanticParser

# Sentence shapes (all within what the grammar can score). {N},{M} names; {a},{b} adjectives;
# {c},{d} nouns; {v} a verb (3rd person added where needed).
SHAPES: List[str] = [
    "{N} is a {c}.", "{N} is {a}.", "All {c}s are {d}s.", "Every {c} is a {d}.", "No {c} is a {d}.",
    "A {c} is a {d}.", "{N} {v}s {M}.", "{N} is not {a}.", "{N} can {v}.", "{N} is {a}er than {M}.",
    "If someone is {a} then they are {b}.", "Is {N} a {c}?", "Is {N} {a}?", "Who {v}s {M}?",
    "What does {N} {v}?", "Who is the {a}est?", "Can {N} {v}?", "Is a {c} a {d}?", "Does {N} {v} {M}?",
    "Why is {N} {a}?",
]


def fill(shape: str, w: Words) -> str:
    s = {"N": w.name(), "M": w.name(), "a": w.word(), "b": w.word(), "c": w.word(), "d": w.word(), "v": w.word()}
    out = shape.format(**s)
    # use the real plural for {c}s / {d}s
    for k in ("c", "d"):
        out = out.replace(s[k] + "s ", pluralize(s[k]) + " ").replace(s[k] + "s.", pluralize(s[k]) + ".")
    return out


def experiences_from_seed() -> List[Tuple[str, List[dict], str, float]]:
    from hsci.mind import Mind
    m = Mind(encoder="hash")
    rows = m.kb._conn.execute("SELECT text, meaning, source FROM experiences").fetchall()
    import json
    return [(r["text"], json.loads(r["meaning"]), r["source"], 0.9) for r in rows]


def run(k: int = 10, seed: int = 0) -> Dict[str, Dict[str, int]]:
    exps = experiences_from_seed()
    net = NeuralSemanticParser(dialogue_lexicon()["fillers"], seed=seed)
    t0 = time.perf_counter()
    net.fit(exps)
    train_s = time.perf_counter() - t0
    grammar = SemanticParser()
    rng = random.Random(seed)
    res: Dict[str, Dict[str, int]] = {}
    for shape in SHAPES:
        row = {"correct": 0, "wrong": 0, "none": 0}
        for _ in range(k):
            sent = fill(shape, Words(rng))
            gold = grammar.parse(sent, ParseContext())
            gold_md = mn.meanings_to_dicts(gold) if gold and not any(isinstance(g, Unparsed) for g in gold) else None
            readings = net.read(utterance_tokens(sent), sent)
            if not readings:
                row["none"] += 1
            elif gold_md and mn.key(readings[0].meaning) == mn.key(gold_md):
                row["correct"] += 1
            else:
                row["wrong"] += 1
        res[shape] = row
    res["_meta"] = {"experiences": len(exps), "constructions": len(net.constructions), "train_seconds": round(train_s, 1)}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    res = run(args.k, args.seed)
    meta = res.pop("_meta")
    print(meta)
    tot = {"correct": 0, "wrong": 0, "none": 0}
    for shape, row in res.items():
        print(f"{shape:<40} correct {row['correct']:>2}  wrong {row['wrong']:>2}  no-reading {row['none']:>2}")
        for k2 in tot:
            tot[k2] += row[k2]
    n = sum(tot.values())
    print(f"overall: correct {tot['correct'] / n:.0%}  wrong {tot['wrong'] / n:.0%}  no-reading {tot['none'] / n:.0%}")


if __name__ == "__main__":
    main()
