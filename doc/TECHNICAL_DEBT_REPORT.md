# HSCI V4 — Technical Debt Report

This document integrates the Phase 0 Architecture Audit findings, registers identified codebase debt, ranks each item by severity, and defines clear remediation paths.

---

## 1. Audit Integration Summary

The Phase 0 Audit assessed the repository across 15 dimensions. It revealed that while the core reasoning logic (`hsci/core/rir_loop.py`) and verifiers are conceptually strong, the system is burdened by a fragmented dual-path runtime and thread-unsafe storage mechanisms. 

The primary architectural debt is the existence of two parallel, un-unified brains running in the same repo, using incompatible type systems (plain dicts in V2 vs typed dataclasses in V3) and separate file-append memory stores.

---

## 2. Technical Debt Registry & Severity Rankings

### 2.1 Critical Severity (Data Corruption & Concurrency Risks)

#### TD-1: Shared Mutable State in Neural Perceiver (`self.last_embedding`)
*   **Description**: The `NeuralPerceiver` stores the computed input tensor embedding in `self.last_embedding` during Stage 1. This value is read asynchronously by the `LearningEngine` at Stage 5. 
*   **Impact**: In a multi-threaded web environment (e.g., concurrent FastAPI calls), overlapping requests overwrite `self.last_embedding`, leading to cross-contamination of GNN embeddings and corrupted proof-guided updates.
*   **Remediation**: Move all request-specific state variables to the request-scoped `WorkingMemory` passed along the pipeline.

#### TD-2: Un-Locked Concurrent File Writes in `EpisodeLogger`
*   **Description**: The legacy `EpisodeLogger.log_episode()` writes directly to `episodes.jsonl` by loading the JSON array, appending the run data, and writing the entire file back to disk without locks or transactions.
*   **Impact**: High probability of file truncation, data loss, or write corruption during concurrent request processing or background self-play executions.
*   **Remediation**: Replaced by the SQLite-backed `EpisodeStore` under the transactional `UniversalKnowledgeModel`.

---

### 2.2 High Severity (Security & Routing Architecture Gaps)

#### TD-3: Hardcoded Keyword-Based Solver Routing
*   **Description**: Legacy routing in `hnsds/brain/cognitive_core.py` determines which deterministic solver to execute using raw string matches in an `if/elif` chain (e.g., `if "ENTERPRISE DEPLOYMENT TOPOLOGY" in stimulus:`).
*   **Impact**: Severe violation of the Open/Closed Principle. Adding a new domain solver or changing keyword patterns requires modifying core brain files.
*   **Remediation**: Replace the `if/elif` block with a dynamic `SolverRegistry` dispatch table in Phase 1, migrating to solver plugins in Phase 5.

#### TD-4: Unsafe `exec()` Code Execution in Synthesizer
*   **Description**: `hnsds/synthesizer/enumerative.py` compiles and runs generated Python code using python's built-in `exec()`. Z3 interface (`z3_interface.py`) parses mathematical constraints using python's `eval()`.
*   **Impact**: Security vulnerability. If a malicious input bypasses the parser, it can execute arbitrary shell code.
*   **Remediation**: Implement a strict AST-based evaluator/whitelist check inside the `ConceptCompiler`, and execute code synthesis steps in a sandboxed, restricted environment.

---

### 2.3 Medium Severity (Performance & Maintenance Waste)

#### TD-5: O(N) Linear File Scans for Memory Queries
*   **Description**: Episodic memory retrieval load the entire `episodes.jsonl` file into memory on every query, performing linear TF-IDF fits and scans.
*   **Impact**: Severe performance degradation as the database grows. Latency scales linearly with the number of historical episodes.
*   **Remediation**: Migrate episodes to SQLite database tables with a full-text search index (FTS5) for rapid, indexed similarity matching.

#### TD-6: Write-Per-Add Performance Bottleneck in `NativeGraph`
*   **Description**: The adjacency list loader in `hnsds/brain/lobes/native_graph.py` writes changes to disk immediately on every single node/edge addition during initialization, resulting in hundreds of synchronous write calls on startup.
*   **Impact**: Slow cold-start bootstrap times (several seconds on cloud environments).
*   **Remediation**: Implement batch writes and check-before-write checks during graph initialization.

#### TD-7: Dual Parallel Runtimes
*   **Description**: The codebase contains both V2 (`hnsds`) and V3 (`hsci`) core orchestrators. Developers must maintain dual test configurations, type systems, and logging styles.
*   **Impact**: Maintenance overhead and split focus.
*   **Remediation**: Transition HNSDS into a pure deterministic solver package, routing all solver actions as plugins through the single V4 `BrainKernel`.

---

### 2.4 Low Severity (Dead Code & Style Inconsistencies)

#### TD-8: Misnamed `HTNPlanner`
*   **Description**: The planning class `hnsds/planner/htn_planner.py` performs a simple 3-branch if/else check instead of running a genuine hierarchical task decomposition network.
*   **Impact**: Confusing design expectation for developers.
*   **Remediation**: Rename to `TaskDecomposer` and replace in V4 with a genuine HTN planner guided by explicit `DECOMPOSITION_RULES`.

#### TD-9: Dead Code Modules
*   **Description**: Modules like `hnsds/formalizer/spec_builder.py` and `hnsds/perception/parser.py` are completely unused by active execution paths but remain in the codebase.
*   **Impact**: Repository clutter.
*   **Remediation**: Delete during Phase 1 (stabilization) after verifying zero dependencies.

#### TD-10: Mixed Type System Discipline
*   **Description**: HNSDS modules communicate using nested Python dictionaries. HSCI modules use strict typed dataclasses. Bounding them requires silent type conversions.
*   **Impact**: Type-checking gaps and translation bugs.
*   **Remediation**: Enforce V4 `data_types.py` dataclasses across all interface boundaries.

---

## 3. Debt Severity Summary & Action Map

```
   Severity      Technical Debt Item                          Remediation Target
┌────────────┬────────────────────────────────────────────┬─────────────────────────────┐
│  CRITICAL  │ TD-1: Perceiver last_embedding Race        │ Phase 3 (Working Memory)    │
│  CRITICAL  │ TD-2: EpisodeLogger Concurrent Writes      │ Phase 2 (Data Layer)        │
├────────────┼────────────────────────────────────────────┼─────────────────────────────┤
│    HIGH    │ TD-3: Hardcoded Solver Routing             │ Phase 1 (Registry Init)     │
│    HIGH    │ TD-4: Unsafe exec() / eval() in Synthesizer │ Phase 13 (Sandbox Compiler) │
├────────────┼────────────────────────────────────────────┼─────────────────────────────┤
│   MEDIUM   │ TD-5: O(N) Linear File Scans in Episodes   │ Phase 2 (Data Layer)        │
│   MEDIUM   │ TD-6: NativeGraph Write-Per-Add Latency    │ Phase 1 (Stabilization)     │
│   MEDIUM   │ TD-7: Dual Brain Runtimes (V2 vs V3)       │ Phase 4 & 5 (BrainKernel)   │
├────────────┼────────────────────────────────────────────┼─────────────────────────────┤
│    LOW     │ TD-8: Misnamed HTNPlanner                  │ Phase 9 (Genuine HTN)       │
│    LOW     │ TD-9: Dead Code spec_builder.py / parser.py│ Phase 1 (Stabilization)     │
│    LOW     │ TD-10: Mixed Type System (Dicts/Dataclasses│ Phase 3 (Working Memory)    │
└────────────┴────────────────────────────────────────────┴─────────────────────────────┘
```
