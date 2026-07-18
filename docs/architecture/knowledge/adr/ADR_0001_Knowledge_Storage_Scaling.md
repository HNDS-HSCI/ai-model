# Architecture Decision Record — ADR-0001: Knowledge Storage Scaling

*   **Status**: Approved
*   **Decided By**: Chief AI Architect
*   **Date**: 2026-07-18

---

## 1. Context

The HSCI Knowledge Infrastructure must store millions of concepts and billions of relationships, supporting concurrent transactions, thread-safe logical evaluations, and future graph queries.

---

## 2. Alternatives Evaluated

### Option A: Relational Database (SQLite to PostgreSQL)
*   **Pros**: ACId compliance, simple migration, low resource footprint.
*   **Cons**: Graph traversals require recursive SQL CTE queries, reducing performance at scale.

### Option B: Native Graph Database (Neo4j)
*   **Pros**: Efficient multi-hop relationship traversals.
*   **Cons**: Higher resource requirements; complex installation steps limit local development.

---

## 3. Decision

We choose **Option A (SQLite today, PostgreSQL tomorrow)** wrapped behind repository abstractions, with a path to support Option B optionally.

---

## 4. Consequences

1.  **SQLite usage in MVP**: We will use SQLite with WAL mode enabled to support concurrent local reads and writes.
2.  **Generic Repository Interfaces**: The core engine depends on interfaces (`IConceptRepository`), ensuring switching to Neo4j or PostgreSQL later requires zero changes to the logical engine codebase.
