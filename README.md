# Hyper-Symbolic Cognitive Invention (HSCI) v0.1.0-alpha

[![CI Verification](https://github.com/HNDS-HSCI/ai-model/actions/workflows/verify.yml/badge.svg)](https://github.com/HNDS-HSCI/ai-model/actions/workflows/verify.yml)
[![Tests Passing](https://img.shields.io/badge/tests-206%20passed-green.svg)](https://github.com/HNDS-HSCI/ai-model/actions/workflows/verify.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-yellow.svg)](https://github.com/HNDS-HSCI/ai-model/blob/main/LICENSE)
[![Latest Release](https://img.shields.io/badge/release-v0.1.0--alpha-cyan.svg)](https://github.com/HNDS-HSCI/ai-model/releases)

HSCI is a **Self-Verifying Cognitive Architecture** that replaces the probabilistic weights of traditional AI with a **Symbolic Brain**. It is a deterministic reasoning machine built to solve, prove, and explain with mathematical certainty.

---

## 1. Executive Summary

Unlike Large Language Models (LLMs) that estimate the next token based on statistical probabilities, HSCI operates through **Axiomatic Deliberation**. It perceives input as structured entity maps, resolves them to conceptual networks, verifies logic statements using SMT (Microsoft Z3) solvers, and outputs explainable answers.

---

## 2. Current Architecture

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
├── evaluation_runner.py      # Benchmark runner execution script
├── pyproject.toml            # Project configuration & version
├── requirements.txt          # Package dependencies
└── run_app.py                # Server execution entrypoint
```

---

## 5. Performance Snapshot Benchmarks

Measured latencies calculated by the evaluation runner framework:
*   **BrainKernel startup**: `1.82ms`
*   **WorkingMemory allocation**: `0.0036ms`
*   **KnowledgeManager lookup**: `0.04ms`
*   **Concept Activation latency**: `2.12ms`
*   **Understanding latency**: `1.93ms`
*   **Reasoning latency**: `0.09ms`
*   **Overall cognitive pipeline latency**: `6.89ms`
*   **Total Passing Tests**: 206 tests.

---

## 6. Installation & Execution

### Prerequisites
*   Python 3.11+
*   [Z3 Theorem Prover](https://github.com/Z3Prover/z3)

### Setup
```bash
pip install -r requirements.txt
```

### Running Tests
```bash
pytest
```

### Running Evaluation Runner
```bash
python evaluation_runner.py
```
This executes the evaluation runner over the JSON datasets, checks accuracy metrics, and writes the output report to `evaluation_report.md`.

### Running Demonstrations
*   **CAE Spreading Demo**: `python -m hsci.knowledge.demo_concept_activation`
*   **Understanding Engine Demo**: `python -m hsci.knowledge.demo_understanding_engine`
*   **Reasoning Engine Demo**: `python -m hsci.knowledge.demo_reasoning_engine`
*   **AGE Response Demo**: `python -m hsci.knowledge.demo_answer_generation`

---

## 7. Documentation Index
All specification files are mapped under the [Documentation Index](file:///C:/Work/P/ai-model/docs/reports/DOCUMENTATION_INDEX.md).

---

## 8. Roadmap & Backlog
Refer to [ROADMAP.md](file:///C:/Work/P/ai-model/docs/reports/ROADMAP.md) and [BACKLOG.md](file:///C:/Work/P/ai-model/docs/reports/BACKLOG.md) for future release goals.

---

## 9. License
HSCI is licensed under the Apache 2.0 License.
