# HSCI V4 — Project Rules & Core Philosophy (PROJECT_RULES.md)

This document establishes the architectural rules and engineering policies that govern the development of the Hyper-Symbolic Cognitive Invention (HSCI) V4 codebase.

---

## 1. Core Coding Philosophy

HSCI is a native, self-contained AI architecture designed for deterministic, axiomatized reasoning. The codebase is engineered as a **Cognitive Operating System**, which requires the same level of safety, concurrency isolation, and predictability as a traditional software kernel.

---

## 2. Architecture & Design Principles

### 2.1 Clean Architecture
*   **Layer Separation**: The system must be strictly layered. High-level cognitive orchestration (e.g., the `BrainKernel`) must never depend directly on low-level database operations or concrete solver instances. Communication between layers must proceed via abstract interfaces and typed structures defined in `hsci/core/data_types.py`.
*   **Dependency Inversion**: All external integrations—such as databases, parsers, and specialized verifiers—must exist as plugins that are injected or registered dynamically. High-level policies remain unaffected by shifts in storage backends (e.g., SQLite vs. PostgreSQL).

### 2.2 SOLID & DRY
*   **Single Responsibility**: Every module must have exactly one reason to change. Separate the parsing of a signal from its semantic evaluation, and verification from database updates.
*   **Open/Closed Principle**: The system must be open for extension but closed for modification. Adding a new domain solver or concept type must not require editing the orchestrator pipeline. New solvers register as plugins in the `SolverRegistry`.
*   **Don't Repeat Yourself (DRY)**: Abstract common algorithms (such as graph traversals, AST evaluations, and Z3 builders) into core utilities instead of duplicate implementations across individual verifiers.

### 2.3 Dependency Injection
*   **Explicit Constructors**: Do not hide dependencies by instantiating service clients inside constructors. Always inject database stores (`ConceptStore`), classifiers, and verifiers via the initializer.
*   **Context Propagation**: Propagate request-scoped resources using a unified `CognitiveContext` argument passed across all methods in the execution loop.

---

## 3. Concurrency & Thread Safety

*   **Stateless Services**: All services (including classifiers, verifiers, and planners) must be stateless. They must not write to class-level or instance-level attributes during execution cycles.
*   **WorkingMemory Isolation**: All request-scoped states must live inside the `WorkingMemory` structure. This ensures that concurrent requests running on different worker threads do not mutate shared resources.
*   **Database Locking**: SQLite database writes must be serialised using readers-writer locks (`threading.RLock` or `asyncio.Lock` where appropriate). Enable WAL (Write-Ahead Logging) mode to allow concurrent reads during active write transactions.

---

## 4. Error Handling & Exception Hygiene

*   **No Silent Failures**: Never write empty `try/except` blocks or swallow exceptions without logging.
*   **Structured Exceptions**: Group exceptions into a clear hierarchy derived from a base `HSCIError`:
    *   `ValidationError` (syntactic and schema failures)
    *   `SolverError` (plugin solver runtime failures)
    *   `UKMError` (database write/lock failures)
    *   `VerificationError` (Z3 compiler or verification timeouts)
*   **Defensive API Boundaries**: The FastAPI layer (`brain_api.py`) must wrap execution calls in high-level handlers to return HTTP 500 error payloads instead of raising internal traces to API clients.

---

## 5. Structured Logging & Observability

*   **No Standard Prints**: Never use python's built-in `print()` in production code. All logs must use the unified `logging` module.
*   **Severity Guidelines**:
    *   `DEBUG`: Log internal loop states, variables, and intermediate solver outcomes.
    *   `INFO`: Log major cognitive transitions (e.g., "Stage 3 planning started").
    *   `WARNING`: Log soft validation failures, retries, and database busy signals.
    *   `ERROR`: Log failures in solvers, failed updates, and transaction rollbacks.
*   **Trace Contexts**: Include the `request_id` context parameter in all logs to track cycles across worker threads.

---

## 6. Security Standards

*   **No Arbitrary Code Execution**: Avoid executing raw strings using `exec()` or `eval()`. 
*   **Whitelist AST Validation**: Any template evaluation or code synthesis operation must parse candidate strings using `ast.parse()` and assert that only whitelisted nodes (e.g., binary operations, numerical attributes, and standard comparison operators) exist before execution.
*   **Database Safety**: Use SQL parameter binding for all queries to prevent SQL injection. Never format query strings dynamically.

---

## 7. Performance Thresholds

*   **Tight Latency Budgets**: The target latency for a complete cognitive cycle (LanguageBridge to ResponseBridge) must be $\le 100\text{ms}$ for linear arithmetic problems.
*   **Subsystem Budget Limits**:
    *   CAE Activation: $\le 15\text{ms}$
    *   HTN Planning: $\le 15\text{ms}$
    *   Z3 Verification: $\le 50\text{ms}$ (timeouts capped at 5s)
*   **Cache CADENCE**: Enforce active caches (LRU size 256) on semantic parses and graph activations to reduce computational overhead.

---

## 8. Versioning Policy

*   **Semantic Versioning**: All releases and API packages must use semantic versioning (`vMajor.Minor.Patch` format).
*   **Database Schema Versioning**: SQLite database migrations must be tracked using a schema version variable in the user_version DB header. Incremental updates require a corresponding migration script.
