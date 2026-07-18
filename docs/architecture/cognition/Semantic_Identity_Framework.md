# HSCI V4 — Semantic Identity Framework (Semantic_Identity_Framework.md)

This specification defines the semantic identity systems that resolve synonymy and homonymy without relying solely on string matches.

---

## 1. Context-Based Namespace Isolates

HSCI enforces absolute separation of homonyms by appending mandatory namespace identifiers:

```
                  [ Raw Ingestion Term: "Apple" ]
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
            Context: "Finance/Tech"     Context: "Agriculture"
                     │                       │
                     ▼                       ▼
      [concept.corp.apple_inc]    [concept.food.apple_fruit]
```

---

## 2. Identity Resolution Strategies

To resolve term references, the identity manager performs the following queries:

### 2.1 Multi-Dimensional Distance Vector
*   Calculates similarity over associated relationships. If term A shares parent `fruits` and term B shares parent `corporations`, the semantic distance evaluates to maximum, forcing partition.

### 2.2 Property Overlap Analysis
*   **Synonyms (Car / Automobile)**: If two terms share parent node `vehicle` and property `wheels: 4`, the similarity is above the merge threshold. The synonym resolver consolidates the entities.
*   **Homonyms (Java Language / Java Island)**: If terms share a label but have zero property overlaps, the homonym resolver instantiates separate namespace partitions.
*   **Version History Tracking**: Historical edits to namespaces preserve lineage to enable rollbacks when split decisions are corrected.
