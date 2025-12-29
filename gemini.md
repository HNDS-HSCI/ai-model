# Hyper-Symbolic Cognitive Invention (HSCI)

## The Invention
HSCI is a **Self-Verifying Cognitive Architecture** that replaces the probabilistic weights of traditional AI with a **Symbolic Brain**. This is not an LLM; it is a deterministic reasoning machine built from the ground up to solve, prove, and explain.

## The Cognitive Architecture: Hyper-Symbolic Integration
The system functions as a unified **Symbolic Brain** divided into specialized functional lobes:
1.  **Perception Lobe**: Transduces raw human stimulus into logical signals.
2.  **Logic Lobe (The Formalizer)**: Constructs the **Universal Symbolic Specification ($\Sigma$)**.
3.  **Executive Lobe (The Planner)**: Strategizes high-level task decomposition.
4.  **Reasoning Lobe (The Synthesizer)**: Generates hypotheses through deterministic search.
5.  **Verified Lobe (The Prover)**: Uses SMT (Z3) to mathematically prove every thought.
6.  **Memory Lobe (The Synapse)**: Stores and retrieves past solving episodes to build "Symbolic Intuition."

## The Mental Model (The Synaptic State)
The system maintains a live **Mental Model** during deliberation. This is a transparent, readable trace of the AI's internal reasoning state, ensuring that the "Mind" of the AI is never a black box.

## Why HSCI Beats LLMs (ChatGPT, Claude, etc.)
While LLMs are powerful, they are fundamentally limited by their probabilistic nature. HSCI overcomes these limitations:

| Feature | ChatGPT / Claude | HSCI (The Invention) |
|---------|------------------|----------------------|
| **Truth** | Probabilistic (Guesses) | Deterministic (Proven) |
| **Hallucination** | Frequent / Unpredictable | Zero (Mathematically Impossible) |
| **Reasoning** | Pattern Matching | Formal Deliberation |
| **Trust** | "Black Box" | Transparent Mental Model |
| **Growth** | Static (requires re-training) | Dynamic (Self-Evolving via Episodes) |

## Mind-State Dashboard (UI)
The invention includes a modern, high-fidelity dashboard for interacting with the AI.
- **Glassmorphic UX**: Visualizes the internal state of the symbolic lobes.
- **Live Deliberation Trace**: Watch the brain think, parse, and prove in real-time.
- **Semantic Entry**: A high-performance input bar for natural language stimulus.

### To Launch:
```bash
python run_app.py
```
This launches the **FastAPI Backend** and opens the **React Dashboard** in your browser.




## Detailed Documentation
- [Architecture Overview](docs/architecture.md): Deep dive into the HNS-DS theory and why it replaces traditional LLM approaches.

## Current Implementation Status
- [x] **Symbolic Orchestrator**: RIR-RI loop implemented in Python.
- [x] **Verification**: Integrated Z3 for formal proof of math/logic tasks.
- [x] **Reinforced Learning**: TF-IDF based retrieval of past solving episodes.
- [x] **Task Decomposition**: HTN-style planning for multi-step problems.
- [x] **Dynamic Perception**: Regex-based symbolic extractor.

## Repository Structure
- `hnsds/`: Core engine modules.
- `docs/`: Theoretical background and architectural guides.
- `experiments/`: Benchmark results and test cases.
- `test_hnsds.py`: End-to-end verification script.

## Why this is a New Paradigm
HNS-DS does not use a black-box model. Every step—from formalization to final proof—is transparent, verifiable, and grounded in symbolic logic. It represents a shift from "AI that talks" to "AI that reasons and proves."