# HSCI V4 — Implementation Phases

This document details the 13 sequential engineering phases required to execute the HSCI V4 migration. Each phase is self-contained and does not depend on unfinished future work.

---

## Phase 1: Repository Stabilization

*   **Objectives**:
    *   Clean legacy dead code to reduce complexity.
    *   Implement standard thread locks on legacy file-based databases to prevent corruption before migration.
    *   Fix the `NativeGraph` slow write performance issue.
*   **Files affected**:
    *   `hnsds/formalizer/spec_builder.py` (Delete)
    *   `hnsds/perception/parser.py` (Delete)
    *   `hnsds/verifier/pytest_runner.py` (Delete)
    *   `self_play_engine.py` (Delete)
    *   `hnsds/learner/episode_logger.py` (Add `threading.RLock`)
    *   `hnsds/brain/lobes/native_graph.py` (Implement batching)
*   **Expected duration**: 3 days
*   **Risks**:
    *   Deleting files might break legacy tests referencing them.
    *   *Mitigation*: Run grep searches to check imports before deleting; update demo scripts to import from `logic_parser.py`.
*   **Testing strategy**:
    *   Run legacy unit tests: `pytest hnsds/tests/` and verify 100% pass rates.
    *   Execute concurrent write stress tests against `EpisodeLogger` to verify lock safety.
*   **Rollback strategy**:
    *   Revert files using `git checkout` or restore deleted files from Git history.
*   **Completion criteria**:
    *   All identified dead code files are deleted.
    *   Zero compile-time or import errors in tests.
    *   Concurrent writes to legacy logs do not raise exceptions.

---

## Phase 2: Universal Knowledge Model (UKM)

*   **Objectives**:
    *   Create the unified SQLite database schema matching the V4 Knowledge Architecture.
    *   Write a migration script to import all legacy JSON and JSONL data files into SQLite.
    *   Implement the SQLite-backed stores (`ConceptStore`, `OntologyStore`, `EpisodeStore`, `WeightStore`).
*   **Files affected**:
    *   Create `hsci/knowledge/ukm.py`
    *   Create `hsci/knowledge/sqlite_store.py`
    *   Create `migrations/v2_to_v4.py`
    *   `hsci/knowledge/concept_library.py` (Deprecate)
    *   `hsci/knowledge/ontology_graph.py` (Deprecate)
    *   `hsci/knowledge/episode_memory.py` (Deprecate)
*   **Expected duration**: 5 days
*   **Risks**:
    *   SQLite database lock contention during concurrent weight serialization and concept updates.
    *   *Mitigation*: Enforce SQLite WAL (Write-Ahead Logging) mode and implement an asynchronous write-buffering mechanism.
*   **Testing strategy**:
    *   Unit test database schema migrations.
    *   Verify data parity between source JSON files and migrated SQLite tables.
    *   Test transactional atomicity: verify a failed concept insert rolls back its associated ontology edges.
*   **Rollback strategy**:
    *   Delete the SQLite file `hsci_v4.db` and revert to reading from the original read-only JSON backups.
*   **Completion criteria**:
    *   Unified SQLite database is successfully initialized.
    *   All concept and episode logs are migrated with 100% record parity.
    *   Write buffer flush operations commit atomic transactions.

---

## Phase 3: Working Memory (Session Isolation)

*   **Objectives**:
    *   Implement the request-scoped `WorkingMemory` class.
    *   Remove stateful variables (`self.last_embedding`) from `NeuralPerceiver` and `intent_classifier.py`.
    *   Add the `CognitiveContext` parameter to all layer classes to propagate state.
*   **Files affected**:
    *   Create `hsci/core/working_memory.py`
    *   `hsci/neural/perceiver.py` (Refactor methods to accept context)
    *   `hsci/neural/intent_classifier.py` (Refactor methods)
    *   `hsci/core/data_types.py` (Introduce `CognitiveContext`)
*   **Expected duration**: 4 days
*   **Risks**:
    *   High refactoring footprint; passing `context` through every method signature could break interface boundaries.
    *   *Mitigation*: Keep helper wrappers with backward-compatible method signatures where context is optional and defaults to a fresh instance.
*   **Testing strategy**:
    *   Run parallel classification requests in multiple threads; verify that distinct `WorkingMemory` instances maintain isolated embeddings.
*   **Rollback strategy**:
    *   Revert context-passing changes via Git.
*   **Completion criteria**:
    *   `NeuralPerceiver` class is completely stateless.
    *   Type signatures of all pipeline layers accept a unified `CognitiveContext`.

---

## Phase 4: Brain Kernel

*   **Objectives**:
    *   Implement the unified `BrainKernel` orchestrator.
    *   Build the 10-stage execution pipeline structure, managing transitions through the cognitive stages.
    *   Expose the main process entry point to replace `RIRLoop`.
*   **Files affected**:
    *   Create `hsci/core/kernel.py`
    *   `hsci/core/rir_loop.py` (Mark as deprecated, route to kernel)
*   **Expected duration**: 5 days
*   **Risks**:
    *   Changes to orchestration logic might introduce control-flow bugs.
    *   *Mitigation*: Implement the orchestrator as a step-by-step state machine with logging hooks at every transition.
*   **Testing strategy**:
    *   Run test cases for each execution stage independently using mock inputs.
    *   Verify stage timing and transition trace logging.
*   **Rollback strategy**:
    *   Redirect imports back to the V3 `RIRLoop`.
*   **Completion criteria**:
    *   `BrainKernel` executes the complete 10-stage sequence.
    *   Request executions return structured `FinalOutput` dataclass tokens.

---

## Phase 5: Solver Registry & Solver Plugins

*   **Objectives**:
    *   Create the `SolverRegistry` locator.
    *   Wrap all five HNSDS solvers as plugins implementing `AbstractSolver`.
    *   Implement the dispatch logic to route sub-goals to solver plugins.
*   **Files affected**:
    *   Create `hsci/reasoning/solver_registry.py`
    *   Create `hsci/reasoning/plugins/` (Wrap HNSDS verifiers)
    *   `hnsds/brain/cognitive_core.py` (Reroute to registry)
*   **Expected duration**: 5 days
*   **Risks**:
    *   Legacy solver outputs may not match V4 `Expression` type expectations.
    *   *Mitigation*: Write clean adapters that coerce solver outputs to V4 dataclasses.
*   **Testing strategy**:
    *   Execute the full HNSDS benchmark task suite (`tasks.json`) against the new `SolverRegistry` runner. Verify 100% parity.
*   **Rollback strategy**:
    *   Fall back to legacy `cognitive_core.py` routing checks.
*   **Completion criteria**:
    *   All five benchmark solvers successfully run as registry plugins.
    *   All benchmark domains pass with identical or improved execution latency.

---

## Phase 6: Concept Activation Engine (CAE)

*   **Objectives**:
    *   Implement spreading activation with the 0.6 decay rate over the `OntologyStore`.
    *   Add an LRU cache (256 slots) for activation field results.
    *   Define active concept pruning thresholds (minimum activation 0.1).
*   **Files affected**:
    *   Refactor `hsci/knowledge/knowledge_base.py` -> `hsci/knowledge/concept_activation.py`
*   **Expected duration**: 4 days
*   **Risks**:
    *   Spreading activation traversal causing latency spikes on deep graphs.
    *   *Mitigation*: Hard cap traversal depth at 2 hops and enforce maximum concept limits (max 500 nodes).
*   **Testing strategy**:
    *   Verify concept retrieval precision/recall ratios using configured decay values (0.3, 0.5, 0.6, 0.7).
*   **Rollback strategy**:
    *   Fallback to direct name/intent matches.
*   **Completion criteria**:
    *   Activation traversal returns decay-weighted concept lists.
    *   Average CAE retrieval latency is under 15ms.

---

## Phase 7: Understanding Engine

*   **Objectives**:
    *   Build the `UnderstandingEngine` for Stage 0.5 semantic grounding.
    *   Add co-reference resolution and follow-up context parsing.
    *   Implement `SemanticFrame` generation and `ClarificationRequest` interruption rules.
*   **Files affected**:
    *   Create `hsci/language/understanding.py`
    *   `hsci/language/bridge.py` (Update calls)
*   **Expected duration**: 4 days
*   **Risks**:
    *   Incorrect co-reference mappings lead to nonsensical input interpretations.
    *   *Mitigation*: Restrict automatic co-reference resolution to the most recent entity of a matching type; generate clarification requests if ambiguous.
*   **Testing strategy**:
    *   Run test scripts containing 50 conversation pairs with nested pronoun references. Verify grounding accuracy.
*   **Rollback strategy**:
    *   Disable context resolution; parse every user input as an isolated query.
*   **Completion criteria**:
    *   Inputs yield fully resolved `SemanticFrame` attributes.
    *   Ambiguous inputs trigger appropriate clarification structures.

---

## Phase 8: Mental Model Engine (MME)

*   **Objectives**:
    *   Implement the `WorldStateGraph` using the SQLite-backed EAV FactStore.
    *   Implement fact confidence decay rules (`e^(-0.01 * t)`).
    *   Build the `SelfModel` aggregator for tracking system proof counts.
*   **Files affected**:
    *   Create `hsci/knowledge/mental_model.py`
*   **Expected duration**: 4 days
*   **Risks**:
    *   Fact confidence decay running continuously degrades database performance.
    *   *Mitigation*: Compute decay lazily during query execution instead of running batch updates.
*   **Testing strategy**:
    *   Verify fact confidence levels decay correctly over mock timeline steps.
*   **Rollback strategy**:
    *   Use non-decaying permanent attributes.
*   **Completion criteria**:
    *   World state facts update dynamically on successful verifications.
    *   Decayed facts correctly trigger knowledge gap warnings.

---

## Phase 9: Goal Manager & Planner

*   **Objectives**:
    *   Build the `GoalManager` prioritizing priority goal queues.
    *   Create the genuine Hierarchical Task Network (`HTNPlanner`) guided by `DECOMPOSITION_RULES` and `SkillMemory`.
*   **Files affected**:
    *   Create `hsci/reasoning/goal_manager.py`
    *   `hsci/reasoning/htn_planner.py` (Rewrite)
*   **Expected duration**: 5 days
*   **Risks**:
    *   Planner enters infinite decomposition loops if rules contain cyclic definitions.
    *   *Mitigation*: Enforce structural validation checks on planning rule trees to prevent cycles.
*   **Testing strategy**:
    *   Test decompositions across all four canonical AxiomTypes.
*   **Rollback strategy**:
    *   Fallback to static procedural step mappings.
*   **Completion criteria**:
    *   Planner correctly maps complex intents to ordered sub-goal sequences.
    *   `GoalManager` successfully resolves priority goals.

---

## Phase 10: Reflection Engine & CEE

*   **Objectives**:
    *   Implement the `ReflectionEngine` using the diagnosis decision tree.
    *   Create `ConceptEvolutionEngine` (CEE) for structural concept mergers (Generalisation) and splits (Specialisation).
    *   Implement counterfactual reasoning loops executing Z3 proof comparisons.
*   **Files affected**:
    *   Create `hsci/learning/reflection.py`
    *   Create `hsci/learning/evolution.py`
*   **Expected duration**: 6 days
*   **Risks**:
    *   Incorrect generalisations (merging separate concepts) can corrupt the knowledge database.
    *   *Mitigation*: Set CEE auto-generalisation to `False` by default (dry-run mode). Require manual approval before applying mergers.
*   **Testing strategy**:
    *   Inject artificial failures (e.g., incorrect formulas) and verify that reflection diagnoses the failure correctly.
*   **Rollback strategy**:
    *   Disable automatic evolution; restrict database writes to explicit updates.
*   **Completion criteria**:
    *   Failures yield actionable correction proposals.
    *   Auto-evolution proposals are logged with detailed justification.

---

## Phase 11: Learning Engine

*   **Objectives**:
    *   Refactor the `LearningEngine` to coordinate proof-guided neural weight updates and concept database commits.
    *   Implement strengthening and weakening updates asynchronously.
*   **Files affected**:
    *   `hsci/learning/learning_engine.py` (Refactor)
    *   `hsci/learning/proof_guided_updater.py` (Refactor)
*   **Expected duration**: 4 days
*   **Risks**:
    *   Slow neural updates degrade cycle latency times.
    *   *Mitigation*: Run neural training steps asynchronously on a background helper thread.
*   **Testing strategy**:
    *   Verify concept strength changes match mathematical expectations after successes or failures.
*   **Rollback strategy**:
    *   Disable neural feedback updates; run in deterministic validation-only mode.
*   **Completion criteria**:
    *   Verification outcomes trigger appropriate strength updates in the database.
    *   Weight updates successfully run without blocking request loops.

---

## Phase 12: Teaching Protocol

*   **Objectives**:
    *   Implement `TeachingProtocol` managing lesson compilation and ingestion validation.
    *   Add HTTP endpoints for interactive human teaching.
*   **Files affected**:
    *   Create `hsci/core/teaching.py`
    *   `brain_api.py` (Add `/v1/teach` routing endpoints)
*   **Expected duration**: 3 days
*   **Risks**:
    *   Ingesting incorrect teaching formulas corrupts Z3 solver logic.
    *   *Mitigation*: Run syntactic AST parsing and Z3 semantic validation checks on all candidate formulas before database commit.
*   **Testing strategy**:
    *   Simulate teaching calls with both valid and invalid formulas. Verify reject behaviors.
*   **Rollback strategy**:
    *   Disable teaching API endpoints.
*   **Completion criteria**:
    *   Valid lesson inputs insert active concept rows into SQLite.
    *   Invalid inputs return structured validation warnings.

---

## Phase 13: Programming Domain Integration

*   **Objectives**:
    *   Sandbox `exec` and `eval` execution paths inside the code synthesis engine.
    *   Refactor code generation to run in an isolated environment.
*   **Files affected**:
    *   `hnsds/synthesizer/enumerative.py` (Sandbox)
    *   `hsci/reasoning/synthesizer.py` (Sandbox)
*   **Expected duration**: 4 days
*   **Risks**:
    *   Execution sandboxing blocks legitimate synthesis operations.
    *   *Mitigation*: Restrict execution calls using a secure sub-process runner or strict AST validation whitelists.
*   **Testing strategy**:
    *   Attempt code injections (e.g., executing system calls). Verify execution blocks.
*   **Rollback strategy**:
    *   Restore previous execution hooks with warn-only flags.
*   **Completion criteria**:
    *   Code generation runs correctly.
    *   Arbitrary code executions are blocked and logged.
