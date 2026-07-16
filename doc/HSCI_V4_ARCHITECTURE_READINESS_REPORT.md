# HSCI V4 — Architecture Readiness Report

**Document:** HSCI_V4_ARCHITECTURE_READINESS_REPORT.md
**Date:** 2026-06-28
**Basis:** Phase 0 Audit + V4 Architecture Spec + V4 Cognitive Spec + V4 Theory Sprint Documents
**Scope:** Complete review of the HSCI architecture across all five design documents

---

## 1. Contradiction Analysis

The following contradictions or tensions exist across the design documents. Each is classified and a resolution is proposed.

---

### C1: "ConceptActivationEngine" appears in both Architecture Spec and Cognitive Spec with different scopes

**Location:** Architecture Spec — Component 4 (engineering view). Cognitive Spec — Subsystem 2 (cognitive view).

**Tension:** The Architecture Spec defines CAE as a software component with an LRU cache and UKM subscription model. The Cognitive Spec defines CAE with a richer model: recency buffer, frequency map, inhibition store, and GoalManager integration. These are additive, not contradictory, but the Architecture Spec's version is a strict subset.

**Resolution:** The Cognitive Spec is authoritative on behaviour. The Architecture Spec is authoritative on integration points (BrainKernel Layer 2, UKM subscriptions). Both documents are consistent when read as defining different aspects of the same component. Implementation must satisfy both.

**Risk:** Low. The two descriptions are complementary.

---

### C2: Layer numbering inconsistency between Architecture Spec and Cognitive Spec

**Location:** Architecture Spec defines 7 layers (0–6). Cognitive Spec introduces "Layer 0.5" (Understanding Engine) and "Layer 1.5" (Mental Model Engine gap detection) and "Layer 2.5" (Skill Memory retrieval).

**Tension:** The canonical RIR loop has 7 layers. The cognitive spec inserts 3 new half-layers, implying a 10-stage pipeline. No document defines the new canonical layer count.

**Resolution:** Adopt a 10-stage pipeline explicitly. Rename the layers:

| Old Name | Stage | New Name |
|---|---|---|
| Layer 0 | Stage 0 | LanguageBridge |
| (new) | Stage 0.5 | UnderstandingEngine |
| Layer 1 | Stage 1 | NeuralPerceiver |
| (new) | Stage 1.5 | MentalModelEngine (gap detection) |
| Layer 2 | Stage 2 | ConceptActivationEngine |
| (new) | Stage 2.5 | SkillMemory (retrieval) |
| Layer 3 | Stage 3 | SolverRegistry + ReasoningEngine |
| Layer 4 | Stage 4 | Z3VerificationEngine (CEGIS) |
| Layer 5 | Stage 5 | LearningEngine |
| Layer 6 | Stage 6 | ResponseBridge |

The BrainKernel owns this 10-stage pipeline. The GEMINI.md description of "7 layers" is outdated and should be updated to "10 stages" after implementation.

**Risk:** Low. This is a naming issue, not a structural contradiction.

---

### C3: TeachingProtocol and UnderstandingEngine both handle "intent detection"

**Location:** Architecture Spec (Component 5) and Cognitive Spec (Subsystem 7).

**Tension:** TeachingProtocol.intercept() detects teaching intent in raw input using pattern matching. UnderstandingEngine.understand() also processes structured input and could reclassify intent. Who detects teaching intent first?

**Resolution:** Define a strict ordering: TeachingProtocol.intercept() runs BEFORE UnderstandingEngine (at Stage -1, before any other processing). If intercept() returns a TeachingRequest, the entire RIR loop is bypassed. UnderstandingEngine never sees teaching instructions.

This eliminates the ambiguity: teaching is pre-empted at the kernel level; understanding applies only to non-teaching inputs.

**Risk:** Low once ordering is made explicit.

---

### C4: Forgetting mechanism is defined in Cognitive Spec but not in Architecture Spec

**Location:** Cognitive Spec — Concept Evolution Engine (DEPRECATE trigger: days_since_last_proof > 90, strength < 0.1).

**Tension:** The Architecture Spec's UKM has no "deprecation" concept — it only has put_concept and update_concept_strength. There is no UKM API for marking a Concept as DEPRECATED.

**Resolution:** Add two UKM methods to the Architecture Spec:
- `deprecate_concept(concept_id: str, reason: str) -> None` — sets status=DEPRECATED
- `archive_concept(concept_id: str) -> None` — moves to archived table (soft delete)

These are minor additions, not architectural changes.

**Risk:** Low. These are missing CRUD operations, not design conflicts.

---

### C5: SelfModel in Mental Model Engine references "proof_count_total" but LearningEngine tracks proof counts per concept

**Location:** Cognitive Spec — Mental Model Engine (SelfModel.proof_count_total). Architecture Spec — UKM (concept.proof_count per concept).

**Tension:** "Total proof count" is an aggregate that must be derived from the sum of all concept.proof_count values. Who maintains this aggregate — the MME or the UKM?

**Resolution:** The UKM maintains the authoritative per-concept proof_count. The MME derives proof_count_total lazily from UKM when SelfModel is requested: proof_count_total = SUM(concept.proof_count for all concepts). The MME does not maintain its own counter. This eliminates the dual-maintenance problem.

**Risk:** Low. Performance: SUM over N concepts is O(N) — acceptable for a non-hot-path self-model request.

---

## 2. Duplicated Responsibilities

---

### D1: KnowledgeBase.query() and ConceptActivationEngine.activate() — same Layer 2 slot

**Status:** RESOLVED IN ARCHITECTURE SPEC. KnowledgeBase.query() is explicitly replaced by CAE.activate() in V4. KnowledgeBase is retained only as a compatibility wrapper delegating to CAE. This is documented.

**Action required:** When implementing, ensure KnowledgeBase is immediately deprecated in V4 and all callers updated. No new code should call KnowledgeBase.query().

---

### D2: ReflectionEngine and LearningEngine both "update concept strength"

**Location:** Learning Engine updates strength via ProofGuidedUpdater (per cycle). Reflection Engine proposes CORRECT evolutions via CEE which change concept rules (not just strength).

**Tension:** Both touch concepts after a cycle. Is there a write conflict?

**Resolution:** Divide responsibility explicitly:
- **LearningEngine** updates `concept.strength` and `concept.proof_count` ONLY — numeric metadata fields
- **CEE** updates `concept.abstract_rule`, `concept.z3_template`, and `concept.status` ONLY — structural fields
- **These two update categories are disjoint.** No write conflict is possible if this boundary is enforced.

**UKM API enforcement:** `update_concept_strength()` only touches strength/proof_count fields. `put_concept()` (full upsert) is only called by TeachingProtocol and CEE.

---

### D3: GoalManager and MetaCognitiveController both "direct SelfPlay"

**Location:** Architecture Spec — MCC directs SelfPlay toward weak concepts. Cognitive Spec — GoalManager directs SelfPlay toward SELF_IMPROVEMENT goals.

**Tension:** Two authorities directing SelfPlay could produce conflicting instructions.

**Resolution:** Establish a single command chain: **GoalManager is the sole authority for SelfPlay targets.** MCC's role is supervisory only (watchdog, restart, rate limiting). MCC does not generate SelfPlay problem targets directly — it escalates to GoalManager, which generates them. GoalManager.get_active_goals() filtered by type==SELF_IMPROVEMENT is the single source of SelfPlay direction.

---

### D4: UniversalConceptEngine.learn_concept() and TeachingProtocol.teach() — duplicate teaching

**Status:** RESOLVED IN ARCHITECTURE SPEC (Component 5). TeachingProtocol wraps UniversalConceptEngine. UniversalConceptEngine.extract_definition() is retained as TeachingProtocol._parse_instruction(). No duplicate responsibilities after migration.

---

## 3. Unnecessary Modules

---

### U1: hnsds/formalizer/spec_builder.py

**Status:** Identified as dead code in the Phase 0 Audit. Confirmed no callers exist. **Schedule for deletion in Phase 1 (stabilization).** No migration required.

---

### U2: hnsds/brain/cognitive_core.py (post-Phase 4)

**Status:** Identified in Architecture Spec for deletion in Phase 4. Contains the primary architectural debt (if/elif routing). **No action in Phases 1-3.** Delete only after full BrainKernel migration is complete and all benchmarks pass.

---

### U3: run_mind.py, brain_inspector.py, and debug_*.py root-level scripts

**Status:** Legacy development utilities. Not part of any production path. These do not need to be deleted but must not be referenced from any V4 component. **Flag as maintenance scripts** in V4 documentation index.

---

### U4: hnsds/perception/parser.py (vs logic_parser.py)

**Status:** Two parsers exist in hnsds/perception/. The audit did not identify parser.py's role distinctly. Before Phase 1, determine: is parser.py used by any production path or benchmark? If not, schedule deletion alongside spec_builder.py.

---

## 4. Architectural Gaps

---

### G1: No session persistence layer is defined

**Gap:** The BrainKernel processes requests with a CognitiveContext scoped to one request. The Mental Model Engine defines `snapshot()` and `restore()` for session continuity. But no component is responsible for triggering snapshots at the right time (end of session? periodically? on user disconnect?).

**Proposed Owner:** MetaCognitiveController. Add `session_manager` responsibility: on session end signal from brain_api.py, MCC calls `MME.snapshot(session_id)` and stores it in UKM. On session resume, BrainKernel calls `MME.restore(snapshot)` before the first cycle.

**brain_api.py change required:** Add session lifecycle events (session_start, session_end) to the API surface.

---

### G2: No benchmark coverage for cognitive subsystems (MME, Reflection, Goal Manager)

**Gap:** The existing benchmark framework (benchmarks/) tests only the 5 deterministic solvers and the constraint/dependency/state/graph/requirements categories. There are no benchmarks for:
- Mental Model Engine world state accuracy
- Reflection Engine diagnosis accuracy
- Goal Manager goal completion rate
- Skill acquisition correctness
- Concept evolution correctness

**Action:** A `benchmarks/cognitive/` directory must be created in V4 with task sets for each cognitive subsystem. This is a prerequisite for validating Phase 3 and Phase 4 of the migration.

---

### G3: No defined error boundary between BrainKernel and brain_api.py

**Gap:** The Architecture Spec states "BrainKernel returns FinalOutput for all inputs, never raises." But brain_api.py's exception handling is not defined. If BrainKernel.process() somehow raises (a kernel bug), what does the API return?

**Proposed Policy:** brain_api.py wraps every kernel.process() call in a try/except that returns HTTP 500 with a structured error body. The kernel's own guarantee (never raise) is a design contract, not a Python guarantee — the API layer must be defensive.

---

### G4: Conversation history storage is undefined

**Gap:** ConversationTurn is defined in data_types.py. ResponseBridge uses session_history (List[ConversationTurn]) for follow-up context. But no component stores or retrieves ConversationTurn objects persistently. The UnderstandingEngine's follow-up resolution depends on session_history being available.

**Proposed Owner:** BrainKernel maintains an in-memory session_history dict keyed by session_id, bounded to last 20 turns per session. UKM provides `store_conversation_turn()` for persistence across sessions. This must be added to the UKM API.

---

### G5: No defined cold-start bootstrap sequence

**Gap:** The Architecture Spec describes BrainKernel.__init__() at a high level but does not specify: what happens if the UKM is empty (first run ever)? Which component seeds primordial knowledge? In what order do subsystems initialise?

**Proposed Bootstrap Sequence:**
```
1. UKM.__init__() — open/create SQLite DB
2. If UKM is empty: seed from metaphysical_blueprint.json (migrate primordial_knowledge.jsonl)
3. BrainKernel instantiates services in dependency order:
   a. UKM (prerequisite for all)
   b. NeuralPerceiver (loads weights from UKM.WeightStore; if absent → cold start with random weights)
   c. ConceptActivationEngine (subscribes to UKM events)
   d. SkillMemory (loads from UKM skills table)
   e. MentalModelEngine (builds WorldStateGraph from UKM primordial concepts)
   f. TeachingProtocol (no state, no init needed)
   g. SolverRegistry (registers all built-in solvers)
   h. MetaCognitiveController (starts background threads — always last)
4. SelfPlayEngine (started by MCC.start())
5. System ready — first request accepted
```

This sequence must be documented in BrainKernel and enforced via constructor dependency injection.

---

## 5. Scalability Risks

---

### S1: OntologyGraph fully in-memory — risk at scale

**Current state:** ~200 nodes (from audit). V4 target: ~5,000 nodes at 1 year, ~50,000 at 5 years.

**Risk:** At 50,000 nodes with average degree 5, the spreading activation graph traversal in CAE becomes O(250,000 edges × 2 hops). At current O(E×hops) complexity: potentially 500,000 edge traversals per activation call. At 50ms target, this requires sub-100ns per edge — borderline.

**Mitigation (already partially specified):**
- Partition OntologyGraph by domain — only traverse within domain + cross-domain GENERALIZES edges
- Cache ActivationField for repeated identical fingerprints (LRU 256 slots)
- At scale: consider GPU-accelerated graph neural network for structural similarity (already present as GNN in NeuralPerceiver — could be extended)
- Hard limit: cap spreading activation at depth=2 and max 500 activated nodes — prune by activation threshold 0.1

**Action:** Add explicit node count thresholds to SystemConfig and corresponding partitioning logic to CAE. Document this as a known scaling boundary.

---

### S2: UKM SQLite write throughput at high request rates

**Risk:** SQLite in WAL mode supports ~1,000 write transactions/second. Under high API load (100+ requests/second), LearningEngine writing episodes and concept strength updates simultaneously could saturate SQLite WAL.

**Mitigation:**
- Batch writes: collect LearningEngine write operations in a write buffer; flush every 500ms or 100 items (whichever comes first)
- Separate episode writes and strength updates — episodes are bulk-appendable; strength updates can be coalesced (last write wins within a flush window)
- For proof_count: use an in-memory counter; flush to SQLite every flush cycle
- At extreme scale (>1000 req/s): replace SQLite with PostgreSQL WAL streaming — this is a backend swap, not an architecture change (UKM's MemoryStore abstraction enables this)

**Action:** Add write buffer design to UKM specification. Buffer flush must be atomic.

---

### S3: Reflection Engine failure log unbounded growth

**Risk:** At 100 req/s with 20% failure rate: 20 failures/second → 1.7M failures/day. Even with a 10,000 entry rolling window, systematic failure detection runs O(10,000) — acceptable. But log persistence in UKM needs partitioned storage.

**Mitigation:**
- Rolling in-memory window (10,000 entries) for systematic detection — as specified
- Persist to UKM as a `reflection_log` table with composite index on (domain, failure_cause, timestamp)
- Compress archives older than 7 days to binary format
- Systematic failure detection runs on indexed summary table, not raw log: `SELECT COUNT(*) FROM reflection_summary GROUP BY domain, failure_cause HAVING last_7_days_count > 5`

---

### S4: Goal Manager goal flood from aggressive Reflection

**Risk:** If Reflection Engine detects a systematic failure in domain X and creates a LEARN_CONCEPT goal, and the system is still failing in domain X while that goal is active (because the concept hasn't been learned yet), Reflection will keep creating new goals for the same domain.

**Mitigation:**
- Rate limit: max 1 new goal per (domain, failure_cause) pair per 24 hours (already specified)
- Idempotency: before creating a new goal, check if an identical goal is already ACTIVE → skip
- Add `find_similar_active_goal(goal_type, domain)` to GoalManager API

**Action:** Document this rate-limit rule in GoalManager specification and add idempotency check.

---

## 6. Architecture Validation Verdict

### Components Assessed

| Document | Sections | Completeness |
|---|---|---|
| Architecture Audit | 15 sections | Complete — source of truth |
| V4 Architecture Spec | 9 components + system layout | Complete engineering skeleton |
| V4 Cognitive Spec | 7 subsystems + pipeline + 42 types | Complete cognitive layer |
| V4 Knowledge Architecture | 11 sections | Complete (this sprint) |
| V4 Learning Architecture | 17 processes + invariants + metrics | Complete (this sprint) |
| V4 Thinking Algorithms | 14 algorithms + complexity table | Complete (this sprint) |

### Contradictions: 5 identified, 5 resolved
### Duplicated Responsibilities: 4 identified, 4 resolved
### Unnecessary Modules: 4 identified, actions defined
### Architectural Gaps: 5 identified, 5 with proposed resolutions
### Scalability Risks: 4 identified, 4 mitigated

---

## 7. Unresolved Research Questions

These questions remain open. They require either empirical testing or further design work before the affected component can be fully implemented.

---

**RQ1: Optimal spreading activation decay rate**

The Cognitive Spec specifies a decay of 0.6 per hop (score × 0.6^hop). This value was chosen as a reasonable starting point. The optimal decay rate depends on the concept graph structure, which varies per domain. Research question: what decay rate produces the best concept retrieval precision/recall tradeoff for HSCI's specific ontology structure?

**Resolution path:** Implement CAE with a configurable decay parameter. Run retrieval benchmarks across a range of values (0.3, 0.5, 0.6, 0.7, 0.8) after seeding UKM with 500+ concepts. Select by F1 score on activation recall.

---

**RQ2: Optimal CEGIS iteration count**

The system caps CEGIS at 5 iterations (SystemConfig). Is 5 the right number? Too few → missing valid solutions. Too many → slow responses and wasted Z3 time.

**Resolution path:** Run benchmark suite, measure: what fraction of solvable problems are solved at iteration 1, 2, 3, 4, 5? If 99% are solved by iteration 2, reduce cap to 3. If many require iteration 4-5, keep at 5 or increase to 7. Empirical measurement after implementation.

---

**RQ3: Skill acquisition similarity threshold**

Skill Memory specifies: "If an existing Skill has trigger pattern similarity > 0.85 with this new candidate, update existing Skill rather than creating a new one." The 0.85 threshold is a design assumption.

**Resolution path:** After acquiring 100 skills, measure: does 0.85 correctly de-duplicate similar skills without over-merging distinct skills? Adjust based on false positive and false negative de-duplication rates.

---

**RQ4: ConceptEvolutionEngine generalisation detection accuracy**

CEE detects generalisation when two concepts have entity-type Jaccard similarity > 0.7 AND structural similarity > 0.7. Both thresholds are design assumptions. A false positive generalisation (merging two concepts that should remain distinct) is a destructive action.

**Resolution path:** Before enabling automatic generalisation, run CEE in dry-run mode for 30 days. Log all proposals with is_auto=False — require human review. After manually validating 50 proposals, compute precision. Only enable automatic generalisation if precision > 0.9.

**Interim design decision:** Default CEE.auto_generalise = False in V4.0. Set to True only after threshold validation.

---

**RQ5: Neural Perceiver cold-start performance**

The NeuralPerceiver uses a GNN with 128-dim embeddings. At cold start (random weights, no training), the intent classification falls back to keyword matching. How many training examples are needed before the neural classifier outperforms keyword matching?

**Resolution path:** This was partially answered in the v3 implementation (the blend policy: keyword fallback < 20 proofs, blend 20-100, neural > 100). Validate this threshold with the V4 NeuralPerceiver architecture after the WorkingMemory migration (which changes the training input format).

---

**RQ6: Mental Model Engine world state graph accuracy over time**

The MME maintains a WorldStateGraph updated from verified proofs. Over time: does the graph converge to an accurate world model, or does it accumulate noise from low-confidence inferences? What is the expected precision of MME.query_world_state() after 1000 cycles vs 10,000 cycles?

**Resolution path:** This requires a benchmark with ground-truth world state. Create a synthetic domain with known facts and entities. Run 10,000 cycles. Measure MME node accuracy (% of nodes with correct attribute values) at cycle 100, 1000, 10000. Target: > 95% accuracy at 10,000 cycles.

---

**RQ7: Understanding Engine follow-up resolution precision**

The Understanding Engine resolves follow-up references using a "most recent entity of matching type" heuristic. This heuristic may fail for complex multi-entity conversations where multiple entities of the same type are in play.

**Resolution path:** Build a follow-up resolution test suite (50 conversation pairs with gold-standard resolutions). Measure resolution precision. If < 80%, add a more sophisticated co-reference resolution step (possibly using the spaCy NLP model's co-reference extension or the LLM parser fallback for this specific task).

---

## 8. Implementation Readiness Recommendation

### Readiness Assessment by Migration Phase

| Phase | Description | Readiness |
|---|---|---|
| Phase 1: Stabilize | ConceptCompiler, pre-compile regex, threading locks, delete dead code | **READY** — all specs complete, no open questions block Phase 1 |
| Phase 2: Data Layer | UKM SQLite, WorkingMemory, MME world state bootstrap | **READY** — gap G5 (bootstrap sequence) is now resolved in this report |
| Phase 3: Kernel | BrainKernel, SolverRegistry, CAE, TeachingProtocol, MCC | **READY with conditions** — RQ1 (CAE decay rate) and RQ2 (CEGIS count) are open but configurable; implementation can proceed with defaults |
| Phase 4: Cognitive | Understanding Engine, Skill Memory, Reflection Engine, Goal Manager | **READY with conditions** — RQ3, RQ4, RQ7 are open but they affect tuning, not architecture |
| Phase 5: Evolution | Concept Evolution Engine, auto-generalisation | **NOT YET READY** — RQ4 requires dry-run validation before auto-generalisation is enabled. CEE can be implemented with auto_generalise=False |

### Overall Recommendation

**HSCI is ready for implementation starting with Phase 1.**

The theoretical foundation is complete across six documents. All architectural contradictions are resolved. All duplicated responsibilities are clarified. The 5 architectural gaps each have concrete resolution proposals. The 7 open research questions affect tuning parameters only — they do not block implementation of any Phase 1-4 component.

The implementation must proceed in strict phase order: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5. Phase 5 (concept auto-evolution) must remain in dry-run mode until RQ4 is validated empirically.

### Conditions for Phase 5 Activation

CEE auto-generalise may be set to True only after:
1. CEE has operated in dry-run mode for ≥ 30 days
2. ≥ 50 generalisation proposals have been manually reviewed
3. Empirical precision of auto-proposals ≥ 90%
4. Rollback mechanism tested on at least 3 committed generalisations

### What Must NOT Change During Implementation

The following are frozen design decisions. No engineer may change them during implementation without a full design review:

1. The 10-stage cognitive pipeline order (as defined in this report, Section 2, C2)
2. The CEGIS loop cap of 5 iterations (adjustable via SystemConfig, but 5 is the default)
3. The ConceptCompiler AST whitelist (no new AST node types may be permitted without security review)
4. The principle that only verified knowledge enters permanent UKM storage
5. The principle that working memory never outlives its request
6. CEE auto_generalise default = False until RQ4 is resolved
