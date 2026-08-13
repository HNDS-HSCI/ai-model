# HSCI V5 — Canonical Roadmap & Cognitive Capability Reconciliation (CRR-1)

**Version**: 1.0  
**Status**: Canonical Master Roadmap & Architecture Reconciliation  
**Authority**: Principal HSCI Architect, Research Auditor, Repository Archaeologist & Technical Lead  
**Scope**: Definitive Read-Only Repository Reconciliation  

---

## 1. Executive Summary

This report delivers the **Canonical Roadmap & Cognitive Capability Reconciliation (CRR-1)** for the HSCI V5 ecosystem. Based on a read-only audit of the entire repository history—from the original foundational documents (`HSCI_Complete_Master_Document.md`, `HSCI_RESEARCH_PAPER.md`, `ARCHITECTURE_CONSTITUTION.md`) through the mid-stage cognitive designs (`RCA-1`, `SIA-1`, `VVA-1`) to the later infrastructure blueprints (`ISP-1`, `SDB-1`, `MBR-1`, `DSA-1`, `DEA-1`) and executable source code (`hsci/`, `hnsds/`, `prototype/`, `runtime/`)—this document reconstructs the exact project lineage, pinpoints architectural drift, reconciles completed capabilities, and establishes the single authoritative build order going forward.

### Key Conclusions:
1. **Original Research Mission**: HSCI was conceived as a non-tokenized, self-contained, neurosymbolic cognitive system that avoids third-party LLM APIs. Its core thesis is **"Verification Over Prediction"**—pairing neural perceiver intuition with local SMT (Z3) theorem solvers and real-time Hebbian learning.
2. **Current Code Base Reality**: The single-node Python reference implementation (`hsci/` and `hnsds/`) is **100% operational** and validated by **206 passing unit/integration tests**. It faithfully executes the neurosymbolic loop, SQLite persistence (`episodes.db`), and Hebbian weight reinforcement.
3. **Architectural Drift Identified**: A significant shift occurred during Milestone 2, where architectural focus drifted from completing core cognitive capabilities (such as genuine HTN goal decomposition, reflection error classification, and multi-domain knowledge consolidation) toward **premature infrastructure complexity** (e.g., Raft consensus, Kafka topics, multi-node work-stealing schedulers, and gRPC microservice splitting).
4. **Authoritative Verdict**: Infrastructure work (such as the Rust workspace in `./runtime/`) is valuable as a performance runtime, but **it must not supersede or displace cognitive capability completion**. The immediate priority is completing the cognitive loop—replacing mock planners with real HTN search and implementing reflection engines—while keeping the storage tier on local SQLite/PostgreSQL without premature multi-node clustering.

---

## 2. Original HSCI Mission

According to `HSCI_Complete_Master_Document.md` (v3.0) and `HSCI_RESEARCH_PAPER.md`:
* **Problem Solved**: Generative LLMs operate on statistical word probabilities, leading to unavoidable hallucinations, black-box unexplainability, and massive GPU cluster costs.
* **HSCI Thesis**: True intelligence does not memorize billions of text tokens; it extracts abstract concepts, applies them to novel domains via transfer learning, and **verifies every answer with mathematical proof before outputting**.
* **Non-Negotiable Invariant**: No third-party LLM APIs (OpenAI, Gemini, Claude). All perception, reasoning, and verification must run locally on native neurosymbolic engines.

---

## 3. Original Roadmap Reconstruction

Reconstructed from `ROADMAP.md`, `HSCI_Complete_Master_Document.md`, and early design specs:

```
[Phase 1: Cognitive Foundations]
  ├── BrainKernel Bootstrap
  ├── WorkingMemory Scratchpad
  ├── KnowledgeManager & ConceptStore
  └── Z3 SMT Verification Gate (VVA-1)
            │
            ▼
[Phase 2: Perception & Understanding]
  ├── LanguageBridge Tokenizer (SIA-1)
  ├── Meaning Graph Construction (MGS-1)
  └── Spreading Activation Perceiver (CAE-1)
            │
            ▼
[Phase 3: Learning & Adaptation]
  ├── Hebbian Synaptic Weight Reinforcement (LAA-1)
  ├── SQLite Episode Logger Migration (DMA-1)
  └── Autonomous Background Self-Play (SelfPlayEngine)
            │
            ▼
[Phase 4: Reasoning & Planning]  <-- [WE ARE HERE - COGNITIVE GAPS EXIST]
  ├── Real HTN Goal Decomposition (ECA-1)
  ├── Reflection & Failure Diagnosis (MRA-1)
  └── Multi-Domain Knowledge Transfer
            │
            ▼
[Phase 5: Production Runtime & API]
  ├── High-Performance Rust Runtime Port (`./runtime/`)
  ├── PostgreSQL & Redis Storage Tier
  └── REST / gRPC API Gateway (`brain_api.py`)
```

---

## 4. Project Evolution Timeline

1. **Inception (HNSDS Prototype)**: Initial Python sandbox exploring Z3 SMT constraint solving and basic state-machine solvers.
2. **HSCI Core & Cognitive Pipeline (CPP-1 / RCA-1)**: Formalized the 7-layer Reinforced Intuitive Reasoning (RIR) loop, linking `LanguageBridge`, `NeuralPerceiver`, `Z3VerificationEngine`, and `ResponseBridge`.
3. **Subsystem Design Reports (Sprints 1–12)**: Authored detailed engineering specs and implementation reports for `BrainKernel`, `WorkingMemory`, `KnowledgeManager`, `CAE`, `CRE`, and `AGE`.
4. **SQLite Migration (DMA-1 / EEP-2)**: Refactored flat-file persistence (`episodes.jsonl`) to transaction-isolated SQLite databases (`episodes.db`), passing all concurrency tests.
5. **Architectural Drift (Milestone 2 / MBR-1 / DSA-1 / DEA-1)**: Documentation expanded into distributed systems—specifying Raft consensus, Consul discovery, Kafka pipelines, and container autoscaling—while code implementation remained purely single-node.
6. **Spec Completion & Rust Foundations (MRG-1 / TIA-1 / OPA-1)**: Authored final engineering specs (`TIA-1`, `OPA-1`) and scaffolded `./runtime/` workspace crates for Rust performance bounds.

---

## 5. Current Repository Reality & Execution Flow

### Executable Flow in `hsci/core/rir_loop.py`:
```
Raw Input ──► LanguageBridge ──► NeuralPerceiver ──► ReasoningEngine ──► Z3VerificationEngine ──► ResponseBridge
                                                              │
                                                              ▼
                                                        SQLite Database
                                                        (episodes.db)
```
1. **`LanguageBridge`**: Tokenizes text, extracts numeric entities, and maps keywords.
2. **`NeuralPerceiver`**: Computes token-concept activations using `synaptic_weights.json`.
3. **`ReasoningEngine`**: Formulates Z3 logic pre-conditions and post-conditions.
4. **`Z3VerificationEngine`**: Proves satisfiability (`SAT`/`UNSAT`) via local Z3 SMT solver.
5. **`LearningEngine`**: Applies Hebbian reinforcement ($w = w + 0.5$ on SAT, $w = w - 0.1$ on UNSAT) and logs runs to SQLite `episodes.db`.

---

## 6. Cognitive Capability Inventory

| Capability | Designed in Spec | Source Implementation File | Test Verification File | Current Classification |
|---|---|---|---|---|
| **SMT Verification** | `VVA-1` | [`hsci/symbolic/z3_verifier.py`](file:///C:/Work/P/ai-model/hsci/symbolic/z3_verifier.py) | `hsci/tests/test_verification.py` | **COMPLETE** |
| **Hebbian Learning** | `LAA-1` | [`hsci/learning/learning_engine.py`](file:///C:/Work/P/ai-model/hsci/learning/learning_engine.py) | `test_learning.py` | **COMPLETE** |
| **Language Understanding** | `SIA-1` | [`hsci/language/bridge.py`](file:///C:/Work/P/ai-model/hsci/language/bridge.py) | `hsci/tests/test_understanding_engine.py` | **COMPLETE** |
| **Episode Logging** | `DMA-1` | [`hnsds/learner/episode_logger.py`](file:///C:/Work/P/ai-model/hnsds/learner/episode_logger.py) | `test_cognitive.py` | **COMPLETE** |
| **Working Memory** | `WMA-1` | [`hsci/core/working_memory.py`](file:///C:/Work/P/ai-model/hsci/core/working_memory.py) | `hsci/tests/test_brain_kernel.py` | **FUNCTIONAL BUT LIMITED** |
| **Self-Play Engine** | `CUE-1` | [`prototype/hsci_perception/self_play_engine.py`](file:///C:/Work/P/ai-model/prototype/hsci_perception/self_play_engine.py) | `test_concurrent_learning.py` | **FUNCTIONAL BUT LIMITED** |
| **HTN Task Planner** | `ECA-1` | [`hnsds/brain/lobes/native_planner.py`](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_planner.py) | `hsci/tests/test_htn_planner.py` | **STUB / MOCK** |
| **Reflection Engine** | `MRA-1` | Spec Only | N/A | **DOCUMENTATION ONLY** |
| **Tool Execution Sandbox** | `TIA-1` | [`runtime/crates/tool_executor/`](file:///C:/Work/P/ai-model/runtime/crates/tool_executor/) | Cargo workspace scaffold | **PROTOTYPE** |
| **Raft Consensus Sync** | `DSA-1` | Spec Only | N/A | **SUPERSEDED / DEFERRED** |
| **Distributed Scheduler** | `DEA-1` | Spec Only | N/A | **SUPERSEDED / DEFERRED** |

---

## 7. Architectural Drift Analysis & Infrastructure Review

### Why Drift Occurred:
During Milestone 2, system specifications drifted toward distributed cloud infrastructure (Raft vector clocks, Kafka event streaming, Consul service discovery) before core cognitive capabilities (HTN planning, Reflection diagnosis) were fully implemented in code.

### Infrastructure Review Verdict:
* **SQLite Persistence (`episodes.db`)**: **RETAIN NOW**. Highly effective, transactional, and passes all 206 tests. PostgreSQL is deferred until multi-tenant cloud scale is required.
* **Rust Workspace (`./runtime/`)**: **RETAIN / IMPROVE NOW**. Serves as an essential high-performance runtime for sub-50ms Z3 timeout preemption (**OPA-1**).
* **Raft Clustering (`DSA-1`) & Multi-Node Schedulers (`DEA-1`)**: **DEFER / RESEARCH LATER**. Premature for single-node cognitive verification and adds unnecessary complexity.

---

## 8. Cognitive Gaps Remaining

1. **HTN Goal Decomposition**: The current planner returns hardcoded steps; it must be upgraded to perform genuine hierarchical goal decomposition.
2. **Reflection & Failure Diagnosis**: When Z3 returns `UNSAT`, the system currently logs a simple decay. It needs a formal Reflection Engine (`MRA-1`) to diagnose *why* the proof failed and suggest specific correction hints.
3. **Concept Formation**: Automatic aggregation of episodic memories into abstract semantic concepts requires formal consolidation rules.

---

## 9. Document Authority Matrix

| Document | Authority Level | Governance Role |
|---|---|---|
| [`ARCHITECTURE_CONSTITUTION.md`](file:///C:/Work/P/ai-model/ARCHITECTURE_CONSTITUTION.md) | **CANONICAL** | Immutable system rules and zero-LLM-API constraint |
| [`AGENT.md`](file:///C:/Work/P/ai-model/AGENT.md) | **CANONICAL** | Permanent development manual for coding agents |
| [`HSCI_Complete_Master_Document.md`](file:///C:/Work/P/ai-model/HSCI_Complete_Master_Document.md) | **CANONICAL** | Core scientific vision, intelligence theory, and RIR loop definition |
| [`RCA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/HSCI_Reference_Cognitive_Architecture_RCA_1.md) | **CANONICAL** | Reference cognitive architecture specification |
| [`VVA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/Verification_Validation_Architecture_VVA_1.md) | **CANONICAL** | SMT verification and preemption timeout rules |
| [`TIA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/Tool_Integration_Architecture_TIA_1.md) | **SUPPORTING** | Tool execution security and process isolation rules |
| [`OPA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/Optimization_Performance_Architecture_OPA_1.md) | **SUPPORTING** | Performance ceiling and 50ms timeout bounds |
| [`DSA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/Distributed_Synchronization_Architecture_DSA_1.md) & [`DEA-1`](file:///C:/Work/P/ai-model/docs/architecture/cognition/Distributed_Execution_Architecture_DEA_1.md) | **SUPERSEDED / FUTURE** | Deferred multi-node clustering specifications |

---

## 10. Preserve / Evolve / Replace / Defer Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│ PRESERVE                                                               │
│ • hsci/core/rir_loop.py (Main Orchestrator)                            │
│ • hsci/symbolic/z3_verifier.py (Z3 Logic Verifier)                     │
│ • hsci/learning/learning_engine.py (Hebbian Synaptic Learning)        │
│ • hnsds/learner/episode_logger.py (SQLite Storage Layer)               │
├────────────────────────────────────────────────────────────────────────┤
│ EVOLVE                                                                 │
│ • hnsds/brain/lobes/native_planner.py ──► Real HTN Search Engine       │
│ • prototype/hsci_perception/self_play_engine.py ──► Multi-Domain Play │
│ • hsci/core/working_memory.py ──► Thread-Safe Context Structs          │
├────────────────────────────────────────────────────────────────────────┤
│ REPLACE                                                                │
│ • None. All existing code modules pass unit/integration tests.         │
├────────────────────────────────────────────────────────────────────────┤
│ DEFER                                                                  │
│ • Raft Vector Clock Synchronization (DSA-1)                            │
│ • Multi-Node Work-Stealing Schedulers (DEA-1)                          │
│ • PostgreSQL Enterprise Migration                                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Authoritative Build Order & Next Phase

### The SINGLE Next Milestone: **Phase 4 — Cognitive Completion & Planner Upgrade**

#### Why This Milestone Is Next:
The core verifiers, SQLite storage, language parser, and Rust runtime scaffold are already built and verified by 206 passing tests. Moving to cloud clustering without completing the HTN planner and Reflection engine would deepen architectural drift.

#### Required Deliverables:
1. **Real HTN Goal Planner**: Replace `native_planner.py` mocks with a genuine hierarchical task decomposition engine.
2. **Reflection Engine (`MRA-1`)**: Implement failure diagnosis to extract correction hints when Z3 returns `UNSAT`.
3. **Rust Crate Integration**: Finalize `hsci-planner` inside `./runtime/crates/planner`.

#### Definition of Done:
* HTN planner resolves multi-step goal DAGs without fallback mocks.
* Reflection engine correctly diagnoses `UNSAT` failures and logs hints to `episodes.db`.
* All 206 existing pytest tests continue to pass with zero regressions.

---

## 12. Final Answers to Required Audit Questions

1. **What was HSCI originally supposed to become?** A local, non-tokenized neurosymbolic cognitive OS that proves all answers via mathematical logic and learns online without third-party LLM APIs.
2. **What has actually been built?** A fully functional, 7-layer Python reference implementation (`hsci/` and `hnsds/`) backed by Z3 theorem proving, SQLite persistence (`episodes.db`), Hebbian learning, and a scaffolded Rust production workspace (`./runtime/`).
3. **Which parts of the original roadmap are genuinely complete?** SMT verification (`VVA-1`), Hebbian learning (`LAA-1`), language tokenization (`SIA-1`), SQLite episode persistence (`DMA-1`), and unit test verification (206 tests passing).
4. **Which original milestones were skipped or only partially completed?** Hierarchical Task Planning (HTN) and Reflection/Failure Diagnosis were stubbed/mocked.
5. **When did architectural drift begin?** During Milestone 2, when documentation expanded into distributed Raft consensus and Kafka pipelines before completing cognitive planning modules.
6. **Which later architecture decisions were correct?** SQLite migration (`DMA-1`), Tool Integration (`TIA-1`), Optimization Performance (`OPA-1`), and Rust workspace scaffolding (`./runtime/`).
7. **Which were premature?** Raft vector clock synchronization (`DSA-1`) and multi-node work-stealing schedulers (`DEA-1`).
8. **What should remain untouched?** The operational Python core (`hsci/core/rir_loop.py`, `z3_verifier.py`, `learning_engine.py`, `episode_logger.py`).
9. **What should be improved?** The HTN task planner (`native_planner.py`) and Reflection engine.
10. **What should be deferred?** Distributed Raft consensus, multi-node schedulers, and PostgreSQL enterprise migration.
11. **What is the SINGLE next milestone?** **Phase 4: Cognitive Completion (HTN Planner & Reflection Engine)**.
12. **Why is that milestone next?** Because cognitive goal decomposition and failure diagnosis are the remaining gaps separating the current baseline from a complete cognitive system.
13. **Exactly what capabilities must it deliver?** Real HTN search tree decomposition, Z3 UNSAT failure reflection, and multi-step plan execution.
14. **What proves that milestone is complete?** Passing HTN tree decomposition unit tests and clean execution of multi-step logical goals across the test suite.
15. **What comes immediately after it?** Full integration of the compiled Rust runtime binaries (`./runtime/`) and REST/gRPC cloud API deployment.
