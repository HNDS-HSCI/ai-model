"""Does the concept-graph network learn real intuition? Held-out link prediction.

A world of invented classes, each with *typical* properties (held by ~85 % of its
members, so no strict rule exists and rule induction stays silent), plus a few
random exceptions. 20 % of the property facts are hidden; the network is trained on
the rest and must judge hidden true facts vs. false ones it was never told about.

    python -m hsci.mind.neural.evaluation [--seed 0]

Reports AUC (0.5 = guessing, 1.0 = perfect) and, through the full Mind, how
questions about hidden facts are answered: proven / probably (intuition) / unknown,
and whether any answer marked *verified* was wrong (must be 0).
"""
from __future__ import annotations

import argparse
import random
from typing import Dict, List, Tuple

from hsci.mind.evaluation import Words
from hsci.mind.logic import IS
from hsci.mind.neural.graph_net import ConceptGraphNet


def make_world(seed: int, n_classes: int = 5, members: int = 8, props_per_class: int = 3,
               typicality: float = 0.85, holdout: float = 0.2):
    rng = random.Random(seed)
    w = Words(rng)
    classes = [w.word() for _ in range(n_classes)]
    props = [w.word() for _ in range(n_classes * props_per_class + 4)]
    typical = {c: props[i * props_per_class:(i + 1) * props_per_class] for i, c in enumerate(classes)}
    known: List[Tuple[str, str]] = []          # (entity, class) facts
    prop_facts: List[Tuple[str, str]] = []     # (entity, property) true facts
    all_true = set()
    for c in classes:
        for _ in range(members):
            e = w.name()
            known.append((e, c))
            for p in typical[c]:
                if rng.random() < typicality:
                    prop_facts.append((e, p)); all_true.add((e, p))
            if rng.random() < 0.15:
                p = rng.choice(props); prop_facts.append((e, p)); all_true.add((e, p))
    rng.shuffle(prop_facts)
    k = int(len(prop_facts) * holdout)
    test_pos, train_pos = prop_facts[:k], prop_facts[k:]
    ents = [e for e, _ in known]
    test_neg = []
    while len(test_neg) < len(test_pos):
        pair = (rng.choice(ents), rng.choice(props))
        if pair not in all_true and pair not in test_neg:
            test_neg.append(pair)
    return known, train_pos, test_pos, test_neg


def auc(pos: List[float], neg: List[float]) -> float:
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / max(1, len(pos) * len(neg))


def run_network(seed: int) -> Dict[str, float]:
    known, train_pos, test_pos, test_neg = make_world(seed)
    triples = [(e, IS, c) for e, c in known] + [(e, IS, p) for e, p in train_pos]
    net = ConceptGraphNet(seed=seed).fit(triples)
    sp = [net.plausibility((e, IS, p)) for e, p in test_pos]
    sn = [net.plausibility((e, IS, p)) for e, p in test_neg]
    sp = [x for x in sp if x is not None]
    sn = [x for x in sn if x is not None]
    return {"auc": round(auc(sp, sn), 3),
            "pos_ge_0.5": round(sum(x >= 0.5 for x in sp) / max(1, len(sp)), 3),
            "neg_ge_0.5": round(sum(x >= 0.5 for x in sn) / max(1, len(sn)), 3),
            "links": net.report.links if net.report else 0}


def run_mind(seed: int) -> Dict[str, float]:
    from hsci.mind import Mind
    known, train_pos, test_pos, test_neg = make_world(seed)
    m = Mind(encoder="hash")
    text = " ".join([f"{e} is a {c}." for e, c in known] + [f"{e} is {p}." for e, p in train_pos])
    m.process(text, "w", direct=True)
    out = {"pos": {}, "neg": {}}
    wrong_verified = 0
    for label, pairs in (("pos", test_pos), ("neg", test_neg)):
        for e, p in pairs:
            it = m.process(f"Is {e} {p}?", "w").items[-1]
            kind = ("yes" if it.answer.startswith("Yes") else "no" if it.answer.startswith("No") else
                    "probably yes" if it.answer.lower().startswith("probably yes") or "intuition says yes" in it.answer.lower()
                    else "probably not" if "probably not" in it.answer.lower() else "unknown")
            out[label][kind] = out[label].get(kind, 0) + 1
            if it.verified and ((label == "pos" and kind == "no") or (label == "neg" and kind == "yes")):
                wrong_verified += 1
    out["wrong_verified"] = wrong_verified
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mind", action="store_true", help="also evaluate end-to-end through the Mind")
    args = ap.parse_args()
    print("network:", run_network(args.seed))
    if args.mind:
        print("mind:", run_mind(args.seed))


if __name__ == "__main__":
    main()
