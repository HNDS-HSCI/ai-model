"""Neural semantic parser: understanding learned from experience, not written by hand.

Every remembered experience (sentence -> meaning) is abstracted into a
*construction*: a frame of grammar words with slots ("every _ is a _"), and a meaning
template with the same slots. A small neural network learns, from those
experiences, to read a new sentence and predict

  1. which construction it is (sentence classification), and
  2. which words fill which slot (token tagging).

The meaning is the construction's template with the new words in its slots.

Words are represented so that the network generalises to words it has never seen:
grammar and frame words get their own embedding, every other word a shared "open
word" embedding plus character features and shape (capitalised, number, -s ...).
Training examples are augmented with random invented words and filler words, so the
network learns *structure*, not vocabulary.

Nothing here is specific to any phrasing: new constructions appear the moment a
person teaches a new kind of sentence, and the network retrains on them.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from hsci.mind import lexicon as lx
from hsci.mind.parser import Tok
from hsci.mind.understanding import meaning as mn
from hsci.mind.understanding.analogy import Slot, apply_transform, find_slots

MAX_SLOTS = 8
_CHAR_BUCKETS = 1024
_SYLL = ["ba", "do", "ki", "mu", "ze", "lo", "pi", "ra", "su", "te", "vo", "gu", "ne", "fi", "ko", "da"]


@dataclass
class Construction:
    cid: int
    key: str
    tokens: List[Tok]                  # representative sentence
    slots: List[Slot]                  # in sentence order
    meaning: List[dict]                # representative meaning
    count: int = 1
    sources: Set[str] = field(default_factory=set)


@dataclass
class NeuralReading:
    construction: Construction
    probability: float
    slot_confidence: float
    meaning: List[dict]
    fillers: Dict[int, List[int]]


@lru_cache(maxsize=200_000)
def _char_ids(word: str) -> List[int]:
    g = f"#{word}#"
    return [int(hashlib.blake2b(g[k:k + 3].encode(), digest_size=4).hexdigest(), 16) % _CHAR_BUCKETS
            for k in range(max(1, len(g) - 2))]


def _closed(fillers: Set[str]) -> Set[str]:
    return lx.FUNCTION_WORDS | lx.PREPOSITIONS | fillers | lx.VARIABLE_WORDS | {"?", ",", "'s", "be", "people", "things"}


def construction_key(tokens: List[Tok], slots: List[Slot], meaning: List[dict]) -> str:
    slot_at = {s.index: k for k, s in enumerate(slots)}
    frame = " ".join(f"<{slot_at[i]}>" if i in slot_at else t.low for i, t in enumerate(tokens))
    placeholders = {s.meaning_word: f"slot{k}" for k, s in enumerate(slots)}
    return frame + " || " + mn.key(mn.substitute(meaning, placeholders, {}, ""))


class _Net(nn.Module):
    def __init__(self, vocab: int, n_cons: int, dim: int = 64, hidden: int = 64) -> None:
        super().__init__()
        self.word = nn.Embedding(vocab, dim, padding_idx=0)
        self.chars = nn.EmbeddingBag(_CHAR_BUCKETS, 32, mode="mean")
        self.proj = nn.Linear(dim + 32 + 6, dim)
        self.rnn = nn.GRU(dim, hidden, batch_first=True, bidirectional=True)
        self.cons = nn.Linear(2 * hidden, n_cons)
        self.slot = nn.Linear(2 * hidden + n_cons, MAX_SLOTS + 1)   # slot index, or "not a slot"

    def forward(self, words, chars, offsets, feats, mask, cons_hint=None):
        b, n = words.shape
        c = self.chars(chars, offsets).view(b, n, -1)
        x = torch.tanh(self.proj(torch.cat([self.word(words), c, feats], -1)))
        h, _ = self.rnn(x)
        pooled = h.masked_fill(~mask.unsqueeze(-1), -1e4).max(1).values
        cons_logits = self.cons(pooled)
        cons_p = F.softmax(cons_logits, -1) if cons_hint is None else cons_hint
        slot_logits = self.slot(torch.cat([h, cons_p.unsqueeze(1).expand(-1, n, -1)], -1))
        return cons_logits, slot_logits


class NeuralSemanticParser:
    def __init__(self, fillers: Set[str], seed: int = 0) -> None:
        self.fillers = set(fillers)
        self.seed = seed
        self.constructions: List[Construction] = []
        self.vocab: Dict[str, int] = {}
        self.net: Optional[_Net] = None
        self.trained_on = 0
        self.train_seconds = 0.0

    # ------------------------------------------------------------ constructions
    def build_constructions(self, experiences: Sequence[Tuple[str, List[dict], str, float]]) -> None:
        from hsci.mind.understanding.engine import utterance_tokens
        by_key: Dict[str, Construction] = {}
        for text, meaning, source, reliability in experiences:
            if reliability < 0.5 or any(m["type"] == "question" and m["kind"] == "math" for m in meaning):
                continue
            toks = utterance_tokens(text)
            slots = find_slots(toks, mn.symbol_words(meaning))
            if not slots or len(slots) > MAX_SLOTS:
                continue
            k = construction_key(toks, slots, meaning)
            if k in by_key:
                by_key[k].count += 1
                by_key[k].sources.add(source)
            else:
                by_key[k] = Construction(len(by_key), k, toks, slots, meaning, 1, {source})
        self.constructions = list(by_key.values())

    # ------------------------------------------------------------ features
    def _encode(self, batch: List[List[Tok]]):
        n = max(len(t) for t in batch)
        words, feats, mask, chars, offsets = [], [], [], [], []
        pad_feat = [0.0] * 6
        for toks in batch:
            for j in range(n):
                offsets.append(len(chars))
                if j >= len(toks):
                    chars.append(0)
                    words.append(0)
                    feats.append(pad_feat)
                    mask.append(False)
                    continue
                t = toks[j]
                low = t.low
                words.append(self.vocab.get(low, 1))
                chars += _char_ids(low)
                feats.append([float(t.cap), float(j == 0), float(low.replace(".", "").isdigit()),
                              float(low.endswith("s")), float(len(low) > 6), float(low.endswith("er"))])
                mask.append(True)
        b = len(batch)
        return (torch.tensor(words).view(b, n), torch.tensor(chars), torch.tensor(offsets),
                torch.tensor(feats).view(b, n, 6), torch.tensor(mask).view(b, n))

    # ------------------------------------------------------------ augmentation
    def _nonce(self, rng: random.Random, cap: bool) -> str:
        w = "".join(rng.choice(_SYLL) for _ in range(rng.randint(1, 3))) + rng.choice(["", "n", "k", "t", "p", "m"])
        return w.capitalize() if cap else w

    def _samples(self, rng: random.Random, per_example: int):
        out = []
        for c in self.constructions:
            slot_at = {s.index: k for k, s in enumerate(c.slots)}
            for r in range(per_example):
                toks: List[Tok] = []
                labels: List[int] = []
                for i, t in enumerate(c.tokens):
                    if i in slot_at and r > 0:
                        s = c.slots[slot_at[i]]
                        if s.transform == "num":
                            w = [str(rng.randint(1, 999))]
                        else:
                            w = [self._nonce(rng, t.cap)]
                            if s.transform in ("noun", "verb") and t.low != s.meaning_word and t.low.endswith("s"):
                                w[-1] += "s"
                            if not t.cap and s.transform != "verb" and rng.random() < 0.15:
                                w = [self._nonce(rng, False)] + w           # a modifier: "big dog"
                            elif t.cap and rng.random() < 0.15:
                                w = w + [self._nonce(rng, True)]            # a two-word name
                        for x in w:
                            toks.append(Tok(x, x.lower()))
                            labels.append(slot_at[i])
                    else:
                        if r > 0 and t.low in ("a", "an") and rng.random() < 0.5:
                            t = Tok("an" if t.low == "a" else "a", "an" if t.low == "a" else "a")  # one word, two spellings
                        toks.append(t)
                        labels.append(slot_at.get(i, MAX_SLOTS))
                    if r > 0 and rng.random() < 0.06:
                        f = rng.choice(sorted(self.fillers))
                        toks.append(Tok(f, f))
                        labels.append(MAX_SLOTS)
                out.append((toks, c.cid, labels))
        return out

    # ------------------------------------------------------------ training
    def fit(self, experiences: Sequence[Tuple[str, List[dict], str, float]], epochs: int = 12, per_example: int = 20) -> None:
        start = time.perf_counter()
        torch.manual_seed(self.seed)
        rng = random.Random(self.seed)
        self.build_constructions(experiences)
        if len(self.constructions) < 2:
            self.net = None
            return
        closed = _closed(self.fillers)
        frame_words = {t.low for c in self.constructions for i, t in enumerate(c.tokens)
                       if i not in {s.index for s in c.slots}}
        self.vocab = {"<pad>": 0, "<open>": 1}
        for w in sorted(closed | frame_words):
            self.vocab.setdefault(w, len(self.vocab))
        self.net = _Net(len(self.vocab), len(self.constructions))
        opt = torch.optim.Adam(self.net.parameters(), lr=3e-3)
        data = self._samples(rng, per_example)
        for _ in range(epochs):
            rng.shuffle(data)
            for b in range(0, len(data), 32):
                chunk = data[b:b + 32]
                words, chars, offsets, feats, mask = self._encode([x[0] for x in chunk])
                y_c = torch.tensor([x[1] for x in chunk])
                n = words.shape[1]
                y_s = torch.full((len(chunk), n), -100, dtype=torch.long)
                for i, x in enumerate(chunk):
                    y_s[i, :len(x[2])] = torch.tensor(x[2])
                hint = F.one_hot(y_c, len(self.constructions)).float()       # teacher forcing for the tagger
                cl, sl = self.net(words, chars, offsets, feats, mask, cons_hint=hint)
                loss = F.cross_entropy(cl, y_c) + F.cross_entropy(sl.reshape(-1, MAX_SLOTS + 1), y_s.reshape(-1), ignore_index=-100)
                opt.zero_grad()
                loss.backward()
                opt.step()
        self.net.eval()
        self.trained_on = len(experiences)
        self.train_seconds = time.perf_counter() - start

    # ------------------------------------------------------------ reading
    def read(self, tokens: List[Tok], sentence: str, top: int = 6) -> List[NeuralReading]:
        if self.net is None or not tokens:
            return []
        with torch.no_grad():
            words, chars, offsets, feats, mask = self._encode([tokens])
            cl, _ = self.net(words, chars, offsets, feats, mask)
            probs = F.softmax(cl, -1)[0]
            out = []
            for cid in torch.argsort(probs, descending=True)[:top].tolist():
                c = self.constructions[cid]
                hint = F.one_hot(torch.tensor([cid]), len(self.constructions)).float()
                _, sl = self.net(words, chars, offsets, feats, mask, cons_hint=hint)
                sp = F.softmax(sl[0, :, list(range(len(c.slots))) + [MAX_SLOTS]], -1)   # only this construction's slots
                labels = sp.argmax(-1).tolist()
                fillers: Dict[int, List[int]] = {}
                confs = []
                for j, lab in enumerate(labels):
                    if lab < len(c.slots):
                        fillers.setdefault(lab, []).append(j)
                        confs.append(float(sp[j, lab]))
                if len(fillers) != len(c.slots) or any(v != list(range(v[0], v[-1] + 1)) for v in fillers.values()):
                    continue
                adapted = self._adapt(c, tokens, fillers, sentence)
                if adapted is None:
                    continue
                out.append(NeuralReading(c, float(probs[cid]), min(confs) if confs else 0.0, adapted, fillers))
        # Constructions that lead to the same meaning agree: pool their probability.
        pooled: Dict[str, NeuralReading] = {}
        for r in out:
            k = mn.key(r.meaning)
            if k in pooled:
                best = pooled[k]
                best.probability = min(1.0, best.probability + r.probability)
                best.slot_confidence = max(best.slot_confidence, r.slot_confidence)
            else:
                pooled[k] = r
        return sorted(pooled.values(), key=lambda r: -r.probability)

    @staticmethod
    def _role_transform(c: Construction, s: Slot) -> str:
        """Normalise word form by its role in the meaning (category -> singular, relation -> base verb),
        rather than copying whatever form the single remembered example happened to use."""
        if s.transform not in ("id", "noun"):
            return s.transform
        roles = set()
        for d in c.meaning:
            rule_atoms = [x for r in d.get("rules", []) for x in r["rule"]["body"] + [r["rule"]["head"]]]
            for a in d.get("facts", []) + d.get("goals", []) + d.get("hypothetical", []) + rule_atoms:
                if s.meaning_word in a["pred"].split() and a["pred"] != "is":
                    roles.add("verb")
                if a["pred"] == "is" and len(a["args"]) > 1 and s.meaning_word in a["args"][1].split():
                    roles.add("noun")
        if roles == {"verb"}:
            return "verb"
        if roles == {"noun"}:
            return "noun"
        return s.transform

    def _adapt(self, c: Construction, tokens: List[Tok], fillers: Dict[int, List[int]], sentence: str):
        word_map: Dict[str, str] = {}
        display_map: Dict[str, str] = {}
        for k, s in enumerate(c.slots):
            toks = [tokens[j] for j in fillers[k]]
            if any(t.low in _closed(self.fillers) for t in toks):
                return None
            new = toks[-1].low if s.transform == "num" else apply_transform(self._role_transform(c, s), [t.text for t in toks])
            if word_map.get(s.meaning_word, new) != new:
                return None
            word_map[s.meaning_word] = new
            display_map[c.tokens[s.index].text] = " ".join(t.text for t in toks)
        try:
            meaning = mn.substitute(c.meaning, word_map, display_map, sentence)
            [mn.from_dict(d) for d in meaning]
        except Exception:
            return None
        return meaning
