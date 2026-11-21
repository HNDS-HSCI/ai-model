"""Evaluation harness for the HSCI Mind.

The generated suites use **invented words** ("Every zorb is a blick") in randomised
structures with answers known by construction. The system has never seen these
words, so the only way to score is genuine parsing + reasoning: this is the test
that the architecture contains no domain hard-coding.

    python -m hsci.mind.evaluation              # all suites, 25 problems each
    python -m hsci.mind.evaluation --n 100 --seed 7 --out results/mind_eval.json
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from hsci.mind.lexicon import FUNCTION_WORDS, pluralize, singularize
from hsci.mind.mind import Mind

_ONSETS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "t", "v", "z", "bl", "dr", "gr", "kl", "pr", "tr", "sn", "fl"]
_VOWELS = ["a", "e", "i", "o", "u"]
_CODAS = ["b", "d", "g", "k", "m", "n", "p", "t", "rk", "nd", "mp", "lt", "rb", "ng"]


@dataclass
class Problem:
    suite: str
    context: List[str]
    question: str
    expect: str            # yes | no | unknown | contains:<text> | number:<value>
    note: str = ""


@dataclass
class Result:
    problem: Problem
    answer: str
    status: str
    verified: bool
    correct: bool
    latency_ms: float


class Words:
    """Pronounceable nonce words, guaranteed unique and free of English inflection traps."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.used: set = set()

    def word(self) -> str:
        while True:
            w = self.rng.choice(_ONSETS) + self.rng.choice(_VOWELS) + self.rng.choice(_CODAS)
            if self.rng.random() < 0.4:
                w += self.rng.choice(_VOWELS) + self.rng.choice(_CODAS)
            if w not in self.used and len(w) >= 3 and w not in FUNCTION_WORDS and singularize(w) == w:
                self.used.add(w)
                return w

    def name(self) -> str:
        return self.word().capitalize()


def _class_rule(rng: random.Random, a: str, b: str) -> str:
    return rng.choice([f"Every {a} is a {b}.", f"All {pluralize(a)} are {pluralize(b)}.",
                       f"A {a} is a {b}.", f"Each {a} is a {b}.", f"A {a} is a kind of {b}."])


def gen_taxonomy(rng: random.Random, w: Words) -> Problem:
    depth = rng.randint(1, 5)
    classes = [w.word() for _ in range(depth + 1)]
    ent = w.name()
    ctx = [_class_rule(rng, classes[i], classes[i + 1]) for i in range(depth)]
    ctx.append(f"{ent} is a {classes[0]}.")
    distractor = w.word()
    other = w.name()
    ctx.append(f"{other} is a {distractor}.")
    rng.shuffle(ctx)
    kind = rng.choice(["yes", "no", "unknown", "generic"])
    if kind == "yes":
        return Problem("taxonomy", ctx, f"Is {ent} a {classes[-1]}?", "yes", f"depth {depth}")
    if kind == "generic":
        return Problem("taxonomy", ctx, f"Is a {classes[0]} a {classes[-1]}?", "yes", f"generic depth {depth}")
    if kind == "no":
        neg = w.word()
        ctx.append(f"No {classes[-1]} is a {neg}.")
        return Problem("taxonomy", ctx, f"Is {ent} a {neg}?", "no", f"depth {depth}+neg")
    return Problem("taxonomy", ctx, f"Is {ent} a {distractor}?", "unknown", "open world")


def gen_conditional(rng: random.Random, w: Words) -> Problem:
    """ProofWriter-style: attribute chains through if-then rules, some with conjunctions."""
    depth = rng.randint(1, 4)
    attrs = [w.word() for _ in range(depth + 2)]
    ent = w.name()
    ctx = [f"{ent} is {attrs[0]}.", f"{ent} is {attrs[-1]}."]
    for i in range(depth):
        if i == 0 and rng.random() < 0.5:
            ctx.append(f"If someone is {attrs[0]} and {attrs[-1]} then they are {attrs[1]}.")
        else:
            ctx.append(rng.choice([f"If someone is {attrs[i]} then they are {attrs[i + 1]}.",
                                   f"If something is {attrs[i]}, it is {attrs[i + 1]}.",
                                   f"Anyone who is {attrs[i]} is {attrs[i + 1]}."]))
    rng.shuffle(ctx)
    if rng.random() < 0.75:
        return Problem("conditional", ctx, f"Is {ent} {attrs[depth]}?", "yes", f"depth {depth}")
    other = w.name()
    ctx.append(f"{other} is {attrs[-1]}.")
    return Problem("conditional", ctx, f"Is {other} {attrs[depth]}?", "unknown", "missing premise")


def gen_comparative(rng: random.Random, w: Words) -> Problem:
    n = rng.randint(3, 6)
    people = [w.name() for _ in range(n)]      # people[0] is the most <adj>
    adj = w.word()
    comp = adj + "er"
    ctx = [f"{people[i]} is {comp} than {people[i + 1]}." for i in range(n - 1)]
    rng.shuffle(ctx)
    kind = rng.choice(["super", "yes", "no"])
    if kind == "super":
        return Problem("comparative", ctx, f"Who is the {adj}est?", f"contains:{people[0]}", f"{n} people")
    i, j = sorted(rng.sample(range(n), 2))
    if kind == "yes":
        return Problem("comparative", ctx, f"Is {people[i]} {comp} than {people[j]}?", "yes", "transitive")
    return Problem("comparative", ctx, f"Is {people[j]} {comp} than {people[i]}?", "no", "asymmetric")


def gen_relation(rng: random.Random, w: Words) -> Problem:
    verb = w.word()
    n = rng.randint(3, 5)
    ents = [w.name() for _ in range(n)]
    ctx = [f"{ents[i]} {verb}s {ents[i + 1]}." for i in range(n - 1)] + [f"{verb.capitalize()} is transitive."]
    rng.shuffle(ctx)
    kind = rng.choice(["yes", "who", "unknown"])
    if kind == "yes":
        return Problem("relation", ctx, f"Does {ents[0]} {verb} {ents[-1]}?", "yes", f"chain {n}")
    if kind == "who":
        return Problem("relation", ctx, f"Who {verb}s {ents[-1]}?", f"contains:{ents[0]}", "wh over closure")
    return Problem("relation", ctx, f"Does {ents[-1]} {verb} {ents[0]}?", "unknown", "no reverse")


def gen_default(rng: random.Random, w: Words) -> Problem:
    cls, ability = w.word(), w.word()
    a, b = w.name(), w.name()
    ctx = [f"{pluralize(cls).capitalize()} can {ability}.", f"{a} is a {cls}.", f"{b} is a {cls}.", f"{b} cannot {ability}."]
    if rng.random() < 0.5:
        return Problem("default", ctx, f"Can {a} {ability}?", "yes", "default applies")
    return Problem("default", ctx, f"Can {b} {ability}?", "no", "exception blocks default")


def gen_quantity(rng: random.Random, w: Words) -> Problem:
    x, y, z, t = w.word(), w.word(), w.word(), w.word()
    a, b, c = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 9)
    ctx = [f"The {z} equals the {x} times the {y}.", f"The {t} equals the {z} plus {c}.",
           f"The {x} is {a}.", f"The {y} is {b}."]
    rng.shuffle(ctx)
    if rng.random() < 0.5:
        return Problem("quantity", ctx, f"What is the {t}?", f"number:{a * b + c}", "two-step chain")
    return Problem("quantity", ctx, f"What is the {z}?", f"number:{a * b}", "one step")


def gen_algebra(rng: random.Random, w: Words) -> Problem:
    x = rng.randint(-9, 12)
    a = rng.choice([2, 3, 4, 5, 7])
    b = rng.randint(-20, 20)
    return Problem("algebra", [], f"solve {a}x + {b} = {a * x + b}".replace("+ -", "- "), f"contains:x = {x}", "linear")


SUITES: Dict[str, Callable[[random.Random, Words], Problem]] = {
    "taxonomy": gen_taxonomy, "conditional": gen_conditional, "comparative": gen_comparative,
    "relation": gen_relation, "default": gen_default, "quantity": gen_quantity, "algebra": gen_algebra,
}


def judge(expect: str, answer: str, status: str) -> bool:
    a = answer.strip()
    if expect == "yes":
        return status == "answered" and a.startswith("Yes")
    if expect == "no":
        return status == "answered" and a.startswith("No")
    if expect == "unknown":
        return status == "unknown"
    if expect.startswith("contains:"):
        return status == "answered" and expect.split(":", 1)[1].lower() in a.lower()
    if expect.startswith("number:"):
        want = float(expect.split(":", 1)[1])
        import re
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", a)]
        return status == "answered" and any(abs(n - want) < 1e-6 for n in nums)
    return False


def run(n: int = 25, seed: int = 0, suites: List[str] | None = None, mind: Mind | None = None) -> Tuple[List[Result], dict]:
    rng = random.Random(seed)
    mind = mind or Mind()
    results: List[Result] = []
    for suite in suites or list(SUITES):
        for i in range(n):
            w = Words(rng)
            p = SUITES[suite](rng, w)
            world = f"eval-{suite}-{seed}-{i}"
            mind.reset(world)
            if p.context:
                mind.process(" ".join(p.context), world)
            t0 = time.perf_counter()
            items = mind.process(p.question, world).items
            ms = (time.perf_counter() - t0) * 1000
            it = items[-1] if items else None
            ans, status, ver = (it.answer, it.status, it.verified) if it else ("", "error", False)
            results.append(Result(p, ans, status, ver, judge(p.expect, ans, status), ms))
            mind.reset(world)
    return results, summarise(results)


def summarise(results: List[Result]) -> dict:
    by: Dict[str, List[Result]] = {}
    for r in results:
        by.setdefault(r.problem.suite, []).append(r)
    rows = {}
    for s, rs in by.items():
        answered = [r for r in rs if r.status == "answered"]
        rows[s] = {"n": len(rs), "accuracy": round(sum(r.correct for r in rs) / len(rs), 4),
                   "verified_rate_of_answered": round(sum(r.verified for r in answered) / max(1, len(answered)), 4),
                   "median_ms": round(statistics.median(r.latency_ms for r in rs), 2)}
    total = len(results)
    return {"suites": rows, "overall_accuracy": round(sum(r.correct for r in results) / max(1, total), 4), "n": total}


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate the HSCI Mind on generated nonce-word reasoning problems")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--suite", action="append")
    ap.add_argument("--out")
    ap.add_argument("--show-failures", action="store_true")
    args = ap.parse_args()
    results, summary = run(args.n, args.seed, args.suite)
    print(f"{'suite':<13}{'n':>5}{'accuracy':>10}{'verified':>10}{'median ms':>11}")
    for s, row in summary["suites"].items():
        print(f"{s:<13}{row['n']:>5}{row['accuracy']:>10.1%}{row['verified_rate_of_answered']:>10.1%}{row['median_ms']:>11}")
    print(f"{'overall':<13}{summary['n']:>5}{summary['overall_accuracy']:>10.1%}")
    if args.show_failures:
        for r in results:
            if not r.correct:
                print("\nFAIL", r.problem.suite, r.problem.note, "| expect", r.problem.expect)
                print("  ctx:", " ".join(r.problem.context))
                print("  Q:", r.problem.question, "->", r.status, "|", r.answer)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "failures": [
                {"suite": r.problem.suite, "context": r.problem.context, "question": r.problem.question,
                 "expect": r.problem.expect, "answer": r.answer, "status": r.status}
                for r in results if not r.correct]}, fh, indent=2)


if __name__ == "__main__":
    main()
