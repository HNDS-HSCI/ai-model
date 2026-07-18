# HSCI V4 — Cognitive Memory Architecture (Cognitive_Memory_Architecture.md)

This document specifies the storage subdivisions, retrieval pathways, and operational boundaries of the HSCI memory systems.

---

## 1. Memory Subsystems Layout

HSCI splits memory into 6 isolated components:

```mermaid
graph TD
    Sensory["Sensory Memory (KAL Ingestion Buffer)"] --> WM["Working Memory (Active Workspace / Semantic Frame)"]
    WM --> Cache["Knowledge Cache (Fast retrieval facade)"]
    Cache --> USM["Semantic Memory (Concepts, Rules, Axioms - SQLite)"]
    
    subgraph Long-Term Storage
        USM --> Episodic["Episodic Memory (Historical events & reasoning traces)"]
        USM --> Procedural["Procedural Memory (HTN task schemas & actions)"]
        USM --> MetaMemory["Meta Memory (Confidence logs & self-improvement records)"]
    end
```

---

## 2. Memory Ingestion & Retrieval Pathway

```mermaid
sequenceDiagram
    participant KAL as Sensory (KAL)
    participant WM as Working Memory (Workspace)
    participant KC as Cache
    participant USM as Semantic Memory DB
    
    KAL->>WM: Push raw input tokens
    WM->>KC: Query concept coordinates
    KC-->>WM: Hit (Return active ID)
    Note over KC, USM: Miss triggers SQL retrieval
    KC->>USM: SELECT concept WHERE name == term
    USM-->>KC: Return Concept row
    KC-->>WM: Load into workspace attention buffer
```

---

## 3. Cognitive Memory Characteristics

*   **Working Memory**: Request-scoped, thread-isolated storage containing active concept schemas.
*   **Semantic Memory**: The persistent, structured concept ontology graph.
*   **Procedural Memory**: Sequence of actions and logic plans executed by the task planner.
*   **Episodic Memory**: Chronicles history traces of previous inputs and output reasoning answers.
*   **Meta Memory**: Tracking indices recording "what the system knows" and confidence statistics.
