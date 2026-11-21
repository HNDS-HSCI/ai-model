"""Verbaliser: logical forms and proofs back into English (the generation side).

It is the inverse of the parser and equally domain-free: how a symbol is rendered
("is a dog" vs "is mortal" vs "likes") comes from the lexicon the parser recorded
when the symbol was first taught.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from hsci.mind import lexicon as lx
from hsci.mind.logic import IS, Atom, Rule, is_var


class Verbalizer:
    def __init__(self, lexicon: Dict[str, Dict[str, str]]) -> None:
        self.lex = lexicon

    def term(self, sym: str) -> str:
        if is_var(sym):
            named = self.lex.get(sym, {}).get("entity")
            return named or ("something" if sym in ("?x", "?q") else sym[1:])
        disp = self.lex.get(sym, {}).get("entity") or sym
        return disp.split(" #")[0]

    def category(self, cat: str, neg: bool, subject: str) -> str:
        kinds = self.lex.get(cat, {})
        first = cat.split()[0]
        if "modal" in kinds or first in lx.MODALS:
            if neg:
                rest = cat.split(" ", 1)[1] if " " in cat else ""
                return f"{subject} {'cannot' if first == 'can' else first + ' not'} {rest}".strip()
            return f"{subject} {cat}"
        noun = "noun" in kinds and "adj" not in kinds
        pred = f"{lx.article_for(cat)} {cat}" if noun else cat
        return f"{subject} is {'not ' if neg else ''}{pred}"

    def atom(self, a: Atom) -> str:
        if a.pred == IS and len(a.args) == 2:
            return self.category(a.args[1], a.neg, self.term(a.args[0]))
        subj = self.term(a.args[0]) if a.args else ""
        kinds = self.lex.get(a.pred, {})
        words = a.pred.split()
        obj = (" " + self.term(a.args[1])) if len(a.args) > 1 else ""
        if words[0] in lx.MODALS:
            verb = " ".join(words[1:])
            return f"{subj} {'cannot' if words[0] == 'can' and a.neg else words[0] + (' not' if a.neg else '')} {verb}{obj}"
        if "crel" in kinds or a.pred.endswith((" than", " of")) or words[0] in lx.PREPOSITIONS:
            rel = kinds.get("crel", a.pred)
            return f"{subj} is {'not ' if a.neg else ''}{rel}{obj}"
        if a.neg:
            return f"{subj} does not {a.pred}{obj}"
        return f"{subj} {lx.third_person(words[0])}{(' ' + ' '.join(words[1:])) if len(words) > 1 else ''}{obj}"

    def rule(self, r: Rule) -> str:
        if r.source_text:
            return f"“{r.source_text.strip()}”"
        body = " and ".join(self.atom(b) for b in r.body)
        return f"if {body} then {self.atom(r.head)}"

    def proof_lines_many(self, trees: List[dict]) -> List[str]:
        seen: set = set()
        return [line for t in trees for line in self.proof_lines(t, seen)]

    def proof_lines(self, tree: dict, seen: Optional[set] = None) -> List[str]:
        """Bottom-up, one line per step, each derived step citing its rule."""
        lines: List[str] = []
        seen = set() if seen is None else seen

        def walk(n: dict) -> None:
            a = n["atom"]
            if a in seen:
                return
            seen.add(a)
            for p in n.get("premises", []):
                walk(p)
            if n.get("rule") is None:
                src = n.get("source") or ""
                if src.startswith("assumption: consider"):
                    lines.append(_cap(src[len("assumption:"):].strip()) + ".")
                elif src.startswith("assumption:"):
                    lines.append(f"Assume {self.atom(a)} ({src[len('assumption:'):].strip()}).")
                else:
                    lines.append(f"{_cap(self.atom(a))} — given" + (f": “{src.strip()}”" if src else "") + ".")
            else:
                because = " and ".join(self.atom(p["atom"]) for p in n["premises"])
                lines.append(f"{_cap(self.atom(a))}, because {because} — by {self._rule_ref(n['rule'])}.")

        walk(tree)
        return lines

    def _rule_ref(self, r: Rule) -> str:
        if r.origin == "grammar":
            return r.source_text
        if r.origin == "induced":
            return f"an induced hypothesis ({self.rule(r)})"
        if r.origin == "default":
            return f"the general rule {self.rule(r)} (no exception known)"
        return self.rule(r)

    def because(self, tree: dict) -> Optional[str]:
        """One-line justification: the premises of the final step."""
        if tree.get("rule") is None:
            src = tree.get("source")
            return f"you told me so (“{src.strip()}”)" if src and not src.startswith("assumption:") else None
        return " and ".join(self.atom(p["atom"]) for p in tree["premises"])


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def join_list(items: List[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
