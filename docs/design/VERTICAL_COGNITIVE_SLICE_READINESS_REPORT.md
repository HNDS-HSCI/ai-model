# HSCI V4 — Vertical Cognitive Slice Readiness Report

**Report Type**: System Reality Audit (No Implementation)
**Date**: 2026-08-08
**Scope**: Determine the REAL current state of the repository and the smallest work needed to run one end-to-end cognitive vertical slice.
**Author**: Autonomous audit session
**Status**: Complete — awaiting further instructions. No production code written.

> This document was produced by reading and executing the actual repository code. Where a claim is made, it is grounded in a file, a demo run, or a test run — not in documentation prose.

---

## 1. Executive Summary

The repository contains **two parallel, non-converged cognitive stacks**:

1. **The V3 "RIRLoop" stack** — the only stack actually wired to a runtime entry point. `brain_api.py` (FastAPI) and both CLIs (`hsci_cli.py`, `hsci/cli/main.py`) instantiate `hsci/core/rir_loop.py::RIRLoop`. This stack is executable and is the deployed application. It targets *math/physics/finance/geometry/code/logic* symbolic problems with Z3 verification — **not** conceptual "explain" questions.

2. **The V4 "BrainKernel + UKM" stack** — the stack that matches the historical target architecture (Understanding → KnowledgeManager → Concept Activation → Workspace → Reasoning → Answer Generation). Every one of its cognitive engines **exists as real, tested code** and the four core engines **execute end-to-end today** — but **only inside `demo_*.py` scripts**. They are **not** wired to any runtime entry point.

The critical structural finding: **`BrainKernel` (`hsci/core/kernel.py`) is a hollow shell.** Its 10 pipeline stages are all `ShellStage` placeholders that call `time.sleep(0.001)` and return a hardcoded `"conversational_response"`. The constitution names `BrainKernel` as the authoritative orchestrator, but the real orchestrator in production is `RIRLoop`, and `BrainKernel` orchestrates nothing.

**Vertical slice verdict for "Explain what a Java interface is":**
- The **V4 engines can already perform steps 1, 2, 3, 5, 6, 7, 8, 9, 11** of the target scenario in isolation (proven by running `demo_answer_generation.py`).
- The slice **does not run through any callable runtime** because nothing wires the four V4 engines together outside demo scripts.
- The slice **would return an empty/degraded answer** for the Java-interface question specifically, because the "Interface"/"Java Interface" concept is **not seeded** into the UKM `ConceptStore`; concept resolution only matches concepts already present in the store.
- **Formal Z3 verification (step 10) is not connected** to the V4 conceptual path at all.

**The smallest missing implementation is small**: (a) one thin orchestration facade that assembles the already-working four engines over a UKM instance, and (b) a canonical knowledge seed for the demonstrator concept(s). No new engine needs to be written. No SCG-L5 / HTN / Z3 / SkillGraph component needs to change.

---

## 2. Actual Repository State

### 2.1 Two stacks, one runtime

| Concern | V3 stack (LIVE) | V4 stack (target) |
|---|---|---|
| Orchestrator | `RIRLoop` (`hsci/core/rir_loop.py`) — real | `BrainKernel` (`hsci/core/kernel.py`) — **shell placeholders** |
| Entry points | `brain_api.py`, `hsci_cli.py`, `hsci/cli/main.py` | none (only `demo_*.py`) |
| Knowledge store | `KnowledgeBase` + `concept_library` (in-memory/JSON) | `KnowledgeManager` → `ConceptStore` → `ConceptRepository` → `SQLiteProvider` (UKM) |
| Parsing | `LanguageBridge` + `NeuralPerceiver` | `UnderstandingEngine` |
| Retrieval/activation | `KnowledgeBase.query()` | `ConceptActivationEngine` (spreading activation) |
| Reasoning | `ReasoningEngine` (legacy, HTN + solvers) | `CognitiveReasoningEngine` (rule-based graph inference) |
| Verification | `Z3VerificationEngine` (CEGIS repair loop) — connected | none in the V4 conceptual path |
| Answer | `ResponseBridge` | `AnswerGenerationEngine` |
| Learning | `LearningEngine` + self-play — connected | `LearningEngine` present but not in V4 conceptual path |

Note: `hsci/reasoning/reasoning_engine.py` contains **both** classes — `CognitiveReasoningEngine` (V4, line 186) and the legacy `ReasoningEngine` (line 323, used by RIRLoop). They share a file but are different engines.

### 2.2 Constitutional drift (documented, not corrected here)

The `ARCHITECTURE_CONSTITUTION.md` declares `BrainKernel` + UKM as the two immutable structural blocks and a strict 10-stage pipeline. In reality:
- The live runtime bypasses `BrainKernel` entirely (uses `RIRLoop`).
- `BrainKernel`'s 10 stages are placeholders (`ShellStage.execute` → `time.sleep`).
- Tenet 2.1 ("Z3 is the final arbiter, no unverified fact persists") is **not** enforced in the V4 conceptual path — `CognitiveReasoningEngine` "verifies" only via internal consistency checks (circular-reasoning and contradiction detection), never Z3.

Per AGENT.md §3.1 this drift is recorded here for user awareness; **no corrective code is written in this audit.**

---

## 3. Existing Runtime Call Graph (from code, not docs)

### 3.1 LIVE path (what actually runs in production)

```
HTTP POST /process  (brain_api.py)
  └─ RIRLoop.process_internal(stimulus)              hsci/core/rir_loop.py
       ├─ LanguageBridge.parse()                     hsci/language/bridge.py
       ├─ [intercept] universal_concept.can_learn()  hsci/reasoning/universal_concept_engine.py
       ├─ NeuralPerceiver.perceive()                 hsci/neural/perceiver.py
       ├─ KnowledgeBase.query()                      hsci/knowledge/knowledge_base.py
       ├─ ReasoningEngine.reason()  (legacy)         hsci/reasoning/reasoning_engine.py:323
       │    └─ HTNPlanner / SolverRegistry / SkillGraph
       ├─ CEGIS loop x5:
       │    └─ Z3VerificationEngine.verify()          hsci/symbolic/z3_verifier.py
       │    └─ ReasoningEngine.repair()
       ├─ ReflectionEngine.reflect_verification_failure()  hsci/reasoning/reflection_engine.py
       ├─ LearningEngine.learn()                      hsci/learning/learning_engine.py
       ├─ SkillUtilityStore / SkillLifecycleManager   hsci/memory/*
       └─ ResponseBridge.generate()                   hsci/response/response_bridge.py
  + background: SelfPlayEngine thread (prototype/hsci_perception/self_play_engine.py)
```

`BrainKernel` does **not** appear anywhere in this graph.

### 3.2 TARGET V4 path (exists ONLY inside demo scripts)

```
demo_answer_generation.py  /  demo_reasoning_engine.py
  └─ SQLiteProvider + SchemaMigration            hsci/core/storage.py  (UKM)
  └─ ConceptRepository → ConceptStore → KnowledgeManager
  └─ CognitiveContext(request_id, session_id, stimulus)   hsci/core/kernel.py
       ├─ UnderstandingEngine.understand(text, ctx)  → UnderstandingResult
       ├─ ConceptActivationEngine.activate_concepts(seed_concepts, ctx) → ActivatedSet
       ├─ (workspace = plain list of resolved Concept objects — no builder class)
       ├─ CognitiveReasoningEngine.reason(concepts, ctx, ReasoningContext) → ReasoningResult
       └─ AnswerGenerationEngine.generate(reasoning_result, ctx, style) → Answer
```

**The break:** there is no runtime, service, kernel stage, or test that assembles §3.2. It exists only as script `main()` bodies. `BrainKernel.process()` (§3.1's would-be host) runs shells instead.

---

## 4. Component-by-Component Status

Legend: **Exists** = real code (not `pass`/mock). **Prod/Shell** = production-grade vs placeholder. **Unit / Integ** = has passing tests. **In runtime** = reached by a real entry point.

| # | Component | File | Exists | Prod/Shell | Unit | Integ | In runtime | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | BrainKernel | `hsci/core/kernel.py` | Yes | **Shell** | Yes (`test_brain_kernel.py`) | Shell only | **No** | 10 stages = `ShellStage.time.sleep`; tests exercise shell orchestration, not cognition |
| 2 | WorkingMemory | `hsci/core/working_memory.py` | Yes | Prod | Yes | Yes | Partially | Used by CognitiveContext; RIRLoop uses its own ctx |
| 3 | Universal Knowledge Model (storage) | `hsci/core/storage.py` | Yes | Prod | Yes (`test_storage.py`) | Yes | **V4 only** | SQLite, WAL, savepoints, migrations |
| 4 | KnowledgeManager | `hsci/knowledge/knowledge_manager.py` | Yes | Prod | Yes (`test_knowledge_manager.py`) | Yes | **V4 only** | Façade over ConceptStore + cache |
| 5 | ConceptStore / Repository | `hsci/knowledge/concept_store.py`, `concept_repository.py` | Yes | Prod | Yes (`test_concept_store.py`) | Yes | **V4 only** | CRUD, aliases, namespaces, history, events |
| 6 | Concept Activation Engine | `hsci/knowledge/concept_activation.py` | Yes | Prod | Yes (`test_concept_activation_engine.py`) | Yes | **V4 only** | Spreading activation, ActivationField/AttentionBuffer |
| 7 | Understanding Engine | `hsci/knowledge/understanding_engine.py` | Yes | Prod | Yes (`test_understanding_engine.py`) | Yes | **V4 only** | 8-stage rule pipeline; intents: ExplainConcept/SolveEquation/VerifyAxiom |
| 8 | Cognitive Workspace / builder | — | **No dedicated class** | — | — | — | — | "Workspace" = resolved concept list; no builder component exists |
| 9 | ReasoningEngine (V4 conceptual) | `hsci/reasoning/reasoning_engine.py:186` | Yes | Prod (shallow) | Yes (`test_reasoning_engine.py`) | Yes | **V4 only** | Rule-based graph inference; no Z3 |
| 9b | ReasoningEngine (legacy/live) | `hsci/reasoning/reasoning_engine.py:323` | Yes | Prod | Yes | Yes | **Yes (live)** | HTN + solvers, used by RIRLoop |
| 10 | Answer Generation Engine | `hsci/response/answer_generation_engine.py` | Yes | Prod | Yes (`test_answer_generation_engine.py`) | Yes | **V4 only** | Standard/Step-by-Step/Technical styles |
| 11 | ReflectionEngine | `hsci/reasoning/reflection_engine.py` | Yes | Prod | Yes (`test_reflection_engine.py`) | Yes | **Yes (live)** | Reached on Z3 failure in RIRLoop |
| 12 | LearningEngine | `hsci/learning/learning_engine.py` | Yes | Prod | Yes | Yes | **Yes (live)** | RIRLoop path; not in V4 conceptual path |
| 13 | Planner / HTNPlanner | `hsci/reasoning/htn_planner.py` | Yes | Prod | Yes (`test_htn_planner.py`) | Yes | **Yes (live)** | Do NOT modify (per task) |
| 14 | VerificationEngine (Z3) | `hsci/symbolic/z3_verifier.py` | Yes | Prod | Yes (`test_verification.py`) | Yes | **Yes (live)** | CEGIS; connected to RIRLoop only |
| 15 | RIRLoop | `hsci/core/rir_loop.py` | Yes | Prod | via integration | Yes | **Yes (live)** | The real orchestrator |

**Executed proof:** `python -m hsci.knowledge.demo_answer_generation` ran successfully and produced a structured `Answer` object (direct answer, verified connections, confidence 0.88) — confirming components 3–7, 9, 10 execute together **outside** any runtime.

---

## 5. Complete and Connected Components (Category A)

Reached by a real entry point (`brain_api.py` / CLIs → `RIRLoop`):

- `RIRLoop` (orchestrator)
- `LanguageBridge`, `NeuralPerceiver`
- `KnowledgeBase` (+ `concept_library`, `episode_memory`) — the V3 store
- `ReasoningEngine` (legacy, line 323) + `HTNPlanner` + `SolverRegistry` + `SkillGraph`
- `Z3VerificationEngine` (with CEGIS repair loop)
- `ReflectionEngine`
- `LearningEngine` + `SkillUtilityStore` + `SkillLifecycleManager` + `SelfPlayEngine`
- `ResponseBridge`

These work in the live runtime, but for **symbolic problem-solving** (equations, physics, code-gen), **not** for conceptual "explain X" questions.

---

## 6. Implemented but Disconnected Components (Category B)

Real, tested code that participates in **no** runtime path (only demos/tests):

- `BrainKernel` — present but a shell; connected to nothing real.
- `SQLiteProvider` / `SchemaMigration` (UKM storage)
- `ConceptRepository`, `ConceptStore`
- `KnowledgeManager` (+ `InMemoryKnowledgeCache`)
- `UnderstandingEngine`
- `ConceptActivationEngine`
- `CognitiveReasoningEngine` (V4, line 186)
- `AnswerGenerationEngine`
- `CognitiveContext` / `WorkingMemory` (used by the V4 engines but only in demos)

Every item in this list already **executes correctly together** — the only thing missing is a caller.

---

## 7. Missing Components (Category C)

To run the target vertical slice, the following do **not** exist anywhere:

1. **A pipeline orchestrator that wires the four V4 engines** over a live UKM instance and is callable from a runtime (not a `demo` `main()`). Nothing plays this role: `BrainKernel` is a shell; `RIRLoop` uses the V3 stack.
2. **A canonical knowledge seed** that inserts the demonstrator concept(s) — e.g. "Interface"/"Java Interface", "Class", "Method", "Abstraction" — into the UKM `ConceptStore`. Without it, `UnderstandingEngine` resolves **zero** seed concepts for the Java-interface question (resolution matches only concepts already in the store; see `understanding_engine.py` Stage 5, lines 108–146).
3. **A formal "Cognitive Workspace" builder** (optional for MVP) — currently the "workspace" is an inline `List[Concept]` built by the demo. An MVP can keep this inline.
4. **An end-to-end integration test** asserting the full slice for a real question. Today only per-engine tests and non-test demo scripts exist.
5. **(Deferred, not MVP)** Z3 verification hook for the conceptual path. Explanation answers are not equational; Tenet 2.1 applies to *facts entering permanent storage*, so for a read-only "explain" slice this can remain absent and be flagged.

---

## 8. Existing Test Coverage

Test run performed this session: **48 passed** across the seven V4-relevant suites
(`pytest hsci/tests/test_understanding_engine.py test_concept_activation_engine.py test_reasoning_engine.py test_answer_generation_engine.py test_knowledge_manager.py test_concept_store.py test_brain_kernel.py` → `48 passed in 172.55s`).

| Stage | Unit | Integration (real UKM) | E2E slice | Exercises real integration? |
|---|---|---|---|---|
| Understanding | `test_understanding_engine.py` ✅ | uses SQLite mock/store ✅ | none | Real UKM, single engine |
| Concept Activation | `test_concept_activation_engine.py` ✅ | ✅ | none | Real UKM, single engine |
| Reasoning (V4) | `test_reasoning_engine.py` ✅ | ✅ | none | Real UKM, single engine |
| Answer Generation | `test_answer_generation_engine.py` ✅ | builds `ReasoningResult` via **mock** | none | Answer engine tested against a mocked reasoning result |
| KnowledgeManager | `test_knowledge_manager.py` ✅ | ✅ (SQLite) | n/a | Real UKM |
| ConceptStore | `test_concept_store.py` ✅ | ✅ (SQLite, concurrency) | n/a | Real UKM |
| BrainKernel | `test_brain_kernel.py` ✅ | shell only | n/a | **Tests placeholders, not cognition** |
| Live V3 runtime | root `tests/`, `test_*` at root | partial | `evaluation_runner.py` | Real RIRLoop for symbolic domains |

**Key gaps:**
- **No test assembles Understanding → Activation → Reasoning → Answer.** That assembly lives only in `demo_answer_generation.py` / `demo_reasoning_engine.py`, which are scripts, not tests. Per TESTING_STANDARD, demos do not count as proof of E2E functionality.
- `AnswerGenerationEngine` is validated against a **mocked** `ReasoningResult`, so no test proves real reasoning output feeds it correctly.
- `test_brain_kernel.py` passing is **not** evidence of a working pipeline — it validates shell timing/orchestration only.

---

## 9. End-to-End Readiness — "Explain what a Java interface is."

| Step | Capability | Status | Evidence |
|---|---|---|---|
| 1 | Parse the question | ✅ Works | `UnderstandingEngine.understand()` runs |
| 2 | Produce UnderstandingResult | ✅ Works | returns `intent`, `seed_concepts`, entities |
| 2b | Classify intent = ExplainConcept | ✅ Works | rule `\b(what is|explain|describe|define)\b` → `ExplainConcept` (0.95) |
| 3 | Identify concept "Java Interface" | ❌ **Fails** | resolution matches only concepts already in UKM; "Interface" is not seeded → empty seeds |
| 4 | Retrieve relevant knowledge | ⚠ Conditional | `KnowledgeManager` works, but returns nothing if concept absent |
| 5 | Activate relevant concepts | ✅ Works (given seeds) | `ConceptActivationEngine.activate_concepts()` proven in demo |
| 6 | Build a cognitive workspace | ⚠ Inline only | resolved-concept list; no builder class |
| 7 | Reason over knowledge | ✅ Works (shallow) | `CognitiveReasoningEngine.reason()` — graph relations only |
| 8 | Produce ReasoningResult | ✅ Works | demo produced 2 verified conclusions |
| 9 | Generate answer | ✅ Works | `AnswerGenerationEngine.generate()` produced structured `Answer` |
| 10 | Verify (Z3) where applicable | ❌ Not connected | no Z3 in V4 path; N/A for explanation but unenforced |
| 11 | Return final response | ⚠ No runtime | works in demo; no callable service assembles it |

**Net:** The engines are ready; the slice fails today for two concrete reasons only — **(3) missing knowledge seed** and **(11) missing orchestration caller**. Everything between them already works.

---

## 10. Smallest Required Implementation

To turn the slice green **without** touching SCG-L5 / HTN / Z3 / SkillGraph / lifecycle:

1. **One orchestration facade** (~1 small module) — e.g. `CognitivePipeline` — that:
   - accepts an initialized `KnowledgeManager` + `EventBus`,
   - constructs `UnderstandingEngine`, `ConceptActivationEngine`, `CognitiveReasoningEngine`, `AnswerGenerationEngine` once,
   - exposes `answer(question: str) -> Answer` running the exact sequence already proven in `demo_answer_generation.py`.
   - This is *assembly of existing, tested APIs* — no new cognition.

2. **One canonical concept seed** — insert a small OOP concept set including "Interface"/"Java Interface", "Class", "Method", "Abstraction" (with `generalizes_to` / namespace links) into the UKM `ConceptStore`, marked as canonical provenance.

3. **One E2E integration test** — assert that `CognitivePipeline.answer("Explain what a Java interface is.")` yields intent `ExplainConcept`, non-empty activated concepts, ≥1 conclusion, and a non-empty `direct_answer`.

That is the whole MVP. No engine is created; no authoritative component is modified.

---

## 11. Proposed Integration Sequence

1. Stand up a UKM instance (`SQLiteProvider` + migrations) and `KnowledgeManager` (reuse demo bootstrap).
2. Seed canonical OOP concepts into `ConceptStore` (idempotent).
3. Introduce the `CognitivePipeline` facade wiring the four engines over that manager + a shared `EventBus`.
4. Add the E2E integration test for the Java-interface question.
5. (Optional, later) expose the facade behind a runtime surface — either a new `brain_api` route or real `BrainKernel` StageExecutors that delegate to the facade — deferred beyond MVP.

---

## 12. Risks

- **Two-stack divergence**: building the facade risks a *third* orchestrator. Mitigation: name it clearly as the V4 conceptual pipeline; keep RIRLoop untouched; do not merge stacks in the MVP.
- **Shallow reasoning quality**: `CognitiveReasoningEngine` only traverses `generalizes_to` + namespace co-existence. The Java-interface answer will be structurally correct but thin. Acceptable for a slice; not a knowledge product.
- **No Z3 in conceptual path**: constitutional Tenet 2.1 is unenforced here. For a read-only explanation this is tolerable, but it must be documented, not silently accepted.
- **Seed provenance**: seeded concepts must carry canonical provenance to respect the canonical/learned distinction; a careless seed could pollute the learned space.
- **BrainKernel remains a shell**: leaving it as-is preserves the drift between constitution and reality. The MVP does not fix this; a later ADR should decide whether BrainKernel adopts real stages or is formally superseded.
- **UKM lifecycle in a service**: demos create/delete a throwaway DB per run. A persistent runtime needs a decision on DB location/lifecycle (out of MVP scope; note it).

---

## 13. Architecture Integrity Assessment

The proposed MVP **can be built without modifying** the established authority model:

- **BrainKernel** — untouched (remains a shell; drift documented, not corrected).
- **WorkingMemory / CognitiveContext** — reused as-is (the V4 engines already accept `CognitiveContext`).
- **UKM (`SQLiteProvider`/`ConceptStore`/`KnowledgeManager`)** — used through its existing public API; no schema change required for the slice.
- **Concept Activation / CognitiveReasoningEngine / Z3 / lifecycle / provenance** — unchanged; the facade only *calls* them.
- **Canonical vs learned distinction** — respected by marking seeded concepts as canonical provenance.

The MVP is **pure assembly + data seeding**. It introduces one new façade module and one seed, and adds tests. It bypasses nothing: every authoritative component is invoked through its real interface. The one honest caveat is that Z3 arbitration (Tenet 2.1) is absent from the conceptual path today and remains absent in the MVP — this is flagged for a future decision rather than worked around.

---

## NEXT IMPLEMENTATION SPRINT

**Sprint name:** VS-1 — Vertical Conceptual Slice Assembly ("Explain a Concept")

**Objective:** Make the target scenario *"Explain what a Java interface is."* run end-to-end through the existing V4 engines via one callable facade, backed by a canonical UKM seed and proven by an integration test — without modifying any authoritative cognitive component.

**Files/components to inspect (read-only, already audited):**
- `hsci/knowledge/understanding_engine.py` — `understand()` API, seed resolution (Stage 5).
- `hsci/knowledge/concept_activation.py` — `ConceptActivationEngine.activate_concepts()`.
- `hsci/reasoning/reasoning_engine.py:186` — `CognitiveReasoningEngine.reason()` + `ReasoningContext`.
- `hsci/response/answer_generation_engine.py` — `AnswerGenerationEngine.generate()`.
- `hsci/knowledge/knowledge_manager.py`, `concept_store.py`, `concept_repository.py`, `hsci/core/storage.py` — UKM bootstrap.
- `hsci/core/kernel.py` — `CognitiveContext`, `EventBus` (constructors only).
- `hsci/knowledge/demo_answer_generation.py` — the exact working sequence to mirror.

**Files/components to create or modify:**
- **Create** `hsci/core/cognitive_pipeline.py` — `CognitivePipeline` facade: constructor takes `KnowledgeManager` + `EventBus`; method `answer(question, style="Standard") -> Answer` runs Understanding → Activation → resolve concepts → Reasoning → Answer.
- **Create** a canonical seed (e.g. `hsci/knowledge/seeds/oop_concepts.py` or a migration/data loader) inserting "Interface"/"Java Interface", "Class", "Method", "Abstraction" with `generalizes_to`/namespace links and canonical provenance; must be idempotent.
- **Create** `hsci/tests/test_cognitive_pipeline_e2e.py` — the integration test below.
- **Do NOT modify**: `kernel.py` stages, `reasoning_engine.py` reasoning bodies, `z3_verifier.py`, HTN planner, SkillGraph, lifecycle, RIRLoop, or any benchmark/publication artifact.

**APIs to connect (all already exist):**
- `UnderstandingEngine(manager).understand(text, ctx) -> UnderstandingResult{intent, seed_concepts, ...}`
- `ConceptActivationEngine(manager, event_bus).activate_concepts(seed_concepts, ctx) -> ActivatedSet{.concepts[].concept.id/.name}`
- `manager.get_concept(id) -> Concept` (resolve activated set to `List[Concept]`)
- `CognitiveReasoningEngine(manager, event_bus).reason(List[Concept], ctx, ReasoningContext(goal)) -> ReasoningResult`
- `AnswerGenerationEngine(event_bus).generate(reasoning_result, ctx, style) -> Answer{direct_answer, sections, confidence, explanation, metadata}`

**Tests required:**
- Unit: `CognitivePipeline` constructs all four engines and calls them in order (mockable engines).
- Unit: seed loader is idempotent and marks provenance canonical.
- Integration (real UKM): `answer("Explain what a Java interface is.")` returns `intent == "ExplainConcept"`, non-empty activated concepts including "Interface", ≥1 reasoning conclusion, non-empty `direct_answer`.
- Regression: seeding twice does not duplicate concepts.

**End-to-end acceptance criteria:**
1. A single call `CognitivePipeline.answer("Explain what a Java interface is.")` returns an `Answer` with a non-empty `direct_answer` referencing the Interface concept.
2. `UnderstandingResult.intent == "ExplainConcept"` and `seed_concepts` is non-empty (proves the seed fixed step 3).
3. The integration test passes under `pytest`, exercising **real** UKM (no mocked reasoning result).
4. No file under SCG-L5 / HTN / Z3 / SkillGraph / lifecycle / RIRLoop / benchmarks / publications is modified (verify via `git diff --stat`).
5. Existing 48 V4 tests still pass (zero regression).

**Stop condition:** Stop when the integration test in criterion 3 passes and `git diff --stat` shows only the new facade, the new seed, and the new test (plus doc updates). Do **not** wire the facade into `brain_api.py` or `BrainKernel` in this sprint; do **not** add Z3 to the conceptual path; do **not** deepen `CognitiveReasoningEngine`. Report results and await instructions.

---

## CRITICAL STOP

This audit is complete. **No production code was written, no cognitive architecture modified, no benchmark or publication artifact touched.** Awaiting further instructions before implementing Sprint VS-1.
