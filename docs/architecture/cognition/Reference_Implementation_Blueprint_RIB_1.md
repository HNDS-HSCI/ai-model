# HSCI V5 — Reference Implementation Blueprint (RIB-1)

**Version**: 1.0  
**Status**: Implementation Blueprint  
**Verdict**: Approved for Milestone 2 Development  

---

## 1. High-Level System Architecture

HSCI V5 is implemented as a **Modular Monolith** transitioning to **Microservices** under high load. Process boundaries divide low-latency execution engines (gRPC) from high-throughput semantic event processing (Kafka):

```
                       User Request (REST/WS)
                                 │
                                 ▼
                     APIGateway / LoadBalancer
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
        ExecutiveController (gRPC)      WorldModel (CoW Database)
                 │                               │
                 ├───────────────────────────────┤
                 ▼                               ▼
       Reasoning Engine (CRE)             Task Planner (HTN)
```

---

## 2. Technology Mapping

### 2.1 Languages
*   **Rust**: Core performance engines (HTN Planner, Z3 SMT bindings) to guarantee low latency.
*   **Python**: Cognitive wrappers and ontology ingestion tools for fast prototyping.
*   **Go**: Microservice coordination APIs and Gateway handlers for high-throughput routing.

### 2.2 Frameworks & Data Stores
*   **gRPC**: Low-latency sync messaging between active modules.
*   **Kafka**: Async telemetry event streams and trace logs.
*   **PostgreSQL**: Entity attributes and transaction-history tables.
*   **Neo4j**: Meaning Graph (MGS-1) database for property relationships.
*   **Redis**: In-memory focus active WorkingMemory cache.

---

## 3. Repository Monorepo Structure

```
hsci-monorepo/
├── services/
│   ├── brainkernel/          # Core boot logic
│   ├── governance/           # GCA-1 safety checks
│   ├── reasoning/            # Z3 integration wrappers
│   ├── planner/              # HTN planning algorithms (Rust)
│   ├── memory/               # USM databases migrations
│   ├── simulation/           # Copy-on-Write forks manager
│   ├── learning/             # LAA-1 consolidations
│   └── monitoring/           # RMA-1 observability pipeline
├── shared/
│   ├── sdk/                  # Common gRPC clients (Rust/Python)
│   └── proto/                # Protocol Buffer contracts
├── deployment/
│   └── kubernetes/           # Helm charts and manifests
└── docs/                     # Specifications indexes
```

---

## 4. Database Architecture

*   **PostgreSQL**: Maps core schemas (e.g. `beliefs` and `agents` tables) with index partitioning on `agent_id` coordinates.
*   **Neo4j**: Captures entity graphs using Cypher index parameters on node labels.
*   **Redis Cache**: Stores active focus nodes with an eviction threshold of Least-Attended-First (LAF).

---

## 5. Event & Message Topologies (Kafka)

Kafka arbitrates event notifications. Topics are partitioned by `topic.partition.key` representing coordinates:

*   `telemetry.monitoring.metrics`: System performance events.
*   `belief.update.committed`: Consolidated updates.
*   `dlq.execution.failures`: Dead Letter Queue for task execution errors.

---

## 6. Security & CI/CD Pipelines

*   **Zero-Trust Identity**: Module execution requires tokenized authorization validation from the GCA-1 permission registry.
*   **CI/CD Pipeline**: GitHub Actions verify that all code compiles, format guidelines are respected, and all unit/integration tests pass before merging.

---

## 7. Performance & Roadmap Goals

*   **Latency Target**: Critical path execution (precondition validation to plan completion) must complete in under **100ms** (50ms budget ceiling for Z3 calls).
*   **Memory Limit**: Capped focus registers \(\le 7\) active entities (Miller's law) to limit RAM allocations.

### Development Roadmap
*   **Phase 1**: Boot logic, HTN planning engines, USM Postgres databases.
*   **Phase 2**: SMT reasoning checks, CoW simulation branches, verification engines.
*   **Phase 3**: Multi-agent consensus, GCA-1 safety validations.
*   **Phase 4**: Production load audits and SRE optimizations.
