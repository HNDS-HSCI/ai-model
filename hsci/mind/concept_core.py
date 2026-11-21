"""Concept core (prototype): concepts as small typed programs that are learned, linked and reused.

A concept is NOT a vector and NOT a row in a table. It is a named, typed, executable
definition built out of other concepts:

    even(x)      = eq(mod(x, 2), 0)                      learned from 6 examples
    odd(x)       = not(even(x))                          learned from 6 examples, uses `even`
    prime(x)     = eq(count(divides, x), 2)              uses `divides`
    plural(w)    = if hisses(w) then w+"es" else ...     uses `hisses`, `consonant`, `penult`

Three ways a concept enters the library:

    teach_set   told by listing members        ("the vowels are a, e, i, o, u")
    tell        told as a definition           (a composition of known concepts)
    learn       shown input/output examples    (search for the smallest program that fits)

`learn` is bottom-up enumeration over the current library, with two standard tricks:
observational equivalence (two candidates that behave the same on the examples are the
same candidate) and decision lists (different programs for different groups of examples,
separated by a learned guard). Recursive concepts use the examples themselves as the
answer for the smaller case, the way a child is shown 3! before 4!.

Nothing about numbers, primes, plurals or tenses is in this file: only ~20 domain-general
primitives. Run ``python -m hsci.mind.concept_core`` for the curriculum experiment.
"""
from __future__ import annotations

import itertools
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

INT, BOOL, STR, REL = "int", "bool", "str", "rel"
_COMMUTATIVE = {"add", "mul", "eq", "and", "or", "same"}
_MAX_INT, _MAX_STR, _MAX_DEPTH = 10 ** 7, 40, 200

Example = Tuple[Tuple[Any, ...], Any]


def type_of(v: Any) -> str:
    if isinstance(v, bool):
        return BOOL
    if isinstance(v, int):
        return INT
    if isinstance(v, str):
        return STR
    raise TypeError(f"unsupported value {v!r}")


@dataclass
class Concept:
    name: str
    args: Tuple[str, ...]
    ret: str
    fn: Callable
    kind: str = "primitive"            # primitive | set | told | learned
    body: Any = None                   # expression tree (None for primitives)
    uses: Tuple[str, ...] = ()         # links to the concepts this one is built from
    examples: List[Example] = field(default_factory=list)
    size: int = 1
    candidates: int = 0                # how many candidate programs the search evaluated
    seconds: float = 0.0


def _ok(v: Any) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, int):
        return abs(v) <= _MAX_INT
    if isinstance(v, str):
        return len(v) <= _MAX_STR
    return True


def _mod(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("mod by non-positive")
    return a % b


def _drop_last(s: str, n: int) -> str:
    if n < 0 or n > len(s):
        raise ValueError("drop out of range")
    return s[:len(s) - n]


def _count(rel: Callable, n: int) -> int:
    """How many d in 1..n stand in relation rel(d, n)? (bounded counting, domain-general)"""
    if n < 0 or n > 5000:
        raise ValueError("count out of range")
    return sum(1 for d in range(1, n + 1) if rel(d, n))


def _measure(v: Any) -> Optional[int]:
    if isinstance(v, bool):
        return None
    return abs(v) if isinstance(v, int) else len(v)


class Library:
    def __init__(self) -> None:
        self.concepts: Dict[str, Concept] = {}
        p = lambda n, a, r, f: self.concepts.__setitem__(n, Concept(n, a, r, f))
        p("add", (INT, INT), INT, lambda a, b: a + b)
        p("sub", (INT, INT), INT, lambda a, b: a - b)
        p("mul", (INT, INT), INT, lambda a, b: a * b)
        p("mod", (INT, INT), INT, _mod)
        p("eq", (INT, INT), BOOL, lambda a, b: a == b)
        p("lt", (INT, INT), BOOL, lambda a, b: a < b)
        p("and", (BOOL, BOOL), BOOL, lambda a, b: a and b)
        p("or", (BOOL, BOOL), BOOL, lambda a, b: a or b)
        p("not", (BOOL,), BOOL, lambda a: not a)
        p("concat", (STR, STR), STR, lambda a, b: a + b)
        p("drop_last", (STR, INT), STR, _drop_last)
        p("last", (STR,), STR, lambda s: s[-1])
        p("first", (STR,), STR, lambda s: s[0])
        p("ends_with", (STR, STR), BOOL, lambda s, t: s.endswith(t))
        p("same", (STR, STR), BOOL, lambda a, b: a == b)
        p("length", (STR,), INT, len)
        p("count", (REL, INT), INT, _count)

    # ------------------------------------------------------------ execution
    def run(self, expr: Any, env: Sequence[Any], me: Optional[Callable], depth: int = 0) -> Any:
        tag = expr[0]
        if tag == "x":
            return env[expr[1]]
        if tag == "k":
            return expr[1]
        if tag == "ref":
            return self.concepts[expr[1]].fn
        if tag == "member":
            return env[0] in expr[1]
        if tag == "if":
            return self.run(expr[2] if self.run(expr[1], env, me, depth) else expr[3], env, me, depth)
        args = [self.run(a, env, me, depth) for a in expr[-1]]
        if tag == "rec":
            if depth >= _MAX_DEPTH or me is None:
                raise RecursionError("recursion too deep")
            return me(args, depth + 1)
        return self.concepts[expr[1]].fn(*args)

    def _make(self, name: str, args: Tuple[str, ...], ret: str, body: Any, kind: str, examples=()) -> Concept:
        cache: Dict[tuple, Any] = {}      # concepts are pure functions, so results can be remembered

        def me(a, depth):
            a = tuple(a)
            if a in cache:
                hit = cache[a]
                if isinstance(hit, Exception):
                    raise hit
                return hit
            try:
                cache[a] = self.run(body, a, me, depth)
            except RecursionError:
                raise
            except Exception as exc:
                cache[a] = exc
                raise
            return cache[a]

        uses = tuple(sorted({u for u in _names(body) if self.concepts[u].kind != "primitive"}))
        return Concept(name, args, ret, lambda *a: me(a, 0), kind, body, uses, list(examples), _size(body))

    def call(self, name: str, *args: Any) -> Any:
        return self.concepts[name].fn(*args)

    # ------------------------------------------------------------ being told
    def teach_set(self, name: str, members: Sequence[Any]) -> Concept:
        c = self._make(name, (type_of(members[0]),), BOOL, ("member", tuple(members)), "set")
        self.concepts[name] = c
        return c

    def tell(self, name: str, args: Tuple[str, ...], ret: str, body: Any) -> Concept:
        c = self._make(name, args, ret, body, "told")
        self.concepts[name] = c
        return c

    # ------------------------------------------------------------ being shown
    def learn(self, name: str, examples: List[Example], max_size: int = 11, timeout: float = 10.0,
              use_library: bool = True, register: bool = True) -> Optional[Concept]:
        """Find the smallest program over the library that fits the examples."""
        start = time.time()
        args = tuple(type_of(v) for v in examples[0][0])
        ret = type_of(examples[0][1])
        pool = [c for c in self.concepts.values()
                if c.name != name and (use_library or c.kind == "primitive")]
        found, candidates = self._search(args, ret, examples, pool, max_size, start + timeout)
        if found is None:
            return None
        c = self._make(name, args, ret, found, "learned", examples)
        c.candidates, c.seconds = candidates, time.time() - start
        if register:
            self.concepts[name] = c
        return c

    def _constants(self, args: Tuple[str, ...], ret: str, examples: List[Example]) -> List[Any]:
        consts: List[Any] = [0, 1, 2]
        if ret == BOOL:
            consts += [True, False]
        strs: List[str] = []
        for ins, out in examples:
            words = [v for v in ins if isinstance(v, str)]
            for w in words:                        # endings a guard might need
                strs += [w[-1:], w[-2:]]
            if isinstance(out, str) and words:     # what was added / removed
                w = words[0]
                k = 0
                while k < min(len(w), len(out)) and w[k] == out[k]:
                    k += 1
                strs += [out[k:], w[k:]] if k else [out]
        seen: set = set()
        for s in strs:
            if s and len(s) <= 4 and s not in seen:
                seen.add(s)
                consts.append(s)
        return consts

    def _search(self, args, ret, examples, pool: List[Concept], max_size: int, deadline: float):
        n = len(examples)
        ins = [e[0] for e in examples]
        outs = tuple(e[1] for e in examples)
        table = {e[0]: e[1] for e in examples}
        bank: Dict[str, Dict[int, list]] = defaultdict(lambda: defaultdict(list))   # type -> size -> [(expr, vals, has_var)]
        seen: Dict[str, set] = defaultdict(set)
        count = [0]

        def put(t: str, size: int, expr: Any, vals: tuple, has_var: bool) -> None:
            count[0] += 1
            if all(v is None for v in vals) or vals in seen[t]:
                return
            seen[t].add(vals)
            bank[t][size].append((expr, vals, has_var))

        for i, t in enumerate(args):
            put(t, 1, ("x", i), tuple(inp[i] for inp in ins), True)
        for k in self._constants(args, ret, examples):
            # A specific constant costs more than a variable: "b > a" is a simpler idea than "b > 2".
            put(type_of(k), 2, ("k", k), (k,) * n, False)
        for c in pool:
            if c.args == (INT, INT) and c.ret == BOOL and c.kind != "primitive":
                put(REL, 1, ("ref", c.name), (c.fn,) * n, False)

        def rec_fn(e: int, *a: Any) -> Any:
            if a == ins[e] or a not in table:
                return None
            if not any(_measure(x) is not None and _measure(x) < _measure(y) for x, y in zip(a, ins[e])):
                return None       # the recursive call must be on a smaller case
            return table[a]

        callables = [(c.name, c.args, c.ret, c.fn, False) for c in pool] + [("rec", args, ret, rec_fn, True)]
        best: Optional[Tuple[int, Any]] = None             # (total size, expr): smaller is better
        for size in range(2, max_size + 1):
            for cname, cargs, cret, fn, is_rec in callables:
                k = len(cargs)
                for sizes in _compositions(size - 1, k):
                    if cname in _COMMUTATIVE and sizes[0] > sizes[1]:
                        continue
                    pools = [bank[cargs[j]][sizes[j]] for j in range(k)]
                    if any(not p for p in pools):
                        continue
                    for combo in itertools.product(*pools):
                        if not (count[0] & 1023) and time.time() > deadline:
                            return (best[1] if best else None), count[0]
                        if not any(c[2] for c in combo):
                            count[0] += 1
                            continue      # constant-only expression
                        vals = []
                        for e in range(n):
                            a = [c[1][e] for c in combo]
                            if any(x is None for x in a):
                                vals.append(None)
                                continue
                            try:
                                v = fn(e, *a) if is_rec else fn(*a)
                                vals.append(v if v is None or _ok(v) else None)
                            except Exception:
                                vals.append(None)
                        expr = ("rec", tuple(c[0] for c in combo)) if is_rec else \
                            ("call", cname, tuple(c[0] for c in combo))
                        put(cret, size, expr, tuple(vals), True)
            # a single program that fits everything is the best possible answer
            for expr, vals, _ in bank[ret][size]:
                if vals == outs and self._fits(args, ret, expr, examples):
                    return expr, count[0]
            dl = self._decision_list(bank, ret, outs, n)
            if dl and (best is None or dl[1] < best[0]) and self._fits(args, ret, dl[0], examples):
                best = (dl[1], dl[0])
            if best and size >= best[0] - 3:
                break      # every piece of a smaller rule would already have been enumerated
        return (best[1] if best else None), count[0]

    def _fits(self, args, ret, expr, examples) -> bool:
        c = self._make("?", args, ret, expr, "learned")
        try:
            return all(c.fn(*i) == o for i, o in examples)
        except Exception:
            return False

    @staticmethod
    def _decision_list(bank, ret: str, outs: tuple, n: int):
        full = (1 << n) - 1
        progs: Dict[int, Tuple[int, Any]] = {}
        for size in sorted(bank[ret]):
            for expr, vals, _ in bank[ret][size]:
                m = sum(1 << i for i in range(n) if vals[i] is not None and vals[i] == outs[i])
                if m and m not in progs:
                    progs[m] = (size, expr)
        guards: Dict[Tuple[int, int], Tuple[int, Any]] = {}
        for size in sorted(bank[BOOL]):
            for expr, vals, has_var in bank[BOOL][size]:
                if not has_var:
                    continue
                key = (sum(1 << i for i in range(n) if vals[i] is True),
                       sum(1 << i for i in range(n) if vals[i] is not None))
                guards.setdefault(key, (size, expr))
        plist = sorted(progs.items(), key=lambda kv: kv[1][0])

        def prog_for(mask: int):
            return next(((sz, e) for m, (sz, e) in plist if m & mask == mask), None)

        memo: Dict[int, Any] = {}

        def build(rem: int, depth: int):
            if rem in memo:
                return memo[rem]
            p = prog_for(rem)
            if p:
                memo[rem] = (p[1], p[0], 1)
                return memo[rem]
            if depth >= 6:
                return None
            choices: Dict[int, tuple] = {}
            for (t, d), (gs, ge) in guards.items():
                if d & rem != rem:
                    continue
                part = t & rem
                if part == 0 or part == rem:
                    continue
                p = prog_for(part)
                if p:
                    score = (bin(part).count("1"), -(gs + p[0]))
                    if part not in choices or score > choices[part][0]:
                        choices[part] = (score, part, ge, gs, p)
            # Try the few most promising first splits and keep the smallest complete rule.
            ranked = sorted(choices.values(), key=lambda c: c[0], reverse=True)
            result = None
            for _, part, ge, gs, p in ranked[:3 if depth < 2 else 1]:
                rest = build(rem & ~part, depth + 1)
                if rest is None:
                    continue
                cand = (("if", ge, p[1], rest[0]), gs + p[0] + rest[1] + 1, rest[2] + 1)
                if result is None or cand[1] < result[1]:
                    result = cand
            memo[rem] = result
            return result

        return build(full, 0)

    # ------------------------------------------------------------ the two "matrix" views
    def link_matrix(self) -> Tuple[List[str], List[List[int]]]:
        """Adjacency matrix of the concept graph: A[i][j] = 1 if concept i is built from concept j."""
        names = [c.name for c in self.concepts.values() if c.kind != "primitive"]
        idx = {n: i for i, n in enumerate(names)}
        a = [[0] * len(names) for _ in names]
        for c in self.concepts.values():
            if c.kind != "primitive":
                for u in c.uses:
                    a[idx[c.name]][idx[u]] = 1
        return names, a

    def fingerprint(self, name: str, probes: Sequence[tuple]) -> List[Any]:
        """Behaviour vector: what the concept does on a fixed set of probe inputs."""
        out = []
        for p in probes:
            try:
                out.append(self.concepts[name].fn(*p))
            except Exception:
                out.append(None)
        return out

    def show(self, name: str) -> str:
        c = self.concepts[name]
        names = "xyz" if len(c.args) == 1 else "abc"
        return f"{name}({', '.join(names[:len(c.args)])}) = {_show(c.body, names)}"


# ----------------------------------------------------------------- helpers

def _compositions(total: int, parts: int):
    if parts == 1:
        if total >= 1:
            yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


def _names(expr: Any) -> List[str]:
    tag = expr[0]
    if tag == "ref":
        return [expr[1]]
    if tag == "if":
        return _names(expr[1]) + _names(expr[2]) + _names(expr[3])
    if tag in ("call", "rec"):
        return ([expr[1]] if tag == "call" else []) + [n for a in expr[-1] for n in _names(a)]
    return []


def _size(expr: Any) -> int:
    tag = expr[0]
    if tag == "if":
        return 1 + _size(expr[1]) + _size(expr[2]) + _size(expr[3])
    if tag in ("call", "rec"):
        return 1 + sum(_size(a) for a in expr[-1])
    return 2 if tag == "k" else 1


def _show(expr: Any, names: str) -> str:
    tag = expr[0]
    if tag == "x":
        return names[expr[1]]
    if tag == "k":
        return repr(expr[1])
    if tag == "ref":
        return expr[1]
    if tag == "member":
        return f"{names[0]} in {set(expr[1])}"
    if tag == "if":
        return f"if {_show(expr[1], names)} then {_show(expr[2], names)} else {_show(expr[3], names)}"
    head = "SELF" if tag == "rec" else expr[1]
    return f"{head}({', '.join(_show(a, names) for a in expr[-1])})"


# ----------------------------------------------------------------- curriculum experiment

def _ex(*pairs) -> List[Example]:
    return [((i if isinstance(i, tuple) else (i,)), o) for i, o in pairs]


CURRICULUM = [
    # name, taught examples, held-out tests
    ("double", _ex((3, 6), (5, 10), (0, 0), (7, 14)), _ex((11, 22), (20, 40), (1, 2))),
    ("square", _ex((3, 9), (4, 16), (1, 1), (0, 0), (5, 25)), _ex((7, 49), (12, 144), (2, 4))),
    ("even", _ex((4, True), (7, False), (0, True), (9, False), (10, True), (3, False)),
     _ex((100, True), (51, False), (2, True), (13, False))),
    ("odd", _ex((4, False), (7, True), (0, False), (9, True), (10, False), (3, True)),
     _ex((100, False), (51, True), (2, False), (13, True))),
    ("max", _ex(((3, 5), 5), ((7, 2), 7), ((4, 4), 4), ((0, 9), 9), ((8, 1), 8)),
     _ex(((10, 20), 20), ((6, 5), 6), ((1, 1), 1))),
    ("divides", _ex(((2, 6), True), ((4, 6), False), ((3, 9), True), ((5, 9), False), ((1, 7), True),
                    ((7, 7), True), ((6, 3), False), ((2, 7), False)),
     _ex(((5, 20), True), ((6, 20), False), ((9, 81), True), ((8, 4), False))),
    ("prime", _ex((2, True), (3, True), (4, False), (5, True), (6, False), (7, True), (9, False), (1, False),
                  (11, True), (15, False)),
     _ex((13, True), (21, False), (29, True), (49, False), (97, True), (91, False))),
    ("factorial", _ex((0, 1), (1, 1), (2, 2), (3, 6), (4, 24), (5, 120)), _ex((6, 720), (7, 5040))),
    ("sum_to", _ex((0, 0), (1, 1), (2, 3), (3, 6), (4, 10), (5, 15)), _ex((6, 21), (10, 55), (20, 210))),
    ("gcd", _ex(((12, 18), 6), ((18, 12), 6), ((12, 6), 6), ((6, 0), 6), ((7, 3), 1), ((3, 1), 1), ((1, 0), 1),
                ((9, 6), 3), ((6, 3), 3), ((3, 0), 3)),
     _ex(((48, 36), 12), ((17, 5), 1), ((100, 75), 25), ((8, 12), 4))),
    ("consonant", _ex(("b", True), ("a", False), ("t", True), ("e", False), ("k", True), ("o", False),
                      ("s", True), ("u", False), ("i", False), ("m", True)),
     _ex(("z", True), ("a", False), ("r", True), ("o", False), ("y", True))),
    ("penult", _ex(("baby", "b"), ("day", "a"), ("city", "t"), ("dish", "s"), ("box", "o")),
     _ex(("church", "c"), ("play", "a"), ("try", "r"))),
    ("hisses", _ex(("bus", True), ("box", True), ("dish", True), ("church", True), ("cat", False), ("dog", False),
                   ("baby", False), ("day", False), ("buzz", True), ("kiss", True), ("tree", False),
                   ("lamp", False)),
     _ex(("fox", True), ("wish", True), ("match", True), ("glass", True), ("pen", False), ("toy", False),
         ("path", False), ("book", False))),
    ("plural", _ex(("cat", "cats"), ("dog", "dogs"), ("box", "boxes"), ("bus", "buses"), ("dish", "dishes"),
                   ("church", "churches"), ("baby", "babies"), ("city", "cities"), ("day", "days"),
                   ("toy", "toys")),
     _ex(("fox", "foxes"), ("lady", "ladies"), ("key", "keys"), ("book", "books"), ("glass", "glasses"),
         ("match", "matches"), ("party", "parties"), ("tree", "trees"))),
    ("past", _ex(("walk", "walked"), ("jump", "jumped"), ("bake", "baked"), ("love", "loved"), ("try", "tried"),
                 ("cry", "cried"), ("play", "played"), ("stay", "stayed")),
     _ex(("talk", "talked"), ("hope", "hoped"), ("carry", "carried"), ("enjoy", "enjoyed"), ("open", "opened"),
         ("dance", "danced"))),
    ("article", _ex(("apple", "an"), ("dog", "a"), ("egg", "an"), ("cat", "a"), ("owl", "an"), ("tree", "a"),
                    ("ice", "an"), ("umbrella", "an")),
     _ex(("orange", "an"), ("book", "a"), ("elephant", "an"), ("zebra", "a"))),
]


# A second, fresh test set per concept: never used for teaching or for corrections.
FRESH = {
    "double": _ex((9, 18), (15, 30), (4, 8)),
    "square": _ex((6, 36), (9, 81), (10, 100)),
    "even": _ex((22, True), (37, False), (8, True), (15, False)),
    "odd": _ex((22, False), (37, True), (8, False), (15, True)),
    "max": _ex(((2, 3), 3), ((9, 4), 9), ((5, 5), 5), ((1, 0), 1), ((6, 7), 7), ((12, 3), 12)),
    "divides": _ex(((3, 12), True), ((5, 12), False), ((4, 4), True), ((10, 5), False), ((7, 49), True),
                   ((2, 9), False)),
    "prime": _ex((17, True), (25, False), (31, True), (33, False), (2, True), (51, False), (53, True), (1, False)),
    "factorial": _ex((8, 40320), (3, 6)),
    "sum_to": _ex((7, 28), (12, 78), (100, 5050)),
    "gcd": _ex(((10, 4), 2), ((21, 14), 7), ((9, 28), 1), ((30, 12), 6), ((5, 15), 5), ((14, 21), 7)),
    "consonant": _ex(("d", True), ("e", False), ("p", True), ("u", False), ("w", True)),
    "penult": _ex(("glass", "s"), ("toy", "o"), ("river", "e")),
    "hisses": _ex(("class", True), ("tax", True), ("brush", True), ("bench", True), ("quiz", True), ("bird", False),
                  ("moon", False), ("cloth", False), ("key", False), ("cup", False)),
    "plural": _ex(("class", "classes"), ("tax", "taxes"), ("brush", "brushes"), ("bench", "benches"),
                  ("story", "stories"), ("boy", "boys"), ("bird", "birds"), ("fly", "flies"),
                  ("monkey", "monkeys"), ("cup", "cups")),
    "past": _ex(("work", "worked"), ("like", "liked"), ("study", "studied"), ("pray", "prayed"),
                ("clean", "cleaned"), ("move", "moved"), ("reply", "replied"), ("obey", "obeyed")),
    "article": _ex(("insect", "an"), ("house", "a"), ("arm", "an"), ("uncle", "an"), ("pig", "a"), ("river", "a"),
                   ("octopus", "an"), ("bench", "a")),
}


def _right(c: Optional[Concept], case: Example) -> bool:
    try:
        return c is not None and c.fn(*case[0]) == case[1]
    except Exception:
        return False


def _score(c: Optional[Concept], tests: List[Example]) -> str:
    return "not found" if c is None else f"{sum(_right(c, t) for t in tests)}/{len(tests)}"


def teach(lib: Library, name: str, examples: List[Example], tests: List[Example], timeout: float, rounds: int = 3):
    """Teach from examples, quiz, and correct with the cases it got wrong -- as a teacher would."""
    shown = list(examples)
    c = lib.learn(name, shown, timeout=timeout)
    first, added = _score(c, tests), 0
    for _ in range(rounds):
        new = [t for t in tests if not _right(c, t) and t not in shown]
        if not new:
            break
        shown += new
        added += len(new)
        c = lib.learn(name, shown, timeout=timeout) or c
    return c, first, added


def experiment(timeout: float = 8.0) -> None:
    lib = Library()
    lib.teach_set("vowel", ["a", "e", "i", "o", "u"])           # told, not searched
    print(f"{'concept':<10} {'first quiz':>10} {'corrections':>11} {'fresh test':>10} {'tried':>8} {'sec':>5}"
          f"   | primitives only, first quiz: {'score':>9} {'tried':>8}")
    rows = []
    for name, examples, tests in CURRICULUM:
        alone = Library().learn(name, examples, timeout=timeout, register=False)
        c, first, added = teach(lib, name, examples, tests, timeout)
        rows.append((name, c))
        print(f"{name:<10} {first:>10} {added:>11} {_score(c, FRESH[name]):>10} {c.candidates if c else 0:>8} "
              f"{c.seconds if c else timeout:>5.1f}   | {_score(alone, tests):>38} {alone.candidates if alone else 0:>8}")
    print("\nWhat was learned:")
    for name, c in rows:
        if c:
            print(f"  {lib.show(name)}")

    # Some concepts are a list of cases and have to be told, not guessed from a dozen examples.
    ends = lambda s: ("call", "ends_with", (("x", 0), ("k", s)))
    body = ends("s")
    for s in ("x", "z", "sh", "ch"):
        body = ("call", "or", (body, ends(s)))
    lib.tell("hisses", (STR,), BOOL, body)
    print(f"\nAfter TELLING `hisses` (ends in s, x, z, sh, ch): fresh test {_score(lib.concepts['hisses'], FRESH['hisses'])}")
    for name, examples, tests in CURRICULUM:
        if name in ("plural", "article"):
            c, first, added = teach(lib, name, examples, tests, timeout)
            if c is None:
                print(f"  {name:<8} relearning ran out of time ({timeout:.0f}s); the earlier rule is kept")
                continue
            print(f"  {name:<8} relearned: first quiz {first}, corrections {added}, fresh test {_score(c, FRESH[name])}")
            print(f"    {lib.show(name)}")

    # a concept that is told as a definition, built on a learned one
    d = lambda k: ("call", "divides", (("k", k), ("x", 0)))
    lib.tell("leap_year", (INT,), BOOL,
             ("call", "and", (d(4), ("call", "or", (("call", "not", (d(100),)), d(400))))))
    leap = [lib.call("leap_year", y) for y in (2024, 1900, 2000, 2023)]
    print(f"\nleap_year (told, built on learned `divides`): 2024,1900,2000,2023 -> {leap}")
    names, a = lib.link_matrix()
    print("\nConcept graph (row is built from column):")
    for n, row in zip(names, a):
        used = [names[j] for j, v in enumerate(row) if v]
        if used:
            print(f"  {n:<10} -> {', '.join(used)}")
    probes = [(i,) for i in range(1, 61)]
    fp = {n: lib.fingerprint(n, probes) for n in ("even", "odd", "prime")}
    agree = lambda x, y: sum(p == q for p, q in zip(fp[x], fp[y])) / len(probes)
    print(f"\nBehaviour similarity on 1..60: even~odd {agree('even', 'odd'):.2f}, "
          f"odd~prime {agree('odd', 'prime'):.2f}, even~prime {agree('even', 'prime'):.2f}")


if __name__ == "__main__" and not os.getenv("HSCI_CURIOUS"):
    experiment()


# ----------------------------------------------------------------- curiosity: ask when rules disagree

def candidates(lib: Library, name: str, examples: List[Example], timeout: float) -> List[Concept]:
    """Distinct fitting rules from different starting points (primitives only; whole library).

    A big library makes some rules unreachable in the time budget, and a small one makes
    others unreachable -- so search both and keep everything that fits.
    """
    out: List[Concept] = []
    for use_library in (True, False):
        c = lib.learn(name, examples, timeout=timeout / 2, use_library=use_library, register=False)
        if c is not None and all(_show(c.body, "ab") != _show(o.body, "ab") for o in out):
            out.append(c)
    return sorted(out, key=lambda c: c.size)


def curious_learn(lib: Library, name: str, examples: List[Example], teacher: Callable, probes: Sequence[tuple],
                  timeout: float = 8.0, max_questions: int = 6):
    """Learn; whenever two fitting rules disagree on some input, ask the teacher about that input."""
    shown, asked = list(examples), []
    known = {e[0] for e in shown}
    while True:
        cands = candidates(lib, name, shown, timeout)
        if not cands:
            return None, asked
        question = None
        if len(cands) > 1 and len(asked) < max_questions:
            for p in probes:
                if p in known:
                    continue
                answers = set()
                for c in cands:
                    try:
                        answers.add(repr(c.fn(*p)))
                    except Exception:
                        answers.add("error")
                if len(answers) > 1:
                    question = p
                    break
        if question is None:
            best = cands[0]
            lib.concepts[name] = lib._make(name, best.args, best.ret, best.body, "learned", shown)
            lib.concepts[name].candidates, lib.concepts[name].seconds = best.candidates, best.seconds
            return lib.concepts[name], asked
        answer = teacher(*question)
        asked.append((question, answer))
        shown.append((question, answer))
        known.add(question)


def _teacher_plural(w: str) -> str:
    if w.endswith(("s", "x", "z", "sh", "ch")):
        return w + "es"
    if w.endswith("y") and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    return w + "s"


def _teacher_past(w: str) -> str:
    if w.endswith("e"):
        return w + "d"
    if w.endswith("y") and w[-2] not in "aeiou":
        return w[:-1] + "ied"
    return w + "ed"


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# The teacher: a person who can answer "what is X for this input?" -- never seen by the learner.
TEACHER = {
    "double": lambda x: 2 * x, "square": lambda x: x * x, "even": lambda x: x % 2 == 0,
    "odd": lambda x: x % 2 == 1, "max": max, "divides": lambda a, b: a > 0 and b % a == 0,
    "prime": lambda x: x > 1 and all(x % d for d in range(2, x)),
    "factorial": lambda x: 1 if x < 2 else x * TEACHER["factorial"](x - 1),
    "sum_to": lambda x: x * (x + 1) // 2, "gcd": _gcd,
    "consonant": lambda c: c not in "aeiou", "penult": lambda w: w[-2],
    "hisses": lambda w: w.endswith(("s", "x", "z", "sh", "ch")),
    "plural": _teacher_plural, "past": _teacher_past,
    "article": lambda w: "an" if w[0] in "aeiou" else "a",
}
_WORDS = ["map", "sky", "wax", "bush", "peach", "lily", "boy", "rose", "jam", "fizz", "pony", "dress", "ray",
          "bake", "hurry", "spray", "plan", "use", "copy", "obey", "rub", "inch", "ant", "egg", "oak", "yak",
          "thing", "graph", "moth", "fly", "tie", "ash", "fix", "grey", "enjoy", "list", "tidy", "hike"]


def _probes(examples: List[Example]) -> List[tuple]:
    first = examples[0][0]
    if all(isinstance(v, int) for v in first):
        top = max(max(v for v in e[0]) for e in examples)
        rng = range(0, max(top, 6) + 1)
        return [(a,) for a in rng] if len(first) == 1 else [(a, b) for a in rng for b in rng]
    if len(examples[0][0][0]) == 1:
        return [(c,) for c in "abcdefghijklmnopqrstuvwxyz"]
    return [(w,) for w in _WORDS]


def curious_experiment(timeout: float = 8.0) -> None:
    lib = Library()
    lib.teach_set("vowel", ["a", "e", "i", "o", "u"])
    print(f"{'concept':<10} {'questions':>9} {'fresh test':>10}   rule")
    total = right = 0
    for name, examples, _tests in CURRICULUM:
        c, asked = curious_learn(lib, name, examples, TEACHER[name], _probes(examples), timeout)
        score = _score(c, FRESH[name])
        if c:
            right += sum(_right(c, t) for t in FRESH[name])
        total += len(FRESH[name])
        qs = ", ".join(f"{q[0] if len(q) == 1 else q}" for q, _ in asked)
        print(f"{name:<10} {len(asked):>9} {score:>10}   {lib.show(name) if c else '-'}")
        if qs:
            print(f"{'':<10} asked about: {qs}")
    print(f"\nFresh-test cases right: {right}/{total}")


if __name__ == "__main__" and os.getenv("HSCI_CURIOUS"):
    curious_experiment()
