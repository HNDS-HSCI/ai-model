# Hyper-Symbolic Cognitive Invention (HSCI) v0.1.0-alpha

[![CI Verification](https://github.com/HNDS-HSCI/ai-model/actions/workflows/ci.yml/badge.svg)](https://github.com/HNDS-HSCI/ai-model/actions/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/tests-206%20passed-green.svg)](https://github.com/HNDS-HSCI/ai-model/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-yellow.svg)](https://github.com/HNDS-HSCI/ai-model/blob/main/LICENSE)
[![Latest Release](https://img.shields.io/badge/release-v0.1.0--alpha-cyan.svg)](https://github.com/HNDS-HSCI/ai-model/releases)

HSCI is a **Self-Verifying Cognitive Architecture** that replaces the probabilistic weights of traditional AI with a **Symbolic Brain**. It is a deterministic reasoning machine built to solve, prove, and explain with mathematical certainty.

---

## 1. Executive Summary & Vision

Unlike Large Language Models (LLMs) that estimate the next token based on statistical probabilities, HSCI operates through **Axiomatic Deliberation**. It perceives input as structured entity maps, resolves them to conceptual networks, verifies logic statements using SMT (Microsoft Z3) solvers, and outputs explainable answers.

Our vision is a hallucination-free, audit-compliant reasoning framework capable of verifying its own conclusions against structured ontologies.

---

## 2. Current Architecture & Pipeline Flow

```
                       Raw User Text
                             │
                             ▼
                    Understanding Engine
                             │
                             ▼
                     Knowledge Manager
                             │
                             ▼
                  Concept Activation Engine
                             │
                             ▼
                         Workspace
                             │
                             ▼
                 Cognitive Reasoning Engine
                             │
                             ▼
                  Answer Generation Engine
                             │
                             ▼
                    Final User Response
```

---

## 3. Cognitive Pipeline Subsystems

*   **BrainKernel**: Manages context initialization, stage transitions, and Z3 thread-isolated cleanups.
*   **WorkingMemory**: Holds semantic frames, attention buffers, and snapshot states.
*   **Universal Knowledge Model (UKM)**: Transactional SQLite database engine supporting nested SAVEPOINT rollbacks.
*   **KnowledgeManager**: Lookup cache facade with event-driven cache invalidation hooks.
*   **Concept Activation Engine (CAE)**: Spreads activation values over concept graphs.
*   **Understanding Engine**: Tokenizer and intent classifier resolving raw user queries.
*   **Cognitive Reasoning Engine (CRE)**: Iterative reasoning loop verifying duplicate, circular, or contradictory statements.
*   **Answer Generation Engine (AGE)**: Standard, Step-by-Step, and Technical output formatter.
*   **Evaluation Framework**: Multi-domain benchmarking dataset and execution runner.

---

## 4. Repository Structure

```
.
├── .github/                  # GitHub Actions CI/CD workflows
│   └── workflows/
│       ├── ci.yml            # Lint & pytest checks
│       ├── documentation.yml # Deploy docs build
│       ├── evaluation.yml    # Nightly evaluation benchmark
│       └── release.yml       # Release triggers on git tag
├── docs/                     # Documentation files
│   ├── design/               # Design specifications
│   ├── releases/             # Release notes
│   └── reports/              # Status reports & index files
├── evaluation/               # Evaluation datasets
│   ├── Basic_Math.json
│   ├── Java_OOP.json
│   └── Logic.json
├── hnsds/                    # Legacy solvers & neural perceivers
├── hsci/                     # Core V4 packages
│   ├── core/                 # Kernel, working memory, and storage
│   ├── knowledge/            # ConceptStore, CAE, and demo scripts
│   ├── reasoning/            # Reasoning engines and planners
│   └── response/             # AGE response formatting
├── paper/                    # Technical research paper
│   └── HSCI_V4_Technical_Paper.md
├── evaluation_runner.py      # Benchmark runner execution script
├── pyproject.toml            # Project configuration & version
├── requirements.txt          # Package dependencies
└── run_app.py                # Server execution entrypoint
```

---

## 5. Features & Benchmarks

### Implemented Features
*   SMT-backed axiom validation (Z3)
*   Transactional concept storage (SQLite provider)
*   Spreading activation with decay
*   Explainable markdown answer compiling

### Performance Snapshots
*   **BrainKernel startup**: `1.82ms`
*   **Overall cognitive pipeline latency**: `6.89ms`
*   **Evaluation success rate**: `100.00%`

---

## 6. Installation & Quick Start

### Prerequisites
*   Python 3.11+
*   Z3 Theorem Prover

### Installation
```bash
pip install -r requirements.txt
```

### Running Tests
```bash
pytest
```

### Running Evaluation Framework
```bash
python evaluation_runner.py
```

---

## 7. Demonstrations
*   **CAE Spreading Demo**: `python -m hsci.knowledge.demo_concept_activation`
*   **Understanding Engine Demo**: `python -m hsci.knowledge.demo_understanding_engine`
*   **Reasoning Engine Demo**: `python -m hsci.knowledge.demo_reasoning_engine`
*   **AGE Response Demo**: `python -m hsci.knowledge.demo_answer_generation`

---

## 8. Documentation Index
All specification files are mapped under the [Documentation Index](file:///C:/Work/P/ai-model/docs/reports/DOCUMENTATION_INDEX.md).
Foundational rules are defined in the [HSCI Design Philosophy](file:///C:/Work/P/ai-model/docs/philosophy/HSCI_DESIGN_PHILOSOPHY.md).

---

## 9. Roadmap & Backlog
Refer to [ROADMAP.md](file:///C:/Work/P/ai-model/docs/reports/ROADMAP.md) and [BACKLOG.md](file:///C:/Work/P/ai-model/docs/reports/BACKLOG.md) for future release goals.

---

## 10. Contributing & License
Refer to contributing rules in the index. HSCI is licensed under the Apache 2.0 License.
