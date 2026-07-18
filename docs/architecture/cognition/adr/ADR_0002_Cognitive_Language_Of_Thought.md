# Architecture Decision Record — ADR-0002: Cognitive Language of Thought

*   **Status**: Approved
*   **Decided By**: AGI Research Team
*   **Date**: 2026-07-18

---

## 1. Context

HSCI requires an internal representation language to store, retrieve, and verify logical deductions across multiple ingestion formats (PDFs, Source Code, User conversations) without semantic drift.

---

## 2. Alternatives Evaluated

### Option A: Natural Language (English strings)
*   **Pros**: Human-readable, simple tokenization.
*   **Cons**: Subject to semantic ambiguity, homonym collisions, and inability to run formal SMT validation tests directly.

### Option B: Predicate Logic Graph (Language of Thought - LoT)
*   **Pros**: Explicit namespace separation, clear relation types, SMT-compatible (Z3).
*   **Cons**: Requires extraction parsing compile phases.

---

## 3. Decision

We choose **Option B (Language of Thought - LoT predicate graphs)** as the internal language of HSCI.

---

## 4. Consequences

1.  **Compiler Required**: The compiler must normalize raw text into LoT before database injection.
2.  **SMT Alignment**: Inferences can be translated directly into SMT axioms for deterministic proofs.
