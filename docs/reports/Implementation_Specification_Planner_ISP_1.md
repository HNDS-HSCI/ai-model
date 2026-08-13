# HSCI V5 — Implementation Specification Planner (ISP-1)

**Version**: 1.0  
**Status**: Project Engineering Blueprint  
**Verdict**: Approved  

---

## 1. Step 1 — Validate Architecture Freeze

Prior to compiling the execution blueprints, all system prerequisites have been verified:
*   **Architecture Completeness**: Cognitive designs (RCA-1 to ASC-1) and core engineering layers (SCA-1, DMA-1, SEA-2, DSA-1, DEA-1) are successfully mapped and frozen.
*   **Decoupled Boundaries**: No overlapping responsibilities or circular service dependencies are detected.
*   **Blocker Check**: Ready. No architectural blockers prevent translating these files into module specifications.

---

## 2. Step 2 — Master Implementation Map

Every abstract subsystem design maps directly to folders and packages:

```
RCA-1 (Cognitive Anatomy) ──────► /services/brainkernel
ECA-1 (Executive Controller) ───► /services/execution/scheduler
WMA-1 (Working Memory) ─────────► /services/memory/cache (Redis)
DMA-1 (Data Management) ────────► /services/memory/db (PostgreSQL/Neo4j)
DSA-1 (Distributed Sync) ───────► /services/distributed/sync (Raft/Consul)
DEA-1 (Distributed Execution) ──► /services/distributed/executor
```

---

## 3. Step 3 — Repository Directory Structure

```
hsci-v5/
├── services/
│   ├── brainkernel/        # Bootstrap loaders
│   ├── reasoning/          # Z3 solver wrappers
│   ├── planning/           # HTN planners (Rust)
│   ├── memory/             # Postgres database migrations
│   ├── simulation/         # CoW forks managers
│   └── distributed/        # Raft sync & executors
├── shared/
│   ├── sdk/                # Shared client libraries
│   └── proto/              # Protobuf API definitions
└── deployment/             # Dockerfiles & Helm manifests
```

---

## 4. Step 4 — Module Specifications

*   **HTN Planning Module (Rust)**:
    *   *Responsibilities*: Resolves action plans from goal queues.
    *   *Inputs*: `GoalTask` Protobuf messages.
    *   *Outputs*: Topologically sorted DAG execution states.
    *   *Thread Safety*: Stateless execution. Clones parameter spaces to avoid locks.
*   **SMT Verification Module (Rust/Z3)**:
    *   *Responsibilities*: Validates logical consistency against rule assertions.
    *   *Constraints*: 50ms thread timeouts.

---

## 5. Step 5 — API & Interface Contracts

### 5.1 gRPC Protobuf Definition (`shared/proto/hsci.proto`)
```protobuf
syntax = "proto3";
package hsci.execution.v5;

service ExecutionService {
  rpc SubmitTask(TaskRequest) returns (TaskResponse);
}

message TaskRequest {
  string task_id = 1;
  string payload = 2;
  int32 priority = 3;
}

message TaskResponse {
  string status = 1;
  string result = 2;
}
```

### 5.2 Kafka Event Topics
*   `telemetry.execution.latency`: Latency metrics logs.
*   `sync.raft.state_change`: Term leader changes notifications.

---

## 6. Step 6 — Data & Caching Specifications

*   **Working Memory Caching**: Redis keys use time-to-live bounds (TTL=300s) with Least-Attended-First (LAF) eviction parameters.
*   **Relational Schema (USM)**: Time-ordered UUIDv7 primary keys in PostgreSQL.
*   **Graph Schema (MGS-1)**: Neo4j relationship maps with active indexing on concept nodes.

---

## 7. Step 7 & 10 — Implementation Milestones & Build Order

```
Phase 1: Bootstrap & Memory
├─ Milestone A: Core Kernel (brainkernel)
├─ Milestone B: Relational Memory (Postgres/USM)
└─ Milestone C: Graph Memory (Neo4j/MGS)

Phase 2: Reasoning & Planning
├─ Milestone D: SMT Logic (Z3/Reasoning)
├─ Milestone E: Task Planning (HTN/Planner)
└─ Milestone F: CoW Simulation (Sandbox/Simulation)

Phase 3: Scale & Distribute
├─ Milestone G: Raft Sync (DSA-1)
├─ Milestone H: Task Schedulers (DEA-1)
└─ Milestone I: Tool Sandbox APIs (TCA-1)
```

---

## 8. Step 8 — Testing Strategy

*   **Unit Tests**: Local mocks testing individual solver parameters.
*   **Integration Tests**: Validating gRPC connectivity and message schemas.
*   **Property Tests**: Generating randomized state assertions to stress Z3 engines.
*   **Chaos Tests**: Simulating network partitions to verify minority quorums drop write locks.

---

## 9. Step 9 — Traceability Matrix

| Feature | Architecture | Repository Module | Test Target | Status |
|---|---|---|---|---|
| Non-Blocking Commit | DSA-1 | `/services/distributed/sync` | `test_3pc_timeouts` | Pending |
| SMT Verification | VVA-1 | `/services/reasoning` | `test_z3_preconditions` | Pending |
| MGS Graph Update | MGS-1 | `/services/memory` | `test_neo4j_concept_indexing` | Pending |
