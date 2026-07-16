# HSCI V4 — ConceptStore Architecture Refinement (ConceptStore_Architecture_Refinement.md)

This document details the refined architecture and design specifications for the `ConceptStore` component, maximizing separation of concerns, testability, and future scalability.

---

## 1. Updated Architecture

The architecture separates logical business logic, persistence operations, and physical database commands:

```
  BrainKernel
      ↓
  WorkingMemory
      ↓
  ConceptStore  (Logical/Business operations)
      ↓
  ConceptRepository  (Data mapping & persistence)
      ↓
  IStorageProvider  (Abstract storage operations)
      ↓
  SQLiteProvider  (Concrete engine)
```

### Responsibility Matrix
*   **ConceptStore**: Coordinates transactional business operations (such as splits, mergers, version promotions, and deprecations) and publishes events to the `EventBus`. It is completely database-agnostic.
*   **ConceptRepository**: Converts the lightweight, logical `Concept` dataclass to database rows. It designs database-specific tables and queries, mapping relational results back to logical objects.
*   **IStorageProvider**: Exposes generic, thread-safe connection and execution primitives (`execute_read`, `execute_write`, savepoint boundaries).
*   **EventBus**: Broker that propagates state changes to concurrent systems (e.g. Concept Activation Engine caches).

---

## 2. Model Refinement & Ownership

### 2.1 Lightweight Concept Model
The `Concept` dataclass is stripped of all graph/relationship and historical logging structures. It represents only intrinsic identity and metadata properties:

```python
@dataclass
class Concept:
    id: str                       # Identity
    name: str                     # Identity
    namespace: str                # Identity
    version: int                  # Identity
    axiom_type: AxiomType         # Metadata
    abstract_rule: str            # Metadata
    z3_template: str              # Metadata
    domain: str                   # Metadata
    status: str                   # Metadata (ACTIVE, DEPRECATED, ARCHIVED)
    created_at: datetime          # Metadata
    last_used: datetime           # Metadata
    z3_verified: bool             # Metadata
```

### 2.2 Relationship Separation
Relationships are modeled and managed independently from `Concept` entities. This decouples taxonomic inheritance or precondition maps from basic concept definitions, preventing heavy graph serialization overhead during read loops:

```python
@dataclass
class ConceptRelationship:
    relationship_id: str
    source_concept_id: str
    target_concept_id: str
    relationship_type: str        # IS_A, DEPENDS_ON, CONFLICTS_WITH, SUPERSEDES, etc.
    created_at: datetime
```

*   **Ownership**: Relationships are owned and queried by the future `OntologyStore`, writing to distinct database tables (`concept_relationships`).

### 2.3 Provenance Model
Rather than embedding dedicated `proof_id` or `episode_id` fields inside a concept, a generic provenance record captures historical learning sources. This allows the ingestion engine to link concepts to new input modalities (e.g. human teaching, self-play, verification repair runs) without schema updates:

```python
@dataclass
class ProvenanceRecord:
    provenance_id: str
    concept_id: str
    source_type: str              # EPISODE, PROOF, TEACHING_PROTOCOL, REFLECTION_DIAGNOSIS
    source_id: str                # ID referencing the original database entity
    timestamp: datetime
    acquisition_method: str       # HUMAN_INPUT, SELF_PLAY, CEGIS_REPAIR
    confidence: float             # Ingestion reliability (e.g., 1.0 for human, 0.4 for self-play)
    notes: Optional[str] = None
```

*   **Ownership**: Provenance records are stored in a dedicated `concept_provenance` table, managed by the `ConceptRepository` but queryable independently.

---

## 3. Separation of Concerns (Learning & Validation)

### 3.1 Learning Separation
The `ConceptStore` does not execute Hebbian updates or calculate decay. It acts purely as a transactional ledger. 
*   **Logical flow**:
    1.  `LearningEngine` calculates new strength and parameter variables based on feedback signals.
    2.  `LearningEngine` calls `ConceptStore.update_strength(concept_id, strength)`.
    3.  `ConceptStore` delegates write calls to `ConceptRepository`.

### 3.2 Validation Separation
Validation is split into structural (schema/type constraints) and logical (axiomatic validity) phases:
*   **Structural Validation**: Checked by `ConceptStore` via standard schemas (e.g. assert fields are not empty, names adhere to namespace rules, types match).
*   **Logical Validation**: Extension interfaces are designed for cognitive verification (does the concept satisfy SMT proofs?):
    *   *Interface*: `IKnowledgeValidator` exposes `validate_logic(concept: Concept) -> bool`.
    *   *Implementation*: Handled by the future `VerificationEngine` using the Z3 prover plugin. The store does not block writes on solver runs; instead, it writes candidate status and awaits external verification triggers.

---

## 4. Lifecycle APIs

The store interface defines the complete programmatic lifecycle:

```python
class IConceptStore(ABC):
    # Core CRUD
    @abstractmethod
    def create_concept(self, concept: Concept, provenance: ProvenanceRecord) -> str: pass
    @abstractmethod
    def get_concept(self, concept_id: str) -> Optional[Concept]: pass
    @abstractmethod
    def update_concept(self, concept: Concept) -> None: pass
    @abstractmethod
    def exists(self, concept_id: str) -> bool: pass

    # Versioning & Audit History
    @abstractmethod
    def list_versions(self, name: str) -> List[Concept]: pass
    @abstractmethod
    def restore_version(self, concept_id: str, version: int) -> Concept: pass
    @abstractmethod
    def get_history(self, concept_id: str) -> List[Dict[str, Any]]: pass

    # Dynamic Metadata (Extension Hooks)
    @abstractmethod
    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None: pass
    @abstractmethod
    def detach_metadata(self, concept_id: str, key: str) -> None: pass

    # Search & Lookups
    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[Concept]: pass
    @abstractmethod
    def get_concepts_by_namespace(self, namespace: str) -> List[Concept]: pass
    @abstractmethod
    def search_by_metadata(self, key: str, value: Any) -> List[Concept]: pass

    # Refactoring & Evolution
    @abstractmethod
    def deprecate_concept(self, concept_id: str, superseded_by_id: str) -> None: pass
    @abstractmethod
    def archive_concept(self, concept_id: str) -> None: pass
    @abstractmethod
    def merge_concepts(self, id_1: str, id_2: str, merged_concept: Concept) -> str: pass
    @abstractmethod
    def split_concept(self, parent_id: str, split_1: Concept, split_2: Concept) -> Tuple[str, str]: pass
```

### Omission Rationales
*   `delete_concept()`: Intentionally omitted. To maintain referential integrity of historical episodes, concepts are never permanently hard-deleted. They are instead marked as `DEPRECATED` or `ARCHIVED`.
*   `search_by_relationship()`: Omitted. Relationship traversals belong to the `OntologyStore` to ensure proper separation of graph queries from document structures.

---

## 5. Event Bus integration

Subsystems register callbacks via the global `EventBus` to respond to state mutations.

| Event Type | Publisher | Subscribed Receivers | Action Triggered |
|---|---|---|---|
| `ConceptCreated` | `ConceptStore` | `BrainKernelLogger` | Formats stdout and records trace audits. |
| `ConceptUpdated` | `ConceptStore` | `ConceptActivationEngine` | Invalidates LRU caches, forcing fresh reads. |
| `ConceptMerged` | `ConceptStore` | `OntologyStore`, CAE | Updates relationship edges (`GENERALIZES`, `SUPERSEDES`) and clears cached activations. |
| `ConceptSplit` | `ConceptStore` | `OntologyStore`, CAE | Registers `SPECIALIZES` relationships and invalidates caches. |
| `ConceptDeprecated` | `ConceptStore` | `OntologyStore` | Flags active usage restrictions. |
| `ConceptArchived` | `ConceptStore` | `BrainKernel` | Updates active reasoning registers. |

---

## 6. Migration Strategy

The core storage migration framework must move away from fixed array variables inside Python scripts to sequential, file-system-discovered SQL scripts. This supports future schema evolutions cleanly:

*   **Script Location**: `hsci/core/migrations/*.sql`
*   **Format**: `[0001-0999]_description_metadata.sql` (e.g. `0001_create_concepts_table.sql`)
*   **Discovery**: The `SchemaMigration` framework scans the directory, orders files numerically, and executes scripts incrementally against the `schema_versions` table.

---

## 7. Future Subsystem Compatibility

The refined interfaces ensure seamless integration with future cognitive subsystems without requiring backend updates:

*   **Concept Activation Engine (CAE)**: Relies on `get_concepts_by_namespace` and relationship queries via `OntologyStore` (graph queries). The lightweight concept footprint guarantees that traversal speeds remain fast.
*   **Understanding Engine**: Maps strings to aliases using `ConceptRepository` index queries.
*   **Planner & Reasoning Engine**: Fetch compile-ready Z3 rules by querying specific namespaces via `get_concepts_by_namespace`.
*   **Reflection Engine**: Initiates split/merge transactions to reflect dynamic adjustments.
*   **Teaching Protocol**: Invokes `create_concept` with human provenance markers (`1.0` confidence).
