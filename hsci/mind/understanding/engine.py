"""Understanding engine: from what was said to what was meant, with a confidence.

For every utterance it gathers candidate readings from two sources:

* the **grammar** (the innate, hand-written construction grammar -- a teacher), and
* **analogy with experience**: the neural encoder recalls the most similar
  utterances the Mind has understood before; each is aligned with the new
  sentence and its meaning adapted (see ``analogy.py``).

Every reading is checked for *plausibility* (does it make sense as a meaning of
these words?), readings that agree reinforce each other, and close competitors
lower confidence. The Mind then acts, asks for confirmation, or asks for a
rephrasing -- and every confirmation or correction becomes a new experience. Over
time understanding is driven by experience, with the grammar as a bootstrap.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from hsci.mind.parser import ParseContext, Question, SemanticParser, Tok, Unparsed, tokenize
from hsci.mind.semantic_space import lexical_similarity
from hsci.mind.understanding import meaning as mn
from hsci.mind.understanding.analogy import adapt_maps, align, find_slots
from hsci.mind.understanding.encoder import EncoderProvider
from hsci.mind.understanding.memory import SOURCE_PRIOR, ExperienceMemory, normalise
from hsci.mind.understanding.neural_parser import NeuralSemanticParser
from hsci.mind.quantities import detect_math

logger = logging.getLogger("HSCI.Mind.Understanding")

_DATA = os.path.join(os.path.dirname(__file__), "..", "data")

ACT = 0.70        # confident enough to act
CONFIRM = 0.40    # plausible enough to ask "do you mean ...?"


@lru_cache(maxsize=1)
def dialogue_lexicon() -> dict:
    with open(os.path.join(_DATA, "dialogue.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    return {k: set(v) if isinstance(v, list) else v for k, v in d.items()}


@dataclass
class Reading:
    parsed: list
    meaning: List[dict]
    confidence: float
    source: str                       # grammar | analogy | grammar+analogy
    experience_id: Optional[int] = None
    experience_text: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    taught: bool = False              # this exact sentence was explained by a person


def utterance_tokens(text: str) -> List[Tok]:
    toks = tokenize(text.strip().rstrip(".!"))
    if text.strip().endswith("?"):
        toks.append(Tok("?", "?"))
    return toks


class UnderstandingEngine:
    def __init__(self, conn, parser: SemanticParser, encoders: Optional[EncoderProvider] = None,
                 grammar: Optional[str] = None, sync_training: Optional[bool] = None) -> None:
        self.parser = parser
        self.encoders = encoders or EncoderProvider()
        self.memory = ExperienceMemory(conn, self.encoders)
        self._word_vecs: Dict[Tuple[str, str], np.ndarray] = {}
        # "on": the hand-written grammar reads input alongside learned understanding.
        # "teacher": it only produced the first experiences; input is read by learned components alone.
        self.grammar = (grammar or os.getenv("HSCI_MIND_GRAMMAR", "on")).lower()
        self.sync_training = sync_training if sync_training is not None else os.getenv("HSCI_MIND_SYNC_TRAIN") == "1"
        self.neural = NeuralSemanticParser(dialogue_lexicon()["fillers"])
        self._neural_lock = threading.Lock()
        self._training = False
        self._trained_count = -1

    # ------------------------------------------------------------ main entry
    def understand(self, sentence: str, ctx: ParseContext) -> List[Reading]:
        tokens = utterance_tokens(sentence)
        fillers = dialogue_lexicon()["fillers"]
        readings: List[Reading] = []

        expr = detect_math(sentence)
        if expr is not None:   # arithmetic is read by the calculator, exactly; never by analogy
            taught = self.parser.parse(sentence, ctx)
            if taught and isinstance(taught[0], Question) and taught[0].kind == "math":
                return [Reading(taught, mn.meanings_to_dicts(taught), 0.98, "calculator")]

        if self.grammar != "teacher":
            taught = self.parser.parse(sentence, ctx)
            if taught and not any(isinstance(p, Unparsed) for p in taught):
                md = mn.meanings_to_dicts(taught)
                if md:
                    p, reasons = mn.plausibility(md, tokens, fillers)
                    readings.append(Reading(taught, md, 0.9 * p, "grammar", reasons=reasons))

        self._ensure_trained()
        with self._neural_lock:
            neural = self.neural.read(tokens, sentence)
        for nr in neural:
            p, reasons = mn.plausibility(nr.meaning, tokens, fillers, consumed=self._frame_positions(tokens, nr.fillers))
            conf = nr.probability * (0.5 + 0.5 * nr.slot_confidence) * p
            meaning = mn.renumber_skolems(nr.meaning, self.parser._skolem)
            try:
                parsed = [mn.from_dict(d) for d in meaning]
            except Exception:
                continue
            readings.append(Reading(parsed, meaning, conf, "neural", None, " ".join(t.text for t in nr.construction.tokens), reasons))

        norm = normalise(sentence)
        for exp, sim in self.memory.recall(sentence, k=32):
            r = self._by_analogy(sentence, tokens, exp, sim, fillers)
            if r:
                if normalise(exp.text) == norm and exp.source in ("user", "confirmed", "seed") and exp.reliability >= 0.6:
                    r.taught = True
                    r.confidence = max(r.confidence, 0.97 * exp.reliability)
                readings.append(r)
        if any(r.taught for r in readings):
            # Being told what a sentence means outweighs guessing at it.
            taught_keys = {mn.key(r.meaning) for r in readings if r.taught}
            for r in readings:
                if not r.taught and mn.key(r.meaning) not in taught_keys:
                    r.confidence *= 0.6
        return self._combine(readings)

    def _by_analogy(self, sentence: str, tokens: List[Tok], exp, sim: float, fillers) -> Optional[Reading]:
        ex_tokens = utterance_tokens(exp.text)
        slots = find_slots(ex_tokens, mn.symbol_words(exp.meaning))
        al = align(ex_tokens, slots, tokens, fillers, self._similar)
        if not al or al.score < 0.35:
            return None
        maps = adapt_maps(ex_tokens, slots, tokens, al)
        if maps is None:
            return None
        adapted = mn.substitute(exp.meaning, maps[0], maps[1], sentence)
        try:
            parsed = [mn.from_dict(d) for d in adapted]
        except Exception:
            return None
        used = {j for js in al.fillers.values() for j in js} | set(al.skipped)
        frame = set(range(len(tokens))) - used
        p, reasons = mn.plausibility(adapted, tokens, fillers, consumed=frame)
        # The alignment is the evidence; recall similarity only nudges.
        conf = (0.85 * al.score + 0.15 * max(sim, 0.0)) * (0.55 + 0.45 * exp.reliability) * p
        if exp.source == "grammar":
            conf *= 0.8   # an echo of the grammar's own past reading: second-hand evidence
        return Reading(parsed, adapted, conf, "analogy", exp.id, exp.text, reasons)

    def _combine(self, readings: List[Reading]) -> List[Reading]:
        groups: Dict[str, List[Reading]] = {}
        for r in readings:
            groups.setdefault(mn.key(r.meaning), []).append(r)
        merged: List[Reading] = []
        for rs in groups.values():
            rs.sort(key=lambda r: -r.confidence)
            best = rs[0]
            sources = sorted({r.source for r in rs})
            support = len(rs) - 1
            conf = min(0.99, best.confidence + 0.05 * min(support, 3))
            analog = next((r for r in rs if r.source == "analogy"), None)
            merged.append(Reading(best.parsed, best.meaning, conf, "+".join(sources),
                                  analog.experience_id if analog else None,
                                  analog.experience_text if analog else None, best.reasons,
                                  taught=any(r.taught for r in rs)))
        merged.sort(key=lambda r: -r.confidence)
        if len(merged) > 1 and not merged[0].taught and merged[0].confidence - merged[1].confidence < 0.08:
            merged[0].confidence *= 0.8   # two different readings are about equally likely: ask
            merged[0].reasons = merged[0].reasons + ["another reading is almost as likely"]
        return merged

    # ------------------------------------------------------------ learning
    def remember(self, sentence: str, meaning: List[dict], source: str, world: Optional[str] = None) -> int:
        return self.memory.add(sentence, meaning, source, world)

    # ------------------------------------------------------------ neural parser training
    @staticmethod
    def _frame_positions(tokens: List[Tok], fillers: Dict[int, List[int]]) -> set:
        used = {j for js in fillers.values() for j in js}
        return set(range(len(tokens))) - used

    def _ensure_trained(self) -> None:
        """(Re)train the neural parser when experience has grown -- in the background unless sync."""
        if os.getenv("HSCI_MIND_NEURAL", "on").lower() == "off":
            return
        n = self.memory.count()
        if n == self._trained_count or self._training:
            return
        rows = self.memory.conn.execute("SELECT text, meaning, source, confirmed, rejected FROM experiences").fetchall()
        exps = [(r["text"], json.loads(r["meaning"]), r["source"],
                 (SOURCE_PRIOR.get(r["source"], 0.8) * 4 + r["confirmed"]) / (4 + r["confirmed"] + r["rejected"]))
                for r in rows]
        self._training = True
        self._trained_count = n

        def train() -> None:
            fresh = NeuralSemanticParser(dialogue_lexicon()["fillers"])
            try:
                fresh.fit(exps)
                with self._neural_lock:
                    self.neural = fresh
            except Exception as exc:  # keep the previous model
                logger.warning("neural parser training failed: %s", exc)
            finally:
                self._training = False

        if self.sync_training:
            train()
        else:
            # Not a daemon: killing torch mid-training at interpreter exit aborts the process on Linux
            # ("terminate called without an active exception"); exit waits for training instead.
            threading.Thread(target=train, daemon=False, name="neural-parser-training").start()

    def wait_for_training(self, timeout: float = 300.0) -> None:
        import time as _t
        end = _t.time() + timeout
        while self._training and _t.time() < end:
            _t.sleep(0.05)

    def feedback(self, experience_id: Optional[int], confirmed: bool) -> None:
        if experience_id:
            self.memory.feedback(experience_id, confirmed)

    def dialogue_act(self, text: str) -> Optional[str]:
        d = dialogue_lexicon()
        norm = re.sub(r"[^a-z' ]", "", text.lower()).strip()
        if norm in d["affirm"]:
            return "affirm"
        if norm in d["deny"]:
            return "deny"
        return None

    def related(self, a: str, b: str) -> float:
        v = self.encoders.current.encode([a, b])
        return float(v[0] @ v[1])

    # ------------------------------------------------------------ seeding
    def bootstrap(self, path: str, ctx: ParseContext) -> List[str]:
        """Loads first experiences: plain sentences, and 'surface => canonical' teaching pairs."""
        if self.memory.count():
            return []
        problems = []
        fillers = dialogue_lexicon()["fillers"]
        with open(path, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
        for ln in lines:
            surface, _, canonical = ln.partition("=>")
            surface, canonical = surface.strip(), (canonical.strip() or surface.strip())
            parsed = self.parser.parse(canonical, ctx)
            md = mn.meanings_to_dicts(parsed) if parsed and not any(isinstance(p, Unparsed) for p in parsed) else None
            if not md:
                problems.append(f"{ln} (canonical not understood)")
                continue
            if mn.plausibility(md, utterance_tokens(canonical), fillers)[0] < 0.9:   # the teacher can misread too
                problems.append(f"{ln} (implausible parse)")
                continue
            # plain lines were understood by the grammar; '=>' lines were explained by a person
            self.memory.add(surface, mn.substitute(md, {}, {}, surface), "grammar" if canonical == surface else "seed")
        return problems

    # ------------------------------------------------------------ similarity
    def _similar(self, a: str, b: str) -> float:
        lex = lexical_similarity(a, b)
        enc = self.encoders.current
        if enc.name.startswith("hash"):
            return lex
        va, vb = self._vec(enc, a), self._vec(enc, b)
        return max(lex, float(va @ vb))

    def _vec(self, enc, word: str) -> np.ndarray:
        k = (enc.name, word)
        if k not in self._word_vecs:
            self._word_vecs[k] = enc.encode([word])[0]
        return self._word_vecs[k]

    def status(self) -> dict:
        return {"encoder": self.encoders.status(), "experiences": self.memory.count(), "by_source": self.memory.stats(),
                "grammar": self.grammar,
                "neural_parser": {"constructions": len(self.neural.constructions), "trained_on": self.neural.trained_on,
                                  "train_seconds": round(self.neural.train_seconds, 1), "training": self._training}}
