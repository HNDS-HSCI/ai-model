# HSCI V5 — Data Management Architecture (DMA-1)

**Version**: 1.0  
**Status**: Constitutional Engineering Specification  
**Verdict**: Approved for Milestone 2 Development  

---

## 1. Purpose

The Data Management Architecture (DMA-1) defines how all data is modeled, stored, indexed, versioned, migrated, secured, replicated, archived, and governed across the HSCI V5 ecosystem.

### Core Data Objectives
*   **Single Source of Truth**: Universal Semantic Memory (USM) serves as the persistent state broker.
*   **Logical Consistency**: Database commits must satisfy Z3 preconditions.
*   **Recoverability**: Support Point-in-Time Recovery (PITR) with RPO \(\le 10\text{s}\) and RTO \(\le 5\text{m}\).

---

## 2. Terminology

*   **Entity / Attribute / Relation**: Relational database storage constructs.
*   **Node / Edge / Property**: Property Graph database constructs.
*   **Ontology**: Formally validated concept schemas.
*   **UUIDv7 Strategy**: Time-ordered UUID keys for efficient clustered index insertions.
*   **Point-in-Time Recovery (PITR)**: Restoring database states using Transaction Log replays.

---

## 3. Positioning Inside HSCI

```
                  User Request / Input
                           │
                           ▼
              Executive Controller (ECA-1)
                           │
                           ▼
               Working Memory Cache (Redis)
                           │
                           ▼
             Universal Semantic Memory (Postgres)
                           │
                           ▼
               Knowledge Graph (Neo4j)
                           │
                           ▼
             Long-Term Archival (Object Storage)
```
### Why Data Governance wraps all database integrations
Every write operation targeting USM tables must undergo row-level security checks and verification proofs to prevent data drift or invalid schema mutations.

---

## 4. Overall Data Architecture Technologies

*   **PostgreSQL**: Core relational entities (Beliefs, Goals, Tasks, Policies, Telemetry).
*   **Neo4j**: Meaning Graph System (MGS-1) property relations.
*   **Redis**: High-speed focus tracking and WorkingMemory caches.
*   **Object Storage (MinIO / S3)**: Transaction logs and cold backup archives.
*   **Vector DB (Qdrant / Milvus)**: Concept semantic embeddings.

---

## 5. Logical Data Domains

*   **Belief Store**: Postgres tables tracking confidence weights, source, and history.
*   **Goal & Task registries**: Task planner dependencies graphs.
*   **Shared Semantic Memory**: Dynamic multi-agent 3PC consensus states database.

---

## 6. Caching & Transaction Isolation

### 6.1 Redis Working Memory Cache
Cache implements **Write-Through** updates to PostgreSQL. Focus entities use a Least-Attended-First (LAF) eviction threshold with a default TTL of 300s.

### 6.2 Transaction Locking
*   **Optimistic Concurrency Control (OCC)**: Used for high-frequency goal modifications (based on record version numbers).
*   **Pessimistic Locking**: Used during 3PC multi-agent consensus validation blocks to guarantee mutual exclusion.

---

## 7. Data Lifecycle & Migrations

```
Created ──► Validated (Z3 check) ──► Stored ──► Indexed ──► Accessed ──► Archived (S3 Cold)
```
*   **Migrations**: Enforces **Zero-Downtime Rolling Migrations** using the Expand/Contract schema pattern. Backward compatibility is verified using formal schema tests before commits.

---

## 8. Failure Scenarios

### Scenario 1: Primary Database Node Failure
1.  **Detection**: Telemetry Collector registers Consul heartbeat timeout.
2.  **Mitigation**: Auto-failover initiates promotion of the hot standby replica node to Primary.
3.  **Validation**: Read-write connection pools redirect transactions. RPO verified at \(\le 10\text{s}\).

### Scenario 2: Schema Migration Failure
1.  **Detection**: Migration execution script encounters constraint error during contract validation checks.
2.  **Rollback**: System aborts, executes schema rollback DDL, restores base versions from active backups, and alerts.

---

## 9. Observability Metrics

*   **Transaction Rate**: Commit operations completed per second.
*   **Replication Lag**: Delta duration (ms) between primary and replica commits.
*   **Cache Hit Ratio**: Redis cache hit rate percentage.

---

## 10. DMA-1 Architecture Principles

The Data Management Architecture **MUST NOT**:
1.  Perform cognitive reasoning or HTN planning operations.
2.  Modify task execution logic.
3.  Bypass verification proofs or safety checks.

Its sole responsibility is data mapping, ACID storage maintenance, caching performance optimization, replication safety, and recovery orchestration.
