# HSCI V4 — Release Plan (RELEASE_PLAN.md)

This release plan schedules release versions and criteria for the HSCI V4 transition.

---

## 1. Release Schedule

### v4.0.0-alpha.1 (Stabilization & Data Layer)
*   **Target Date**: Q3 2026
*   **Features**:
    *   Phase 1: Stabilization (Dead code removal and `EpisodeLogger` locking).
    *   Phase 2: Universal Knowledge Model (SQLite database setup, JSON migrations).
    *   Phase 3: Working Memory (Stateless perceiver, `CognitiveContext` passing).
*   **Release Gate**: Unit test suites pass with $100\%$ success. SQLite WAL concurrency stresses pass.

### v4.0.0-alpha.2 (Orchestration & Solver Plugins)
*   **Target Date**: Q4 2026
*   **Features**:
    *   Phase 4: BrainKernel 10-stage execution pipeline.
    *   Phase 5: SolverRegistry & HNSDS verifier plugins.
*   **Release Gate**: HSCI HNSDS benchmark task suite (`tasks.json`) runs via the new kernel dispatch and registers $100\%$ accuracy.

### v4.0.0-beta.1 (Cognitive Subsystems)
*   **Target Date**: Q1 2027
*   **Features**:
    *   Phase 6: CAE Concept Activation Engine.
    *   Phase 7: Understanding Engine.
    *   Phase 8: Mental Model Engine.
    *   Phase 9: Goal Manager & Planner.
*   **Release Gate**: Cognitive benchmark tests written and passing. Average end-to-end latency $\le 100\text{ms}$.

### v4.0.0 (General Availability)
*   **Target Date**: Q2 2027
*   **Features**:
    *   Phase 10: Reflection Engine & CEE Evolution Proposal Logging.
    *   Phase 11: Asynchronous Learning Engine updates.
    *   Phase 12: Interactive Teaching API (`/v1/teach`).
    *   Phase 13: Sandboxed enumerative synthesizer.
*   **Release Gate**: Continuous self-play loops run for 48 hours without exceptions. All test coverage $\ge 90\%$.
