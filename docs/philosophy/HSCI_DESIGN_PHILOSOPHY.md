# Hyper-Symbolic Cognitive Invention (HSCI) Design Philosophy (HSCI_DESIGN_PHILOSOPHY.md)

This document outlines the foundational philosophy of HSCI. It establishes why the project exists, the core principles guiding its design, and the constitutional framework required to make future architectural decisions.

---

## 1. Introduction

HSCI was created to address the fundamental limitations of modern probabilistic AI systems (specifically Large Language Models). While statistical token engines excel at pattern matching, they lack structural safety, logic guarantees, and transparency. HSCI is designed as a transparent, modular, and deterministic cognitive architecture, replacing probabilistic predictions with axiomatic symbolic deliberation.

---

## 2. Core Principles

Our design decisions are bound by the following uncompromisable principles:

*   **Deterministic Reasoning**: Identical cognitive states must yield identical logical inferences. Determinism guarantees reliability and debugging sanity.
*   **Explainability**: Inferences must be accompanied by a trace log mapping the conclusion back to the initial stimulus and supporting concept facts.
*   **Traceability**: Every processing step within the cognitive pipeline must be inspectable.
*   **Verifiability**: Deductions are verified using Satisfiability Modulo Theories (SMT) solver verification (Microsoft Z3) before they are accepted.
*   **Modularity**: Subsystems must interact solely through defined interfaces, preventing cascading failures and enabling component swaps.
*   **Separation of Concerns**: Orchestration, data stores, parsing, activation, and generation are isolated.
*   **Knowledge-First Cognition**: Facts and concept nodes form the semantic foundation; reasoning is performed over this explicit graph, not implicit weights.
*   **Evidence-Based Conclusions**: No assertion is compiled into an answer without explicit, verified proof tracks.
*   **Reproducibility**: Experiments, evaluation runs, and latency benchmarks must be reproducible under identical environments.
*   **Maintainability**: Code clarity and consistent terminology take priority over complex micro-optimizations.

---

## 3. Architectural Philosophy

HSCI is divided into independent cognitive subsystems:
1.  **BrainKernel**: Acts strictly as the coordinator, managing context lifetimes and stage handoffs, rather than performing cognitive computations itself.
2.  **WorkingMemory**: Serves as a request-scoped database holding active state information, preventing data corruption across concurrent pipelines.
3.  **Universal Knowledge Model (UKM)**: Isolates database layers. Relational and transactional actions are wrapped behind ConceptStore interfaces.
4.  **KnowledgeManager, CAE, UE, CRE, and AGE**: Decoupled modules that perform distinct tasks in sequence (Parsing -> Activating -> Proving -> Compiling).

---

## 4. Engineering Philosophy

We follow standard clean engineering practices:
*   **Clean Architecture**: Low level details (like SQLite storage providers) depend on high-level policies (Knowledge repositories), not vice-versa.
*   **SOLID**: Interfaces are segregated and dependencies are inverted via dynamic constructor composition.
*   **DRY**: Common database migrations and event emission routines are unified inside shared core modules.
*   **Documentation-First**: Architectural decisions are documented and committed before coding begins. The repository is the single source of truth.

---

## 5. Knowledge Philosophy

*   **Explicit**: Concept definitions, namespaces, and coordinates are saved in structured tables.
*   **Versioned**: Updates increment logical versions; historical states are kept to prevent loss of context.
*   **Traceable**: Any retrieved concept tracks its source validation record.
*   **Immutable**: Concepts are never silently altered in place.

---

## 6. Reasoning Philosophy

Reasoning must be fully inspectable and mathematically verified. Rather than using heuristic approximations, we enforce strict axiom verification using Z3 solvers. This prevents circular logic loops and logical negations from entering the reasoning trace.

---

## 7. Evolution Philosophy

*   **Incremental**: Enhancements are introduced step-by-step; we refactor existing modules before adding new ones.
*   **Documented Justification**: Major changes require Architecture Decision Records (ADRs).
*   **Backward Compatibility**: Interfaces remain stable across releases.

---

## 8. Documentation Philosophy

Documentation is a primary project deliverable. Chat logs are ephemeral; every design decision, benchmark, implementation spec, and workflow audit must be committed to the repository to serve as the authoritative engineering reference.

---

## 9. Research Philosophy

HSCI coordinates engineering with scientific research. Claims regarding speed or reliability must be backed by reproducible benchmarks (e.g. `evaluation_runner.py` metrics) and limitations must be documented honestly.

---

## 10. Long-Term Vision

Milestone 1 establishes the core cognitive infrastructure. Subsequent phases will introduce:
*   *Learning Engine*: Weights adjustments.
*   *Reflection Engine*: Automatic failure classification.
*   *Planning Engine*: HTN-based task planning.

---

## 11. Decision Framework

Future contributors proposing changes must answer:
1.  *Does it improve explainability?*
2.  *Does it preserve modularity?*
3.  *Does it reduce unnecessary coupling?*
4.  *Is it supported by reproducible evaluation runner evidence?*
5.  *Is it aligned with the core design principles?*
