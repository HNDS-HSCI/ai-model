"""Semantic parser: English sentences -> logical forms (the paper's P and F stages).

The parser is construction-based. It recognises *grammatical* structure -- copulas,
determiners and quantifiers, comparatives ("-er than"), relational nouns ("the X of
Y"), prepositions, modals, relative clauses, conditionals ("if ... then ...") -- and
treats every open-class word as a symbol. It never contains domain vocabulary, so a
sentence about "wugs" and "blickets" is handled exactly like one about dogs.

Where the grammar is ambiguous without part-of-speech knowledge (e.g. where does the
subject end in "Is the big dog brown?"), candidate parses are *ranked by grounding*:
the reading whose symbols the knowledge base already knows wins. Knowledge therefore
feeds back into perception, which is the cognitive loop the architecture calls for.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from hsci.mind import lexicon as lx
from hsci.mind.logic import IS, Atom, Rule
from hsci.mind.quantities import Formula, Quantity, detect_math, parse_formula, parse_quantity

S = "?S"  # subject placeholder inside predicate templates


# ----------------------------------------------------------------- data model

@dataclass
class LexEntry:
    symbol: str
    kind: str      # entity | noun | adj | verb | crel | modal
    display: str


@dataclass
class Assertion:
    text: str
    facts: List[Atom] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    lexicon: List[LexEntry] = field(default_factory=list)
    definitions: List[Tuple[str, str]] = field(default_factory=list)  # (term, gloss)
    focus: Optional[str] = None


@dataclass
class FormulaStatement:
    text: str
    formula: Formula


@dataclass
class QuantityStatement:
    text: str
    quantity: Quantity


@dataclass
class Question:
    text: str
    kind: str                          # yesno | wh | superlative | describe | count | math | similar | learned
    goals: List[Atom] = field(default_factory=list)
    hypothetical: List[Atom] = field(default_factory=list)
    generic: Optional[str] = None      # display of the arbitrary individual for generic questions
    target: Optional[str] = None       # describe / similar / superlative relation / count category
    target_display: Optional[str] = None
    explain: bool = False
    expr: Optional[str] = None
    wh_word: Optional[str] = None
    lexicon: List[LexEntry] = field(default_factory=list)
    givens: List[object] = field(default_factory=list)
    superlative_word: Optional[str] = None


@dataclass
class Unparsed:
    text: str
    reason: str


Parsed = object  # Assertion | FormulaStatement | QuantityStatement | Question | Unparsed


@dataclass
class ParseContext:
    """What the parser may consult about the current knowledge (for grounding/ranking)."""
    entities: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    predicates: Set[str] = field(default_factory=set)
    adjectives: Set[str] = field(default_factory=set)
    quantities: Set[str] = field(default_factory=set)
    last_entity: Optional[str] = None
    last_entity_display: Optional[str] = None

    def known(self, symbol: str) -> bool:
        return symbol in self.entities or symbol in self.categories or symbol in self.predicates


class ParseError(ValueError):
    pass


# ----------------------------------------------------------------- tokens

@dataclass
class Tok:
    text: str
    low: str

    @property
    def cap(self) -> bool:
        return self.text[:1].isupper()


_CONTRACTIONS = [
    (r"\bcan't\b", "can not"), (r"\bcannot\b", "can not"), (r"\bwon't\b", "will not"),
    (r"\b(\w+)n't\b", r"\1 not"), (r"\bwhat's\b", "what is"), (r"\bwho's\b", "who is"),
    (r"\bit's\b", "it is"), (r"\bthat's\b", "that is"),
]


def tokenize(sentence: str) -> List[Tok]:
    s = sentence.strip()
    for pat, rep in _CONTRACTIONS:
        s = re.sub(pat, rep, s, flags=re.I)
    s = re.sub(r"(\w)'s\b", r"\1 's", s)
    raw = re.findall(r"'s|[A-Za-z][A-Za-z0-9\-]*|\d+(?:\.\d+)?|[,;:]", s)  # "K2", "COVID-19"
    return [Tok(t, t.lower()) for t in raw]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?;])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip(" .;")]


def _words(toks: Sequence[Tok]) -> List[str]:
    return [t.low for t in toks]


# ----------------------------------------------------------------- parser

class VarScope:
    """Maps pronouns, 'someone'-words and single-letter names to rule variables."""

    def __init__(self) -> None:
        self.map: Dict[str, str] = {}

    def var_for(self, tok: Tok) -> Optional[str]:
        w = tok.low
        # Only ever called on a one-token noun phrase, so "A" here is a name, not an article.
        if len(tok.text) == 1 and tok.text.isupper() and tok.text != "I":
            return self.map.setdefault(tok.text, f"?{tok.text}")
        if w in lx.VARIABLE_WORDS or w in {"it", "they", "them", "he", "she", "him", "her"}:
            return self.map.setdefault("_x", "?x")
        return None


@dataclass
class Subject:
    kind: str                     # entity | generic | var | skolem
    term: str = ""                # constant / variable
    display: str = ""
    classes: List[Atom] = field(default_factory=list)   # atoms about S for generic/skolem subjects
    quant: str = "all"            # all | no
    plural: bool = False
    default: bool = False         # bare generic ("Birds fly"): holds unless an exception is known
    lex: List[LexEntry] = field(default_factory=list)


class SemanticParser:
    def __init__(self) -> None:
        self._skolem = itertools.count(1)
        self._default_marker = False

    # ------------------------------------------------------------ entry point
    def parse(self, sentence: str, ctx: ParseContext) -> List[Parsed]:
        s = sentence.strip()
        is_q = s.endswith("?")
        core = s.rstrip(" ?.!;")
        if not core:
            return []
        first = core.split()[0].lower()
        if not is_q and first in (lx.WH | lx.COPULAS | lx.DO_AUX | {"can", "could"}) - {"that", "which", "when"}:
            is_q = first in lx.WH or len(core.split()) > 2 and first in lx.COPULAS | lx.DO_AUX | {"can"}

        expr = detect_math(core)
        if expr is not None and ("=" in expr or is_q or re.match(r"^(?:solve|calculate|compute|evaluate|find|simplify)\b", core, re.I)
                                 or re.fullmatch(r"[\d\s\.\+\-\*/\^\(\)]+", expr)):
            return [Question(s, "math", expr=expr)]

        if is_q:
            m = re.match(r"^(?:if|suppose|given that|assuming|assume)\s+(.+?),\s*(?:then\s+)?(.+)$", core, re.I)
            if m:
                givens = self._parse_givens(m.group(1), ctx)
                if isinstance(givens, Unparsed):
                    return [givens]
                q = self.parse_question(m.group(2), ctx, original=s)
                if isinstance(q, Question):
                    q.givens = givens
                return [q]
            return [self.parse_question(core, ctx, original=s)]

        formula = parse_formula(core)
        if formula:
            return [FormulaStatement(s, formula)]
        qty = parse_quantity(core)
        if qty:
            return [QuantityStatement(s, qty)]
        try:
            return [self.parse_statement(core, ctx, original=s)]
        except ParseError as exc:
            return [Unparsed(s, str(exc))]

    def _parse_givens(self, text: str, ctx: ParseContext):
        pieces = [p.strip() for p in re.split(r",?\s+and\s+|,\s*", text) if p.strip()]
        out: List[object] = []
        if all(parse_quantity(p) for p in pieces):
            return [QuantityStatement(p, parse_quantity(p)) for p in pieces]
        try:
            return [self.parse_statement(text, ctx, original=text)]
        except ParseError:
            pass
        for p in pieces:
            q = parse_quantity(p)
            if q:
                out.append(QuantityStatement(p, q))
                continue
            f = parse_formula(p)
            if f:
                out.append(FormulaStatement(p, f))
                continue
            try:
                out.append(self.parse_statement(p, ctx, original=p))
            except ParseError as exc:
                return Unparsed(text, f"could not understand the assumption '{p}': {exc}")
        return out

    # ------------------------------------------------------------ statements
    def parse_statement(self, text: str, ctx: ParseContext, original: str = "") -> Assertion:
        low = text.lower().strip()
        out = Assertion(original or text)

        if self._relation_property(low, out, ctx) or self._opposites(low, out, ctx):
            return out

        # "Typically, birds fly" / "Usually ..." / "Most birds fly" mark defaults explicitly.
        self._default_marker = False
        m = re.match(r"^(?:typically|usually|normally|generally|in general|most)\b,?\s+", text, re.I)
        if m:
            self._default_marker = True
            text = text[m.end():]
        toks = tokenize(text)
        if not toks:
            raise ParseError("empty sentence")
        if toks[0].low == "if" or (any(t.low == "if" for t in toks[1:]) and toks[0].low not in lx.WH):
            self._conditional(toks, out, ctx)
            return out

        for clause in self._split_clauses(toks):
            subj, atoms, lex, extra = self._clause(clause, ctx, scope=None, mode="assert")
            out.lexicon += subj.lex + lex
            if extra and extra[0] == "__definition__":
                term = subj.term if subj.kind == "entity" else subj.display
                out.definitions.append((term, out.text))
            self._emit(subj, atoms, out)
        comparative_rules(out)
        return out

    def _emit(self, subj: Subject, atoms: List[Atom], out: Assertion) -> None:
        if subj.kind == "entity":
            for a in atoms:
                out.facts.append(_bind(a, subj.term))
            out.focus = subj.term
        elif subj.kind == "skolem":
            for a in subj.classes + atoms:
                out.facts.append(_bind(a, subj.term))
            out.focus = subj.term
        elif subj.kind == "generic":
            body = tuple(_bind(a, "?x") for a in subj.classes)
            if not body:
                raise ParseError("a general statement needs a class to talk about (e.g. 'All birds ...')")
            origin = "default" if (subj.default or self._default_marker) else "told"
            for a in atoms:
                head = _bind(a, "?x")
                if subj.quant == "no":
                    head = head.negate()
                out.rules.append(Rule(body, head, origin=origin, source_text=out.text))
        else:
            raise ParseError("statements about 'someone'/'something' need an 'if ... then ...' form")

    def _relation_property(self, low: str, out: Assertion, ctx: ParseContext) -> bool:
        m = re.match(r"^(?:the\s+relation\s+|being\s+)?['\"]?(.+?)['\"]?\s+is\s+(?:a\s+)?(transitive|symmetric)(?:\s+relation)?$", low)
        if not m:
            return False
        pred = self._relation_name(m.group(1), ctx)
        a, b, c = "?a", "?b", "?c"
        if m.group(2) == "transitive":
            out.rules.append(Rule((Atom(pred, (a, b)), Atom(pred, (b, c))), Atom(pred, (a, c)), origin="told", source_text=out.text))
        else:
            out.rules.append(Rule((Atom(pred, (a, b)),), Atom(pred, (b, a)), origin="told", source_text=out.text))
        out.lexicon.append(LexEntry(pred, "crel" if not _looks_verbal(pred, ctx) else "verb", pred))
        return True

    def _relation_name(self, phrase: str, ctx: ParseContext) -> str:
        phrase = re.sub(r"^(?:is|are|being)\s+", "", phrase.strip())
        if phrase in ctx.predicates:
            return phrase
        words = phrase.split()
        if words and words[-1] == "than" or phrase in ctx.predicates:
            return phrase
        lemma = " ".join([lx.verb_lemma(words[0])] + words[1:]) if words else phrase
        return lemma if lemma in ctx.predicates or len(words) == 1 else phrase

    def _opposites(self, low: str, out: Assertion, ctx: ParseContext) -> bool:
        m = re.match(r"^(?:the\s+word\s+)?['\"]?([a-z][a-z ]*?)['\"]?\s+is\s+the\s+(?:opposite|reverse|inverse)\s+of\s+['\"]?([a-z][a-z ]*?)['\"]?$", low)
        if not m:
            return False
        x, y = m.group(1).strip(), m.group(2).strip()
        comparative = lambda w: w.endswith("er") or w.startswith(("more ", "less ")) or f"{w} than" in ctx.predicates
        a, b = "?a", "?b"
        if comparative(x) and comparative(y):
            px, py = f"{x} than", f"{y} than"
            out.rules += [Rule((Atom(px, (a, b)),), Atom(py, (b, a)), origin="told", source_text=out.text),
                          Rule((Atom(py, (a, b)),), Atom(px, (b, a)), origin="told", source_text=out.text)]
            out.rules += self._order_axioms(px) + self._order_axioms(py)
            out.lexicon += [LexEntry(px, "crel", px), LexEntry(py, "crel", py)]
        else:
            out.rules += [Rule((Atom(IS, (a, x)),), Atom(IS, (a, y), True), origin="told", source_text=out.text),
                          Rule((Atom(IS, (a, y)),), Atom(IS, (a, x), True), origin="told", source_text=out.text)]
            out.lexicon += [LexEntry(x, "adj", x), LexEntry(y, "adj", y)]
        return True

    @staticmethod
    def _order_axioms(pred: str) -> List[Rule]:
        """Comparatives grammatically denote strict orders: transitive and asymmetric."""
        a, b, c = "?a", "?b", "?c"
        note = f"'{pred}' is a comparative, so it is transitive and asymmetric"
        return [Rule((Atom(pred, (a, b)), Atom(pred, (b, c))), Atom(pred, (a, c)), origin="grammar", source_text=note),
                Rule((Atom(pred, (a, b)),), Atom(pred, (b, a), True), origin="grammar", source_text=note)]

    def _conditional(self, toks: List[Tok], out: Assertion, ctx: ParseContext) -> None:
        w = _words(toks)
        if w[0] == "if":
            if "then" in w:
                k = w.index("then")
            elif "," in w:
                k = w.index(",")
            else:
                raise ParseError("an 'if' sentence needs 'then' or a comma before its conclusion")
            cond, concl = toks[1:k], toks[k + 1:]
        else:
            k = w.index("if")
            concl, cond = toks[:k], toks[k + 1:]
            if concl and concl[-1].low == ",":
                concl = concl[:-1]
        scope = VarScope()
        body: List[Atom] = []
        for clause in self._split_clauses(cond, scope):
            subj, atoms, lex, _ = self._clause(clause, ctx, scope, mode="query")
            out.lexicon += subj.lex + lex
            term = subj.term if subj.kind in ("entity", "var") else "?x"
            body += [_bind(a, term) for a in subj.classes] + [_bind(a, term) for a in atoms]
        for clause in self._split_clauses(concl, scope):
            subj, atoms, lex, _ = self._clause(clause, ctx, scope, mode="assert")
            out.lexicon += subj.lex + lex
            term = subj.term if subj.kind in ("entity", "var") else "?x"
            for a in atoms:
                out.rules.append(Rule(tuple(body), _bind(a, term), origin="told", source_text=out.text))
        for r in out.rules:
            if not r.is_safe():
                raise ParseError("the conclusion mentions someone the condition never introduced")
        out.rules = [r for r in out.rules if r.body]
        if not out.rules:
            raise ParseError("could not find a condition and conclusion")
        comparative_rules(out)

    def _split_clauses(self, toks: List[Tok], scope: Optional[VarScope] = None) -> List[List[Tok]]:
        """Splits on 'and'/',' only where a new clause (with its own subject) starts."""
        clauses, cur = [], []
        for i, t in enumerate(toks):
            if t.low in ("and", ",") and cur and i + 1 < len(toks) and self._starts_clause(toks[i + 1:], scope):
                clauses.append(cur)
                cur = []
                continue
            cur.append(t)
        if cur:
            clauses.append(cur)
        return clauses

    def _starts_clause(self, rest: List[Tok], scope: Optional[VarScope]) -> bool:
        if len(rest) < 2:
            return False
        r0 = rest[0]
        verbish = lx.COPULAS | lx.DO_AUX | lx.MODALS | {"has", "have"}
        if r0.low in verbish or r0.low in ("and", ","):
            return False
        head = 1
        if r0.low in lx.DETERMINERS:
            head = 2
        while head < len(rest) and rest[head].cap and rest[head - 1].cap:
            head += 1
        if r0.cap or r0.low in lx.PRONOUNS | lx.VARIABLE_WORDS or r0.low in lx.DETERMINERS:
            return head < len(rest) and (rest[head].low in verbish or rest[head].low.endswith("s") or
                                         (head + 1 < len(rest) and rest[head + 1].low in verbish))
        return False

    # ------------------------------------------------------------ clauses
    def _clause(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope], mode: str):
        """Returns (Subject, predicate atoms over S, lexicon, definition)."""
        if not toks:
            raise ParseError("empty clause")
        best, err = None, "could not find the verb of the sentence"
        for b in self._verb_positions(toks, ctx):
            try:
                subj = self._subject(toks[:b], ctx, scope, mode, toks[b])
                atoms, lex, extra = self._vp(toks[b:], ctx, scope, mode, subj.plural)
            except ParseError as exc:
                err = str(exc)
                continue
            score = self._ground_score(subj, atoms, ctx) + self._verb_score(toks[b], ctx) - 0.1 * b
            if best is None or score > best[0]:
                best = (score, subj, atoms, lex, extra)
        if best is None:
            raise ParseError(err)
        return best[1], best[2], best[3], best[4]

    def _verb_positions(self, toks: List[Tok], ctx: ParseContext) -> List[int]:
        w = _words(toks)
        aux = lx.COPULAS | lx.DO_AUX | lx.MODALS
        aux_pos = [i for i, x in enumerate(w) if x in aux and i > 0]
        rel = next((i for i, x in enumerate(w) if x in lx.RELATIVE and i > 0), None)
        if rel is not None and aux_pos and aux_pos[0] < rel:
            rel = None  # "X is the process by which ..." -- the relative belongs to the predicate
        if rel is not None:
            after = [i for i in aux_pos if i > rel + 1]
            cands = after[-1:] if after else []
            cands += [i for i in range(rel + 2, len(toks)) if i not in cands and w[i] not in lx.FUNCTION_WORDS]
            return cands
        if aux_pos:
            return aux_pos[:1]
        verbish = [i for i in range(1, min(len(toks), 6)) if w[i] not in lx.FUNCTION_WORDS and w[i] != "'s"]
        return verbish or [1] if len(toks) > 1 else []

    @staticmethod
    def _verb_score(tok: Tok, ctx: ParseContext) -> float:
        if tok.low in lx.COPULAS | lx.DO_AUX | lx.MODALS:
            return 2.0
        score = 2.0 if lx.verb_lemma(tok.low) in {p.split()[0] for p in ctx.predicates} else 0.0
        if tok.cap:
            score -= 2.0   # names are not verbs
        if tok.low.endswith("s"):
            score += 0.5
        return score

    def _ground_score(self, subj: Subject, atoms: List[Atom], ctx: ParseContext) -> float:
        score = 0.0
        syms = [subj.term] + [a.args[1] if a.pred == IS and len(a.args) > 1 else a.pred for a in subj.classes + atoms]
        syms += [x for a in atoms for x in a.args[1:] if not x.startswith("?")]
        for s in syms:
            if not s or s.startswith("?"):
                continue
            score += 2 if ctx.known(s) else -0.5
        if subj.kind == "entity" and subj.term in ctx.entities:
            score += 1
        return score

    def _subject(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope], mode: str, verb: Tok) -> Subject:
        if not toks:
            raise ParseError("missing subject")
        w = _words(toks)
        # Modals ("can", "must") show no agreement, so they are compatible with plural subjects.
        plural_verb = verb.low in lx.COPULA_PL or verb.low in {"do", "have"} or verb.low in lx.MODALS or (
            verb.low not in lx.FUNCTION_WORDS and not verb.low.endswith("s"))

        rel_i = next((i for i, x in enumerate(w) if x in lx.RELATIVE and i > 0), None)
        rel_atoms: List[Atom] = []
        rel_lex: List[LexEntry] = []
        if rel_i is not None:
            rel_atoms, rel_lex, _ = self._vp(toks[rel_i + 1:], ctx, scope, "query", True)
            toks, w = toks[:rel_i], w[:rel_i]
            if not toks:
                raise ParseError("relative clause without a head noun")

        if len(toks) == 1 and scope is not None:
            v = scope.var_for(toks[0])
            if v:
                return Subject("var", v, toks[0].text, classes=rel_atoms, plural=plural_verb, lex=rel_lex)
        if len(toks) == 1 and w[0] in {"he", "she", "it", "they", "this"} and scope is None:
            if not ctx.last_entity:
                raise ParseError(f"I don't know who '{toks[0].text}' refers to")
            return Subject("entity", ctx.last_entity, ctx.last_entity_display or ctx.last_entity)
        if w[0] in lx.VARIABLE_WORDS | {"people", "everyone", "everybody", "anyone", "anything", "something", "someone"} and len(w) == 1 and rel_atoms:
            return Subject("generic", "?x", toks[0].text, classes=rel_atoms, plural=True, lex=rel_lex)

        det = w[0] if w[0] in lx.DETERMINERS else None
        content = toks[1:] if det else toks
        if not content:
            raise ParseError("missing noun after determiner")
        if any(t.low in (lx.FUNCTION_WORDS | lx.PREPOSITIONS) - {"one"} for t in content):
            raise ParseError("subject contains function words")
        quant = "no" if det in lx.NEGATIVE_QUANT else "all"

        proper = all(t.cap for t in content) and det is None
        if proper and not (plural_verb and lx.looks_plural(content[-1].low) and content[-1].low not in ctx.entities):
            key = " ".join(t.low for t in content)
            disp = " ".join(t.text for t in content)
            return Subject("entity", key, disp, classes=rel_atoms, lex=rel_lex + [LexEntry(key, "entity", disp)])

        words = [t.low for t in content]
        is_plural = lx.looks_plural(words[-1]) and (plural_verb or det in lx.UNIVERSAL)
        if is_plural:
            words[-1] = lx.singularize(words[-1])
        cats, lex = self._categories(words, "query", noun=True)
        if det in lx.DEFINITE | lx.POSSESSIVE_DET or (det is None and not is_plural and not plural_verb):
            key = " ".join(words)
            disp = (f"the {key}" if det in lx.DEFINITE else key)
            return Subject("entity", key, disp, classes=rel_atoms, lex=[LexEntry(key, "entity", disp)] + rel_lex)
        if det in lx.EXISTENTIAL:
            key = f"some {' '.join(words)} #{next(self._skolem)}"
            return Subject("skolem", key, f"some {' '.join(words)}", classes=[Atom(IS, (S, c)) for c in cats] + rel_atoms,
                           plural=is_plural, lex=lex + rel_lex + [LexEntry(key, "entity", f"some {' '.join(words)}")])
        disp = " ".join(words)
        return Subject("generic", "?x", disp, classes=[Atom(IS, (S, c)) for c in cats] + rel_atoms,
                       quant=quant, plural=True, lex=lex + rel_lex, default=det is None)

    def _categories(self, words: List[str], mode: str, noun: bool) -> Tuple[List[str], List[LexEntry]]:
        """'big brown dog' -> assert: [big brown dog, big, brown, dog]; query: [big, brown, dog]."""
        words = [x for x in words if x not in {"very", "really", "quite"} or len(words) == 1]
        if not words:
            return [], []
        head = words[-1]
        mods = words[:-1]
        kind = "noun" if noun else "adj"
        cats = list(mods) + [head]
        lex = [LexEntry(m, "adj", m) for m in mods] + [LexEntry(head, kind, head)]
        if mode == "assert" and len(words) > 1:
            compound = " ".join(words)
            cats = [compound] + cats
            lex.append(LexEntry(compound, kind, compound))
        return cats, lex

    # ------------------------------------------------------------ verb phrases
    def _vp(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope], mode: str, plural: bool):
        if not toks:
            raise ParseError("missing verb phrase")
        w = _words(toks)
        neg = False
        head = w[0]
        rest = toks[1:]
        if rest and rest[0].low in lx.NEGATORS:
            neg, rest = True, rest[1:]
        if head in lx.COPULAS:
            atoms, lex, extra = self._copular(rest, ctx, scope, mode, plural)
        elif head in lx.DO_AUX:
            if not rest:
                raise ParseError("missing verb after 'do'")
            atoms, lex, extra = self._verbal(rest, ctx, scope)
        elif head in lx.MODALS:
            if not rest:
                raise ParseError(f"missing verb after '{head}'")
            atoms, lex, extra = self._modal(head, rest, ctx, scope)
        else:
            atoms, lex, extra = self._verbal(toks, ctx, scope)
        if neg:
            atoms = [a.negate() for a in atoms]
        return atoms, lex, extra

    def _modal(self, modal: str, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope]):
        verb = lx.verb_lemma(toks[0].low) if toks[0].low not in lx.COPULAS else "be"
        if verb == "be" and len(toks) > 1:
            cat = f"{modal} be {' '.join(t.low for t in toks[1:])}"
            return [Atom(IS, (S, cat))], [LexEntry(cat, "modal", cat)], None
        if len(toks) == 1:
            cat = f"{modal} {verb}"
            return [Atom(IS, (S, cat))], [LexEntry(cat, "modal", cat)], None
        atoms, lex, extra = self._verbal(toks, ctx, scope)
        out = [Atom(f"{modal} {a.pred}", a.args, a.neg) for a in atoms]
        return out, [LexEntry(a.pred, "verb", a.pred) for a in out], extra

    def _verbal(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope]):
        verb = lx.verb_lemma(toks[0].low)
        if verb in lx.FUNCTION_WORDS or verb in {"be", "been", "being"} or not toks[0].low.isalpha():
            raise ParseError(f"'{toks[0].text}' is not a verb")
        rest = toks[1:]
        pred = verb
        if rest and rest[0].low in lx.PREPOSITIONS:
            pred = f"{verb} {rest[0].low}"
            rest = rest[1:]
        if not rest:
            return [Atom(pred, (S,))], [LexEntry(pred, "verb", pred)], None
        atoms, lex = [], [LexEntry(pred, "verb", pred)]
        for obj in self._np_list(rest):
            term, disp, olex = self._term(obj, ctx, scope)
            atoms.append(Atom(pred, (S, term)))
            lex += olex
        return atoms, lex, None

    def _copular(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope], mode: str, plural: bool):
        if not toks:
            raise ParseError("missing predicate after 'is'")
        w = _words(toks)

        # superlative inside an assertion is unsupported; comparatives: "older than Bob"
        if "than" in w:
            i = w.index("than")
            rel_words = [x for x in w[:i] if x not in {"much", "a", "little", "lot", "far", "even", "slightly"}]
            if not rel_words or i + 1 >= len(toks):
                raise ParseError("incomplete comparison")
            pred = " ".join(rel_words) + " than"
            atoms, lex = [], [LexEntry(pred, "crel", pred)]
            for obj in self._np_list(toks[i + 1:]):
                term, _, olex = self._term(obj, ctx, scope)
                atoms.append(Atom(pred, (S, term)))
                lex += olex
            return atoms, lex, ("__comparative__", pred)

        # taxonomy markers: "a kind of animal"
        m = re.match(r"^(?:a|an)\s+(?:kind|type|sort|form|example|instance|member)\s+of\s+(?:an?\s+|the\s+)?(.+)$", " ".join(w))
        if m:
            words = m.group(1).split()
            words[-1] = lx.singularize(words[-1])
            cats, lex = self._categories(words, mode, noun=True)
            return [Atom(IS, (S, c)) for c in cats], lex, None

        # prepositional / participial relations: "in Paris", "located in Paris", "part of the engine"
        p = next((i for i, x in enumerate(w[:3]) if x in lx.PREPOSITIONS), None)
        if p is not None and p + 1 < len(toks) and (p == 0 or w[0] not in lx.DETERMINERS):
            j = p + 1
            while j < len(w) and w[j] in lx.PREPOSITIONS and j < p + 3:
                j += 1
            pred = " ".join(w[:j])
            atoms, lex = [], [LexEntry(pred, "crel", pred)]
            for obj in self._np_list(toks[j:]):
                term, _, olex = self._term(obj, ctx, scope)
                atoms.append(Atom(pred, (S, term)))
                lex += olex
            return atoms, lex, None

        # relational noun or definition: "the father of Carl" / "the process by which ..."
        if w[0] in lx.DETERMINERS:
            b = next((i for i, x in enumerate(w) if i >= 2 and (x in lx.PREPOSITIONS or x in lx.RELATIVE
                                                                 or x in {"used", "where", "whose", "made", "found"})), None)
            if b is not None:
                tail = toks[b + 1:]
                head_words = [x for x in w[1:b]]
                if w[b] == "of" and 0 < len(tail) <= 3 and self._entityish(tail, ctx) and len(head_words) <= 2:
                    pred = " ".join(head_words) + " of"
                    term, _, olex = self._term(tail, ctx, scope)
                    # Display keeps the determiner so answers read "is the father of Mary".
                    return [Atom(pred, (S, term))], [LexEntry(pred, "crel", f"{w[0]} {pred}")] + olex, None
                if head_words:
                    head_words[-1] = lx.singularize(head_words[-1]) if plural else head_words[-1]
                    cats, lex = self._categories(head_words, mode, noun=True)
                    gloss = " ".join(t.text for t in toks)
                    return [Atom(IS, (S, c)) for c in cats], lex, ("__definition__", gloss)

        # plain categories: "a man", "mortal", "big and red", "loyal animals"
        atoms: List[Atom] = []
        lex: List[LexEntry] = []
        for phrase in self._np_list(toks):
            pw = [t.low for t in phrase]
            has_article = pw[0] in lx.ARTICLES | {"the"}
            pw = [x for x in pw if x not in lx.DETERMINERS]
            if not pw or any(x in lx.FUNCTION_WORDS for x in pw):
                raise ParseError(f"could not understand '{' '.join(t.text for t in phrase)}'")
            was_plural = lx.looks_plural(pw[-1]) and plural
            if was_plural:
                pw[-1] = lx.singularize(pw[-1])
            noun = has_article or was_plural or (len(pw) > 1 and pw[-1] not in ctx.adjectives)
            cats, plex = self._categories(pw, mode, noun=noun)
            atoms += [Atom(IS, (S, c)) for c in cats]
            lex += plex
        return atoms, lex, None

    def _entityish(self, toks: List[Tok], ctx: ParseContext) -> bool:
        if toks[0].low in {"the", "him", "her", "them", "it"} or toks[0].cap:
            return True
        return " ".join(t.low for t in toks) in ctx.entities

    def _np_list(self, toks: List[Tok]) -> List[List[Tok]]:
        groups, cur = [], []
        for t in toks:
            if t.low in ("and", ",", "or"):
                if cur:
                    groups.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            groups.append(cur)
        if not groups:
            raise ParseError("missing noun phrase")
        return groups

    def _term(self, toks: List[Tok], ctx: ParseContext, scope: Optional[VarScope]) -> Tuple[str, str, List[LexEntry]]:
        """Noun phrase in object position -> constant (or variable inside rules)."""
        if len(toks) == 1 and scope is not None:
            v = scope.var_for(toks[0])
            if v:
                return v, toks[0].text, []
        if len(toks) == 1 and toks[0].low in {"him", "her", "it", "them"}:
            if not ctx.last_entity:
                raise ParseError(f"I don't know who '{toks[0].text}' refers to")
            return ctx.last_entity, ctx.last_entity_display or ctx.last_entity, []
        if len(toks) >= 2 and toks[-1].low == "'s":
            toks = toks[:-1]
        det = toks[0].low if toks[0].low in lx.DETERMINERS else None
        content = toks[1:] if det else toks
        if not content or any(t.low in lx.FUNCTION_WORDS for t in content):
            raise ParseError(f"could not understand the noun phrase '{' '.join(t.text for t in toks)}'")
        if det is None and all(t.cap for t in content):
            key = " ".join(t.low for t in content)
            disp = " ".join(t.text for t in content)
            return key, disp, [LexEntry(key, "entity", disp)]
        words = [t.low for t in content]
        if det not in lx.DEFINITE and lx.looks_plural(words[-1]) and " ".join(words) not in ctx.entities:
            words[-1] = lx.singularize(words[-1])
        key = " ".join(words)
        disp = f"the {key}" if det in lx.DEFINITE else key
        return key, disp, [LexEntry(key, "entity", disp)]

    # ------------------------------------------------------------ questions
    def parse_question(self, text: str, ctx: ParseContext, original: str = "") -> Parsed:
        original = original or text
        core = text.strip().rstrip(" ?.!")
        low = core.lower()
        toks = tokenize(core)
        if not toks:
            return Unparsed(original, "empty question")
        w = _words(toks)

        m = re.match(r"^(?:what\s+(?:do|did)\s+you\s+know\s+about|tell\s+me\s+(?:about|everything\s+about)|describe|explain|define)\s+(.+)$", low)
        if m:
            return self._describe(original, m.group(1), ctx, "what")
        m = re.match(r"^(?:what|who)\s+(?:is|are)\s+(?:similar|related)\s+to\s+(.+)$", low)
        if m:
            key = self._np_key(m.group(1), ctx)
            return Question(original, "similar", target=key, target_display=m.group(1))
        if re.match(r"^what\s+(?:have|did|do)\s+you\s+(?:learn|learned|learnt|induce|induced|hypothesi[sz]e|infer|inferred|notice|noticed)", low):
            return Question(original, "learned")

        if w[0] == "why":
            inner = self.parse_question(" ".join(t.text for t in toks[1:]), ctx, original)
            if isinstance(inner, Question):
                inner.explain = True
            return inner

        if w[:2] == ["how", "many"]:
            return self._count(original, toks[2:], ctx)

        if w[0] in lx.COPULAS | lx.DO_AUX | lx.MODALS:
            return self._yesno(original, toks, ctx)

        if w[0] in {"who", "what", "which", "whom"}:
            return self._wh(original, toks, ctx)

        return Unparsed(original, "I can answer yes/no questions (Is/Does/Can ...), who/what/which questions, "
                                  "'how many', 'why', and maths -- I couldn't read this one")

    def _np_key(self, phrase: str, ctx: ParseContext) -> str:
        toks = tokenize(phrase)
        if toks and toks[0].low in lx.DETERMINERS:
            toks = toks[1:]
        words = [t.low for t in toks]
        key = " ".join(words)
        if key in ctx.entities or key in ctx.categories or key in ctx.quantities:
            return key
        if words and lx.looks_plural(words[-1]):
            words[-1] = lx.singularize(words[-1])
        return " ".join(words)

    def _describe(self, original: str, phrase: str, ctx: ParseContext, wh: str) -> Question:
        key = self._np_key(phrase, ctx)
        disp = re.sub(r"^(?:a|an|the)\s+", "", phrase.strip(), flags=re.I)
        return Question(original, "describe", target=key, target_display=disp, wh_word=wh)

    def _yesno(self, original: str, toks: List[Tok], ctx: ParseContext) -> Parsed:
        aux = toks[0]
        rest = toks[1:]
        best, err = None, "I couldn't work out what the question is about"
        for k in range(1, min(len(rest), 7)):
            subj_t, pred_t = rest[:k], rest[k:]
            if aux.low in lx.DO_AUX:
                vp = pred_t
            else:
                vp = [aux] + pred_t
            try:
                # Agreement lives on the auxiliary: "Does gold ..." is singular, "Do birds ..." plural.
                subj = self._subject(subj_t, ctx, None, "query", aux)
                atoms, lex, extra = self._vp(vp, ctx, None, "query", subj.plural)
            except ParseError as exc:
                err = str(exc)
                continue
            if extra and extra[0] == "__definition__":
                continue
            score = self._ground_score(subj, atoms, ctx) - 0.2 * k
            if aux.low in lx.DO_AUX and pred_t:
                score += self._verb_score(pred_t[0], ctx)   # "Bob" is a poor verb, "like" a fine one
            if len({t.cap for t in subj_t}) > 1:
                score -= 1.0                                 # "Alice like" mixes a name with a word
            if best is None or score > best[0]:
                best = (score, subj, atoms, lex)
        if best is None:
            return Unparsed(original, err)
        _, subj, atoms, lex = best
        q = Question(original, "yesno", lexicon=subj.lex + lex)
        if subj.kind == "entity":
            q.goals = [_bind(a, subj.term) for a in atoms]
            q.target, q.target_display = subj.term, subj.display
        elif subj.kind in ("generic", "skolem"):
            q.generic = subj.display
            const = f"a typical {subj.display}"
            q.hypothetical = [_bind(a, const) for a in subj.classes]
            q.goals = [_bind(a, const) for a in atoms]
            q.target, q.target_display = const, const
            if subj.quant == "no":
                q.goals = [g.negate() for g in q.goals]
        else:
            return Unparsed(original, "I can't answer yes/no questions about 'someone' in general")
        return q

    def _wh(self, original: str, toks: List[Tok], ctx: ParseContext) -> Parsed:
        w = _words(toks)
        wh = w[0]
        rest = toks[1:]
        class_atoms: List[Atom] = []
        lex: List[LexEntry] = []
        if wh == "which" and rest and rest[0].low not in lx.COPULAS | lx.DO_AUX | lx.MODALS:
            j = next((i for i, t in enumerate(rest) if t.low in lx.COPULAS | lx.DO_AUX | lx.MODALS), None)
            if j is None:
                j = 1
            noun = [t.low for t in rest[:j]]
            noun[-1] = lx.singularize(noun[-1])
            cats, lex = self._categories(noun, "query", noun=True)
            class_atoms = [Atom(IS, ("?q", c)) for c in cats]
            rest = rest[j:]
        if not rest:
            return Unparsed(original, "incomplete question")
        r = _words(rest)

        # "What does Alice like?" / "Who does Bob live with?"
        if r[0] in lx.DO_AUX and len(rest) >= 3:
            best = None
            for k in range(1, min(len(rest) - 1, 6)):
                subj_t, verb_t = rest[1:k + 1], rest[k + 1:]
                if not subj_t or not verb_t:
                    continue
                try:
                    subj = self._subject(subj_t, ctx, None, "query", verb_t[0])
                except ParseError:
                    continue
                if subj.kind != "entity":
                    continue
                verb = lx.verb_lemma(verb_t[0].low)
                pred = verb + (" " + verb_t[1].low if len(verb_t) > 1 and verb_t[1].low in lx.PREPOSITIONS else "")
                score = (2 if subj.term in ctx.entities else 0) + (2 if pred in ctx.predicates else 0) - 0.2 * k
                if best is None or score > best[0]:
                    best = (score, subj, pred)
            if best is None:
                return Unparsed(original, "I couldn't find who the question is about")
            _, subj, pred = best
            goals = [Atom(pred, (subj.term, "?q"))] + class_atoms
            return Question(original, "wh", goals=goals, wh_word=wh, lexicon=lex + subj.lex)

        # "Who is the youngest?" / "Which dog is the biggest?" / "Who is the most intelligent?"
        if r[0] in lx.COPULAS and len(r) >= 3 and r[1] == "the":
            sup_words = r[2:]
            comp = None
            if sup_words[0] in {"most", "least"} and len(sup_words) >= 2:
                comp = ("more " if sup_words[0] == "most" else "less ") + " ".join(sup_words[1:2])
            elif len(sup_words) == 1 or (len(sup_words) == 2 and sup_words[1] in {"one", "person"}):
                comp = lx.superlative_to_comparative(sup_words[0])
            if comp:
                return Question(original, "superlative", target=f"{comp} than", goals=class_atoms,
                                wh_word=wh, superlative_word=" ".join(sup_words), lexicon=lex)

        # "What is Paris in?" / "What is Paris located in?" -> in(paris, ?q)
        if r[0] in lx.COPULAS and len(rest) >= 3 and r[-1] in lx.PREPOSITIONS:
            best = None
            for k in range(1, len(rest) - 1):
                subj_t, middle = rest[1:1 + k], rest[1 + k:-1]
                try:
                    subj = self._subject(subj_t, ctx, None, "query", rest[0])
                except ParseError:
                    continue
                if subj.kind != "entity" or any(t.low in lx.FUNCTION_WORDS for t in middle):
                    continue
                pred = " ".join([t.low for t in middle] + [r[-1]])
                score = (2 if subj.term in ctx.entities else 0) + (1 if pred in ctx.predicates else 0) - 0.5 * len(middle)
                if best is None or score > best[0]:
                    best = (score, subj, pred)
            if best:
                _, subj, pred = best
                return Question(original, "wh", goals=[Atom(pred, (subj.term, "?q"))] + class_atoms, wh_word=wh,
                                lexicon=lex + subj.lex + [LexEntry(pred, "crel", pred)])

        # "What is X?" / "Who is Bob?" -> describe, unless X is relational ("older than ...")
        if r[0] in lx.COPULAS and not class_atoms:
            pred_t = rest[1:]
            pw = _words(pred_t)
            relational = "than" in pw or any(x in lx.PREPOSITIONS for x in pw)
            if pred_t and not relational and pw[0] not in lx.NEGATORS:
                q = self._describe(original, " ".join(t.text for t in pred_t), ctx, wh)
                try:
                    atoms, plex, _ = self._vp(rest, ctx, None, "query", r[0] in lx.COPULA_PL)
                    q.goals = [_bind(a, "?q") for a in atoms]
                    q.lexicon = plex
                except ParseError:
                    pass
                return q

        try:
            atoms, plex, _ = self._vp(rest, ctx, None, "query", r[0] in lx.COPULA_PL)
        except ParseError as exc:
            return Unparsed(original, str(exc))
        return Question(original, "wh", goals=[_bind(a, "?q") for a in atoms] + class_atoms, wh_word=wh,
                        lexicon=lex + plex)

    def _count(self, original: str, toks: List[Tok], ctx: ParseContext) -> Parsed:
        if not toks:
            return Unparsed(original, "how many what?")
        w = _words(toks)
        j = next((i for i, x in enumerate(w) if x in lx.COPULAS | lx.DO_AUX | lx.MODALS), len(w))
        noun = w[:j]
        if not noun:
            return Unparsed(original, "how many what?")
        noun[-1] = lx.singularize(noun[-1])
        # "How many people/things ..." counts individuals, not members of a 'person' class.
        unrestricted = noun in (["person"], ["thing"], ["one"], ["individual"])
        cats, lex = ([], []) if unrestricted else self._categories(noun, "query", noun=True)
        goals = [Atom(IS, ("?q", c)) for c in cats]
        tail = toks[j:]
        if tail and not (len(tail) >= 2 and tail[1].low == "there"):
            try:
                atoms, plex, _ = self._vp(tail, ctx, None, "query", True)
                goals += [_bind(a, "?q") for a in atoms]
                lex += plex
            except ParseError as exc:
                return Unparsed(original, str(exc))
        return Question(original, "count", goals=goals, target=" ".join(noun), lexicon=lex)


# ----------------------------------------------------------------- helpers

def _bind(atom: Atom, term: str) -> Atom:
    return Atom(atom.pred, tuple(term if a == S else a for a in atom.args), atom.neg)


def _looks_verbal(pred: str, ctx: ParseContext) -> bool:
    return not pred.endswith((" than", " of")) and pred.split()[0] not in lx.PREPOSITIONS


def comparative_rules(assertion: Assertion) -> None:
    """Adds order axioms for any comparative relation an assertion introduced."""
    preds = {a.pred for a in assertion.facts if a.pred.endswith(" than")}
    preds |= {r.head.pred for r in assertion.rules if r.head.pred.endswith(" than")}
    for p in preds:
        assertion.rules += SemanticParser._order_axioms(p)
