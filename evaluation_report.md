# HSCI V4 — Evaluation Framework Report (evaluation_report.md)

This report summarizes the pipeline execution accuracy and processing latency benchmarks calculated by the evaluation runner framework.

---

## 1. Global Benchmark Metrics

*   **Total Evaluation Cases**: 3
*   **Passed Cases**: 3
*   **Concept Activation & Parsing Accuracy**: 100.00%
*   **Average Pipeline Latency**: 0.92ms

---

## 2. Detailed Test Cases Output

| Case Question | Intent Classified | Resolved Concepts | Latency (ms) | Success |
|---|---|---|---|---|
| What is inheritance in Java? | ExplainConcept | ['Inheritance', 'Java'] | 1.67ms | Passed |
| Solve equation 5+2 | SolveEquation | ['Equation'] | 0.52ms | Passed |
| Verify if axiom 5=5 is true | VerifyAxiom | ['Axiom'] | 0.58ms | Passed |

---
*Report generated automatically by the evaluation framework runner.*