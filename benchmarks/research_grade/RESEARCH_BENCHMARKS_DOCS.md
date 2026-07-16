# HSCI Research-Grade Benchmark Documentation

## Overview
This document outlines the methodology for the research-grade benchmark suite designed to evaluate HSCI against GPT, Claude, and Gemini on complex enterprise tasks.

## Difficulty Tiers
Every category scales through four difficulties. At each tier, the baseline complexity multiplies:
*   **Easy**: 10 Entities, 20 Relationships, 5 Constraints, 3 Rules.
*   **Medium**: 20 Entities, 35 Relationships, 10 Constraints, 5 Rules.
*   **Hard**: 30 Entities, 50 Relationships, 15 Constraints, 7 Rules.
*   **Expert**: 40 Entities, 65 Relationships, 20 Constraints, 9 Rules.

This scaling is specifically designed to overwhelm the attention mechanisms of probabilistic LLMs while testing the runtime complexity bounds of HSCI's Z3 SMT Solver.

## Scoring Logic
The scoring logic ensures deterministic, objective evaluation:
1.  **Format Constraints**: The prompt explicitly bounds the output vocabulary (e.g., "Answer ONLY with: VALID_ORDER or CYCLIC_DEPENDENCY").
2.  **Evaluation**: An automated python script performs a case-insensitive substring match of the expected output keyword.
3.  **Strict Failure**: Any hallucinated context that obfuscates the required logic, or any failure to identify the correct constraint, is scored as 0.

## Reproducibility
The tasks are programmatically generated using a deterministic random seed tied to the `category_difficulty_taskID` hash. This ensures the 100 tasks can be exactly replicated across different systems for independent verification.
