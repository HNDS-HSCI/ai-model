# HSCI V4 — Project Roadmap (ROADMAP.md)

This roadmap outlines long-term milestones and capability releases for the HSCI V4 system.

---

## Current Progress Status
*   **Sprint 1 (Repository Planning & EOS)**: **Completed** (2026-07-11)
*   **Sprint 2 (BrainKernel Engineering Design)**: **Completed** (2026-07-11)
*   **Sprint 2.5 (BrainKernel Architecture Review)**: **Completed** (2026-07-11)
*   **Sprint 3 (BrainKernel Core Implementation)**: **Completed** (2026-07-11)
*   **Sprint 4 (WorkingMemory Engineering Design)**: **Completed** (2026-07-11)
*   **Sprint 4.5 (WorkingMemory Architecture Review)**: **Completed** (2026-07-11)
*   **Sprint 5 (WorkingMemory Implementation)**: **Completed** (2026-07-11)
*   **Sprint 6A (UKM Knowledge Representation Design)**: **Completed** (2026-07-11)
*   **Sprint 6A.5 (UKM Cognitive Access Model Design)**: **Completed** (2026-07-11)
*   **Sprint 6B (UKM Storage Architecture Design)**: **Completed** (2026-07-11)
*   **Sprint 6.5 (UKM Architecture Review)**: **Completed** (2026-07-11)
*   **Sprint 7A (UKM Core Storage Implementation)**: **Completed** (2026-07-13)
*   **Sprint 7B.1 (ConceptStore Architecture Refinement)**: **Completed** (2026-07-14)
*   **Sprint 7B (ConceptStore Implementation)**: **Completed** (2026-07-14)
*   **Sprint 8 (KnowledgeManager Implementation)**: **Completed** (2026-07-14)
*   **Sprint 9 (Concept Activation Engine Implementation)**: **Completed** (2026-07-14)
*   **Sprint 10 (Understanding Engine MVP Implementation)**: **Completed** (2026-07-14)
*   **Sprint 11 (Cognitive Reasoning Engine Implementation)**: **Completed** (2026-07-16)

---

## Milestone 1: Repository Stabilization & Data Layer Unification (Q3 2026)
*   **Goal**: Establish clean thread safety, remove dead code, and implement the transactional SQLite database (UKM).
*   **Impact**: Eliminates file-corruption concurrency risks, reduces startup write latencies, and prepares the repository for request-scoped processing.
*   **Target Phases**: Phase 1 to Phase 3.

## Milestone 2: Pipeline Orchestration & Solver Plugins (Q4 2026)
*   **Goal**: Replace the V3 loop and legacy verifier routing with the 10-stage `BrainKernel` and dynamic `SolverRegistry` plugins.
*   **Impact**: Restores $100\%$ HNSDS benchmark compliance under a unified runtime, separating solvers from cognitive flow logic.
*   **Target Phases**: Phase 4 and Phase 5.

## Milestone 3: Advanced Cognitive Subsystems (Q1 2027)
*   **Goal**: Implement the `ConceptActivationEngine` (CAE), `UnderstandingEngine`, `MentalModelEngine` (MME), and the HTN Planner.
*   **Impact**: Enables co-reference resolution, fact confidence decay tracking, and hierarchical planning.
*   **Target Phases**: Phase 6 to Phase 9.

## Milestone 4: Evolution & Self-Improvement (Q2 2027)
*   **Goal**: Deploy the `ReflectionEngine`, CEE evolution proposal logging, asynchronous learning updates, and sandboxed code synthesis.
*   **Impact**: Provides secure, audited self-improvement capabilities without manual code updates.
*   **Target Phases**: Phase 10 to Phase 13.
