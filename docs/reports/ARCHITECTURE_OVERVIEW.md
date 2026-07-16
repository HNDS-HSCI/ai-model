# HSCI V4 — Architecture Overview (ARCHITECTURE_OVERVIEW.md)

This overview details the unified system architecture, execution lifecycles, and relational dependencies between cognitive subsystems.

---

## 1. Subsystem Dependencies

```
            [ BrainKernel Pipeline Orchestration ]
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
[WorkingMemory] ──► [KnowledgeManager] ──► [Concept Activation Engine]
     ▲                       │                       ▲
     │                       ▼                       │
[Understanding] ◄── [ConceptStore / DB] ─────────────┘
                             │
                             ▼
               [Cognitive Reasoning Engine]
                             │
                             ▼
                [Answer Generation Engine]
```

---

## 2. Dynamic Pipeline Life-Cycles

### 2.1 BrainKernel Stage Lifecycle
1.  **Context Spawning**: Context isolates the request thread and initializes Z3.
2.  **Pipeline Step execution**: Moves from Understanding -> Activation -> Reasoning -> AGE.
3.  **Context Dispose**: Clears references to trigger GC and deletes the Z3 context.

### 2.2 WorkingMemory State Lifespan
```
[Stimulus Input] ──► Allocation (SemanticFrame) ──► AttentionBuffer ──► Disposed (Cleanup GC)
```

---

## 3. Evaluation Pipeline Workflow

```
[evaluation/*.json] ──► Loader ──► End-to-End Pipeline ──► Checker (eval) ──► evaluation_report.md
```
*   **Case Execution**: Evaluates whether matching seeds and intents satisfy success criteria constraints.
*   **Latency Logging**: Compiles average latency.
