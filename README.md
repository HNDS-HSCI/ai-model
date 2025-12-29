# Hyper-Symbolic Cognitive Invention (HSCI)

## Overview
HSCI is a **Self-Verifying Cognitive Architecture** that replaces the probabilistic weights of traditional AI with a **Symbolic Brain**. This system is not a Large Language Model (LLM); it is a deterministic reasoning machine designed to solve, prove, and explain complex problems with mathematical certainty.

Unlike "black box" models, HSCI functions as a unified **Symbolic Brain** with specialized lobes for perception, logic, execution, reasoning, verification, and memory. It maintains a live, transparent **Mental Model** during deliberation, allowing users to verify the "thought process" of the AI.

## Key Features
- **Deterministic Truth**: Replaces probabilistic guesses with proven logic.
- **Zero Hallucination**: Mathematically verified outputs using SMT solvers (Z3).
- **Formal Deliberation**: True reasoning capabilities rather than simple pattern matching.
- **Transparent Mental Model**: A readable trace of the AI's internal state.
- **Dynamic Growth**: Self-evolving memory via stored solving episodes.

## Architecture
The system mimics a biological brain's structure through **Hyper-Symbolic Integration**:
1.  **Perception Lobe**: Converts raw input into logical signals.
2.  **Logic Lobe (The Formalizer)**: Builds a Universal Symbolic Specification ($\Sigma$).
3.  **Executive Lobe (The Planner)**: Decomposes high-level tasks.
4.  **Reasoning Lobe (The Synthesizer)**: Generates hypotheses.
5.  **Verified Lobe (The Prover)**: Validates thoughts using Z3 SMT solver.
6.  **Memory Lobe (The Synapse)**: learns from past episodes ("Symbolic Intuition").

## Repository Structure
```
C:\Work\P\ai\
├── hnsds/                  # Core engine modules
│   ├── brain/              # Cognitive core and lobes
│   ├── formalizer/         # Logic lobe (Spec Builder)
│   ├── learner/            # Memory lobe and episode logging
│   ├── perception/         # Input parsing and transduction
│   ├── planner/            # HTN-style task planning
│   ├── synthesizer/        # Generative and enumerative reasoning
│   └── verifier/           # Z3 interface and validation
├── docs/                   # Documentation and theoretical background
├── experiments/            # Benchmark results and test cases
├── ui/                     # Dashboard frontend
├── run_app.py              # Application entry point
├── test_hnsds.py           # End-to-end verification script
└── gemini.md               # Project context and details
```

## Getting Started

### Prerequisites
- Python 3.8+
- [Z3 Theorem Prover](https://github.com/Z3Prover/z3) (usually installed via `pip install z3-solver`)

### Installation
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure you have `z3-solver` and `fastapi` installed if `requirements.txt` is not yet present.)*

### Running the Application
To launch the FastAPI backend and the React Dashboard:

```bash
python run_app.py
```

Access the Mind-State Dashboard in your browser to interact with the AI, view the live deliberation trace, and explore the internal symbolic states.

## Documentation
- [Architecture Overview](docs/architecture.md): A deep dive into the HNS-DS theory.
- See `gemini.md` for additional project context.

## Current Status
- [x] Symbolic Orchestrator
- [x] Verification (Z3 Integration)
- [x] Reinforced Learning
- [x] Task Decomposition
- [x] Dynamic Perception
