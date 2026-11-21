"""Meanings as data: serialise, compare, adapt and sanity-check understood input.

A *meaning* is the logical form of one utterance (an assertion, question, formula
or quantity), stored as plain JSON so that experiences can be remembered, compared
and adapted to new sentences by analogy.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from hsci.mind import lexicon as lx
from hsci.mind.explain import Verbalizer, join_list
from hsci.mind.logic import IS, Atom, Rule
from hsci.mind.parser import (Assertion, FormulaStatement, LexEntry, QuantityStatement, Question, Tok, Unparsed)
from hsci.mind.quantities import Formula, Quantity

_TEXT_FIELDS = {"text", "source_text", "source"}
_DISPLAY_FIELDS = {"display", "target_display", "generic", "superlative_word", "gloss"}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-']*|-?\d+(?:\.\d+)?")


# ----------------------------------------------------------------- (de)serialise

def to_dict(p) -> Optional[dict]:
    if isinstance(p, Assertion):
        return {"type": "assertion", "text": p.text, "facts": [a.to_json() for a in p.facts],
                "rules": [{"rule": r.to_json(), "origin": r.origin, "source_text": r.source_text} for r in p.rules],
                "lexicon": [{"symbol": e.symbol, "kind": e.kind, "display": e.display} for e in p.lexicon],
                "definitions": [{"term": t, "gloss": g} for t, g in p.definitions], "focus": p.focus}
    if isinstance(p, Question):
        return {"type": "question", "text": p.text, "kind": p.kind, "goals": [a.to_json() for a in p.goals],
                "hypothetical": [a.to_json() for a in p.hypothetical], "generic": p.generic, "target": p.target,
                "target_display": p.target_display, "explain": p.explain, "expr": p.expr, "wh_word": p.wh_word,
                "lexicon": [{"symbol": e.symbol, "kind": e.kind, "display": e.display} for e in p.lexicon],
                "givens": [to_dict(g) for g in p.givens], "superlative_word": p.superlative_word}
    if isinstance(p, FormulaStatement):
        f = p.formula
        return {"type": "formula", "text": p.text, "formula": {"target": f.target, "expr": f.expr, "names": f.names, "source": f.text}}
    if isinstance(p, QuantityStatement):
        q = p.quantity
        return {"type": "quantity", "text": p.text, "quantity": {"name": q.name, "value": q.value, "unit": q.unit, "source": q.source}}
    return None


def from_dict(d: dict):
    t = d["type"]
    lex = [LexEntry(e["symbol"], e["kind"], e["display"]) for e in d.get("lexicon", [])]
    if t == "assertion":
        a = Assertion(d["text"], [Atom.from_json(x) for x in d["facts"]],
                      [Rule.from_json(r["rule"], origin=r["origin"], source_text=r["source_text"]) for r in d["rules"]],
                      lex, [(x["term"], x["gloss"]) for x in d["definitions"]], d.get("focus"))
        return a
    if t == "question":
        return Question(d["text"], d["kind"], [Atom.from_json(x) for x in d["goals"]],
                        [Atom.from_json(x) for x in d["hypothetical"]], d.get("generic"), d.get("target"),
                        d.get("target_display"), d.get("explain", False), d.get("expr"), d.get("wh_word"), lex,
                        [from_dict(g) for g in d.get("givens", []) if g], d.get("superlative_word"))
    if t == "formula":
        f = d["formula"]
        return FormulaStatement(d["text"], Formula(f["target"], f["expr"], list(f["names"]), f["source"]))
    if t == "quantity":
        q = d["quantity"]
        return QuantityStatement(d["text"], Quantity(q["name"], float(q["value"]), q.get("unit"), q.get("source", "")))
    raise ValueError(f"unknown meaning type {t}")


def meanings_to_dicts(parsed: Iterable) -> Optional[List[dict]]:
    out = []
    for p in parsed:
        d = to_dict(p)
        if d is None:
            return None
        out.append(d)
    return out or None


# ----------------------------------------------------------------- identity

def key(meanings: List[dict]) -> str:
    """Canonical identity of a meaning, ignoring wording, displays and provenance."""
    def strip(x, field: str = ""):
        if isinstance(x, dict):
            return {k: strip(v, k) for k, v in sorted(x.items())
                    if k not in _TEXT_FIELDS | _DISPLAY_FIELDS | {"lexicon", "focus", "wh_word", "explain"}}
        if isinstance(x, list):
            items = [strip(v) for v in x]
            if field in ("args", "names"):
                return items          # argument order is meaning: likes(alice, bob) != likes(bob, alice)
            return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
        if isinstance(x, str):
            return re.sub(r" #\d+$", "", x)
        return x
    return json.dumps(strip(meanings), sort_keys=True)


# ----------------------------------------------------------------- symbols

def _symbol_strings(d) -> Iterable[str]:
    if isinstance(d, dict):
        if "pred" in d and "args" in d:
            yield d["pred"]
            yield from d["args"]
            return
        for k, v in d.items():
            if k in _TEXT_FIELDS | _DISPLAY_FIELDS or k in {"kind", "type", "origin", "wh_word"}:
                continue
            if k in {"symbol", "target", "name", "term", "focus"} and isinstance(v, str):
                yield v
            elif k == "expr" and isinstance(v, str):
                yield from re.findall(r"\{([^{}]+)\}", v)
                yield from re.findall(r"-?\d+(?:\.\d+)?", re.sub(r"\{[^{}]+\}", " ", v))
            elif k == "names":
                yield from v
            elif k == "value":
                yield _num_str(v)
            elif k == "unit" and isinstance(v, str):
                yield from re.findall(r"[A-Za-z]+", v)
            else:
                yield from _symbol_strings(v)
    elif isinstance(d, list):
        for v in d:
            yield from _symbol_strings(v)


def symbol_words(meanings: List[dict]) -> Set[str]:
    words: Set[str] = set()
    for s in _symbol_strings(meanings):
        if not isinstance(s, str) or s.startswith("?") or s.startswith("a typical"):
            continue
        for w in re.findall(r"[a-z0-9][a-z0-9\-']*|-?\d+(?:\.\d+)?", s.lower()):
            words.add(w)
    return words


def _num_str(v) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


# ----------------------------------------------------------------- adaptation

def substitute(meanings: List[dict], word_map: Dict[str, str], display_map: Dict[str, str], new_text: str) -> List[dict]:
    """Rewrites a remembered meaning for a new sentence: old slot words -> new words."""
    def sub_str(s: str, display: bool) -> str:
        def rep(m: re.Match) -> str:
            w = m.group(0)
            if display and w in display_map:
                return display_map[w]
            return word_map.get(w.lower(), w) if not display or w.lower() in word_map else w
        return _WORD.sub(rep, s)

    def walk(x, field: str = ""):
        if isinstance(x, dict):
            return {k: walk(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v, field) for v in x]
        if isinstance(x, str):
            if field in _TEXT_FIELDS:
                return new_text
            return sub_str(x, field in _DISPLAY_FIELDS)
        if isinstance(x, (int, float)) and not isinstance(x, bool) and field == "value":
            new = word_map.get(_num_str(x))
            if new is None:
                return x
            try:
                return float(new)
            except ValueError:
                return new   # a placeholder (used when comparing construction shapes)
        return x

    return walk(meanings)


def renumber_skolems(meanings: List[dict], counter) -> List[dict]:
    """Gives adapted meanings fresh individuals: 'some bird #3' from a remembered sentence must
    not become the same individual as the one in that sentence."""
    mapping: Dict[str, str] = {}

    def fresh(m: re.Match) -> str:
        if m.group(1) not in mapping:
            mapping[m.group(1)] = str(next(counter))
        return f" #{mapping[m.group(1)]}"

    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str):
            return re.sub(r" #(\d+)", fresh, x)
        return x
    return walk(meanings)


# ----------------------------------------------------------------- plausibility

_ALLOWED_IN_PRED = lx.PREPOSITIONS | lx.MODALS | {"than", "be", "not", "more", "less"}
# Words the grammar's own constructions consume ("X is the opposite of Y", "R is transitive",
# "how many", "kind of", "people who ..."): they shape the meaning without becoming symbols.
_CONSTRUCTION = {"opposite", "reverse", "inverse", "transitive", "symmetric", "being", "many", "much",
                 "relation", "kind", "type", "sort", "people", "person", "typically", "usually", "normally",
                 "generally", "most", "equals", "equal", "defined", "times", "divided", "multiplied", "plus",
                 "minus", "squared", "cubed", "half", "twice", "power", "know", "tell", "learned", "learn"}
_PRONOUNS = {"i", "me", "my", "mine", "you", "your", "yours", "we", "us", "our", "myself", "yourself"}
_GRAMMAR = lx.FUNCTION_WORDS | _PRONOUNS | {"be", "been", "being"}


def plausibility(meanings: List[dict], tokens: List[Tok], fillers: Set[str],
                 consumed: Set[int] = frozenset()) -> Tuple[float, List[str]]:
    """Does this reading make sense as a meaning of these words? Returns (score, reasons).

    ``consumed`` are token positions accounted for by a learned construction's frame
    (e.g. "is known to be"): they shape the meaning without becoming symbols.
    """
    if not meanings:
        return 0.0, ["no meaning"]
    if any(m["type"] in ("formula", "quantity") for m in meanings) or \
            any(m["type"] == "question" and m["kind"] in ("math", "learned") for m in meanings):
        return 1.0, []
    reasons: List[str] = []
    penalty = 0.0
    # Capitalised words are names -- except the first word, which is capitalised anyway.
    names = {t.low for i, t in enumerate(tokens) if t.cap and i > 0}
    case_of = {t.low: t.cap for i, t in enumerate(tokens) if t.low.isalpha() and i > 0}  # first word is capitalised anyway
    atoms: List[dict] = []
    for m in meanings:
        atoms += m.get("facts", []) + m.get("goals", []) + m.get("hypothetical", [])
        for r in m.get("rules", []):
            atoms += r["rule"]["body"] + [r["rule"]["head"]]
            for b in r["rule"]["body"]:
                if b["pred"] == IS and b["args"][1] in names and b["args"][0].startswith("?"):
                    penalty += 0.6
                    reasons.append(f"treats the name '{b['args'][1]}' as a category")
    for a in atoms:
        pred_words = a["pred"].split()
        if a["pred"] != IS and (a["pred"] in names or pred_words[0] in names):
            penalty += 0.6
            reasons.append(f"uses the name '{a['pred']}' as a verb")
        if a["pred"] != IS and (any(w in _GRAMMAR - _ALLOWED_IN_PRED for w in pred_words) or pred_words[0] == "be"):
            penalty += 0.4
            reasons.append(f"odd relation '{a['pred']}'")
        for arg in a["args"]:
            if arg.startswith("?") or arg.startswith("a typical") or "#" in arg:
                continue
            ws = arg.split()
            is_modal_cat = a["pred"] == IS and ws and ws[0] in lx.MODALS
            if a["pred"] == IS and arg is a["args"][-1] and re.fullmatch(r"-?\d+(?:\.\d+)?", arg):
                penalty += 0.6
                reasons.append(f"treats the number {arg} as a category (numbers are values)")
            # "Tom eats": a capitalised name glued to an ordinary word is almost never one thing
            caps = [case_of.get(w) for w in ws]
            if len(ws) > 1 and caps[0] is True and False in caps[1:]:
                penalty += 0.5
                reasons.append(f"'{arg}' glues a name to an ordinary word")
            if len(ws) > 4:
                penalty += 0.4
                reasons.append(f"'{arg}' is too long to be one thing")
            if any(re.fullmatch(r"\d+(?:\.\d+)?", w) for w in ws) and len(ws) > 1:
                penalty += 0.3
                reasons.append(f"'{arg}' mixes a number into a name")
            if not is_modal_cat and len(ws) > 1 and any(w != lx.singularize(w) and w.endswith("s") and w not in names
                                                       for w in ws[:-1]):
                penalty += 0.4
                reasons.append(f"'{arg}' looks like a verb got glued to a name")
            if any(w in fillers for w in ws):
                penalty += 0.4
                reasons.append(f"'{arg}' contains filler words")
            if not is_modal_cat and any(w in (_GRAMMAR | lx.PREPOSITIONS) - {"of"} for w in ws):
                penalty += 0.3
                reasons.append(f"'{arg}' contains grammar words")

    covered = symbol_words(meanings)
    superlatives = {lx.superlative_to_comparative(t.low) for t in tokens} - {None}
    lost = [t.text for i, t in enumerate(tokens) if i not in consumed and t.low.isalpha()
            and not (len(t.text) == 1 and t.text.isupper())          # rule variables X, Y, Z
            and t.low not in lx.FUNCTION_WORDS | lx.PREPOSITIONS | _CONSTRUCTION
            and t.low not in fillers and t.low not in lx.VARIABLE_WORDS
            and not ({t.low, lx.verb_lemma(t.low), lx.singularize(t.low)} & covered)
            and not (lx.superlative_to_comparative(t.low) in superlatives and
                     lx.superlative_to_comparative(t.low) in covered)]
    if lost:
        penalty += min(0.45, 0.15 * len(lost))
        reasons.append(f"ignores {join_list([repr(x) for x in lost])}")
    return max(0.0, 1.0 - penalty), reasons


# ----------------------------------------------------------------- paraphrase

def paraphrase(meanings: List[dict], v: Verbalizer) -> str:
    parts: List[str] = []
    for m in meanings:
        t = m["type"]
        if t == "assertion":
            parts += [v.atom(Atom.from_json(a)) for a in m["facts"]]
            parts += [_rule_text(Rule.from_json(r["rule"], origin=r["origin"]), v) for r in m["rules"]
                      if r["origin"] != "grammar"]
        elif t == "formula":
            f = m["formula"]
            expr = f["expr"]
            for n in f["names"]:
                expr = expr.replace("{" + n + "}", n)
            parts.append(f"{f['target']} = {expr}")
        elif t == "quantity":
            q = m["quantity"]
            parts.append(f"{q['name']} = {_num_str(q['value'])}{' ' + q['unit'] if q.get('unit') else ''}")
        elif t == "question":
            parts.append(_question_text(m, v))
    return "; ".join(p for p in parts if p)


def _rule_text(r: Rule, v: Verbalizer) -> str:
    vv = Verbalizer({**v.lex, "?x": {"entity": "something"}})
    body = " and ".join(vv.atom(b) for b in r.body)
    head = Verbalizer({**v.lex, "?x": {"entity": "it"}}).atom(r.head)
    prefix = "usually, " if r.origin == "default" else ""
    return f"{prefix}if {body}, then {head}"


def _question_text(m: dict, v: Verbalizer) -> str:
    kind = m["kind"]
    goals = [Atom.from_json(g) for g in m["goals"]]
    if kind == "yesno":
        lex = dict(v.lex)
        if m.get("generic"):
            lex[m["target"]] = {"entity": f"every {m['generic']}"}
        return "you're asking whether " + join_list([Verbalizer(lex).atom(g) for g in goals])
    if kind in ("wh", "count"):
        who = {"?q": {"entity": "who/what"}}
        prefix = "how many: " if kind == "count" else "you're asking "
        return prefix + join_list([Verbalizer({**v.lex, **who}).atom(g) for g in goals])
    if kind == "superlative":
        return f"you're asking who is the {m.get('superlative_word')}"
    if kind == "describe":
        return f"you're asking what I know about {m.get('target_display') or m.get('target')}"
    if kind == "math":
        return f"calculate {m.get('expr')}"
    if kind == "similar":
        return f"you're asking what is similar to {m.get('target')}"
    return "you're asking what I have learned"
