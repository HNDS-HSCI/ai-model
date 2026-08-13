# HSCI V5 — Simulation Engine v2 (SEA-2)

**Version**: 2.0  
**Status**: Constitutional Engineering Specification  
**Verdict**: Approved for Milestone 2 Development  

---

## 1. Purpose

The Simulation Engine v2 (SEA-2) is the high-performance execution runtime for counterfactual projections, trajectory evaluations, and state space explorations within HSCI V5. It optimizes the copy-on-write (CoW) branching models defined in SEA-1 for execution in highly parallel, sandboxed virtual environments.

### Core Objectives
*   **Low-Latency Branching**: Multi-path projections must fork in under 5ms using memory-mapped virtual environments.
*   **Safety-Constrained Execution**: Run speculative plans within isolated containers to prevent side effects in production domains.
*   **Parallel Trajectory Scoring**: Evaluate up to 50 paths concurrently to identify optimal utility-risk balances.

---

## 2. Terminology

*   **CoW Fork Session**: A virtual memory segment containing a copy-on-write copy of the active World Model state.
*   **Counterfactual Trajectory**: A sequence of simulated state transitions resulting from speculative actions.
*   **State Space Explorer**: A search engine executing Monte Carlo Tree Search (MCTS) or Heuristic Search over graph states.
*   **Utility-Risk Frontier**: The mathematical boundary balancing predicted goal utility against execution failure risk.

---

## 3. Position Inside HSCI

```
                   Executive Controller (ECA-1)
                                │
                                ▼
                   Simulation Engine (SEA-2)
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   Fork Manager        State Explorer       Sandbox Executor
        │                       │                       │
        ▼                       ▼                       ▼
 World Model (WMA-1)     Belief System (BSA-1)   Tool Registry (TCA-1)
```

---

## 4. Internal Architecture

*   **Simulation Coordinator**: Manages active simulations, arbitrating thread pools and task distribution.
*   **Fork Manager**: Creates and destroys lightweight, copy-on-write state spaces.
*   **State Space Explorer**: Traverses path graphs using heuristic scoring metrics.
*   **Constraint Evaluator**: Checks simulated state transitions against Governance (GCA-1) invariants.
*   **Metric Estimator**: Calculates path utility, confidence bounds, and risk profiles.
*   **Rollback Manager**: Reverts memory states upon path discard or simulation completion.
*   **Sandbox Executor**: Safely emulates sandboxed tool invocations.

---

## 5. Walkthroughs

### Scenario A: Speculative Path Evaluation
1.  **Initiation**: Goal Manager (GMA-1) requests projection for: *"Retrieve resource X via Path A vs Path B."*
2.  **State Forking**: Fork Manager creates two copy-on-write segments (`fork.path_a`, `fork.path_b`) from the current World Model.
3.  **Simulated Execution**: Sandbox Executor mocks the tool calls for each path.
4.  **Constraint Evaluation**: Evaluator verifies both paths satisfy safety constraints.
5.  **Path Selection**: Metric Estimator scores Path A higher due to lower latency, prompting ECA-1 to commit Path A to execution queues.

---

## 6. Observability Metrics

*   **Fork Allocation Latency**: Duration (ms) required to instantiate a copy-on-write memory segment.
*   **Exploration Throughput**: Number of state nodes evaluated per second.
*   **Rollback Integrity Rate**: Percentage of rollbacks completed without leaving orphaned state parameters in Working Memory.

---

## 7. SEA-2 Architecture Principles

The Simulation Engine v2 **MUST NOT**:
1.  Directly apply state updates to the production database.
2.  Bypass Governance constraints or Verification checks.
3.  Expose speculative tool executions to external networks.
