# HSCI V4 — Architectural Decisions Log (DECISIONS.md)

This log records structural engineering decisions made during the V4 planning and design phases.

---

## DEC-0001: Unified Relational Data Store (UKM)
*   **Decision**: Replaced all six fragmented JSON/JSONL memory files (`episodes.jsonl`, `concept_graph.json`, `cognitive_weights.json`, etc.) with a single SQLite database file (`hsci_v4.db`) managed by the `UniversalKnowledgeModel` (UKM).
*   **Rationale**: Solves data corruption, lack of atomic transactions, and performance degradation during O(N) linear text scans.
*   **Consequence**: Write transactions are serialised using readers-writer locks. Read speed is optimized using indexes and SQLite FTS5 matching.

---

## DEC-0002: Stateless Services & Context-Passed WorkingMemory
*   **Decision**: Removed all transient class-level and instance-level state variables (e.g., `self.last_embedding` inside `NeuralPerceiver`) from pipeline services.
*   **Rationale**: Resolves intent classification race conditions occurring when concurrent request threads overwrite class variables before they are processed by the learning engine.
*   **Consequence**: All pipeline layers are completely stateless, accepting a request-scoped `CognitiveContext` holding a fresh `WorkingMemory` object.

---

## DEC-0003: 10-Stage Pipeline Orchestration (BrainKernel)
*   **Decision**: Expanded the V3 7-layer RIR loop to a **10-stage sequential execution pipeline** owned by the `BrainKernel`.
*   **Rationale**: Integrates V4 cognitive specifications—specifically the `UnderstandingEngine` (Stage 0.5), the `MentalModelEngine` (Stage 1.5), and `SkillMemory` retrieval (Stage 2.5)—without violating interface boundaries.
*   **Consequence**: Outlines a clear, step-by-step state machine with execution tracing for observability.

---

## DEC-0004: Dynamic Solver Plugins
*   **Decision**: Wrapped the five legacy HNSDS verifiers in `hnsds/verifier/` as `DeterministicSolverPlugin` adapters, registering them dynamically with the `SolverRegistry`.
*   **Rationale**: Decouples the orchestrator pipeline from specific mathematical or logical solvers, resolving the open/closed architectural violation in `cognitive_core.py`.
*   **Consequence**: Adding a new solver requires zero modifications to the `BrainKernel` execution loop.
