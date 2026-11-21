"""Experience memory: every utterance the Mind has understood, with its meaning.

This is the store that language understanding grows from. Experiences come from
the grammar ("teacher"), from seed teaching pairs, and -- most valuably -- from the
user confirming or correcting what the Mind understood. Each experience tracks how
often analogies drawn from it were confirmed or rejected, so unreliable experiences
lose influence over time.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, norm TEXT NOT NULL UNIQUE,
    meaning TEXT NOT NULL, source TEXT NOT NULL, world TEXT, uses INTEGER NOT NULL DEFAULT 0,
    confirmed INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
"""

# How much an experience is trusted before any feedback, by where it came from.
SOURCE_PRIOR = {"user": 0.95, "confirmed": 0.95, "seed": 0.9, "grammar": 0.8}


@dataclass
class Experience:
    id: int
    text: str
    meaning: List[dict]
    source: str
    confirmed: int
    rejected: int

    @property
    def reliability(self) -> float:
        prior = SOURCE_PRIOR.get(self.source, 0.8)
        return (prior * 4 + self.confirmed) / (4 + self.confirmed + self.rejected)


def normalise(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(" .!")


class ExperienceMemory:
    def __init__(self, conn, encoders) -> None:
        self.conn = conn
        self.encoders = encoders
        self.conn.executescript(_SCHEMA)
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[int, np.ndarray, List[int]]] = {}

    def add(self, text: str, meaning: List[dict], source: str, world: Optional[str] = None) -> int:
        with self._lock:
            norm = normalise(text)
            row = self.conn.execute("SELECT id, source FROM experiences WHERE norm=?", (norm,)).fetchone()
            if row:
                # a user's teaching overrides what the grammar guessed for the same sentence
                if SOURCE_PRIOR.get(source, 0) >= SOURCE_PRIOR.get(row["source"], 0):
                    self.conn.execute("UPDATE experiences SET meaning=?, source=? WHERE id=?",
                                      (json.dumps(meaning), source, row["id"]))
                return int(row["id"])
            cur = self.conn.execute(
                "INSERT INTO experiences(text, norm, meaning, source, world, created) VALUES (?,?,?,?,?,?)",
                (text.strip(), norm, json.dumps(meaning), source, world, time.time()))
            return int(cur.lastrowid)

    def feedback(self, exp_id: int, confirmed: bool) -> None:
        col = "confirmed" if confirmed else "rejected"
        self.conn.execute(f"UPDATE experiences SET {col} = {col} + 1, uses = uses + 1 WHERE id=?", (exp_id,))

    def get(self, exp_id: int) -> Optional[Experience]:
        r = self.conn.execute("SELECT * FROM experiences WHERE id=?", (exp_id,)).fetchone()
        return self._row(r) if r else None

    def count(self) -> int:
        return self.conn.execute("SELECT count(*) FROM experiences").fetchone()[0]

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT source, count(*) n, sum(confirmed) c, sum(rejected) r FROM experiences GROUP BY source")
        return {r["source"]: {"experiences": r["n"], "confirmed": r["c"] or 0, "rejected": r["r"] or 0} for r in rows}

    def recall(self, text: str, k: int = 8) -> List[Tuple[Experience, float]]:
        """Remembered experiences similar to ``text``, through two channels.

        *Semantic* recall (the neural encoder) finds paraphrases in familiar words;
        *structural* recall (surface/frame overlap) finds the same construction with
        entirely new words, which the neural encoder cannot see past.
        """
        best: Dict[int, float] = {}
        encoders = [self.encoders.current]
        if not self.encoders.current.name.startswith("hash"):
            encoders.append(self.encoders._fallback)
        for enc in encoders:
            ids, matrix = self._index(enc)
            if not ids:
                return []
            sims = matrix @ enc.encode([text])[0]
            for i in np.argsort(-sims)[:k]:
                best[ids[i]] = max(best.get(ids[i], -1.0), float(sims[i]))
        rows = {r["id"]: r for r in self.conn.execute(
            f"SELECT * FROM experiences WHERE id IN ({','.join(map(str, best))})")}
        return sorted(((self._row(rows[i]), s) for i, s in best.items() if i in rows), key=lambda x: -x[1])

    def _index(self, enc) -> Tuple[List[int], np.ndarray]:
        with self._lock:
            n = self.count()
            cached = self._cache.get(enc.name)
            if cached and cached[0] == n:
                return cached[2], cached[1]
            rows = list(self.conn.execute("SELECT id, text FROM experiences ORDER BY id"))
            if cached and set(cached[2]) <= {r["id"] for r in rows}:
                # incremental: encode only experiences added since the last index build
                known = set(cached[2])
                new_rows = [r for r in rows if r["id"] not in known]
                ids = cached[2] + [r["id"] for r in new_rows]
                matrix = np.vstack([cached[1], enc.encode([r["text"] for r in new_rows])]) if new_rows else cached[1]
            else:
                ids = [r["id"] for r in rows]
                matrix = enc.encode([r["text"] for r in rows]) if rows else np.zeros((0, 1), dtype=np.float32)
            self._cache[enc.name] = (n, matrix, ids)
            return ids, matrix

    @staticmethod
    def _row(r) -> Experience:
        return Experience(r["id"], r["text"], json.loads(r["meaning"]), r["source"], r["confirmed"], r["rejected"])
