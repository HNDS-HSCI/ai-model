"""Persistent knowledge base (SQLite) with full provenance.

Every fact, rule, formula, quantity and definition points back to the *statement*
(sentence) it was compiled from, so any belief can be explained ("you told me ...")
or retracted ("forget statement 12") with everything that depended on it.

Knowledge is partitioned into *worlds* (independent belief contexts, e.g. one per
user or per problem). Reasoning in a world also sees the shared ``__common__``
world, which holds seed knowledge loaded from English text files.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from hsci.mind.logic import Atom, Rule
from hsci.mind.quantities import Formula, Quantity

COMMON = "__common__"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, text TEXT NOT NULL,
    kind TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, statement_id INTEGER,
    atom TEXT NOT NULL, origin TEXT NOT NULL, UNIQUE(world, atom));
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, statement_id INTEGER,
    rule TEXT NOT NULL, origin TEXT NOT NULL, status TEXT NOT NULL, confidence REAL NOT NULL,
    evidence TEXT, source_text TEXT, created REAL NOT NULL, UNIQUE(world, rule));
CREATE TABLE IF NOT EXISTS lexicon (
    world TEXT NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL, display TEXT NOT NULL,
    PRIMARY KEY(world, symbol, kind));
CREATE TABLE IF NOT EXISTS definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, statement_id INTEGER,
    term TEXT NOT NULL, gloss TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS formulas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, statement_id INTEGER,
    target TEXT NOT NULL, expr TEXT NOT NULL, names TEXT NOT NULL, text TEXT NOT NULL,
    UNIQUE(world, target, expr));
CREATE TABLE IF NOT EXISTS quantities (
    world TEXT NOT NULL, name TEXT NOT NULL, value REAL NOT NULL, unit TEXT,
    statement_id INTEGER, text TEXT, PRIMARY KEY(world, name));
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world TEXT NOT NULL, input TEXT NOT NULL,
    kind TEXT NOT NULL, outcome TEXT NOT NULL, verified INTEGER NOT NULL, method TEXT,
    latency_ms REAL NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_facts_world ON facts(world);
CREATE INDEX IF NOT EXISTS idx_rules_world ON rules(world, status);
CREATE INDEX IF NOT EXISTS idx_defs_term ON definitions(world, term);
"""


class KnowledgeBase:
    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(_SCHEMA)
        self._lock = threading.RLock()
        self._versions: Dict[str, int] = {}

    # ---------------------------------------------------------------- versions
    def version(self, world: str) -> Tuple[int, int]:
        return self._versions.get(COMMON, 0), self._versions.get(world, 0)

    def _bump(self, world: str) -> None:
        self._versions[world] = self._versions.get(world, 0) + 1

    def transaction(self):
        return _Tx(self)

    # ---------------------------------------------------------------- writes
    def add_statement(self, world: str, text: str, kind: str) -> int:
        cur = self._conn.execute("INSERT INTO statements(world, text, kind, created) VALUES (?,?,?,?)",
                                 (world, text, kind, time.time()))
        self._bump(world)
        return int(cur.lastrowid)

    def add_facts(self, world: str, sid: Optional[int], atoms: Iterable[Atom], origin: str = "told") -> int:
        n = 0
        for a in atoms:
            cur = self._conn.execute("INSERT OR IGNORE INTO facts(world, statement_id, atom, origin) VALUES (?,?,?,?)",
                                     (world, sid, json.dumps(a.to_json(), sort_keys=True), origin))
            n += cur.rowcount
        self._bump(world)
        return n

    def add_rules(self, world: str, sid: Optional[int], rules: Iterable[Rule], status: str = "active",
                  evidence: Optional[dict] = None) -> int:
        n = 0
        for r in rules:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO rules(world, statement_id, rule, origin, status, confidence, evidence, source_text, created)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (world, sid, json.dumps(r.to_json(), sort_keys=True), r.origin, status, r.confidence,
                 json.dumps(evidence or {}), r.source_text, time.time()))
            n += cur.rowcount
        self._bump(world)
        return n

    def set_rule_status(self, rule_id: int, status: str, evidence: Optional[dict] = None, confidence: Optional[float] = None) -> None:
        row = self._conn.execute("SELECT world FROM rules WHERE id=?", (rule_id,)).fetchone()
        sets, args = ["status=?"], [status]
        if evidence is not None:
            sets.append("evidence=?")
            args.append(json.dumps(evidence))
        if confidence is not None:
            sets.append("confidence=?")
            args.append(confidence)
        self._conn.execute(f"UPDATE rules SET {', '.join(sets)} WHERE id=?", (*args, rule_id))
        if row:
            self._bump(row["world"])

    def add_lexicon(self, world: str, entries: Iterable[Tuple[str, str, str]]) -> None:
        for symbol, kind, display in entries:
            self._conn.execute("INSERT OR IGNORE INTO lexicon(world, symbol, kind, display) VALUES (?,?,?,?)",
                               (world, symbol, kind, display))

    def add_definition(self, world: str, sid: Optional[int], term: str, gloss: str) -> None:
        self._conn.execute("INSERT INTO definitions(world, statement_id, term, gloss) VALUES (?,?,?,?)",
                           (world, sid, term, gloss))
        self._bump(world)

    def add_formula(self, world: str, sid: Optional[int], f: Formula) -> None:
        self._conn.execute("INSERT OR IGNORE INTO formulas(world, statement_id, target, expr, names, text) VALUES (?,?,?,?,?,?)",
                           (world, sid, f.target, f.expr, json.dumps(f.names), f.text))
        self._bump(world)

    def set_quantity(self, world: str, sid: Optional[int], q: Quantity) -> None:
        self._conn.execute("INSERT OR REPLACE INTO quantities(world, name, value, unit, statement_id, text) VALUES (?,?,?,?,?,?)",
                           (world, q.name, q.value, q.unit, sid, q.source))
        self._bump(world)

    def log_episode(self, world: str, text: str, kind: str, outcome: str, verified: bool, method: str, latency_ms: float) -> None:
        self._conn.execute("INSERT INTO episodes(world, input, kind, outcome, verified, method, latency_ms, created) VALUES (?,?,?,?,?,?,?,?)",
                           (world, text, kind, outcome, int(verified), method, latency_ms, time.time()))

    # ---------------------------------------------------------------- reads
    def _worlds(self, world: str) -> Sequence[str]:
        return (COMMON,) if world == COMMON else (COMMON, world)

    def facts(self, world: str) -> List[Tuple[Atom, str, int]]:
        q = ("SELECT f.id, f.atom, s.text FROM facts f LEFT JOIN statements s ON s.id = f.statement_id "
             f"WHERE f.world IN ({','.join('?' * len(self._worlds(world)))}) ORDER BY f.id")
        return [(Atom.from_json(json.loads(r["atom"])), r["text"] or "", r["id"])
                for r in self._conn.execute(q, self._worlds(world))]

    def rules(self, world: str, statuses: Sequence[str] = ("active",)) -> List[Rule]:
        ws = self._worlds(world)
        q = (f"SELECT id, rule, origin, source_text, confidence FROM rules WHERE world IN ({','.join('?' * len(ws))}) "
             f"AND status IN ({','.join('?' * len(statuses))}) ORDER BY id")
        return [Rule.from_json(json.loads(r["rule"]), rule_id=str(r["id"]), origin=r["origin"],
                               source_text=r["source_text"] or "", confidence=r["confidence"])
                for r in self._conn.execute(q, (*ws, *statuses))]

    def rule_rows(self, world: str, statuses: Sequence[str]) -> List[sqlite3.Row]:
        return list(self._conn.execute(
            f"SELECT * FROM rules WHERE world=? AND status IN ({','.join('?' * len(statuses))}) ORDER BY id",
            (world, *statuses)))

    def lexicon(self, world: str) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        ws = self._worlds(world)
        for r in self._conn.execute(f"SELECT symbol, kind, display FROM lexicon WHERE world IN ({','.join('?' * len(ws))})", ws):
            out.setdefault(r["symbol"], {})[r["kind"]] = r["display"]
        return out

    def definitions(self, world: str, term: str) -> List[str]:
        ws = self._worlds(world)
        return [r["gloss"] for r in self._conn.execute(
            f"SELECT gloss FROM definitions WHERE term=? AND world IN ({','.join('?' * len(ws))}) ORDER BY id", (term, *ws))]

    def defined_terms(self, world: str) -> List[str]:
        ws = self._worlds(world)
        return [r["term"] for r in self._conn.execute(
            f"SELECT DISTINCT term FROM definitions WHERE world IN ({','.join('?' * len(ws))})", ws)]

    def formulas(self, world: str) -> List[Formula]:
        ws = self._worlds(world)
        return [Formula(r["target"], r["expr"], json.loads(r["names"]), r["text"], r["id"]) for r in self._conn.execute(
            f"SELECT * FROM formulas WHERE world IN ({','.join('?' * len(ws))}) ORDER BY world = ? DESC, id", (*ws, world))]

    def quantities(self, world: str) -> Dict[str, Quantity]:
        return {r["name"]: Quantity(r["name"], r["value"], r["unit"], r["text"] or "") for r in
                self._conn.execute("SELECT * FROM quantities WHERE world=?", (world,))}

    def statements(self, world: str, limit: int = 500) -> List[dict]:
        return [dict(r) for r in self._conn.execute(
            "SELECT id, text, kind, created FROM statements WHERE world=? ORDER BY id DESC LIMIT ?", (world, limit))]

    def worlds(self) -> List[str]:
        return [r["world"] for r in self._conn.execute("SELECT DISTINCT world FROM statements ORDER BY world")]

    def stats(self, world: str) -> dict:
        one = lambda sql, *a: self._conn.execute(sql, a).fetchone()[0]
        return {
            "statements": one("SELECT count(*) FROM statements WHERE world=?", world),
            "facts": one("SELECT count(*) FROM facts WHERE world=?", world),
            "rules": one("SELECT count(*) FROM rules WHERE world=? AND status='active'", world),
            "hypotheses": one("SELECT count(*) FROM rules WHERE world=? AND status='hypothesis'", world),
            "refuted": one("SELECT count(*) FROM rules WHERE world=? AND status='refuted'", world),
            "formulas": one("SELECT count(*) FROM formulas WHERE world=?", world),
            "quantities": one("SELECT count(*) FROM quantities WHERE world=?", world),
            "definitions": one("SELECT count(*) FROM definitions WHERE world=?", world),
            "episodes": one("SELECT count(*) FROM episodes WHERE world=?", world),
            "verified_answers": one("SELECT count(*) FROM episodes WHERE world=? AND verified=1", world),
            "common_facts": one("SELECT count(*) FROM facts WHERE world=?", COMMON),
            "common_rules": one("SELECT count(*) FROM rules WHERE world=? AND status='active'", COMMON),
            "common_formulas": one("SELECT count(*) FROM formulas WHERE world=?", COMMON),
        }

    # ---------------------------------------------------------------- deletes
    def forget_statement(self, world: str, sid: int) -> bool:
        row = self._conn.execute("SELECT id FROM statements WHERE id=? AND world=?", (sid, world)).fetchone()
        if not row:
            return False
        for table in ("facts", "rules", "definitions", "formulas", "quantities"):
            self._conn.execute(f"DELETE FROM {table} WHERE world=? AND statement_id=?", (world, sid))
        self._conn.execute("DELETE FROM statements WHERE id=?", (sid,))
        self._bump(world)
        return True

    def reset_world(self, world: str) -> None:
        for table in ("statements", "facts", "rules", "lexicon", "definitions", "formulas", "quantities", "episodes"):
            self._conn.execute(f"DELETE FROM {table} WHERE world=?", (world,))
        self._bump(world)

    def close(self) -> None:
        self._conn.close()


class _Tx:
    """Atomic multi-row write: everything a sentence compiles to lands, or nothing does."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def __enter__(self):
        self.kb._lock.acquire()
        self.kb._conn.execute("BEGIN")
        return self.kb

    def __exit__(self, exc_type, exc, tb):
        try:
            self.kb._conn.execute("ROLLBACK" if exc_type else "COMMIT")
        finally:
            self.kb._lock.release()
        return False
