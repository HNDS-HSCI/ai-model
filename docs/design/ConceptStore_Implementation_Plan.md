# HSCI V4 — ConceptStore Implementation Plan (ConceptStore_Implementation_Plan.md)

This document establishes the updated implementation plan for the `ConceptStore` logical manager and repository layers, tracking revisions to the design.

---

## Change History

| Date | Sprint ID | Revision Detail | Status |
|---|---|---|---|
| 2026-07-14 | Sprint 7B | Initial draft for ConceptStore implementation using `IStorageProvider` and Hebbian logic updates directly in the store. | *Superseded* |
| 2026-07-14 | Sprint 7B.1 | Refined design: introduced Repository pattern (`ConceptRepository`), separated relationships/provenance to distinct tables, decoupled learning algorithms, and transitioned validation tasks to verification plugins. | **Frozen / Active** |

---

## 1. Relational Database Schema Design
The `ConceptRepository` manages persistence through the generic `IStorageProvider` using version-controlled tables:

```sql
-- Concepts core table
CREATE TABLE IF NOT EXISTS ukm_concepts (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    namespace TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    axiom_type TEXT NOT NULL,
    abstract_rule TEXT,
    z3_template TEXT,
    domain TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CANDIDATE', 'ACTIVE', 'WEAKENED', 'DEPRECATED', 'ARCHIVED')),
    created_at REAL NOT NULL,
    last_used REAL NOT NULL,
    z3_verified INTEGER NOT NULL CHECK (z3_verified IN (0, 1))
);

-- Concept Aliases table (Decoupled lookup)
CREATE TABLE IF NOT EXISTS ukm_concept_aliases (
    concept_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (concept_id, alias),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Provenance record table
CREATE TABLE IF NOT EXISTS ukm_concept_provenance (
    provenance_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    acquisition_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);
```

---

## 2. Refined Code Boundaries

### 2.1 ConceptRepository
Concrete persistence layer implementing all SQLite query mappings via parameter-bound transactions. It is responsible for assembling SQLite raw dictionaries into the type-hinted `Concept` dataclass.

### 2.2 ConceptStore
Business manager orchestrating calls to `ConceptRepository` and triggering system events:
*   **Merger Flow (Transactional with SAVEPOINT)**:
    1.  Create database savepoint `merge_concept_[ID]`.
    2.  Write merged concept via repository.
    3.  Flag source concepts status to `DEPRECATED`.
    4.  Establish relationship edges (e.g. `GENERALIZES`) calling the relationship registry.
    5.  Release savepoint. Emit `ConceptMerged` event.
    6.  *Error handling*: A write failure triggers rollback to savepoint, preserving the original concepts.
*   **Split Flow (Transactional with SAVEPOINT)**:
    1.  Create database savepoint `split_concept_[ID]`.
    2.  Insert both new specialized concepts.
    3.  Flag parent concept status to `WEAKENED` or `DEPRECATED`.
    4.  Establish `SPECIALIZES` relationships.
    5.  Release savepoint. Emit `ConceptSplit` event.

---

## 3. Sequential Migration Identification
Migrations are placed under `hsci/core/migrations/` using incremental filenames:
*   `0001_initial_concepts_table.sql`
*   `0002_create_provenance_and_aliases.sql`

The `SchemaMigration` system reads, sorts, and executes these files incrementally.

---

## 4. Verification Plan

### Automated Tests
*   `test_concept_repository_crud`: Standard writes/reads mapping validation.
*   `test_alias_resolution`: Verifies alias lookup matching.
*   `test_nested_merge_split_rollback`: Checks rollback status on artificial savepoint failures.
*   `test_event_bus_publishing`: Asserts that correct event triggers emit on creation and mutation cycles.
