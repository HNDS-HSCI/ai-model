# HSCI V4 — Implementation Checklist

This checklist provides a step-by-step verification path for each of the 13 migration phases. Use it to track completion and verify readiness before promoting changes to production.

---

## Phase 1: Repository Stabilization
*   [ ] Delete dead files: `spec_builder.py`, `hnsds/perception/parser.py`, `pytest_runner.py`, and `self_play_engine.py` (root).
*   [ ] Add `threading.RLock` to `hnsds/learner/episode_logger.py` to prevent concurrency collisions.
*   [ ] Optimize `hnsds/brain/lobes/native_graph.py` to support batch writing.
*   *Verification Test*: Run `pytest hnsds/tests/` and verify 100% tests pass. Run concurrent writes to `EpisodeLogger` in 10 threads; verify zero exceptions.
*   *Definition of Done*: Dead files are removed; legacy tests pass; concurrent file writing is stable.

## Phase 2: Universal Knowledge Model (UKM)
*   [ ] Implement SQLite database schemas in `hsci/knowledge/sqlite_store.py`.
*   [ ] Implement the `MemoryStore` abstract interface in `hsci/knowledge/ukm.py`.
*   [ ] Write and execute the migration script `migrations/v2_to_v4.py`.
*   *Verification Test*: Query SQLite DB and compare concepts/episodes count with legacy files. Verify SQLite WAL mode is active.
*   *Definition of Done*: sqlite stores return valid concept rows; migration completes with zero data loss.

## Phase 3: Working Memory & Context
*   [ ] Create `hsci/core/working_memory.py` with the request scratchpad model.
*   [ ] Remove `last_embedding` class state variable from `NeuralPerceiver`.
*   [ ] Refactor `intent_classifier.py` to accept `context: CognitiveContext`.
*   *Verification Test*: Run concurrent request simulations in tests; verify distinct thread contexts maintain isolated embeddings.
*   *Definition of Done*: Class instances are stateless; GNN embeddings are request-scoped.

## Phase 4: Brain Kernel & 10-Stage Pipeline
*   [ ] Create the `BrainKernel` orchestrator in `hsci/core/kernel.py`.
*   [ ] Build the step transition logic for all 10 cognitive stages.
*   [ ] Deprecate `hsci/core/rir_loop.py` and route requests through `BrainKernel`.
*   *Verification Test*: Execute the basic QA test suite using `BrainKernel`; verify step durations are logged in the trace.
*   *Definition of Done*: `BrainKernel` successfully executes and returns `FinalOutput` dataclass tokens.

## Phase 5: Solver Registry & Plugins
*   [ ] Create `hsci/reasoning/solver_registry.py`.
*   [ ] Wrap the 5 verifier solvers in `hnsds/verifier/` as `DeterministicSolverPlugin` adapters.
*   [ ] Rewrite legacy solver routing in `cognitive_core.py` to use `SolverRegistry`.
*   *Verification Test*: Run the HNSDS solver test suite `pytest hnsds/verifier/` and verify all 5 solvers pass via the registry adapter.
*   *Definition of Done*: Hardcoded keyword checks are removed; solvers are dispatched dynamically.

## Phase 6: Concept Activation Engine (CAE)
*   [ ] Implement spreading activation with decay (0.6) over the SQLite `OntologyStore`.
*   [ ] Enforce the 2-hop traversal limit and minimum activation pruning threshold (0.1).
*   [ ] Create the LRU cache (256 slots) for activation fields.
*   *Verification Test*: Verify that querying a physics concept activates decay-weighted related concepts within 2 hops.
*   *Definition of Done*: Concept retrieval latency is under 15ms.

## Phase 7: Understanding Engine
*   [ ] Build co-reference resolution and follow-up grounding in `UnderstandingEngine`.
*   [ ] Implement `SemanticFrame` attributes.
*   *Verification Test*: Send follow-up conversational signals; verify pronouns are resolved to matching entity types from the previous turn.
*   *Definition of Done*: Input signals resolve to fully grounded `SemanticFrame` structures.

## Phase 8: Mental Model Engine (MME)
*   [ ] Implement the `WorldStateGraph` using the SQLite FactStore.
*   [ ] Implement fact confidence decay (`e^(-0.01 * t)`).
*   [ ] Implement the lazy decay calculation during fact query loops.
*   *Verification Test*: Set mock timestamps; verify fact confidence decays to low thresholds over simulated days.
*   *Definition of Done*: facts decay dynamically; knowledge gaps generate active Goal signals.

## Phase 9: Goal Manager & HTN Planner
*   [ ] Create `GoalManager` managing priority queues.
*   [ ] Implement the genuine `HTNPlanner` using `DECOMPOSITION_RULES` and `SkillMemory`.
*   *Verification Test*: Decompose complex multi-step tasks; verify plans match target sub-goal dependencies.
*   *Definition of Done*: HTNPlanner decomposes complex goals without cyclic loops.

## Phase 10: Reflection Engine & CEE
*   [ ] Implement the `ReflectionEngine` diagnosis decision tree.
*   [ ] Implement the CEE generalisation and specialisation logic.
*   [ ] Enforce `CEE.auto_generalise = False` by default.
*   *Verification Test*: Verify that CEE proposals are successfully written to SQLite logs for manual review.
*   *Definition of Done*: Failures are diagnosed; evolution proposals are compiled with justifications.

## Phase 11: Learning Engine
*   [ ] Refactor `LearningEngine` to commit concept strength updates to SQLite.
*   [ ] Coordinate proof-guided MLP weight updates with weight locking.
*   *Verification Test*: Verify that successful proofs increment concept strengths, while failures decrement them.
*   *Definition of Done*: Updates are committed transactionally.

## Phase 12: Teaching Protocol
*   [ ] Create `hsci/core/teaching.py` managing lesson compilation.
*   [ ] Hook up the POST `/v1/teach` API endpoint.
*   *Verification Test*: Send invalid concepts; verify that Z3 semantic validation rejects them. Send valid concepts; verify they enter `ACTIVE` status.
*   *Definition of Done*: Teaching inputs are validated syntactically and semantically before commit.

## Phase 13: Programming Domain Integration
*   [ ] Sandbox `exec` execution paths in `hnsds/synthesizer/enumerative.py` and `hsci/reasoning/synthesizer.py`.
*   [ ] Enforce the AST node whitelist for template compilation checks.
*   *Verification Test*: Attempt code injection payloads; verify execution is blocked and logged.
*   *Definition of Done*: Code synthesis runs; unauthorized system calls are blocked.
