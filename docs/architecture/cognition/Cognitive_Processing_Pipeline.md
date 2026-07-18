# HSCI V4 — Cognitive Processing Pipeline (Cognitive_Processing_Pipeline.md)

This document specifies the end-to-end cognitive processing pipeline (CPP-1) that converts raw text into verified answers and evolved concepts.

---

## 1. End-to-End Cognitive Flow

```mermaid
graph TD
    Raw["Raw Text / Document Ingestion"] --> UE["Understanding (Intent & Concept Resolution)"]
    UE --> SR["Meaning (Universal Semantic representation)"]
    SR --> KC["Knowledge Compiler (Axiom & Fact Extraction)"]
    KC --> USM["Memory (Universal Semantic Memory DB)"]
    USM --> CAE["Concept Activation Engine (Spreading Workspace)"]
    CAE --> CRE["Reasoning Engine (SMT Axiom Proof Verification)"]
    CRE --> Plan["Planning (HTN task scheduler)"]
    Plan --> Reflect["Reflection (Metacognitive contradiction checks)"]
    Reflect --> Learn["Learning Engine (Reinforcement & Decay Updates)"]
    Learn --> AGE["Answer Generation Engine"]
    AGE --> Response["Structured Answer"]
```

---

## 2. Ingestion Transformations Table

| Pipeline Stage | Input Object | Process Performed | Output Object |
|---|---|---|---|
| **Understanding** | Raw Input String | Tokenization & grammatical parsing. | `SemanticFrame` |
| **Meaning** | `SemanticFrame` | Entity mapping and disambiguation. | `LanguageOfThought` |
| **Knowledge** | `LanguageOfThought` | Extract facts, assertions, constraints. | `KnowledgeObject` |
| **Memory** | `KnowledgeObject` | SQLite/PostgreSQL transactional write. | DB Graph State |
| **Activation** | User Query Seed | Spreading decay activation over graphs. | Active Workspace |
| **Reasoning** | Active Workspace | Microsoft Z3 SMT solver proving axioms. | `ReasoningResult` |
| **Answer** | `ReasoningResult` | Compiling markdown sections & evidence logs. | `Answer` Object |
