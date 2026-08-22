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
*   **Sprint 12 (Answer Generation Engine Implementation)**: **Completed** (2026-07-16)
*   **Sprint VS-1 (Vertical Cognitive Slice Assembly)**: **Completed** (2026-08-09) — assembled the existing V4 engines into `CognitivePipeline`; first real end-to-end conceptual slice ("Explain what a Java interface is.") running over a real UKM. No engine rewrite, no SCG-L5 change.
*   **VS-2 Pre-Flight (Runtime Inspection)**: **Completed** (2026-08-09) — read-only runtime audit of VS-1 (`docs/design/VS2_PREFLIGHT_REPORT.md`). Confirmed real integration; identified that the pipeline serializes graph edges instead of explaining concepts (stored `abstract_rule` never surfaced). Bottleneck = Answer Generation; recommended VS-2 = Explanatory Answer Synthesis. No production code modified.
*   **Sprint VS-2 (Explanatory Answer Synthesis)**: **Completed** (2026-08-09) — added `ExplanatoryAnswerSynthesizer`; concept-explanation questions now return a definition-first, traceable answer (stored `abstract_rule` + real reasoning relationships), confidence preserved. Read-only, deterministic, SCG-L5-neutral. No learning, reflection, or Z3 added. See `docs/design/VS2_IMPLEMENTATION_REPORT.md`.
*   **Sprint VS-3 (Reasoning Derivation & Cognitive MVP Gate)**: **Completed** (2026-08-22) — implemented genuine 2-premise transitive closure (`GeneralizationTransitivity`), derivation provenance, refusal on unknown concepts, and user-facing web dashboard integration (`brain_api.py`). Passed Cognitive MVP Acceptance Gate with full 18-test suite. Status: **COGNITIVE MVP — PASS**. See `docs/design/VS3/COGNITIVE_MVP_ACCEPTANCE_REPORT.md`.

---

## Milestone 1: Repository Unification & Advanced Pipelines (Q3 2026)
*   **Goal**: Establish clean thread safety, transactional SQLite UKM data stores, deterministic parsing pipelines, spreading activation engines, symbolic reasoning verifiers, and explainable answer format generators.
*   **Status**: **Milestone 1 Completed** (v0.1.0-alpha).

## Milestone 2: Evolution, Self-Improvement & Dialogues (Q4 2026)
*   **Goal**: Implement the Mental Model Engine (MME), the HTN Planner, the Reflection Engine failure classifications, CEE concept evolution proposals, and the Learning Engine update loops.
*   **Target Phases**: Phase 9 to Phase 13.
