"""Understanding by analogy: map a new sentence onto a remembered one.

Given a remembered experience (sentence -> meaning) and a new sentence:

1. **Slots.** Words of the old sentence that appear in its meaning ("Rex", "dog")
   are *slots*; the rest ("is", "a", "belong to the ... family") is the *frame*.
2. **Alignment.** Dynamic programming aligns the two sentences: frame words must
   correspond (identical, or similar under the encoder), slots may take any content
   word (and absorb modifiers, "big dog"), filler words like "kinda" may be skipped
   cheaply, while skipping meaningful words is expensive.
3. **Adaptation.** The old meaning is rewritten with the new words in the slots.

This is how a learned phrasing ("Wugs belong to the blick family" = "every wug is a
blick") generalises to new words without any new code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from hsci.mind import lexicon as lx
from hsci.mind.parser import Tok

NEG = float("-inf")
# Closed-class words: never slots, never slot fillers.
_CLOSED = (lx.FUNCTION_WORDS | lx.PREPOSITIONS | lx.VARIABLE_WORDS
           | {"be", "been", "being", "me", "you", "i", "we", "us", "my", "your", "people", "things"}
           # keywords of the grammar's own constructions ("R is transitive", "X equals Y times Z")
           | {"opposite", "reverse", "inverse", "transitive", "symmetric", "equals", "equal", "times", "divided",
              "multiplied", "plus", "minus", "squared", "cubed", "twice", "half"})


@dataclass
class Slot:
    index: int
    transform: str        # id | verb | noun | num
    meaning_word: str


@dataclass
class Alignment:
    score: float           # normalised to [0, 1]
    fillers: Dict[int, List[int]]       # example slot index -> new token indices
    skipped: List[int] = field(default_factory=list)


def find_slots(tokens: List[Tok], meaning_words: Set[str]) -> List[Slot]:
    slots = []
    for i, t in enumerate(tokens):
        if t.low in _CLOSED or t.low == "?":
            continue  # grammar words always belong to the frame
        if _is_number(t.low):
            if t.low in meaning_words or str(float(t.low)) in meaning_words:
                slots.append(Slot(i, "num", t.low))
            continue
        sup = lx.superlative_to_comparative(t.low)
        for tr, form in (("id", t.low), ("verb", lx.verb_lemma(t.low)), ("noun", lx.singularize(t.low)), ("sup", sup or "")):
            if form in meaning_words:
                slots.append(Slot(i, tr, form))
                break
    return slots


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def apply_transform(transform: str, words: List[str]) -> str:
    low = [w.lower() for w in words]
    if transform == "verb":
        low[-1] = lx.verb_lemma(low[-1])
    elif transform == "noun":
        low[-1] = lx.singularize(low[-1])
    elif transform == "sup":
        low[-1] = lx.superlative_to_comparative(low[-1]) or low[-1]   # youngest -> younger
    return " ".join(low)


# Grammar words that change meaning: dropping "each", "no" or "not" turns one claim into another.
_MEANINGFUL = lx.DETERMINERS | lx.NEGATORS | lx.MODALS | lx.WH | {"if", "then", "than", "?"}


def _skip_cost(t: Tok, fillers: Set[str]) -> float:
    if t.low in fillers or t.low == ",":
        return 0.3          # "btw", "kinda": no meaning lost
    if t.low in _MEANINGFUL:
        return 2.5          # never silently ignore a quantifier or a negation
    return 1.5 if content(t, fillers) else 0.6


def content(t: Tok, fillers: Set[str]) -> bool:
    return (t.low.isalnum() or "-" in t.low) and t.low not in _CLOSED and t.low not in fillers and t.low != "?"


def align(example: List[Tok], slots: List[Slot], new: List[Tok], fillers: Set[str],
          similar: Callable[[str, str], float], frame_threshold: float = 0.8) -> Optional[Alignment]:
    n, m = len(example), len(new)
    slot_at = {s.index: s for s in slots}
    # dp[i][j][s]: best score aligning example[:i] with new[:j]; s=1 if the last example token was a slot just filled
    dp = [[[NEG, NEG] for _ in range(m + 1)] for _ in range(n + 1)]
    back: Dict[Tuple[int, int, int], Tuple[int, int, int, str]] = {}
    dp[0][0][0] = 0.0

    def relax(i, j, s, val, prev, op):
        if val > dp[i][j][s]:
            dp[i][j][s] = val
            back[(i, j, s)] = (*prev, op)

    for i in range(n + 1):
        for j in range(m + 1):
            for s in (0, 1):
                cur = dp[i][j][s]
                if cur == NEG:
                    continue
                if i < n and j < m:
                    e, t = example[i], new[j]
                    if i in slot_at:
                        if content(t, fillers) or (slot_at[i].transform == "num" and _is_number(t.low)):
                            relax(i + 1, j + 1, 1, cur + 1.0 + (0.3 if e.cap == t.cap else 0.0), (i, j, s), "slot")
                    else:
                        if e.low in _CLOSED or t.low in _CLOSED:
                            sim = 1.0 if e.low == t.low else 0.0   # "are" vs "is": agreement carries meaning
                        else:
                            sim = 1.0 if lx.verb_lemma(e.low) == lx.verb_lemma(t.low) else similar(e.low, t.low)
                        if sim >= frame_threshold:
                            relax(i + 1, j + 1, 0, cur + 2.0 * sim, (i, j, s), "frame")
                if j < m:
                    t = new[j]
                    # A slot may absorb neighbouring words ("big dog", "Mount Everest"), but a slot that
                    # held a name only absorbs names: "Zorp happens" is a name followed by a verb.
                    if s == 1 and content(t, fillers) and (not example[i - 1].cap or t.cap):
                        relax(i, j + 1, 1, cur - 0.25, (i, j, s), "absorb")
                    relax(i, j + 1, 0, cur - _skip_cost(t, fillers), (i, j, s), "skip_new")
                if i < n and i not in slot_at:
                    relax(i + 1, j, 0, cur - (2.5 if example[i].low in _MEANINGFUL else 0.8), (i, j, s), "skip_old")

    end_s = 0 if dp[n][m][0] >= dp[n][m][1] else 1
    best = dp[n][m][end_s]
    if best == NEG:
        return None
    max_score = sum(1.3 if i in slot_at else 2.0 for i in range(n))
    fillers_map: Dict[int, List[int]] = {}
    skipped: List[int] = []
    state = (n, m, end_s)
    current_slot: Optional[int] = None
    while state != (0, 0, 0):
        pi, pj, ps, op = back[state]
        if op == "slot":
            fillers_map.setdefault(pi, []).insert(0, pj)
            current_slot = None
        elif op == "absorb":
            # absorbed tokens belong to the slot filled most recently before them
            k = _last_slot_before(back, (pi, pj, ps))
            fillers_map.setdefault(k, []).insert(0, pj)
        elif op == "skip_new":
            skipped.append(pj)
        state = (pi, pj, ps)
    for idx in slot_at:
        if idx not in fillers_map:
            return None
    return Alignment(max(0.0, best / max_score), {k: sorted(v) for k, v in fillers_map.items()}, sorted(skipped))


def _last_slot_before(back, state) -> int:
    while state in back:
        pi, pj, ps, op = back[state]
        if op == "slot":
            return pi
        state = (pi, pj, ps)
    return -1


def adapt_maps(example: List[Tok], slots: List[Slot], new: List[Tok], al: Alignment) -> Optional[Tuple[Dict[str, str], Dict[str, str]]]:
    word_map: Dict[str, str] = {}
    display_map: Dict[str, str] = {}
    for s in slots:
        toks = [new[j] for j in al.fillers[s.index]]
        new_word = apply_transform(s.transform, [t.text for t in toks]) if s.transform != "num" else toks[-1].low
        if word_map.get(s.meaning_word, new_word) != new_word:
            return None   # one old word cannot become two different new words
        word_map[s.meaning_word] = new_word
        display_map[example[s.index].text] = " ".join(t.text for t in toks)
    return word_map, display_map
