# HSCI V4 — Benchmark Standard (BENCHMARK_STANDARD.md)

This document establishes the execution policies, accuracy success criteria, latency performance thresholds, and regression guidelines for evaluating cognitive and solver architectures in the HSCI repository.

---

## 1. Benchmark Execution Rules

*   **Standardized Context**: All benchmark tests must execute in an isolated environment. Prior to execution, terminate all background user threads to prevent cpu scheduling noise.
*   **Database Seeding**: The `UniversalKnowledgeModel` (UKM) must be seeded with standard validation concepts from `metaphysical_blueprint.json` before benchmarks start, ensuring consistent baseline parameters.
*   **Isolated Solvers**: The benchmark runner must execute each solver task in an isolated transaction scope.

---

## 2. Accuracy Success Criteria

The repository measures correctness across five active HNSDS solver domains. To pass a benchmark run, the system must satisfy the following accuracy ratios:

| Domain | Legacy Solver | Success Threshold (Accuracy) |
|---|---|---|
| Constraint Verification | `ConstraintMatrixSolver` | $100\%$ |
| Requirements Analysis | `RequirementsSolver` | $100\%$ |
| Architecture Planning | `GraphSolver` | $100\%$ |
| State Machine Verification | `StateMachineSolver` | $100\%$ |
| Dependency Resolution | `DependencySolver` | $100\%$ |

---

## 3. Performance & Latency Thresholds

Any implementation of the 10-stage `BrainKernel` or UKM sqlite stores must comply with these target execution time limits (measured under normal API load):

*   **Language Bridge & NLP Parser**: $\le 10\text{ms}$
*   **Concept Spreading Activation (CAE)**: $\le 15\text{ms}$
*   **HTN Planning & Solver Dispatch**: $\le 15\text{ms}$
*   **Z3 Verification & CEGIS Loop**: $\le 50\text{ms}$ (per linear constraint)
*   **Learning & Weight Persist Transactions**: $\le 10\text{ms}$
*   **Total End-to-End Cycle Latency**: $\le 100\text{ms}$

---

## 4. Regression Policy

*   **Zero Tolerance**: Latency regressions are not permitted.
*   **Regression Bound**: If a code change increases the average task execution duration of any domain by $>5\%$, the change is blocked.
*   **Mitigation Procedure**:
    1.  Profile execution traces using `cProfile` to locate latency bottlenecks.
    2.  Check for SQLite write lock contention, slow disk writes, or nested graph traversal loops.
    3.  Implement performance optimizations (such as indexing, LRU caching, or database transaction batching) to restore baseline execution speeds.
*   **Baseline Preservation**: Do not alter accuracy constraints or timeout caps (15 seconds per task) to pass failing benchmarks.
