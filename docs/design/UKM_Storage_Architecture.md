# HSCI V4 — UKM Storage Architecture (UKM_Storage_Architecture.md)

This document presents the detailed architectural design and specifications for the storage and persistence layers of the Universal Knowledge Model (UKM), adhering strictly to storage-independent guidelines.

---

## 1. Architecture Overview

The UKM Storage Layer separates the logical schemas (Core Cognitive Objects) from the physical database implementations. It consists of two sub-layers: the **Logical Store Managers** and the **Persistence Provider Interface**.

```
  ┌────────────────────────────────────────────────────────┐
  │                 WorkingMemory / BrainKernel            │
  └───────────────────────────┬────────────────────────────┘
                              │ uses
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                 Logical Stores (Stores Layer)          │
  │  (ConceptStore, OntologyStore, EpisodeStore, etc.)     │
  └───────────────────────────┬────────────────────────────┘
                              │ delegates via abstract queries
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │              Persistence Provider Abstraction          │
  │                  (IStorageProvider Interface)          │
  └─────┬───────────────────────────┬──────────────────────┘
        │ implements                │ implements (future)
        ▼                           ▼
  ┌─────────────┐             ┌─────────────┐
  │ SQLite      │             │ Neo4j /     │
  │ Provider    │             │ PostgreSQL  │
  └─────────────┘             └─────────────┘
```

---

## 2. Store Hierarchy & Responsibilities

### 2.1 Concept Store
*   **Purpose**: Manages long-term declarative concepts.
*   **Responsibilities**: Retrieves concept templates, updates Hebbian strength counts, handles merge/split versions.
*   **Concurrency**: Multiple read threads; write operations lock using transactional RLocks.

### 2.2 Ontology Store
*   **Purpose**: Persists relationship edges between concepts.
*   **Responsibilities**: Traverses graph edges for spreading activation, adds/deletes directional predicates (e.g., `IS_A`, `DEPENDS_ON`).
*   **Indexes**: Bifocal indexes on `(source_id, relationship_type)` and `(target_id, relationship_type)`.

### 2.3 Episode Store & Skill Store
*   **Purpose**: `EpisodeStore` archives thinking session traces; `SkillStore` contains neural trigger sequences.
*   **Responsibilities**: Episodic analogical lookups using similarity thresholds.

### 2.4 Fact Store & Rule Store
*   **Purpose**: Stores active world state (EAV facts) and logic bounds.

### 2.5 Reflection & Verification Store
*   **Purpose**: Stores proof traces, counterexamples, and diagnosed failure classifications.

---

## 3. Persistence Provider Abstraction

The storage layers query physical backends via `IStorageProvider`:

```python
class IStorageProvider(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Establishes database files, pools, or server handshakes."""
        pass

    @abstractmethod
    def execute_write(self, query: str, params: Dict[str, Any]) -> None:
        """Executes a mutating transaction."""
        pass

    @abstractmethod
    def execute_read(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Queries the backend and returns raw row structures."""
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        pass
```

### SQLite Provider Strategy
For local execution, the `SQLiteProvider` implements thread-safe connection pooling, activates WAL (Write-Ahead Logging) mode, and enforces a `busy_timeout` of **3000ms** to prevent lock exhaustion.

---

## 4. Logical Schema Definitions

The schemas define attributes and indexes without SQL syntax, maintaining database-agnostic semantics:

### 4.1 Concept Entity
*   **Attributes**:
    *   `concept_id` (Text, Primary Key)
    *   `name` (Text, Unique)
    *   `namespace` (Text)
    *   `z3_template` (Text)
    *   `strength` (Float)
    *   `status` (Text, indexing target)
    *   `version` (Integer)
*   **Indexes**: `idx_concept_namespace`, `idx_concept_status`.

### 4.2 Relationship Entity (Ontology)
*   **Attributes**:
    *   `relation_id` (Text, Primary Key)
    *   `source_id` (Text, Foreign Key $\rightarrow$ Concept)
    *   `target_id` (Text, Foreign Key $\rightarrow$ Concept)
    *   `relationship_type` (Text)
*   **Indexes**: `idx_rel_forward (source_id, relationship_type)`, `idx_rel_reverse (target_id, relationship_type)`.

### 4.3 Episode Entity
*   **Attributes**:
    *   `episode_id` (Text, Primary Key)
    *   `stimulus` (Text)
    *   `proof_trace` (Text, raw JSON or S-expression)
    *   `embedding_vector` (Float Array)
*   **Indexes**: `idx_episode_similarity`.

---

## 5. Storage Lifecycle & Transactions

### 5.1 Atomic Operations
All writes are wrapped in transactional blocks. If a step fails, the provider calls `rollback_transaction()` to restore the last validated state.

### 5.2 Concept Merge & Split Transactions
Merges and splits affect multiple entities and must be committed atomically:
1.  **Merge Flow**:
    *   Create `vNew` Concept.
    *   Write `SUPERSEDES` relationships pointing from `vNew` to both original concepts.
    *   Update statuses of original concepts to `DEPRECATED`.
    *   If any of these steps raise an error, roll back the entire transaction.
2.  **Split Flow**:
    *   Create specialized `vSub1` and `vSub2` concepts.
    *   Map `SPECIALIZES` relationships.
    *   Flag parent concept status.

---

## 6. Caching & Scalability

### 6.1 Object Cache
An in-memory concept and relationship cache intercepts read queries. It is invalidated whenever a concept's status changes or when a merge/split transaction completes.

### 6.2 Horizontal Scalability
*   **Low scale (100 - 10k concepts)**: Enforced via local `SQLiteProvider`.
*   **Medium scale (10k - 1M concepts)**: Swapped to `PostgreSQLProvider` with table partitions on namespaces.
*   **High scale (1M - 100M concepts)**: Routed to `Neo4jProvider` for ontology graphs and `pgvector` for episodes.
