# HSCI V4 — Coding Standards (CODING_STANDARDS.md)

This document establishes the python style guide, structural layout rules, type safety requirements, and formatting guidelines for all contributors to the HSCI repository.

---

## 1. Python Standards & Syntax

*   **Target Interpreter**: Python $\ge 3.10$.
*   **Coding Style**: Code must follow standard PEP 8 formatting rules.
*   **Linting & Formatting**: Enforce strict lint checking using `flake8` and format all files using `black`.

---

## 2. Typing & Static Analysis

*   **Strict Typing**: Every function signature must be fully typed (parameter types and return values). No untyped signatures are permitted.
*   **Explicit Returns**: Use `Union`, `Optional`, and generics where appropriate to enforce parameter clarity.
*   **Forbidden Types**: Avoid using `Any` in type annotations unless representing completely generic payload envelopes.
*   **Static Checks**: Code must pass `mypy` strict type checking before merge.

---

## 3. Directory & Folder Organization

The V4 layout enforces strict separation between layers:

```
C:\Work\P\ai-model\
│
├── hsci/                        # Core V4 Cognitive Engine Package
│   ├── cli/                     # CLI interfaces and runner scripts
│   ├── core/                    # System Kernel, types, configurations, and contexts
│   │   ├── kernel.py            # Stage execution orchestrator
│   │   └── working_memory.py    # Request-scoped memory structures
│   ├── knowledge/               # Universal Knowledge Model stores
│   │   ├── ukm.py               # Unified DB coordinator
│   │   └── concept_activation.py# Spreading activation engine
│   ├── language/                # NLP parsing and UnderstandingEngine
│   ├── learning/                # Reflection, learning engines, and evolution CEE
│   ├── neural/                  # GNN text encoders and IntentClassifiers
│   ├── reasoning/               # HTN planners and solver registry dispatchers
│   └── response/                # Response bridges and session turn managers
│
├── hnsds/                       # Legacy Solvers & Verifiers Library
│   ├── verifier/                # Deterministic math, SM, and CSP solvers
│   └── perception/              # Regex logic parser and input extractors
│
└── docs/                        # Project documentation (ADRs, phases, reports)
```

---

## 4. Import Guidelines

*   **Absolute Imports**: Always use absolute imports. Avoid relative imports (`from . import ...`).
*   **Categorization**: Group imports sequentially:
    1.  Standard Python libraries.
    2.  Third-party packages (e.g., `z3`, `torch`).
    3.  Local repository modules (e.g., `hsci.core.data_types`).
*   **No Circular Imports**: Enforce acyclic imports. Avoid nesting imports inside method scopes unless performing lazy loading during startup transitions.

---

## 5. Naming Conventions

*   **Classes**: Use PascalCase (e.g., `Z3VerificationEngine`, `BrainKernel`).
*   **Methods & Functions**: Use snake_case (e.g., `verify_solution`, `put_concept`).
*   **Variables**: Use snake_case.
*   **Constants**: Use UPPER_SNAKE_CASE (e.g., `MAX_CEGIS_ITERATIONS`).
*   **Private Attributes**: Prefix internal helper variables or private class methods with a single underscore (e.g., `_save_weights`).

---

## 6. Async & Threading Policies

*   **Sync Execution Loop**: The primary request-response loop (`BrainKernel.process`) is synchronous. Do not use async blocks in hot reasoning paths.
*   **Async Handlers**: Use `asyncio` loop triggers solely at the HTTP network server boundary (`brain_api.py`) or in background task loops.
*   **Thread Safety**: Verify that no helper service maintains shared class-level mutable states. Protect shared database writes using thread-safe Locks (`threading.RLock`).

---

## 7. Exception Handling Rules

*   **Explicit Exception Classes**: Group exceptions into a subclass hierarchy derived from a custom base `HSCIError`.
*   **No Bare Excepts**: Avoid using `except:` without specifying the exception class. Never swallow exceptions.
*   **Resource Cleanup**: Always use context managers (`with` blocks) to guarantee that file handles and database connections are closed.

---

## 8. Documentation Style

*   **Class Docstrings**: Every class must contain a docstring detailing its architectural role, initialization dependencies, and thread-safety requirements.
*   **Method Docstrings**: Describe inputs, outputs, exceptions raised, and Z3 performance implications.
*   **Style**: Use Sphinx or Google style docstring formats.
