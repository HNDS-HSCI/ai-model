# HSCI V4 — Cognitive Theory of Intelligence (Intelligence_Theory.md)

This document establishes the scientific foundation of the HSCI Theory of Intelligence, defining how information is converted into deterministic understanding.

---

## 1. Information vs. Knowledge vs. Understanding vs. Reasoning vs. Intelligence

HSCI distinguishes these categories structurally and mathematically:

*   **Information**: Raw, unparsed observations (e.g. text bytes, image pixels).
*   **Knowledge**: Structured semantic nodes and relationships compiled into the ontology graph (provenance-tracked concepts).
*   **Understanding**: The deterministic mapping of input context onto active concept nodes, resolving intent and constraints.
*   **Reasoning**: The logical computation over active concept workspaces using Z3 SMT constraint verification.
*   **Intelligence**: The self-verifying utility optimization loop that continuously acquires knowledge, discovers relationships, plans tasks, and corrects contradictions to minimize system entropy.

---

## 2. Mathematical Formalization of Intelligence

HSCI formalizes intelligence as an entropy-minimization function over a concept space (\(\mathcal{K}\)). Let \(\mathcal{W}\) be the active workspace containing activated concepts \(c_i \in \mathcal{K}\). The objective of the cognitive loop is to maximize reasoning utility (\(U\)) while minimizing contradiction entropy (\(H_c\)):

\[
U(\mathcal{W}) = \sum_{c_i \in \mathcal{W}} A(c_i) \cdot T(c_i) - \lambda \cdot H_c(\mathcal{W})
\]

Where:
*   \(A(c_i)\) is the activation potential base of concept \(c_i\).
*   \(T(c_i)\) is the trust/provenance score of the concept.
*   \(H_c(\mathcal{W})\) is the contradiction entropy calculated by Z3 SMT solver consistency assertions.
*   \(\lambda\) is the penalty coefficient for logical inconsistencies.
