# HSCI V5 — Distributed Synchronization Architecture (DSA-1)

**Version**: 1.0  
**Status**: Constitutional Engineering Specification  
**Verdict**: Approved for Milestone 2 Development  

---

## 1. Purpose

The Distributed Synchronization Architecture (DSA-1) is the core coordination system of HSCI V5. It defines how state modifications, transaction histories, and logic variables are synchronized consistently across multi-node cluster networks.

### Core Objectives
*   **Strong Consistency**: Write operations to the shared Universal Semantic Memory (USM) must be validated using Raft consensus before being committed.
*   **Fault Tolerance**: Sustain node losses while preserving operation availability by dynamically resolving new quorums.
*   **Split-Brain Prevention**: Implement lease management and majority voting checks to prevent conflicting primary clusters.

---

## 2. Terminology

*   **Raft Consensus**: An election-based protocol managing duplicated write logs across a cluster.
*   **Quorum**: The minimum count of voting replicas (\(\lfloor \frac{N}{2} \rfloor + 1\)) required to authorize state modifications.
*   **Vector Clock**: An array of logical clocks used to detect causal relationships and identify merge conflicts.
*   **Distributed Lock**: A cluster-wide lease mechanism managed by coordinator nodes to guarantee mutual exclusion.

---

## 3. Position Inside HSCI

```
                     Client Request / API Gateway
                                   │
                                   ▼
                      Executive Controller (ECA-1)
                                   │
                                   ▼
                    Distributed Sync Layer (DSA-1)
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  Consensus Engine          Failure Detector          Lease Coordinator
         │                         │                         │
         ▼                         ▼                         ▼
Distributed Memory (DMA-1)  Simulation (SEA-2)      Tool Sandbox (TCA-1)
```

---

## 4. Cluster Architecture & Consensus

### 4.1 Topology
```mermaid
graph TD
    CP["Control Plane (Coordinators)"] --> W1["Worker Node 1"]
    CP --> W2["Worker Node 2"]
    CP --> W3["Worker Node 3"]
    
    subgraph Consensus Group (Raft)
        NodeA["Node A (Leader)"] <--> NodeB["Node B (Follower)"]
        NodeA <--> NodeC["Node C (Follower)"]
    end
```

### 4.2 Raft Log Replication Loop
1.  **Leader Append**: Leader receives a state modification proposal (e.g. goal commit).
2.  **Broadcast**: Leader sends append entries messages to followers.
3.  **Quorum Check**: Follower nodes acknowledge log receipt. Once the leader registers consensus quorums, the entry is committed.
4.  **State Application**: Nodes apply modifications to local database engines.

---

## 5. Conflict Resolution (Vector Clocks)

To resolve concurrent updates to the Distributed World Model, nodes maintain Vector Clocks (\(VC\)). For a cluster of size \(N\):

\[
VC_A(i) < VC_B(i) \quad \forall i \implies VC_A \text{ causally precedes } VC_B
\]

If clocks are concurrent (\(VC_A \not\prec VC_B \land VC_B \not\prec VC_A\)), DSA-1 triggers the **Semantic Merge Policy**:
*   *Conflict Detection*: Scans graph nodes for overlapping logic assertions.
*   *Arbitration*: Resolves logic inconsistencies using the Z3 constraint validator. If insoluble, changes rollback and notify the caller.

---

## 6. Distributed Transactions (Three-Phase Commit)

To prevent blocking scenarios common in 2PC, DSA-1 implements a non-blocking **Three-Phase Commit (3PC)** protocol:

```
Can-Commit? (Phase 1) ──► Pre-Commit? (Phase 2) ──► Do-Commit! (Phase 3)
```

If a participant node times out during Phase 2 or 3, it queries peer node states. If any peer has committed, the node commits; if any peer has aborted, it rolls back.

---

## 7. Failure Scenarios

### Scenario 1: Leader Node Crash
1.  **Detection**: Followers fail to receive heartbeats from the Leader within the election timeout window (150ms-300ms).
2.  **Mitigation**: Followers transition state to Candidate, increment the election term count, and request votes.
3.  **Recovery**: Once a candidate registers a quorum majority, it is promoted to Leader.

### Scenario 2: Network Partition (Split-Brain)
1.  **Detection**: Node groups cannot communicate across the partition boundary.
2.  **Mitigation**: The minority partition fails to achieve quorum majorities (\(\le \lfloor \frac{N}{2} \rfloor\)) and drops write capabilities, rejecting mutations.
3.  **Recovery**: Once network links recover, nodes in the minority partition pull logs from the active leader.

---

## 8. Observability Metrics

*   **Consensus Latency (p99)**: Duration (ms) required to replicate a log entry to a quorum.
*   **Replication Lag**: Delta log index offsets between followers and the leader.
*   **Failure Detection Latency**: Elapsed time (ms) between a node crash and cluster-wide detection.

---

## 9. DSA-1 Architecture Principles

The Distributed Synchronization Architecture **MUST NOT**:
1.  Perform cognitive reasoning or planner operations.
2.  Interpret meaning representations.
3.  Directly modify Governance policies.

Its sole responsibility is log replication, consensus elections, transactional consistency (3PC), conflict resolutions, and heartbeat monitoring.
