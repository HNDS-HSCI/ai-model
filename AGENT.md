# HSCI V4 — Permanent Agent Operating Instructions (AGENT.md)

This document is the authoritative instruction manual for every autonomous AI coding agent session working in this repository. These instructions override any ad-hoc instructions unless explicitly changed by the user.

---

## 1. Core Operating Rules

### 1.1 The Repository Rule
*   **Single Source of Truth**: The repository is the sole source of truth.
*   **No Chat-Only Artifacts**: Never leave important design decisions, implementation plans, ADRs, test reports, or checklists only in the chat history.
*   **Write to Repository**: Every artifact generated during a session must be written immediately to the appropriate directory in the repository (e.g., `docs/adr/`, `docs/engineering/`, `docs/reports/`, etc.).

### 1.2 The Architecture Rule
*   **Pre-Implementation Read**: Before writing any code, the agent MUST read:
    1.  [AGENT.md](file:///C:/Work/P/ai-model/AGENT.md) (this file)
    2.  [PROJECT_RULES.md](file:///C:/Work/P/ai-model/PROJECT_RULES.md)
    3.  [ARCHITECTURE_CONSTITUTION.md](file:///C:/Work/P/ai-model/ARCHITECTURE_CONSTITUTION.md)
    4.  [IMPLEMENTATION_WORKFLOW.md](file:///C:/Work/P/ai-model/IMPLEMENTATION_WORKFLOW.md)
*   **No Uninformed Code**: Never write code without fully mapping it to the target V4 specifications.

### 1.3 The Engineering Rule
*   **Subsystem Isolation**: Never implement or refactor more than one subsystem at a time.
*   **Sequential Lifecycle**: Every subsystem must progress through the complete engineering workflow lifecycle (Read Spec $\rightarrow$ Review Existing $\rightarrow$ Design $\rightarrow$ Review $\rightarrow$ Implement $\rightarrow$ Unit Test $\rightarrow$ Integration Test $\rightarrow$ Benchmark $\rightarrow$ Document $\rightarrow$ Merge).

### 1.4 The Documentation Rule
*   **Compulsory Updates**: Every code change must be accompanied by updates to the API specifications, implementation reports, and migration notes.
*   **No Untracked Code**: Any code change without corresponding documentation updates is considered incomplete and rejected.

### 1.5 The Testing Rule
*   **Symmetric Test Coverage**: Every implemented component must have a corresponding test suite located in `tests/` or `hsci/tests/`.
*   **Required Test Types**: Every feature must have unit tests (mocking external dependencies) and integration tests (executing against transactional test backends).
*   **Coverage Target**: Branch coverage for new code must be $\ge 90\%$.

### 1.6 The Benchmark Rule
*   **Continuous Performance Verification**: Any change to reasoning engines, databases, or classification layers must run the benchmark suite before merge.
*   **Regression Policy**: Zero tolerance for latency regressions. Any update that increases average cycle duration by $>5\%$ is blocked.

---

## 2. Gatekeeping Policies (DoR & DoD)

### 2.1 Definition of Ready (DoR)
A subsystem task is **Ready** to begin coding only when:
1.  All target specifications (`docs/architecture/` and `docs/engineering/`) have been read and verified.
2.  The existing legacy code in `hnsds/` has been reviewed for reusable algorithms.
3.  A formal design document or ADR is written and saved under `docs/adr/` or `docs/design/`.
4.  A clear set of API contracts and data models has been defined.
5.  A testing strategy has been approved, specifying unit and integration assertions.

### 2.2 Definition of Done (DoD)
A subsystem task is **Done** and ready for merge only when:
1.  All Python source code is written, adhering to strict coding guidelines (typed, formatted, exception-hygienic).
2.  The unit test suite executes with $100\%$ pass rates and $\ge 90\%$ branch coverage.
3.  Integration test suites execute successfully against test database adapters (e.g., transactional SQLite memory instances).
4.  Benchmarks are run, showing zero latency regressions on active solver domains.
5.  The `docs/reports/SESSION_REPORT.md`, `docs/reports/CHANGELOG.md`, and `docs/reports/DECISIONS.md` files are updated with the session changes.
6.  The subsystem has been verified for compliance with the [ARCHITECTURE_CONSTITUTION.md](file:///C:/Work/P/ai-model/ARCHITECTURE_CONSTITUTION.md).

---

## 3. Engineering Policies

### 3.1 Architecture Drift Policy
*   **Stop Work**: If an implementation detail conflicts with the frozen specifications or the [ARCHITECTURE_CONSTITUTION.md](file:///C:/Work/P/ai-model/ARCHITECTURE_CONSTITUTION.md), the agent must **STOP immediately**.
*   **Document Conflict**: Create a new ADR in `docs/adr/` describing the conflict, its technical implications, and alternatives.
*   **Await Approval**: Present the conflict to the user. Do not write any code addressing the drift until the user explicitly approves the proposal.

### 3.2 Migration Policy
*   **No Global Rewrites**: Do not perform blanket codebase rewrites.
*   **Preserve Solvers**: Retain the deterministic solvers under `hnsds/verifier/` and wrap them in V4 `DeterministicSolverPlugin` adapters using the `SolverRegistry`.
*   **SQLite Unification**: Gradually migrate all flat memory files (`episodes.jsonl`, `concept_graph.json`, `cognitive_weights.json`) to the SQLite `UniversalKnowledgeModel` (UKM).

### 3.3 Code Review Policy
*   **Design Compliance**: Code must respect SOLID and DRY principles.
*   **Thread Safety**: Verify that no service classes maintain mutable class instance states across request cycles. All state must be carried in `WorkingMemory`.
*   **No Code Placeholders**: Do not insert mock outputs, empty functions with `pass`, or `TODO` annotations in merge-ready code.

### 3.4 Release Policy
*   **Semantic Commit Messages**: Commit changes using semantic release tags (`feat:`, `fix:`, `docs:`, `chore:`).
*   **Changelog Sync**: Automatically append release notes to `docs/reports/CHANGELOG.md` upon every successful subsystem integration.
