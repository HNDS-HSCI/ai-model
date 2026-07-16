# HSCI V4 — Project Backlog (BACKLOG.md)

This backlog tracks all development tasks across the implementation phases of the HSCI V4 migration.

---

## Completed Phases
*   **Phase 1: Repository Stabilization**
*   **Phase 2: Universal Knowledge Model (SQLite Store)**
*   **Phase 3: Working Memory**
*   **Phase 4: Brain Kernel & 10-Stage Pipeline**
*   **Phase 5: Solver Registry**
*   **Phase 6: Concept Activation Engine (CAE)**
*   **Phase 7: Understanding Engine**
*   **Phase 8: Cognitive Reasoning Engine (CRE)** (completed in Sprint 11)

---

## Active & Upcoming Sprints

### Sprint 12 — Answer Generation Engine (Next Sprint)
*   [ ] **TSK-1201**: Implement natural language converter mapping verified logic statements to fluent summaries.
*   [ ] **TSK-1202**: Add final conversational response templates.
*   [ ] **TSK-1203**: Develop integration demonstration piping CRE outputs to Answer Generator.

---

## Deferred Backlog Items

### Phase 9: Mental Model Engine (MME)
*   [ ] **TSK-901**: Build the `WorldStateGraph` and lazy fact confidence decay.

### Phase 10: HTN Planner
*   [ ] **TSK-1001**: Build `GoalManager` and genuine `HTNPlanner` guided by `DECOMPOSITION_RULES`.

### Phase 11: Reflection Engine & CEE
*   [ ] **TSK-1101**: Build `ReflectionEngine` failure classification.
*   [ ] **TSK-1102**: Implement CEE concept split/merge rules with auto-evolution off by default.

### Phase 12: Learning Engine
*   [ ] **TSK-1201**: Refactor `LearningEngine` SQLite updates and background neural weight updates.

### Phase 13: Teaching Protocol
*   [ ] **TSK-1301**: Implement `TeachingProtocol` lesson validation.
*   [ ] **TSK-1302**: Add the `/v1/teach` API endpoint.
