# HSCI V4 — Documentation Standard (DOCUMENTATION_STANDARD.md)

This document establishes the documentation rules and formatting requirements for all V4 subsystems, interfaces, and databases in the HSCI repository.

---

## 1. Documentation Mandate

Every subsystem (including the `BrainKernel`, `UniversalKnowledgeModel`, `ConceptActivationEngine`, `UnderstandingEngine`, etc.) must maintain an authoritative, up-to-date specification document in the repository. No implementation is considered complete without corresponding documentation updates.

---

## 2. Subsystem Specification Structure

Every subsystem documentation file must be written in Markdown and contain exactly the following seven sections:

### Section 1: Purpose
*   Describe the business logic role of the subsystem.
*   Explain the cognitive or engineering problems it solves.
*   Specify why this subsystem is required and cannot be merged into another layer.

### Section 2: Architecture
*   Explain the internal component layout and control flow.
*   Provide a visual architecture diagram (using Mermaid syntax).
*   Map the subsystem's position in the 10-stage execution pipeline.

### Section 3: Interfaces
*   Detail the public class methods, input parameters, return signatures, and context structures.
*   Document execution exception states and raising policies.
*   Provide Python type signatures and docstring annotations.

### Section 4: Data Model
*   Define all internal data structures, dataclasses, schemas, and variables.
*   Provide JSON canonical schemas and database table specifications if the subsystem persists state.

### Section 5: Testing
*   Outline the testing strategy for the subsystem.
*   Specify the location of unit, integration, and regression test suites.
*   Describe the metrics evaluated (e.g., branch coverage, concurrency limits).

### Section 6: Limitations
*   Document known boundary constraints, performance thresholds, scaling limits, and thread safety warnings.
*   List any open research questions (RQs) that affect tuning.

### Section 7: Future Work
*   Detail planned extensions, optimization strategies, and consolidation tasks.

---

## 3. Formatting & Linking Rules

*   **Markdown Standards**: Follow standard GitHub Flavored Markdown (GFM).
*   **Symbolic File Links**: All referenced file paths, classes, and types must be formatted as clickable markdown links using the `file://` protocol. Do not enclose link text in backticks.
    *   *Correct*: [kernel.py](file:///C:/Work/P/ai-model/hsci/core/kernel.py)
    *   *Incorrect*: \`kernel.py\`
*   **Mermaid Diagrams**: Visualise complex pipelines or relationships using Mermaid code blocks. Quote node labels containing brackets to prevent syntax parsing failures.
