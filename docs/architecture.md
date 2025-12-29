# HNS-DS Architecture: Hybrid Neuro-Symbolic Deliberative Solver

## Core Philosophy
The Hybrid Neuro-Symbolic Deliberative Solver (HNS-DS) is a **post-LLM architecture**. Traditional Large Language Models (LLMs) like GPT-4 or Gemini are probabilistic, meaning they approximate answers based on patterns but cannot guarantee correctness. HNS-DS replaces the "guessing" of LLMs with a formal, deliberative loop centered on **symbolic verification**.

## Why LLMs are Avoided
1. **Lack of Soundness**: LLMs hallucinate code and mathematical proofs that appear correct but fail under formal scrutiny.
2. **Inscrutability**: You cannot "debug" why an LLM reached a specific conclusion. HNS-DS uses a trace-able RIR-RI loop.
3. **Probabilistic vs. Deterministic**: HNS-DS aims for **Bounded Completeness** (if a solution exists in the search space, it will be found and verified).

## The RIR-RI Algorithm
The heart of this architecture is **Reinforced Iterative Repair with Retrieval & Induction**:

1. **Formalizer ($\Sigma$)**: Translates natural language into a rigid logical specification. If it can't be formalized, it isn't solved.
2. **Synthesizer ($S$)**: Instead of predicting tokens, it **generates candidates** through symbolic enumeration, template filling, or sketch-based synthesis.
3. **Verifier ($V$)**: A hard-coded, symbolic oracle (like Z3 or a CAS). It provides a binary Pass/Fail and a **Counterexample**.
4. **Learner ($L$)**: Unlike LLM training (which is static), this Learner updates in real-time by storing "Episodes" (failures and their repairs) to prune future search paths.

## The Symbolic Brain: The Mental Model
In HNS-DS, the **Mental Model** is the explicit internal state of the AI. Unlike LLMs, where the "model" is a collection of probabilistic weights, the HNS-DS mental model is a structured, readable data structure that tracks the system's progress through the **RIR-RI Loop**.

### Components of the Mind:
1.  **Logic Mind (Formalizer)**: This component translates messy natural language into a rigid **Symbolic Specification ($\Sigma$)**. It is the "understanding" layer.
2.  **Executive Mind (Planner)**: This layer performs **Hierarchical Task Decomposition**. It decides the strategy for solving $\Sigma$ by breaking it into manageable subgoals.
3.  **Reasoning Mind (Synthesizer & Verifier)**: This is the core deliberative engine. The Synthesizer generates **Hypotheses**, and the Verifier (Z3) performs **Formal Proofs**.
4.  **Learning Mind (Learner)**: This component maintains a memory of all past "Episodes" (successful and failed reasoning paths). It uses **TF-IDF Retrieval** to provide "intuition" based on historical data.

## Cognitive Evolution: The Growth Loop
The system evolves through two primary mechanisms:
1.  **Monotonic Refinement**: Every counterexample provided by the Verifier reduces the possible search space for that specific class of problem. This is a form of **Symbolic Pruning**.
2.  **Reinforced Induction**: The Learner uses the retrieved episodes to "seed" the Synthesizer. Over time, the Synthesizer stops "searching" and starts "proposing" solutions that it knows worked for structurally similar problems.

This creates a system that gets **faster and smarter** with every interaction, eventually reaching a state of **Symbolic Mastery** in its domain.

## Use Cases
- **Verified Software Synthesis**: Generating code that is mathematically proven to satisfy its specs.
- **Formal Mathematics**: Solving complex proofs without human intervention.
- **Critical Systems**: Where 99% accuracy is not enough (e.g., aerospace, cryptography).
