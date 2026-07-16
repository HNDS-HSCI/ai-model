# HSCI V4 — Implementation Workflow (IMPLEMENTATION_WORKFLOW.md)

This document defines the lifecycle steps required to design, implement, test, and release any subsystem or component in the HSCI repository.

---

## 1. The Engineering Lifecycle

Every development task must follow the sequential lifecycle diagrammed below:

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. Read Architecture & Specifications                  │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. Create Engineering Design & Write ADR               │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. Implement Subsystem Code                            │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 4. Write Unit & Integration Tests                      │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 5. Execute Performance & Regression Benchmarks         │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 6. Update Documentation Standards                      │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 7. Run Code Review & Parity Audits                     │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 8. Merge and Release with Semantic Versioning          │
  └────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Execution Guidelines

### Phase 1: Read Architecture & Specifications
*   **Action**: Read all immutable specification documents under `doc/` and the [ARCHITECTURE_CONSTITUTION.md](file:///C:/Work/P/ai-model/ARCHITECTURE_CONSTITUTION.md).
*   **Verification**: Ensure complete clarity on the target behavior. Check dependencies and locate potential architectural drift.

### Phase 2: Engineering Design & ADR Creation
*   **Action**: Before writing any code, draft an Architectural Decision Record (ADR) under `docs/adr/` (e.g., `docs/adr/0002-subsystem-name.md`).
*   **Content**: Outline the problem context, selected design alternatives, database schema adjustments, and interface modifications.
*   **Gate**: The task is only **Ready** once the design document exists in the repository.

### Phase 3: Code Implementation
*   **Action**: Write clean, fully typed Python source code.
*   **Constraint**: No mock implementations, placeholders, or empty method blocks.
*   **Compliance**: Code must strictly conform to [CODING_STANDARDS.md](file:///C:/Work/P/ai-model/CODING_STANDARDS.md).

### Phase 4: Testing Execution
*   **Action**: Implement test cases under `tests/` or `hsci/tests/`.
*   **Requirements**: Run unit tests (with isolated mocks) and integration tests (using test DB setups).
*   **Coverage target**: Branch coverage $\ge 90\%$.

### Phase 5: Benchmark Execution
*   **Action**: Run the benchmark suite to verify accuracy and compute latency metrics.
*   **Requirement**: Latency regression must be $\le 5\%$. Compare performance directly against baseline run statistics.

### Phase 6: Documentation Updates
*   **Action**: Update the system documentation under `docs/` to reflect API additions or schema updates.
*   **Gate**: Untracked implementation is considered incomplete.

### Phase 7: Code Review & Parity Audits
*   **Action**: Perform automated lint checks and review logic for SOLID, DRY, and thread-safety compliance.
*   **Check**: Ensure zero class-level state variables exist in request pipelines.

### Phase 8: Merge and Release
*   **Action**: Merge code to the primary branch.
*   **Commit Style**: Use semantic releases (`feat:`, `fix:`).
*   **Tracking**: Append summary updates to `docs/reports/CHANGELOG.md` and update `docs/reports/RELEASE_PLAN.md`.
