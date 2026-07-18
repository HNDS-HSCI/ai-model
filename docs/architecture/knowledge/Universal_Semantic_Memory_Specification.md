# HSCI V4 — Universal Semantic Memory Specification (Universal_Semantic_Memory_Specification.md)

This specification defines the schema layout, relational indices, and storage abstractions for the Universal Semantic Memory (USM) long-term memory systems.

---

## 1. Relational Database Schema Model

The core schemas are designed to run on SQLite today and scale to PostgreSQL tomorrow:

```sql
-- Concepts core table
CREATE TABLE IF NOT EXISTS ukm_concepts (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(64) NOT NULL,
    base_activation REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for case-insensitive namespace coordination
CREATE INDEX IF NOT EXISTS idx_concept_lookup ON ukm_concepts(name COLLATE NOCASE, namespace);

-- Relationships mapping table
CREATE TABLE IF NOT EXISTS ukm_relationships (
    id VARCHAR(64) PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    relationship_type VARCHAR(64) NOT NULL,
    weight REAL DEFAULT 1.0,
    FOREIGN KEY(source_id) REFERENCES ukm_concepts(id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES ukm_concepts(id) ON DELETE CASCADE
);

-- Rules and SMT axioms
CREATE TABLE IF NOT EXISTS ukm_rules (
    id VARCHAR(64) PRIMARY KEY,
    description TEXT,
    axiom_formula TEXT NOT NULL, -- Z3 compatible constraint string
    confidence REAL DEFAULT 1.0
);

-- Ingestion Evidence table
CREATE TABLE IF NOT EXISTS ukm_evidence (
    id VARCHAR(64) PRIMARY KEY,
    concept_id VARCHAR(64) NOT NULL,
    source_uri VARCHAR(512) NOT NULL,
    source_hash VARCHAR(64) NOT NULL,
    trust_score REAL NOT NULL,
    FOREIGN KEY(concept_id) REFERENCES ukm_concepts(id) ON DELETE CASCADE
);
```

---

## 2. Storage Mapping Abstractions

To achieve storage portability, the database operations are wrapped behind a generic repository interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from hsci.core.data_types import Concept

class IConceptRepository(ABC):
    @abstractmethod
    def save(self, concept: Concept) -> None:
        pass

    @abstractmethod
    def find_by_id(self, concept_id: str) -> Optional[Concept]:
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> List[Concept]:
        pass

    @abstractmethod
    def delete(self, concept_id: str) -> None:
        pass
```

Future graph database integration (e.g. Neo4j) implements `IConceptRepository` mapping concept nodes as graph vertices and the relationships table as graph edges.
