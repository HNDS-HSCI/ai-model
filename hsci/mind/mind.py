"""HSCI Mind -- the cognitive cycle that ties every layer together.

For each sentence (the HNS-DS RIR loop, applied to language):

    perceive   tokenise + semantic parse, ranked by grounding in current knowledge
    formalise  -> facts / rules / formulas / quantities (statements)
               -> goals + assumptions (questions)                     [Sigma]
    plan       choose the solver: deduction, quantity chaining, algebra,
               superlatives, description, similarity
    solve      forward chaining to a fixed point / SymPy               [S]
    verify     Z3 re-checks every proof; numbers are substituted back  [V]
    learn      statements are committed atomically after a consistency
               check; induction proposes and refutes hypotheses       [L]
    explain    proofs are verbalised back into English with provenance

Answers are three-valued: proven yes, proven no, or an honest "I don't know".
Inductive hypotheses can upgrade "I don't know" to an explicitly-labelled
"probably", but are never presented as verified.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from hsci.mind import learner as learning
from hsci.mind.explain import Verbalizer, join_list
from hsci.mind.kb import COMMON, KnowledgeBase
from hsci.mind.logic import IS, Atom, Rule, constants
from hsci.mind.parser import (Assertion, FormulaStatement, ParseContext, QuantityStatement, Question,
                              SemanticParser, Unparsed, split_sentences)
from hsci.mind.quantities import Formula, Quantity, QuantityAnswer, solve_for, solve_math
from hsci.mind.reasoner import (Closure, Derivation, SaturationLimit, _join, proof_tree, saturate, saturate_all,
                                uses_default)
from hsci.mind.semantic_space import ConceptSpace, fuzzy_match
from hsci.mind.verifier import verify_all
from hsci.mind.neural.intuition import NO_AT, YES_AT, Intuition
from hsci.mind.understanding import meaning as mn
from hsci.mind.understanding.encoder import EncoderProvider
from hsci.mind.understanding.engine import ACT, CONFIRM, Reading, UnderstandingEngine

logger = logging.getLogger("HSCI.Mind")

_SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "common_knowledge.txt")
_UTTERANCES_FILE = os.path.join(os.path.dirname(__file__), "data", "seed_utterances.txt")


# ----------------------------------------------------------------- results

@dataclass
class Item:
    input: str
    kind: str                    # statement | question | unparsed
    status: str                  # learned | known | contradiction | answered | unknown | probable | error
    answer: str
    verified: bool = False
    method: str = ""
    confidence: Optional[float] = None
    explanation: List[str] = field(default_factory=list)
    logic: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    statement_id: Optional[int] = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MindResponse:
    world: str
    items: List[Item]
    latency_ms: float

    @property
    def reply(self) -> str:
        return "\n".join(i.answer for i in self.items)

    def to_dict(self) -> dict:
        return {"world": self.world, "reply": self.reply, "latency_ms": round(self.latency_ms, 2),
                "items": [i.to_dict() for i in self.items]}


@dataclass
class _State:
    version: Tuple[int, int]
    closure: Closure
    rules: List[Rule]
    given: List[Derivation]
    hypotheses: List[Rule]
    lexicon: Dict[str, Dict[str, str]]
    formulas: List[Formula]
    quantities: Dict[str, Quantity]


def _key(rule: Rule) -> str:
    return json.dumps(rule.to_json(), sort_keys=True)


def _num(v: float) -> str:
    if abs(v - round(v)) < 1e-9 * max(1.0, abs(v)):
        return str(int(round(v)))
    return f"{v:.6g}"


@dataclass
class _Pending:
    """An utterance the Mind asked about and is waiting to have clarified."""
    text: str
    reading: Optional[Reading]


def _typical(term: str) -> bool:
    return term.startswith("a typical ") or term.startswith("__")


# ----------------------------------------------------------------- the mind

class Mind:
    def __init__(self, db_path: str = ":memory:", seed: bool = True, encoder: Optional[str] = None) -> None:
        self.kb = KnowledgeBase(db_path)
        self.parser = SemanticParser()
        self._lock = threading.RLock()
        self._cache: Dict[str, _State] = {}
        self._discourse: Dict[str, Tuple[str, str]] = {}
        self._pending: Dict[str, _Pending] = {}
        self._asked_this_message: Dict[str, Optional[_Pending]] = {}
        self._intuitions: Dict[int, Intuition] = {}
        self.seed_report: List[str] = []
        self.understanding = UnderstandingEngine(self.kb._conn, self.parser, EncoderProvider(mode=encoder))
        if seed and not self.kb.statements(COMMON, limit=1):
            self.load_text_file(_SEED_FILE, COMMON)
        if seed:
            self.seed_report += self.understanding.bootstrap(_UTTERANCES_FILE, self._context(COMMON, self._state(COMMON)))

    # ------------------------------------------------------------ public API
    def process(self, text: str, world: str = "default", direct: bool = False) -> MindResponse:
        """Perceive -> understand -> act for each sentence.

        ``direct=True`` skips the understanding layer and trusts the grammar outright
        (used for loading curated knowledge files).
        """
        start = time.perf_counter()
        items: List[Item] = []
        with self._lock:
            # A question the Mind asks can only be answered by the *next* message, not by later
            # sentences of the same message.
            self._asked_this_message[world] = None
            for sentence in split_sentences(text):
                t0 = time.perf_counter()
                ctx = self._context(world, self._state(world))
                if direct:
                    new = [self._run(p, world, sentence) for p in self.parser.parse(sentence, ctx)]
                else:
                    new = self._perceive_and_act(sentence, world, ctx)
                for item in new:
                    item.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                    self.kb.log_episode(world, item.input, item.kind, item.status, item.verified, item.method, item.latency_ms)
                    items.append(item)
        return MindResponse(world, items, (time.perf_counter() - start) * 1000)

    def teach(self, surface: str, canonical: str, world: str = "default") -> str:
        """Explicitly teach a phrasing: from now on ``surface`` means what ``canonical`` means."""
        with self._lock:
            readings = self.understanding.understand(canonical, self._context(world, self._state(world)))
            if not readings or readings[0].confidence < ACT:
                raise ValueError(f"I don't understand “{canonical}” well enough to learn from it")
            best = readings[0]
            self.understanding.remember(surface, mn.substitute(best.meaning, {}, {}, surface), "user", world)
            return mn.paraphrase(best.meaning, self._verbalizer(world, best.meaning))

    # ------------------------------------------------------------ perception
    def _run(self, parsed, world: str, sentence: str) -> Item:
        try:
            return self._handle(parsed, world)
        except SaturationLimit as exc:
            return Item(sentence, "statement", "error", f"That made my knowledge explode: {exc}.")

    def _verbalizer(self, world: str, meaning: List[dict]) -> Verbalizer:
        lex = {k: dict(v) for k, v in self._state(world).lexicon.items()}
        for m in meaning:
            for e in m.get("lexicon", []):
                lex.setdefault(e["symbol"], {})[e["kind"]] = e["display"]
        return Verbalizer(lex)

    def _perceive_and_act(self, sentence: str, world: str, ctx: ParseContext) -> List[Item]:
        pending = self._pending.get(world)
        if pending and pending is not self._asked_this_message.get(world):
            resolved = self._resolve(pending, sentence, world, ctx)
            if resolved is not None:
                return resolved
        elif self.understanding.dialogue_act(sentence):
            return [Item(sentence, "clarify", "clarify", "There's nothing I asked you to confirm right now.",
                         method="understanding")]

        readings = self.understanding.understand(sentence, ctx)
        best = readings[0] if readings else None
        if best and best.confidence >= ACT:
            items = [self._run(p, world, sentence) for p in best.parsed]
            self._after_act(sentence, best, items, world)
            return items

        if best and best.confidence >= CONFIRM:
            self._pending[world] = _Pending(sentence, best)
            self._asked_this_message[world] = self._pending[world]
            para = mn.paraphrase(best.meaning, self._verbalizer(world, best.meaning))
            notes = [f"confidence {best.confidence:.2f}"] + best.reasons
            if best.experience_text:
                notes.append(f"by analogy with “{best.experience_text}”")
            return [Item(sentence, "clarify", "clarify", f"Do you mean: {para}? (yes / no — or say it another way)",
                         method="understanding", confidence=round(best.confidence, 2), notes=notes)]

        self._pending[world] = _Pending(sentence, None)
        self._asked_this_message[world] = self._pending[world]
        why = next((p.reason for p in self.parser.parse(sentence, ctx) if isinstance(p, Unparsed)), None)
        return [Item(sentence, "clarify", "clarify",
                     f"I'm not sure what you mean by “{sentence}”. Could you say it another way? "
                     "I'll remember what it means.", method="understanding",
                     confidence=round(best.confidence, 2) if best else 0.0,
                     notes=([why] if why else []) + (best.reasons if best else []))]

    def _after_act(self, sentence: str, reading: Reading, items: List[Item], world: str) -> None:
        if any(i.status == "error" for i in items):
            return
        if "grammar" in reading.source and reading.confidence >= 0.8:
            self.understanding.remember(sentence, reading.meaning, "grammar", world)
        if reading.source == "analogy" and reading.experience_text and items:
            items[0].notes.insert(0, f"Understood by analogy with “{reading.experience_text}” "
                                     f"(confidence {reading.confidence:.2f}).")

    def _resolve(self, pending: "_Pending", sentence: str, world: str, ctx: ParseContext) -> Optional[List[Item]]:
        """Handles the reply to "Do you mean ...?" / "Could you say it another way?"."""
        act = self.understanding.dialogue_act(sentence)
        if act == "affirm" and pending.reading:
            del self._pending[world]
            items = [self._run(p, world, pending.text) for p in pending.reading.parsed]
            self.understanding.remember(pending.text, pending.reading.meaning, "confirmed", world)
            self.understanding.feedback(pending.reading.experience_id, True)
            if items:
                items[0].answer = f"Thanks, I'll remember that. {items[0].answer}"
            return items
        if act in ("deny", "affirm"):
            if act == "deny" and pending.reading:
                self.understanding.feedback(pending.reading.experience_id, False)
            self._pending[world] = _Pending(pending.text, None)
            return [Item(sentence, "clarify", "clarify", f"OK. Could you say “{pending.text}” another way?",
                         method="understanding")]

        del self._pending[world]
        if (pending.text.rstrip().endswith("?") != sentence.rstrip().endswith("?")
                or self.understanding.related(pending.text, sentence) < 0.35):
            return None  # the user moved on to something else
        readings = self.understanding.understand(sentence, ctx)
        if not readings or readings[0].confidence < ACT:
            return None
        best = readings[0]
        items = [self._run(p, world, sentence) for p in best.parsed]
        self.understanding.remember(pending.text, mn.substitute(best.meaning, {}, {}, pending.text), "user", world)
        if "grammar" in best.source:
            self.understanding.remember(sentence, best.meaning, "grammar", world)
        if pending.reading and mn.key(pending.reading.meaning) != mn.key(best.meaning):
            self.understanding.feedback(pending.reading.experience_id, False)
        if items:
            items[0].answer = f"Got it, from now on I'll understand “{pending.text}” that way. {items[0].answer}"
        return items

    def load_text_file(self, path: str, world: str) -> List[Item]:
        with open(path, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
        items: List[Item] = []
        for ln in lines:
            items += self.process(ln, world, direct=True).items
        failed = [f"{i.input} -> {i.answer}" for i in items if i.status in ("error", "contradiction")]
        self.seed_report = failed
        for f in failed:
            logger.warning("seed sentence not learned: %s", f)
        return items

    def forget(self, statement_id: int, world: str = "default") -> bool:
        with self._lock:
            return self.kb.forget_statement(world, statement_id)

    def reset(self, world: str = "default") -> None:
        with self._lock:
            self.kb.reset_world(world)
            self._discourse.pop(world, None)
            self._pending.pop(world, None)

    def snapshot(self, world: str = "default", limit: int = 300) -> dict:
        with self._lock:
            st = self._state(world)
            v = Verbalizer(st.lexicon)
            own_rules = {r["id"]: r for r in self.kb.rule_rows(world, ("active",))}
            derived = [v.atom(a) for a, d in st.closure.derivations.items() if d.rule is not None and not _typical(a.args[0])]
            return {
                "world": world,
                "stats": {**self.kb.stats(world), "closure_size": len(st.closure)},
                "understanding": self.understanding.status(),
                "pending_question": self._pending[world].text if world in self._pending else None,
                "statements": self.kb.statements(world, limit),
                "facts": [v.atom(d.atom) for d in st.given if not _typical(d.atom.args[0])][:limit],
                "derived": derived[:limit],
                "rules": [{"id": int(r.rule_id), "text": v.rule(r), "origin": r.origin} for r in st.rules
                          if int(r.rule_id) in own_rules][:limit],
                "hypotheses": self._hypothesis_rows(world, v),
                "formulas": [f.text for f in st.formulas],
                "quantities": {k: {"value": q.value, "unit": q.unit} for k, q in st.quantities.items()},
            }

    # ------------------------------------------------------------ state
    def _state(self, world: str) -> _State:
        ver = self.kb.version(world)
        st = self._cache.get(world)
        if st and st.version == ver:
            return st
        given = [Derivation(a, None, (), src, 0) for a, src, _ in self.kb.facts(world)]
        rules = self.kb.rules(world)
        closure = saturate_all(rules, given)
        st = _State(ver, closure, rules, given, self.kb.rules(world, ("hypothesis",)), self.kb.lexicon(world),
                    self.kb.formulas(world), self.kb.quantities(world))
        self._cache[world] = st
        return st

    def _context(self, world: str, st: _State) -> ParseContext:
        ctx = ParseContext()
        for sym, kinds in st.lexicon.items():
            if "entity" in kinds:
                ctx.entities.add(sym)
            if kinds.keys() & {"noun", "adj", "modal"}:
                ctx.categories.add(sym)
            if "adj" in kinds:
                ctx.adjectives.add(sym)
            if kinds.keys() & {"verb", "crel"}:
                ctx.predicates.add(sym)
        for a in st.closure.atoms():
            if a.pred == IS:
                ctx.categories.add(a.args[1])
                ctx.entities.add(a.args[0])
            else:
                ctx.predicates.add(a.pred)
        for r in st.rules:
            for a in (*r.body, r.head):
                if a.pred == IS:
                    ctx.categories.add(a.args[1])
                else:
                    ctx.predicates.add(a.pred)
        ctx.quantities = set(st.quantities) | {v for f in st.formulas for v in f.variables}
        if world in self._discourse:
            ctx.last_entity, ctx.last_entity_display = self._discourse[world]
        return ctx

    # ------------------------------------------------------------ dispatch
    def _handle(self, parsed, world: str) -> Item:
        if isinstance(parsed, Unparsed):
            return Item(parsed.text, "unparsed", "error",
                        f"I couldn't turn that into logic: {parsed.reason}.",
                        notes=["Try simpler sentences, e.g. 'Rex is a dog.', 'All dogs are mammals.', "
                               "'If someone is kind then they are happy.', 'Is Rex a mammal?'"])
        if isinstance(parsed, Assertion):
            return self._tell(parsed, world)
        if isinstance(parsed, FormulaStatement):
            with self.kb.transaction():
                sid = self.kb.add_statement(world, parsed.text, "formula")
                self.kb.add_formula(world, sid, parsed.formula)
            pretty = _pretty_formula(parsed.formula)
            return Item(parsed.text, "statement", "learned", f"Learned the formula {pretty}.",
                        method="formula", logic=[pretty], statement_id=sid)
        if isinstance(parsed, QuantityStatement):
            q = parsed.quantity
            with self.kb.transaction():
                sid = self.kb.add_statement(world, parsed.text, "quantity")
                self.kb.set_quantity(world, sid, q)
            return Item(parsed.text, "statement", "learned", f"Noted: {q.name} = {_num(q.value)}{' ' + q.unit if q.unit else ''}.",
                        method="quantity", logic=[f"{q.name} = {q.value}"], statement_id=sid)
        if isinstance(parsed, Question):
            return self._answer(parsed, world)
        return Item(str(parsed), "unparsed", "error", "Unsupported input.")

    # ------------------------------------------------------------ learning (tell)
    def _tell(self, a: Assertion, world: str) -> Item:
        st = self._state(world)
        unsafe = [r for r in a.rules if not r.is_safe()]
        if unsafe:
            return Item(a.text, "statement", "error", "That rule mentions something its condition never introduces.")
        known_keys = {_key(r) for r in st.rules}
        new_rules = [r for r in a.rules if _key(r) not in known_keys]
        new_facts = [f for f in a.facts if f not in st.closure or st.closure.get(f).rule is not None]
        new_derivs = [Derivation(f, None, (), a.text, 0) for f in a.facts]
        v = Verbalizer({**st.lexicon, **{e.symbol: {e.kind: e.display} for e in a.lexicon}})
        logic = [str(f) for f in a.facts] + [str(r) for r in a.rules if r.origin != "grammar"]

        user_rules = [r for r in new_rules if r.origin != "grammar"]
        if not user_rules and not a.definitions and all(f in st.closure for f in a.facts):
            already = [st.closure.get(f) for f in a.facts]
            if all(d.rule is None for d in already):
                return Item(a.text, "statement", "known", "I already know that.", logic=logic, verified=True)
            tree = proof_tree(st.closure, next(d.atom for d in already if d.rule is not None))
            verdict = verify_all([tree])
            return Item(a.text, "statement", "known", "That already follows from what I know.",
                        verified=verdict.verified, method="deduction", explanation=v.proof_lines(tree), logic=logic)

        closure = _extend(st.closure, st.rules + new_rules, st.given, new_derivs, bool(new_rules))
        clashes = [(p, n) for p, n in closure.contradictions() if not (p in st.closure and n in st.closure)]
        if clashes:
            p, n = clashes[0]
            v2 = Verbalizer({**st.lexicon, **{e.symbol: {e.kind: e.display} for e in a.lexicon}})
            expl = ["If I accepted this:"] + v2.proof_lines(proof_tree(closure, p)) + ["But also:"] + v2.proof_lines(proof_tree(closure, n))
            return Item(a.text, "statement", "contradiction",
                        f"That contradicts what I know: it would mean both “{v2.atom(p)}” and “{v2.atom(n)}”. "
                        "I have not stored it.", explanation=expl, logic=logic, method="consistency-check", verified=True)

        with self.kb.transaction():
            sid = self.kb.add_statement(world, a.text, "rule" if a.rules else "fact")
            self.kb.add_facts(world, sid, a.facts)
            self.kb.add_rules(world, sid, new_rules)
            self.kb.add_lexicon(world, [(e.symbol, e.kind, e.display) for e in a.lexicon])
            for term, gloss in a.definitions:
                self.kb.add_definition(world, sid, term, gloss)
        if a.focus:
            disp = next((e.display for e in a.lexicon if e.symbol == a.focus and e.kind == "entity"), a.focus)
            self._discourse[world] = (a.focus, disp)

        parts = ["Understood."]
        for f in a.facts:
            prior = st.closure.get(f.negate())
            if prior is not None and prior.rule is not None and prior.rule.origin == "default":
                parts.append(f"Noted as an exception to {v.rule(prior.rule)}: I no longer conclude that {v.atom(f.negate())}.")
        # Skip the bookkeeping negatives that order axioms generate ("Bob is not older than Alice").
        conclusions = [x for x, d in closure.derivations.items()
                       if d.rule is not None and x not in st.closure and not _typical(x.args[0])
                       and not (x.neg and d.rule.origin == "grammar")]
        if conclusions:
            shown = [v.atom(c) for c in conclusions[:5]]
            more = f" (+{len(conclusions) - 5} more)" if len(conclusions) > 5 else ""
            parts.append(f"I can now also conclude: {join_list(shown)}{more}.")
        notes = self._learn(world, closure, v)
        parts += notes
        return Item(a.text, "statement", "learned", " ".join(parts), logic=logic, statement_id=sid,
                    method="assert", verified=True, notes=[f"{len(conclusions)} new conclusion(s)"])

    def _learn(self, world: str, closure: Closure, v: Verbalizer) -> List[str]:
        """Refute hypotheses with counterexamples; induce new ones. Returns user-facing notes."""
        if world == COMMON:
            return []
        notes = []
        rows = self.kb.rule_rows(world, ("hypothesis",))
        hyps = [(r["id"], Rule.from_json(json.loads(r["rule"]))) for r in rows]
        for ref in learning.refute(closure, hyps):
            self.kb.set_rule_status(ref.rule_id, "refuted", {"counterexample": ref.counterexample})
            notes.append(f"This refutes my earlier hypothesis that {v.rule(ref.rule)}.")
        st = self._state(world)
        keys = {_key(r) for r in st.rules} | {r["rule"] for r in self.kb.rule_rows(world, ("hypothesis", "refuted"))}
        for h in learning.induce(closure, st.rules, keys):
            h.description = _describe_hypothesis(h.rule, v) or h.description
            rule = Rule(h.rule.body, h.rule.head, origin="induced", confidence=h.confidence,
                        source_text=f"hypothesis: {h.description}")
            if self.kb.add_rules(world, None, [rule], status="hypothesis",
                                 evidence={"support": h.support, "description": h.description}):
                notes.append(f"I noticed a pattern: {h.description} (confidence {h.confidence:.2f}, unproven).")
        return notes

    def _hypothesis_rows(self, world: str, v: Verbalizer) -> List[dict]:
        out = []
        for r in self.kb.rule_rows(world, ("hypothesis", "refuted")):
            ev = json.loads(r["evidence"] or "{}")
            out.append({"id": r["id"], "status": r["status"], "confidence": r["confidence"],
                        "description": ev.get("description") or r["source_text"],
                        "support": ev.get("support", []), "counterexample": ev.get("counterexample")})
        return out

    # ------------------------------------------------------------ answering
    def _answer(self, q: Question, world: str) -> Item:
        st = self._state(world)
        scratch = self._scratch(st, q)
        if isinstance(scratch, Item):
            return scratch
        closure, rules, quantities, formulas, lexicon = scratch
        v = Verbalizer(lexicon)
        # Ground against what the world knows -- not the question's own (possibly misspelled) words.
        notes = self._ground(q, closure, rules, st.lexicon)
        if q.hypothetical:
            v = Verbalizer({**lexicon, q.target: {"entity": f"every {q.generic}"}})
            given = [d for d in closure.derivations.values() if d.rule is None]
            closure = _extend(closure, rules, given, [Derivation(h, None, (), f"assumption: consider an arbitrary {q.generic}", 0)
                                                      for h in q.hypothetical], False)

        if q.kind == "math":
            return self._math(q)
        if q.kind == "learned":
            return self._learned(q, world, v)
        if q.kind == "similar":
            return self._similar(q, closure, rules, v)
        if q.kind == "superlative":
            return self._superlative(q, closure, rules, v, notes)
        if q.kind == "describe":
            return self._describe(q, closure, rules, quantities, formulas, v, world, notes)
        if q.kind == "count":
            return self._wh(q, closure, rules, st, v, notes, count=True)
        if q.kind == "wh":
            return self._wh(q, closure, rules, st, v, notes)
        return self._yesno(q, closure, rules, st, v, notes)

    def _scratch(self, st: _State, q: Question):
        """Applies a question's "if ..." assumptions to a private copy of the world."""
        closure, rules = st.closure, list(st.rules)
        quantities, formulas = dict(st.quantities), list(st.formulas)
        lexicon = dict(st.lexicon)
        facts: List[Derivation] = []
        for g in q.givens:
            if isinstance(g, QuantityStatement):
                quantities[g.quantity.name] = g.quantity
            elif isinstance(g, FormulaStatement):
                formulas.append(g.formula)
            elif isinstance(g, Assertion):
                facts += [Derivation(f, None, (), f"assumption: {g.text}", 0) for f in g.facts]
                rules += g.rules
                lexicon.update({e.symbol: {**lexicon.get(e.symbol, {}), e.kind: e.display} for e in g.lexicon})
        lexicon.update({e.symbol: {**lexicon.get(e.symbol, {}), e.kind: e.display} for e in q.lexicon if e.symbol not in lexicon})
        if facts or len(rules) != len(st.rules):
            closure = _extend(closure, rules, st.given, facts, len(rules) != len(st.rules))
            if closure.contradictions():
                p, n = closure.contradictions()[0]
                return Item(q.text, "question", "error",
                            f"Those assumptions contradict what I know ({Verbalizer(lexicon).atom(p)} vs {Verbalizer(lexicon).atom(n)}).")
        return closure, rules, quantities, formulas, lexicon

    def _ground(self, q: Question, closure: Closure, rules: Sequence[Rule], lexicon: Dict) -> List[str]:
        """Maps unknown words in the question onto known symbols (typo tolerance)."""
        vocab = set(lexicon) | constants(closure.atoms()) | {a.args[1] for r in rules for a in (*r.body, r.head)
                                                              if a.pred == IS and len(a.args) == 2}
        preds = {a.pred for a in closure.atoms()} | {a.pred for r in rules for a in (*r.body, r.head)}
        notes: List[str] = []
        subst: Dict[str, str] = {}
        terms = [t for a in q.goals + q.hypothetical for t in a.args if not t.startswith("?") and not _typical(t)]
        if q.target and q.kind in ("describe", "similar") and q.target not in vocab:
            terms.append(q.target)
        for t in set(terms):
            if t in vocab:
                continue
            m = fuzzy_match(t, vocab)
            if m:
                subst[t] = m[0]
                notes.append(f"I took '{t}' to mean '{m[0]}'.")
        for a in q.goals:
            if a.pred not in preds and a.pred != IS:
                m = fuzzy_match(a.pred, preds)
                if m:
                    subst[a.pred] = m[0]
                    notes.append(f"I took '{a.pred}' to mean '{m[0]}'.")
        if subst:
            fix = lambda a: Atom(subst.get(a.pred, a.pred), tuple(subst.get(x, x) for x in a.args), a.neg)
            q.goals = [fix(a) for a in q.goals]
            q.hypothetical = [fix(a) for a in q.hypothetical]
            if q.target in subst:
                q.target = subst[q.target]
        return notes

    def _unknown_terms(self, atoms: Sequence[Atom], closure: Closure, rules: Sequence[Rule]) -> List[str]:
        vocab = constants(closure.atoms()) | {a.args[1] for r in rules for a in (*r.body, r.head) if a.pred == IS and len(a.args) == 2}
        preds = {a.pred for a in closure.atoms()} | {a.pred for r in rules for a in (*r.body, r.head)}
        out = [t for a in atoms for t in a.args[1:] + (a.args[:1] if not _typical(a.args[0]) else ())
               if not t.startswith("?") and t not in vocab]
        out += [a.pred for a in atoms if a.pred != IS and a.pred not in preds]
        return sorted(set(out))

    def _with_hypotheses(self, closure: Closure, rules: Sequence[Rule], world_hyps: Sequence[Rule]) -> Optional[Closure]:
        if not world_hyps:
            return None
        given = [d for d in closure.derivations.values() if d.rule is None]
        return saturate_all(list(rules) + list(world_hyps), given)

    def _yesno(self, q: Question, closure: Closure, rules, st: _State, v: Verbalizer, notes: List[str]) -> Item:
        logic = [str(g) for g in q.goals]
        if q.hypothetical:
            logic = [f"assume {h}" for h in q.hypothetical] + logic
        proved, refuted = [], []
        for g in q.goals:
            if g in closure:
                proved.append(proof_tree(closure, g))
            elif g.negate() in closure:
                refuted.append(proof_tree(closure, g.negate()))
        for verdict_word, trees in (("No", refuted), ("Yes", proved if len(proved) == len(q.goals) else [])):
            if not trees:
                continue
            verdict = verify_all(trees)
            dflt = any(uses_default(t) for t in trees)
            claim = _sentence(join_list([v.atom(t["atom"]) for t in trees]))
            reason = v.because(trees[-1])
            if q.explain:
                ans = f"{claim}" + (f" because {reason}" if reason else "") + "."
            else:
                ans = f"{verdict_word}{' (by default)' if dflt else ''}. {claim}" + (f", because {reason}." if reason else ".")
            if dflt:
                notes = notes + ["This relies on a general rule that holds unless an exception is known; "
                                 "learning an exception would change the answer."]
            return Item(q.text, "question", "answered", ans, verdict.verified,
                        "deduction(default)+z3" if dflt else "deduction+z3", 1.0, v.proof_lines_many(trees), logic, notes)

        hc = self._with_hypotheses(closure, rules, st.hypotheses)
        if hc is not None:
            if all(g in hc for g in q.goals):
                trees = [proof_tree(hc, g) for g in q.goals]
                conf = min((r.confidence for r in st.hypotheses), default=0.5)
                return Item(q.text, "question", "probable",
                            f"Probably yes, but I can't prove it: it follows only from a pattern I've noticed, not from anything you told me.",
                            False, "induction", conf, v.proof_lines_many(trees), logic, notes)
            if any(g.negate() in hc for g in q.goals):
                g = next(g for g in q.goals if g.negate() in hc)
                return Item(q.text, "question", "probable", "Probably not, but I can't prove it (based on a pattern I've noticed).",
                            False, "induction", 0.5, v.proof_lines(proof_tree(hc, g.negate())), logic, notes)

        unknown = self._unknown_terms(q.goals + q.hypothetical, closure, rules)
        if not unknown and not q.hypothetical and len(q.goals) == 1 and not q.givens:
            item = self._intuit(q, st, v, logic, notes)
            if item:
                return item
        if unknown:
            msg = f"I don't know. I have never been told anything about {join_list([repr(u) for u in unknown])}."
        else:
            missing = [v.atom(g) for g in q.goals if g not in closure]
            msg = f"I don't know. Nothing I know implies that {join_list(missing)}, or that it's false."
        return Item(q.text, "question", "unknown", msg, False, "deduction", None, [], logic, notes)

    def _wh(self, q: Question, closure: Closure, rules, st: _State, v: Verbalizer, notes: List[str], count: bool = False) -> Item:
        logic = [str(g) for g in q.goals]
        answers: Dict[str, List[dict]] = {}
        for theta in _join(closure, list(q.goals), {}):
            x = theta.get("?q")
            if x is None or _typical(x) or x in answers:
                continue
            answers[x] = [proof_tree(closure, g.substitute(theta)) for g in q.goals]
        if answers:
            trees = [t for ts in answers.values() for t in ts]
            verdict = verify_all(trees)
            names = [v.term(x) for x in answers]
            if count:
                ans = f"{len(names)}: {join_list(names)}."
            else:
                ans = f"{join_list(names)}."
            expl = v.proof_lines_many([t for ts in list(answers.values())[:6] for t in ts])
            note = notes + (["Counting only the individuals I know about."] if count else [])
            dflt = any(uses_default(t) for t in trees)
            if dflt:
                note.append("Some of these rely on general rules that hold unless an exception is known.")
            return Item(q.text, "question", "answered", _sentence(ans), verdict.verified,
                        "deduction(default)+z3" if dflt else "deduction+z3", 1.0, expl, logic, note)
        hc = self._with_hypotheses(closure, rules, st.hypotheses)
        if hc is not None:
            guesses = {t.get("?q") for t in _join(hc, list(q.goals), {}) if t.get("?q") and not _typical(t["?q"])}
            if guesses:
                return Item(q.text, "question", "probable",
                            f"Possibly {join_list([v.term(g) for g in guesses])}, but only by a pattern I've noticed, not by proof.",
                            False, "induction", 0.5, [], logic, notes)
        if count:
            return Item(q.text, "question", "answered", "0 — I don't know of any.", True, "deduction", 1.0, [], logic, notes)
        unknown = self._unknown_terms(q.goals, closure, rules)
        msg = (f"I don't know. I have never been told anything about {join_list([repr(u) for u in unknown])}."
               if unknown else "I don't know of anyone or anything that fits.")
        return Item(q.text, "question", "unknown", msg, False, "deduction", None, [], logic, notes)

    def _superlative(self, q: Question, closure: Closure, rules, v: Verbalizer, notes: List[str]) -> Item:
        pred = q.target
        pairs = [a.args for a in closure.atoms() if a.pred == pred and not a.neg and len(a.args) == 2]
        if not pairs:
            comps = sorted({a.pred for a in closure.atoms() if a.pred.endswith(" than")})
            hint = f" I know about {join_list([repr(c) for c in comps])}." if comps else ""
            return Item(q.text, "question", "unknown",
                        f"I don't know how to compare things by '{pred}'.{hint} You could teach me, e.g. "
                        f"“{pred.replace(' than', '').capitalize()} is the opposite of ...”.", logic=[f"argmax {pred}"], notes=notes)
        domain = sorted({x for p in pairs for x in p if not _typical(x)})
        cands = domain
        if q.goals:
            cands = [x for x in domain if all(g.substitute({"?q": x}) in closure for g in q.goals)]
        rel = {p for p in pairs}
        winners = [e for e in cands if all((e, y) in rel for y in domain if y != e)]
        logic = [f"find x: for all y != x, {pred}(x, y)"]
        if winners:
            e = winners[0]
            trees = [proof_tree(closure, Atom(pred, (e, y))) for y in domain if y != e]
            verdict = verify_all(trees)
            others = [v.term(y) for y in domain if y != e]
            ans = f"{v.term(e)} is the {q.superlative_word} ({pred} {join_list(others)})."
            return Item(q.text, "question", "answered", _sentence(ans), verdict.verified, "deduction+z3", 1.0,
                        v.proof_lines_many(trees), logic,
                        notes + [f"Compared among the {len(domain)} individuals I know are ordered by '{pred}'."])
        maximal = [e for e in cands if not any((y, e) in rel for y in domain if y != e)]
        return Item(q.text, "question", "unknown",
                    f"I can't tell for sure. Nobody is known to be {pred} {join_list([v.term(e) for e in maximal])}, "
                    "but I don't know how they compare with each other." if len(maximal) > 1 else
                    "I can't tell from what I know.", logic=logic, notes=notes)

    def _describe(self, q: Question, closure: Closure, rules, quantities, formulas, v: Verbalizer, world: str,
                  notes: List[str]) -> Item:
        t = q.target or ""
        disp = q.target_display or t

        # 1. quantities and formulas
        if t in quantities or any(t in f.variables for f in formulas):
            return self._quantity(q, t, quantities, formulas)

        # 2. "who is kind?" / "what is mortal?" -> list members
        entity_facts = [a for a in closure.atoms() if a.args and a.args[0] == t]
        lex = v.lex.get(t, {})
        is_category = any(a.pred == IS and a.args[1] == t for a in closure.atoms()) or \
            any(a.pred == IS and a.args[1] == t for r in rules for a in r.body) or bool(lex.keys() & {"noun", "adj", "modal"})
        if q.goals and (q.wh_word == "who" or ("adj" in lex and "noun" not in lex)) and not entity_facts:
            return self._wh(Question(q.text, "wh", goals=q.goals), closure, rules, self._state(world), v, notes)

        definitions = self.kb.definitions(world, t)
        lines: List[str] = []
        if entity_facts:
            told = [a for a in entity_facts if closure.get(a).rule is None]
            derived = [a for a in entity_facts if closure.get(a).rule is not None]
            lines = [_sentence(v.atom(a)) + "." for a in _dedupe_categories(told + derived)][:14]
        elif is_category:
            c = f"a typical {t}"
            given = [d for d in closure.derivations.values() if d.rule is None]
            hc = _extend(closure, rules, given, [Derivation(Atom(IS, (c, t)), None, (), f"assumption: consider any {t}", 0)], False)
            vt = Verbalizer({**v.lex, c: {"entity": f"every {t}"}})
            general = [a for a, d in hc.derivations.items() if a.args and a.args[0] == c and d.rule is not None]
            lines = [_sentence(vt.atom(a)) + "." for a in _dedupe_categories(general)][:10]
            members = sorted({a.args[0] for a in closure.atoms() if a.pred == IS and not a.neg and a.args[1] == t and not _typical(a.args[0])})
            if members:
                lines.append(f"Examples I know: {join_list([v.term(m) for m in members[:10]])}.")
        if definitions or lines:
            body = " ".join(definitions[:2] + lines)
            return Item(q.text, "question", "answered", body, True, "retrieval+deduction", 1.0,
                        [], [f"describe({t})"], notes)

        unknown_hint = ""
        near = fuzzy_match(t, set(v.lex) | set(self.kb.defined_terms(world)))
        if near:
            unknown_hint = f" Did you mean '{near[0]}'?"
        return Item(q.text, "question", "unknown",
                    f"I don't know anything about {disp} yet.{unknown_hint} You can teach me, "
                    f"e.g. “{disp[:1].upper() + disp[1:]} is a ...”.", logic=[f"describe({t})"], notes=notes)

    def _quantity(self, q: Question, t: str, quantities: Dict[str, Quantity], formulas: List[Formula]) -> Item:
        ans = solve_for(t, formulas, quantities)
        logic = [f"solve for {t}"] + [_pretty_formula(f) for f in formulas if t in f.variables][:3]
        if ans is None:
            needs = []
            for f in formulas:
                if t in f.variables:
                    missing = [x for x in f.variables if x != t and x not in quantities]
                    needs.append(f"{_pretty_formula(f)} — missing {join_list(missing)}")
            return Item(q.text, "question", "unknown",
                        f"I know how to compute {t}, but I'm missing values: " + "; ".join(needs[:3]) + ".",
                        logic=logic, method="quantity-chaining")
        unit = f" {ans.unit}" if ans.unit else ""
        if ans.given:
            return Item(q.text, "question", "answered", f"{t} = {_num(ans.value)}{unit} (you told me).", True, "retrieval", 1.0,
                        logic=logic)
        expl = []
        for s in ans.steps:
            expr = s.formula.expr
            subst = expr
            for name, val in s.inputs.items():
                expr = expr.replace("{" + name + "}", name)
                subst = subst.replace("{" + name + "}", _num(val))
            expl.append(f"{s.quantity} = {expr} = {subst} = {_num(s.value)}{' ' + s.unit if s.unit else ''}  "
                        f"(from “{s.formula.text}”)")
        expl.append(f"Check: substituting every value back into each formula leaves a residual of {ans.residual:.1e}.")
        return Item(q.text, "question", "answered", f"{t[:1].upper() + t[1:]} = {_num(ans.value)}{unit}.", ans.verified,
                    "quantity-chaining+sympy", 1.0, expl, logic)

    def _math(self, q: Question) -> Item:
        try:
            r = solve_math(q.expr or "")
        except Exception as exc:
            return Item(q.text, "question", "error", f"I couldn't evaluate that expression ({exc}).", method="sympy")
        return Item(q.text, "question", "answered", f"{r.answer}", r.verified, f"sympy-{r.kind}", 1.0,
                    [r.detail] if r.detail else [], [r.expression])

    def _intuition(self, st: _State) -> Intuition:
        key = id(st)
        cached = self._intuitions.get(key)
        if cached is None:
            self._intuitions = {key: Intuition(list(st.closure.atoms()), st.rules)}   # keep only the current one
            cached = self._intuitions[key]
        return cached

    def _intuit(self, q: Question, st: _State, v: Verbalizer, logic: List[str], notes: List[str]) -> Optional[Item]:
        """System 1: a learned 'probably' when proof is silent. Never verified."""
        j = self._intuition(st).judge(q.goals[0])
        if j is None or NO_AT < j.probability < YES_AT:
            return None
        word = "Probably yes" if j.probability >= YES_AT else "Probably not"
        return Item(q.text, "question", "probable",
                    f"{word} ({j.probability:.2f}), but I can't prove it: {j.reason}.", False,
                    f"intuition:{j.source}", round(j.probability, 2), [], logic,
                    notes + ["This is learned intuition, not a proof. Tell me the fact to make it certain."])

    def _similar(self, q: Question, closure: Closure, rules, v: Verbalizer) -> Item:
        space = ConceptSpace(closure.atoms(), rules)
        sims = space.similar(q.target or "")
        if not sims:
            return Item(q.text, "question", "unknown", f"I don't know enough about {q.target_display} to compare it with anything.",
                        method="concept-embedding")
        listing = join_list([f"{v.term(s)} ({score:.2f})" for s, score in sims])
        return Item(q.text, "question", "answered", f"Most similar to {q.target_display}: {listing}.", False,
                    "concept-embedding", None, [],
                    notes=["Similarity is learned from how concepts are used in my knowledge; it is a suggestion, not a proof."])

    def _learned(self, q: Question, world: str, v: Verbalizer) -> Item:
        rows = self._hypothesis_rows(world, v)
        if not rows:
            return Item(q.text, "question", "answered", "I haven't noticed any patterns yet beyond what you told me.",
                        True, "introspection")
        lines = []
        for r in rows:
            if r["status"] == "hypothesis":
                lines.append(f"Hypothesis: {r['description']} (confidence {r['confidence']:.2f}; examples: {', '.join(r['support'][:5])}).")
            else:
                lines.append(f"Refuted: {r['description']} (counterexample: {r['counterexample']}).")
        return Item(q.text, "question", "answered", " ".join(lines), True, "introspection", None, lines)


# ----------------------------------------------------------------- helpers

def _extend(base: Closure, rules: Sequence[Rule], given: Sequence[Derivation], new: Sequence[Derivation],
            rules_changed: bool) -> Closure:
    """Adds facts to a closure: incrementally when possible, from scratch when defaults or new rules require it."""
    if rules_changed or any(r.origin == "default" for r in rules):
        return saturate_all(rules, list(given) + list(new))
    return saturate(base.copy(), rules, new)


def _describe_hypothesis(rule: Rule, v: Verbalizer) -> Optional[str]:
    """'every dog I know of is loyal' / 'everything I know of that is loyal is a dog'."""
    if len(rule.body) != 1 or rule.body[0].pred != IS or rule.head.pred != IS:
        return None
    a, b = rule.body[0].args[1], rule.head.args[1]
    is_b = v.category(b, False, "").strip()
    if "noun" in v.lex.get(a, {}) and "adj" not in v.lex.get(a, {}):
        return f"every {a} I know of {is_b}"
    return f"everything I know of that {v.category(a, False, '').strip()} {is_b.replace('is ', 'is also ', 1)}"


def _pretty_formula(f: Formula) -> str:
    expr = f.expr
    for n in f.names:
        expr = expr.replace("{" + n + "}", n)
    return f"{f.target} = {expr}"


def _sentence(s: str) -> str:
    s = s.strip()
    return s[:1].upper() + s[1:] if s else s


def _dedupe_categories(atoms: List[Atom]) -> List[Atom]:
    """Drops 'is dog' when 'is brown dog' is also present, and duplicates."""
    cats = {a.args[1] for a in atoms if a.pred == IS and not a.neg}
    out, seen = [], set()
    for a in atoms:
        if a in seen:
            continue
        seen.add(a)
        if a.pred == IS and not a.neg and any(c != a.args[1] and a.args[1] in c.split() for c in cats):
            continue
        out.append(a)
    return out
