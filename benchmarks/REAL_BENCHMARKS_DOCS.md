# HSCI Real Benchmark Documentation

## Overview
This document outlines the evaluation criteria, scoring logic, and leaderboard metrics for the HSCI Real Enterprise Benchmark Suite. This suite replaces trivial arithmetic testing with objective, enterprise-grade scenarios designed to test formal verification, planning, and state dependency resolution.

---

## 1. Benchmark Categories

The suite consists of exactly 100 tasks (20 per category), categorized as follows:

1. **Constraint Verification**: Tests banking rules, access control, and allocation.
2. **Requirements Analysis**: Tests user stories and business rules for conflicts.
3. **Architecture Planning**: Tests microservice deployment and topological dependency.
4. **State Machine Verification**: Tests object lifecycle transition legality.
5. **Dependency Resolution**: Tests package dependency ordering and cycle detection.

---

## 2. Evaluation Criteria

Every task is designed to produce exactly one of several deterministic keywords. The criteria for success is absolute:

*   **Constraint Verification**: `VALID`, `INVALID`, `CONTRADICTION`
*   **Requirements Analysis**: `CONSISTENT`, `INCONSISTENT`, `MISSING_REQUIREMENT`
*   **Architecture Planning**: `VALID_ORDER`, `CYCLIC_DEPENDENCY`, `INVALID_ORDER`
*   **State Machine Verification**: `VALID`, `INVALID`
*   **Dependency Resolution**: `VALID_ORDER`, `CYCLIC_DEPENDENCY`, `INVALID_ORDER`

**Failure Conditions:**
*   If the model outputs the wrong keyword, it scores 0.
*   If the model hallucinates reasoning but forgets to output the target keyword, it scores 0.
*   If the model outputs multiple conflicting keywords, the strict substring match in the scoring logic will flag the first found or fail depending on parser strictness (currently checks for presence of the exact expected answer).

---

## 3. Python Scoring Logic

The scoring engine is implemented in `run_benchmarks.py`. It uses an automated string-matching approach to ensure zero subjectivity:

```python
# Automatic scoring (case-insensitive substring match)
is_correct = task["expected"].lower() in str(output).lower()
```

By explicitly asking the models to "Answer ONLY with: [Keyword]", we reduce the likelihood of parsing failures while preserving the objective ground truth of the logical evaluation.

---

## 4. Suggested Leaderboard Metrics

The leaderboard generated at the end of the run tracks two primary dimensions:

1. **Accuracy (Win Rate %)**: Total Correct / Total Attempted. This is the ultimate measure of Logical Truth. HSCI should theoretically achieve 100% here due to Z3 verification, while probabilistic LLMs will drop points on complex cyclic dependencies or constraint intersections.
2. **Average Latency (Seconds)**: Time taken to reach the answer. LLMs are highly parallelized and optimized for fast TTFT (Time To First Token). HSCI may suffer here on NP-hard resolution paths, exposing the cost of certainty.

### Expected Outcome Matrix:
| System | Expected Accuracy | Expected Latency | Notes |
| :--- | :--- | :--- | :--- |
| **HSCI** | 100% | > 2.0s | High accuracy via SMT verification; high latency due to computation limits. |
| **GPT-4** | ~85% | < 1.0s | Fails on deep cyclic dependencies or unseen constraint bounds. |
| **Claude-3** | ~80% | < 1.0s | Excellent context window but still probabilistic. |
| **Gemini** | ~80% | < 1.0s | Fast, but prone to logic drift on deep state machine paths. |
