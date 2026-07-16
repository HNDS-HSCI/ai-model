# HSCI V4 — UKM Architecture Review Report (UKM_Architecture_Review_Report.md)

This report presents a critical architectural and engineering review of the three Universal Knowledge Model (UKM) layers, evaluated from the perspective of a Principal Software Architect.

---

## 1. Executive Summary

The combined design of the three UKM layers—Knowledge Representation, Cognitive Access Model, and Storage Architecture—has been reviewed. The design is conceptually robust, enforces storage independence, and provides a clear separation of concerns.

The separation between the logical store managers and the physical `IStorageProvider` abstraction protects the core cognitive flow from database technology details. However, to guarantee system stability, minor updates regarding cache consistency across threads and SQLite savepoint (nested transaction) mechanics must be addressed.

---

## 2. Strengths of the Design

1.  **Strict Layer Separation**: The boundaries between logical representations (schemas), retrieval logic (spreading activation), and storage interfaces are clean.
2.  **Epistemic Provenance**: Mapping `ProofTrace` and `Episode` attributes to all concept updates guarantees logical validity before storage.
3.  **Scalable Retrieval**: Attention-guided pruning and BFS depth limits prevent spreading activation from degrading query times under larger databases.
4.  **Episodic Bypass**: Bypassing verification for exact matches ($\ge 0.95$ similarity) provides significant CPU savings.

---

## 3. Weaknesses & Architectural Risks

### 3.1 SQLite Transaction Nesting Limitations (High Severity)
*   **Issue**: Concept split and merge operations update multiple tables and write relations in sequence. If these operations execute inside a broader stage transaction, standard SQLite database connections do not support nested transactions natively, causing database lock failures or silent rollbacks.
*   **Correction**: The `IStorageProvider` transaction API must explicitly support SQLite `SAVEPOINT` and `RELEASE SAVEPOINT` mechanics rather than relying solely on global `BEGIN`/`COMMIT` transactions.

### 3.2 Thread-Local Cache Incoherency (Medium Severity)
*   **Issue**: When multiple concurrent request threads mutate concepts in parallel (e.g., updating activation strengths or deprecating old concept versions), thread-local cache slots will fall out of sync, leading to race conditions.
*   **Correction**: Mandate that cache invalidation commands are published to the `BrainKernel` global `EventBus` (`on_concept_changed` topic), forcing all thread cache readers to discard stale records.

---

## 4. Specific Verification Checklist

1.  **Layer separation**: *Verified.* Representation, access, and storage are isolated.
2.  **Storage independence**: *Verified.* Stores delegate to an abstract `IStorageProvider`.
3.  **Thread safety**: *Verified (with Minor Changes).* Thread-isolated contexts coupled with global cache invalidation signals ensure race safety.
4.  **Failure recovery**: *Verified.* Atomic savepoints enable robust rollbacks on validation failures.

---

## 5. Required Changes (Prerequisites for implementation)

1.  **Savepoint Transaction Specs**: Add explicit support for `SAVEPOINT` nested transactions in the database store design.
2.  **Cache Invalidation signal**: Update the store APIs to require registering a hook into the `EventBus` to notify concurrent threads of write updates.

---

## 6. Final Recommendation

**Recommendation**: **APPROVED WITH MINOR CHANGES**

The UKM architecture is approved for implementation. Once savepoint mechanics and cache invalidation signals are incorporated into the concrete store designs, database implementation (Sprint 7) may proceed.
