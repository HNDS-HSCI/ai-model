# HSCI V4 — Module Classification

This document classifies every codebase module into exactly one of four categories: **KEEP**, **MODIFY**, **REPLACE**, or **REMOVE**. This inventory ensures no legacy code is left unmanaged or unintegrated.

---

## 1. Module Classification Summary Table

| Module/File Path | Category | Rationale & V4 Target |
|---|---|---|
| **HNSDS Solvers & Verifiers** | | |
| [hnsds/verifier/graph_solver.py](file:///C:/Work/P/ai-model/hnsds/verifier/graph_solver.py) | **KEEP** | Standard topological sort and cycle check. Solid, reusable, and deterministic. |
| [hnsds/verifier/dependency_solver.py](file:///C:/Work/P/ai-model/hnsds/verifier/dependency_solver.py) | **KEEP** | Correctly wraps graph solver for package resolution. Fully verified. |
| [hnsds/verifier/state_machine_solver.py](file:///C:/Work/P/ai-model/hnsds/verifier/state_machine_solver.py) | **KEEP** | Deterministic DFA trace verification. No changes required. |
| [hnsds/verifier/constraint_matrix_solver.py](file:///C:/Work/P/ai-model/hnsds/verifier/constraint_matrix_solver.py) | **KEEP** | Correctly assertions resources to Z3. Pure solver logic. |
| [hnsds/verifier/requirements_solver.py](file:///C:/Work/P/ai-model/hnsds/verifier/requirements_solver.py) | **KEEP** | Clean Z3 Boolean model checker for feature sets. Fully verified. |
| **HNSDS Legacy Core** | | |
| [hnsds/brain/cognitive_core.py](file:///C:/Work/P/ai-model/hnsds/brain/cognitive_core.py) | **MODIFY** | Legacy entry point (`HyperSymbolicBrain`). Replace hardcoded `if/elif` with `SolverRegistry` dispatch. Eventually deprecated and replaced by `BrainKernel`. |
| [hnsds/brain/lobes/cognitive_lobe.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/cognitive_lobe.py) | **MODIFY** | Clean up `CognitiveAwareness`. Extract math string parsing; fix linear scans; add thread-safe read locks. |
| [hnsds/brain/lobes/native_bayes.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_bayes.py) | **MODIFY** | Add state serialization (`save_state`/`load_state`) and support query priors. |
| [hnsds/brain/lobes/native_engine.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_engine.py) | **MODIFY** | Remove `print` statements; retain Z3 CSP engine logic; wrap with clean API. |
| [hnsds/brain/lobes/native_graph.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_graph.py) | **MODIFY** | Fix the "write-per-add" disk IO performance issue. Use batch commits and check-before-write. |
| [hnsds/brain/lobes/native_neural_lobe.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_neural_lobe.py) | **KEEP** | Reusable adapter class that bridges the legacy V2 neural classifications. |
| [hnsds/brain/lobes/native_planner.py](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_planner.py) | **KEEP** | Simple Jaccard-based concept matching. Valid fallback. |
| [hnsds/formalizer/spec_builder.py](file:///C:/Work/P/ai-model/hnsds/formalizer/spec_builder.py) | **REMOVE** | Dead code. Imports sympy at the bottom of the file; has zero active callers. |
| [hnsds/learner/episode_logger.py](file:///C:/Work/P/ai-model/hnsds/learner/episode_logger.py) | **MODIFY** | Legacy logger. Add file write locks to prevent concurrent corruption. Reroute to UKM database. |
| [hnsds/perception/logic_parser.py](file:///C:/Work/P/ai-model/hnsds/perception/logic_parser.py) | **MODIFY** | Pre-compile all regular expressions; add full type annotations; integrate with WorkingMemory. |
| [hnsds/perception/parser.py](file:///C:/Work/P/ai-model/hnsds/perception/parser.py) | **REMOVE** | Legacy regex parser. Redundant with `logic_parser.py` and HSCI NLP parser engines. |
| [hnsds/planner/htn_planner.py](file:///C:/Work/P/ai-model/hnsds/planner/htn_planner.py) | **MODIFY** | Misnomer (not a real HTN planner, just a 3-branch switch). Rename to `TaskDecomposer` and route through reasoning engine. |
| [hnsds/synthesizer/enumerative.py](file:///C:/Work/P/ai-model/hnsds/synthesizer/enumerative.py) | **MODIFY** | Critical security issue. Sandbox the dynamic `exec()` execution path using AST restrictions or a sandboxed runner. |
| [hnsds/synthesizer/generative.py](file:///C:/Work/P/ai-model/hnsds/synthesizer/generative.py) | **MODIFY** | Sandbox `exec()` paths and clean up generation outputs. |
| [hnsds/verifier/pytest_runner.py](file:///C:/Work/P/ai-model/hnsds/verifier/pytest_runner.py) | **REMOVE** | Obsolete helper utility for launching subprocess tests. |
| [hnsds/verifier/z3_interface.py](file:///C:/Work/P/ai-model/hnsds/verifier/z3_interface.py) | **MODIFY** | Sandbox Z3 string evaluation (`eval`). Reroute math solving to `Z3VerificationEngine`. |
| [hnsds/mental_model.py](file:///C:/Work/P/ai-model/hnsds/mental_model.py) | **MODIFY** | Delegate tracking to the new `MentalModelEngine`. |
| [hnsds/mental_model_chat.py](file:///C:/Work/P/ai-model/hnsds/mental_model_chat.py) | **REMOVE** | Legacy developer REPL console script. |
| [hnsds/mental_model_patch.py](file:///C:/Work/P/ai-model/hnsds/mental_model_patch.py) | **REMOVE** | Obsolete patch utility script. |
| [hnsds/orchestrator.py](file:///C:/Work/P/ai-model/hnsds/orchestrator.py) | **REMOVE** | Obsolete runner script. |
| **HSCI Core & Infrastructure** | | |
| [hsci/core/config.py](file:///C:/Work/P/ai-model/hsci/core/config.py) | **MODIFY** | Add `SystemConfig` variables for decay rate (0.6), CEGIS limit (5), and timeouts (5s). |
| [hsci/core/data_types.py](file:///C:/Work/P/ai-model/hsci/core/data_types.py) | **MODIFY** | Extend the dataclasses to include the 42 typed interfaces specified in the V4 Cognitive Specification. |
| [hsci/core/rir_loop.py](file:///C:/Work/P/ai-model/hsci/core/rir_loop.py) | **REPLACE** | Replaced by the 10-stage RIR loop defined in `BrainKernel`. |
| **HSCI Neural Cortex** | | |
| [hsci/neural/encoder.py](file:///C:/Work/P/ai-model/hsci/neural/encoder.py) | **KEEP** | Correct GNN node and relation encoder. |
| [hsci/neural/entity_extractor.py](file:///C:/Work/P/ai-model/hsci/neural/entity_extractor.py) | **KEEP** | Correct regex-based entity matcher. |
| [hsci/neural/intent_classifier.py](file:///C:/Work/P/ai-model/hsci/neural/intent_classifier.py) | **MODIFY** | Implement the fallback policy: keyword matching (<20 proofs), blended (20-100), neural-only (>100). |
| [hsci/neural/native_neural_classifier.py](file:///C:/Work/P/ai-model/hsci/neural/native_neural_classifier.py) | **KEEP** | Thread-safe neural MLP. Core classifier. |
| [hsci/neural/perceiver.py](file:///C:/Work/P/ai-model/hsci/neural/perceiver.py) | **MODIFY** | Critical concurrency bug. Remove `last_embedding` state variable from class instance; store request embeddings in `WorkingMemory`. |
| [hsci/neural/relationship_detector.py](file:///C:/Work/P/ai-model/hsci/neural/relationship_detector.py) | **KEEP** | Safe relationship extractor. |
| [hsci/neural/text_feature_encoder.py](file:///C:/Work/P/ai-model/hsci/neural/text_feature_encoder.py) | **KEEP** | Solid feature extraction logic. |
| **HSCI Knowledge Systems** | | |
| [hsci/knowledge/concept_library.py](file:///C:/Work/P/ai-model/hsci/knowledge/concept_library.py) | **REPLACE** | Replaced by the SQLite-backed `ConceptStore` under `UniversalKnowledgeModel`. |
| [hsci/knowledge/episode_memory.py](file:///C:/Work/P/ai-model/hsci/knowledge/episode_memory.py) | **REPLACE** | Replaced by the SQLite-backed `EpisodeStore` under `UniversalKnowledgeModel` (FTS5). |
| [hsci/knowledge/knowledge_base.py](file:///C:/Work/P/ai-model/hsci/knowledge/knowledge_base.py) | **REPLACE** | Replaced by the `ConceptActivationEngine` (CAE). Retained only as a deprecated delegate. |
| [hsci/knowledge/ontology_graph.py](file:///C:/Work/P/ai-model/hsci/knowledge/ontology_graph.py) | **REPLACE** | Replaced by the SQLite-backed `OntologyStore` under `UniversalKnowledgeModel`. |
| **HSCI Reasoning & Verification** | | |
| [hsci/language/bridge.py](file:///C:/Work/P/ai-model/hsci/language/bridge.py) | **MODIFY** | Coordinate parsing with `UnderstandingEngine` for follow-ups and context mapping. |
| [hsci/language/llm_parser.py](file:///C:/Work/P/ai-model/hsci/language/llm_parser.py) | **KEEP** | Valid fallback parser (unused in native, but kept as interface). |
| [hsci/language/spacy_parser.py](file:///C:/Work/P/ai-model/hsci/language/spacy_parser.py) | **KEEP** | Standard SpaCy NLP extractor. |
| [hsci/learning/concept_extractor.py](file:///C:/Work/P/ai-model/hsci/learning/concept_extractor.py) | **MODIFY** | Adapt concept extraction to construct V4 concept structures and SQLite insertion parameters. |
| [hsci/learning/learning_engine.py](file:///C:/Work/P/ai-model/hsci/learning/learning_engine.py) | **MODIFY** | Incorporate transactional updates, `ConceptEvolutionEngine` triggers, and skill consolidation. |
| [hsci/learning/proof_guided_updater.py](file:///C:/Work/P/ai-model/hsci/learning/proof_guided_updater.py) | **MODIFY** | Reroute PyTorch weight gradient step hooks through the `UKM.WeightStore` transaction locks. |
| [hsci/reasoning/concept_composer.py](file:///C:/Work/P/ai-model/hsci/reasoning/concept_composer.py) | **MODIFY** | Update to interact with `SolverRegistry` and retrieve concepts via the CAE. |
| [hsci/reasoning/htn_planner.py](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py) | **REPLACE** | Replaced by genuine hierarchical task network planner utilizing explicit `DECOMPOSITION_RULES` and `SkillMemory`. |
| [hsci/reasoning/reasoning_engine.py](file:///C:/Work/P/ai-model/hsci/reasoning/reasoning_engine.py) | **MODIFY** | Adapt reasoning step composition to fetch skills and coordinate with the `SolverRegistry`. |
| [hsci/reasoning/solution_builder.py](file:///C:/Work/P/ai-model/hsci/reasoning/solution_builder.py) | **MODIFY** | Align with composed Z3 expressions and WorkingMemory variable bindings. |
| [hsci/reasoning/synthesizer.py](file:///C:/Work/P/ai-model/hsci/reasoning/synthesizer.py) | **MODIFY** | Sandbox code execution blocks. |
| [hsci/reasoning/universal_concept_engine.py](file:///C:/Work/P/ai-model/hsci/reasoning/universal_concept_engine.py) | **REPLACE** | Replaced and wrapped by the kernel-level `TeachingProtocol`. |
| [hsci/reasoning/universal_math_engine.py](file:///C:/Work/P/ai-model/hsci/reasoning/universal_math_engine.py) | **MODIFY** | Register as a solver plugin under `SolverRegistry`. |
| [hsci/reasoning/universal_physics_engine.py](file:///C:/Work/P/ai-model/hsci/reasoning/universal_physics_engine.py) | **MODIFY** | Register as a solver plugin under `SolverRegistry`. |
| [hsci/response/conversation_manager.py](file:///C:/Work/P/ai-model/hsci/response/conversation_manager.py) | **MODIFY** | Delegate turn storage to UKM SQLite. Manage session persistence through the MCC. |
| [hsci/response/response_bridge.py](file:///C:/Work/P/ai-model/hsci/response/response_bridge.py) | **MODIFY** | Adapt responses to output formal proof summaries, calibrated confidence, and handle clarification events. |
| [hsci/self_play/engine.py](file:///C:/Work/P/ai-model/hsci/self_play/engine.py) | **MODIFY** | GoalManager is the sole authority for SelfPlay targets. Remove independent weak concept scanning; read target queue from GoalManager. |
| [hsci/self_play/hypothesis_builder.py](file:///C:/Work/P/ai-model/hsci/self_play/hypothesis_builder.py) | **MODIFY** | Implement Algorithm 8: Hypothesis Generation. |
| [hsci/symbolic/z3_templates.py](file:///C:/Work/P/ai-model/hsci/symbolic/z3_templates.py) | **MODIFY** | Enforce AST white-listing for z3 templates. |
| [hsci/symbolic/z3_verifier.py](file:///C:/Work/P/ai-model/hsci/symbolic/z3_verifier.py) | **MODIFY** | Re-engineer as `Z3VerificationEngine`. Implement the CEGIS loop with 5 iterations and verification repair. |
| **HSCI Support and Training** | | |
| [hsci/training/coding_trainer.py](file:///C:/Work/P/ai-model/hsci/training/coding_trainer.py) | **KEEP** | Standard training loop for coding. |
| [hsci/training/evaluation_metrics.py](file:///C:/Work/P/ai-model/hsci/training/evaluation_metrics.py) | **KEEP** | Utility metrics. |
| [hsci/training/math_trainer.py](file:///C:/Work/P/ai-model/hsci/training/math_trainer.py) | **KEEP** | Standard training loop for math. |
| [hsci/training/native_trainer.py](file:///C:/Work/P/ai-model/hsci/training/native_trainer.py) | **KEEP** | Standard training loop. |
| [hsci/training/transfer_tester.py](file:///C:/Work/P/ai-model/hsci/training/transfer_tester.py) | **KEEP** | Testing helper. |
| [hsci/training/weight_persistence.py](file:///C:/Work/P/ai-model/hsci/training/weight_persistence.py) | **REPLACE** | Replaced by `UKM.WeightStore`. |
| **System Utilities & Root Scripts** | | |
| [brain_api.py](file:///C:/Work/P/ai-model/brain_api.py) | **MODIFY** | FastAPI application layer. Needs basic token authentication, session lifecycle endpoints, and must route requests through the `BrainKernel` instead of `RIRLoop`. |
| [hsci_cli.py](file:///C:/Work/P/ai-model/hsci_cli.py) | **MODIFY** | Update to run benchmarks and diagnostic tests using the V4 `BrainKernel` runner. |
| [initialize_brain.py](file:///C:/Work/P/ai-model/initialize_brain.py) | **REPLACE** | Replaced by the V4 UKM bootstrap script (which handles migrations and seeds primordial concepts from `metaphysical_blueprint.json` into SQLite). |
| [self_play_engine.py](file:///C:/Work/P/ai-model/self_play_engine.py) | **REMOVE** | Legacy duplicate script. The active self-play script runs in `hsci/self_play/engine.py`. |

---

## 2. In-Depth Justifications for Critical Classifications

### 2.1 Why `hsci/core/rir_loop.py` is classified as **REPLACE**
The V3 `RIRLoop` is a 7-layer pipeline that is hardcoded to orchestrate actions in a fixed sequence. The V4 Cognitive Specification changes the pipeline to a **10-stage execution flow**, introducing intermediate cognitive structures such as the `UnderstandingEngine`, `MentalModelEngine`, and `SkillMemory`. Rewriting the `RIRLoop` in-place would introduce massive regression risks because of structural differences. Replacing it with a clean `BrainKernel` that operates in a modular stage execution manner is cleaner and safer.

### 2.2 Why `hsci/knowledge/` files are classified as **REPLACE**
V3 knowledge persistence is a major source of technical debt (fragmented into separate memory files with no concurrency control). V4 implements the `UniversalKnowledgeModel` (UKM) as a unified transactional data layer. Modifying the in-memory dictionary concepts (`concept_library.py`) to connect to SQL queries would create a highly coupled hybrid model. Instead, replacing these modules with clear SQLite-backed database stores (`ConceptStore`, `OntologyStore`, `EpisodeStore`, `WeightStore`) ensures atomic, thread-safe transactions and query performance via indices.

### 2.3 Why `hnsds/verifier/` solvers are classified as **KEEP**
The deterministic verifiers (such as `GraphSolver` and `RequirementsSolver`) are mathematically sound and have 100% test coverage. They operate as pure functional algorithms, mapping static inputs to verified outputs. They do not contain any cognitive routing, memory references, or external state. Preserving them as-is ensures that the core verification capabilities of HSCI are not altered, maintaining a 100% benchmark score on deterministic tasks.

### 2.4 Why `hnsds/formalizer/spec_builder.py` is classified as **REMOVE**
This file is dead code that imports `sympy` and is not called by any active pipeline, test runner, or benchmark script. Removing it reduces dependencies and speeds up import times.
