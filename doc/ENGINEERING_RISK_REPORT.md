# HSCI V4 — Engineering Risk Report

This document details the engineering, architectural, migration, performance, testing, and deployment risks associated with the HSCI V4 transition, along with mitigation strategies and contingency plans.

---

## 1. Architectural Risks

### R-1: Concept Evolution Engine (CEE) Degradation
*   **Description**: CEE automatic generalisation merges two concepts that are structurally similar but logically distinct, leading to incorrect inferences in the solver.
*   **Probability**: Medium
*   **Impact**: High
*   **Severity**: High
*   **Mitigation**: Default the `auto_generalise` configuration parameter in the CEE to `False`. Run in dry-run mode for the first 30 days. Require human validation for the first 50 proposals.
*   **Trigger Condition**: The system generates a generalisation proposal that leads to a drop in validation success rates on historical domains by >5%.
*   **Contingency Plan**: Execute the rollback command `UKM.rollback_concept(concept_id, version=N-1)` to restore the original concepts from history, restore the original edges, and flag the generalisation proposal as blacklisted.

---

## 2. Migration Risks

### R-2: Regression in Deterministic Solver Benchmark Scores
*   **Description**: Rewriting the perception and routing layers to run through the `BrainKernel` dispatch pipeline fails to invoke the specialized solvers for legacy tasks, dropping the benchmark score below 100%.
*   **Probability**: Low
*   **Impact**: High
*   **Severity**: High
*   **Mitigation**: Wrap the HNSDS solvers as plugins in the `SolverRegistry` before deprecating legacy files. Keep the legacy `HSCIRunner` active alongside the new `RIRLoopRunner` for dual-testing.
*   **Trigger Condition**: Running `pytest benchmarks/` on the V4 kernel yields a score < 100% on the active verifier domains.
*   **Contingency Plan**: Temporarily route benchmark execution prompts directly from `LanguageBridge` to the verifier plugins, bypassing the neural intent classification stage.

---

## 3. Performance & Concurrency Risks

### R-3: Latency Spikes in Spreading Activation
*   **Description**: As the `OntologyGraph` grows (target 50,000 nodes), traversing relationship edges for concept activation exceeds the 50ms latency budget.
*   **Probability**: Medium
*   **Impact**: Medium
*   **Severity**: Medium
*   **Mitigation**: Limit spreading activation depth to 2 hops. Cache computed activation fields in an LRU cache (256 slots) using the input's domain and intent as key fingerprints.
*   **Trigger Condition**: Spreading activation latency during Phase 6 benchmarks exceeds 35ms on average.
*   **Contingency Plan**: Enforce a strict node-limit threshold (max 100 concepts traversed) and skip optional edges during activation checks.

### R-4: SQLite Write Lock Saturation during High Load
*   **Description**: Under concurrent API load, SQLite write locks block multiple concurrent readers, resulting in query timeouts.
*   **Probability**: Medium
*   **Impact**: High
*   **Severity**: High
*   **Mitigation**: Enforce WAL (Write-Ahead Logging) mode. Buffer all concept strength updates and episode logs in a 500ms write buffer, executing updates in a single coalesced transaction.
*   **Trigger Condition**: Database write operations time out or report `database is locked` exceptions under concurrent load testing.
*   **Contingency Plan**: Increase the SQLite busy timeout to 3000ms and isolate the `EpisodeStore` into a separate database file if contention remains.

---

## 4. Testing Risks

### R-5: Lack of Cognitive Benchmark Coverage
*   **Description**: The legacy benchmark framework tests only deterministic solvers. There are no test cases for the cognitive layers (Mental Model Engine, Reflection Engine, Goal Manager).
*   **Probability**: High
*   **Impact**: High
*   **Severity**: High
*   **Mitigation**: Make the creation of a `benchmarks/cognitive/` task suite a strict completion criterion for Phase 4.
*   **Trigger Condition**: The implementation reaches Phase 7 (Understanding Engine) with zero regression benchmarks for conversational turns.
*   **Contingency Plan**: Delay the activation of CEE auto-evolution until cognitive verification tests are written and run successfully.

---

## 5. Deployment Risks

### R-6: Railway Cold-Starts & Upstox Timeout Failures
*   **Description**: Railway cloud environments experience slow cold-starts during automated trading preparation times. If the Playwright browser automation fails to load selectors within the default timeout (10s), authentication fails.
*   **Probability**: Medium
*   **Impact**: High
*   **Severity**: High
*   **Mitigation**: Maintain the Playwright selector timeouts at 20s as established in Gemini memories. Add page diagnostics (title/URL logging) and heartbeat signals to confirm thread health.
*   **Trigger Condition**: Upstox automation logs report `TimeoutError` or selector load failures on startup.
*   **Contingency Plan**: Trigger a fallback command that restarts the Playwright automation sequence and notifies the metagol monitoring log.

### R-7: Real-time Concurrency and WebSocket Deduplication Spikes
*   **Description**: Real-time updates from demat/broker services trigger notification spam.
*   **Probability**: Medium
*   **Impact**: Medium
*   **Severity**: Medium
*   **Mitigation**: Maintain the 5-second WebSocket deduplication and 5-minute database deduplication gates as defined in production rules.
*   **Trigger Condition**: Multiple identical notification messages are sent within a 5-second window.
*   **Contingency Plan**: Enforce a strict sliding window deduplication cache filter on the API broadcast channel.
