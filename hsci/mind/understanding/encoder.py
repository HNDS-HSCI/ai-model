"""Perception encoders: sentence -> meaning vector.

The neural encoder is a small pretrained sentence-embedding network
(all-MiniLM-L6-v2, ~90 MB, CPU). It is used for one thing only: *recalling past
experiences that are similar in meaning* to a new sentence. It never generates
text and never decides what is true.

A dependency-free hashing encoder is the fallback (and is what tests use): it only
captures surface overlap, but keeps the system fully functional when the model is
unavailable or still loading.

Environment:
    HSCI_MIND_ENCODER = auto (default) | neural | hash
    HSCI_MIND_ENCODER_PATH = models/all-MiniLM-L6-v2
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from typing import List, Optional

import numpy as np

logger = logging.getLogger("HSCI.Mind.Encoder")

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "all-MiniLM-L6-v2")


class HashEncoder:
    name = "hash-512"
    dim = 512

    def encode(self, texts: List[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            words = re.findall(r"[a-z0-9']+|\?", t.lower())
            feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
            for w in words:
                g = f"#{w}#"
                feats += [g[k:k + 3] for k in range(len(g) - 2)]
            for f in feats:
                h = int(hashlib.blake2b(f.encode(), digest_size=4).hexdigest(), 16)
                out[i, h % self.dim] += 1.0 if "_" not in f else 0.5
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class NeuralEncoder:
    name = "minilm-l6-v2"

    def __init__(self, path: str) -> None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer  # heavy import, done lazily

        self.model = SentenceTransformer(path, device="cpu")
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True, batch_size=64,
                                            show_progress_bar=False), dtype=np.float32)


class EncoderProvider:
    """Serves the hashing encoder immediately and swaps in the neural one once loaded."""

    def __init__(self, mode: Optional[str] = None, path: Optional[str] = None, background: bool = True) -> None:
        self.mode = (mode or os.getenv("HSCI_MIND_ENCODER", "auto")).lower()
        self.path = os.path.abspath(path or os.getenv("HSCI_MIND_ENCODER_PATH", _DEFAULT_PATH))
        self._fallback = HashEncoder()
        self._neural: Optional[NeuralEncoder] = None
        self.error: Optional[str] = None
        self._ready = threading.Event()
        if self.mode == "hash" or not os.path.isdir(self.path):
            if self.mode == "neural":
                self.error = f"encoder model not found at {self.path}"
            self._ready.set()
        elif background and self.mode == "auto":
            threading.Thread(target=self._load, daemon=False, name="encoder-loader").start()  # see engine.py: no daemon torch threads
        else:
            self._load()

    def _load(self) -> None:
        try:
            self._neural = NeuralEncoder(self.path)
            logger.info("neural encoder loaded from %s", self.path)
        except Exception as exc:  # keep running on the fallback
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("neural encoder unavailable, using hashing encoder: %s", self.error)
        finally:
            self._ready.set()

    @property
    def current(self):
        return self._neural or self._fallback

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._ready.wait(timeout)

    def status(self) -> dict:
        return {"active": self.current.name, "mode": self.mode, "loaded": self._ready.is_set(), "error": self.error}
