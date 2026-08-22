# HSCI VS-7 — Preflight Reality Audit Report
## Cognitive Workspace & Task Decomposition: Semantic Request → Cognitive Workspace → Executable Task Graph

**Date**: August 2026  
**Auditor**: Antigravity Cognitive Architecture Team  
**Scope**: Reality audit of request state management, task representation, dependency tracking, intermediate result persistence, and `WorkingMemory` suitability across `hsci/core/working_memory.py`, `hsci/core/cognitive_pipeline.py`, `hsci/cognition/interpretation/`, and `hsci/cognition/execution/`.

---

## 1. Executive Summary

Sprints VS-1 through VS-6 established a verified, deterministic cognitive pipeline from human language input to grounded task execution:
`RawInput` $\rightarrow$ `LanguageInterpreter` $\rightarrow$ `SemanticRequest` $\rightarrow$ `InterpretationSet` $\rightarrow$ `GroundingEngine` $\rightarrow$ `CognitiveSituation` $\rightarrow$ `TaskDeriver` $\rightarrow$ `CognitiveTask` $\rightarrow$ `CognitiveTaskExecutor` $\rightarrow$ `Grounded Answer`.

However, the architecture currently operates as a **single-shot linear pipeline**:
- It lacks a request-scoped **`CognitiveWorkspace`** to hold multi-goal requests, grounded entities, intermediate results, and execution state across multiple steps.
- `CognitiveTask` is currently a single directive (with an unexecuted `subtasks` list) without explicit dependency edges (`dependencies: List[str]`) or DAG cycle detection.
- Legacy `WorkingMemory` (`hsci/core/working_memory.py`) is decoupled from the current V4 cognitive stack (housing legacy CEGIS, Z3, and HTN fields that are unused by `CognitivePipeline`).

---

## 2. Answers to the 18 Audit Questions

| # | Question | Current Architecture & Finding |
|---|:---|:---|
| **1** | **Where is request state currently stored?** | In transient local variables inside `CognitivePipeline.answer()` (`understanding`, `raw_input`, `interpretation_set`, `situation`, `task`). |
| **2** | **Where are semantic entities stored?** | In `SemanticRequest.entity_mentions` and `CognitiveSituation.grounded_entities`. |
| **3** | **Where are constraints stored?** | In `SemanticRequest.constraints` and `CandidateInterpretation.constraints`. |
| **4** | **Where are intermediate reasoning results stored?** | In local variables within `CognitiveTaskExecutor` methods, passed directly into answer synthesizers. |
| **5** | **Where are completed tasks stored?** | Nowhere persistently or session-scoped; only attached to the final `Answer.metadata`. |
| **6** | **Where are pending tasks stored?** | In `CognitiveTask.subtasks` within the single root task; no active task scheduler or queue exists. |
| **7** | **Can one request contain multiple tasks?** | Yes structurally in `CognitiveTask.subtasks`, but executor only runs the top-level task action. |
| **8** | **Can tasks depend on one another?** | **No**. `CognitiveTask` lacks a `dependencies: List[str]` field and dependency resolution logic. |
| **9** | **Can execution update state?** | No centralized workspace exists to record incremental task state transitions (`PENDING` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETED`). |
| **10** | **Can a later task consume earlier task output?** | **No**. Results are not published to a shared typed scratchpad. |
| **11** | **Does WorkingMemory provide the correct abstraction?** | **No**. It contains legacy CEGIS, Z3, and HTN structures not aligned with V4 models. |
| **12** | **Is WorkingMemory used by reasoning?** | **No**. `CognitiveReasoningEngine` receives `ReasoningContext` directly via function arguments. |
| **13** | **Is WorkingMemory suitable for request-scoped state?** | **No**. It needs to be replaced or superseded by a modern, typed `CognitiveWorkspace`. |
| **14** | **Which state is passed through function arguments?** | `task`, `situation`, `context`, `style`, and engine instances across `CognitiveTaskExecutor.execute()`. |
| **15** | **Which state is lost between pipeline stages?** | Subtask results, alternative candidate hypotheses, intermediate reasoning proofs for secondary entities, and antecedent context history. |
| **16** | **Can current CognitiveTask represent dependencies?** | **No**. It lacks explicit dependency lists and DAG topology. |
| **17** | **Can the current executor execute a task graph?** | **No**. `CognitiveTaskExecutor` is a single-task dispatcher. |
| **18** | **How is provenance preserved between intermediate results?** | Via `Evidence` and `KnowledgeSource` on final answer sections, but intermediate step results lack typed provenance records. |

---

## 3. Recommended Minimal Architecture for VS-7

1. **`CognitiveWorkspace`** (`hsci/cognition/workspace/workspace.py`):
   - Request-scoped lifecycle (`CREATED`, `GROUNDED`, `READY`, `EXECUTING`, `COMPLETED`, `REFUSED`, `FAILED`).
   - Retains validated `SemanticRequest`, `GroundedEntity` pool, `SemanticConstraint` list, and `ContextReference` status.
   - Contains a `CognitiveTaskGraph` and `Dict[str, TaskResult]`.
   - Never acts as a secondary knowledge store; only references UKM knowledge.

2. **`CognitiveTaskGraph`** (`hsci/cognition/workspace/task_graph.py`):
   - Directed Acyclic Graph (DAG) with explicit dependency checking and cycle rejection (`cycle_detected`).
   - Supports linear pipelines ($A \rightarrow B \rightarrow C$), branched dependencies ($A, B \rightarrow C$), and independent tasks ($A \parallel B$).
   - Returns executable tasks whose dependencies are satisfied.

3. **`TaskResult`** (`hsci/cognition/workspace/task_result.py`):
   - Strongly-typed results (`DEFINITION`, `COMPARISON`, `RELATIONSHIP_PROOF`, `REFUSAL`, `DIAGNOSTIC`).
   - Preserves complete provenance, execution timing, and evidence.

4. **Task Decomposition & Multi-Intent Handling** (`hsci/cognition/workspace/decomposer.py`):
   - Decomposes multi-goal or compound semantic requests into structured task graphs (e.g. `EXPLAIN` $\rightarrow$ `COMPARE` $\rightarrow$ `ANALYZE`).

5. **Multi-Step Execution Loop**:
   - `CognitiveTaskExecutor` executes individual tasks while `CognitiveWorkspace` coordinates graph progression and unblocks ready tasks.

6. **WorkingMemory Decision**:
   - Create a clean `CognitiveWorkspace` under `hsci/cognition/workspace/`. Adapt `IWorkingMemory` to ensure clean compatibility without duplicating state.
