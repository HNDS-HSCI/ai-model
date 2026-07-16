# HSCI V4 — Architecture Overview (ARCHITECTURE_OVERVIEW.md)

This overview details the unified system architecture, execution lifecycles, and relational dependencies between the 8 core cognitive subsystems of HSCI V4.

---

## 1. System Dependencies Diagram

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

## 2. Core Subsystems Breakdown

### 2.1 BrainKernel
The orchestrator managing the pipeline lifecycles, stage registers, and resource allocations.
*   **Context Scope**: Spawns isolated environments, deallocates Z3 solver context elements, and handles cleanups to prevent python memory leaks.

### 2.2 WorkingMemory
Maintains context-specific state details during pipeline execution.
*   **AttentionBuffer**: Salience weight mappings for active entities.
*   **SemanticFrame**: Translates parsed statements, intent classifications, and constraints.

### 2.3 Universal Knowledge Model (UKM)
Multi-store relational data provider isolating SQLite logic.
*   **ConceptStore**: Coordinates transactional merges and splits using nested SQL `SAVEPOINT` rollbacks.

### 2.4 KnowledgeManager
Facade routing concept coordinates to underlying store providers. It caches lookups to save cycles and invalidates stale caches on database modifications.

### 2.5 Concept Activation Engine (CAE)
Spreads activation values over concept graphs. Uses decay and competition factors to select the active concept workspace.

### 2.6 Understanding Engine
Deterministic tokenizer and intent classifier parsing raw user query text into structured seed concepts.

### 2.7 Cognitive Reasoning Engine (CRE)
Iterative reasoning loop verifying duplicate, circular, or contradictory statements.

### 2.8 Answer Generation Engine (AGE)
Converts verified conclusions into Standard, Step-by-Step, or Technical responses without fabricating details.
