# HSCI VS-4 — Cognitive Interpretation & Task Derivation Foundation
## Preflight Report

**Type**: Preflight Architecture & Boundary Analysis (Phase 1 — Read Only)  
**Date**: 2026-08-22  
**Predecessors**: `VS1_IMPLEMENTATION_REPORT.md`, `VS2_IMPLEMENTATION_REPORT.md`, `VS3_IMPLEMENTATION_REPORT.md`, `COGNITIVE_MVP_ACCEPTANCE_REPORT.md`, `COGNITIVE_MVP_RUNTIME_TRACE.md`  
**Core Objective**: Establish an honest, robust, grounded boundary between natural human language and the symbolic cognitive system (`LanguageInterpreter` → `GroundingEngine` → `CognitiveSituation` → `TaskDeriver` → `CognitiveTask`).

---

## 1. Executive Summary

In Sprints VS-1 through VS-3, HSCI established a verified cognitive vertical slice over the Universal Knowledge Model (UKM), complete with definition-first synthesis, 2-premise generalization transitivity, and refusal on unknown queries.

However, the **Human Language Boundary** remains the primary bottleneck:
1. **Fragile Language Ingestion**: The existing `UnderstandingEngine` is a rigid regex / N-gram token matching loop. If an input paraphrases or deviates syntactically from exact lexicon strings or patterns, intent classification falls back to low-confidence heuristics or misses compound semantic goals.
2. **Premature Collapse of Ambiguity**: Current parser paths pick the first alias or concept match and discard competing hypotheses, obscuring ambiguities and ungrounded assumptions.
3. **Absence of Structured Cognitive Tasks**: The pipeline directly jumps from keyword/concept activation to answering without deriving an explicit **Cognitive Task** (e.g. `EXPLAIN_CONCEPT`, `COMPARE_CONCEPTS`, `DERIVE_RELATIONSHIP`, `IDENTIFY_PURPOSE`).

VS-4 establishes a formal, additive interpretation and task derivation foundation:

```text
RawInput
   ↓
LanguageInterpreter (Generates candidate hypotheses & semantic frames)
   ↓
InterpretationSet (Multi-hypothesis collection with lexical/semantic provenance)
   ↓
GroundingEngine (UKM validation, entity resolution, ambiguity detection)
   ↓
CognitiveSituation (Accepted grounded situational state & unresolved alerts)
   ↓
TaskDeriver (Constructs executable CognitiveTask hierarchy)
   ↓
CognitivePipeline (Executes task over UKM, reasoning, and response synthesis)
```

---

## 2. Deep Answers to Mandatory Preflight Questions

### 2.1 What Currently Interprets Human Language?
Two disjoint subsystems currently exist in the codebase:
- **Legacy V3 LanguageBridge** (`hsci/language/bridge.py`): Routes text through `SemanticCompiler` (regex word-problem grammar), `SpacyParser` (dependency grammar), or `LLMParser` (dummy fallback), outputting `StructuredInput` targeting linear math or arithmetic reduction.
- **V4 UnderstandingEngine** (`hsci/knowledge/understanding_engine.py`): Performs lowercase normalization, regex sentence segmentation, tokenization, 1..3 N-gram database lookup against `KnowledgeManager`, and a hardcoded list of regex patterns mapping to `ExplainConcept` / `SolveEquation` / `VerifyAxiom`.

### 2.2 What Information Is Lost?
- **User Intent Nuances**: Comparison questions (*"How do interfaces differ from abstract classes?"*), purpose questions (*"Why do interfaces exist?"*), and relationship questions (*"What is the connection between A and B?"*) are all compressed into a generic `ExplainConcept` or `GeneralQuery`.
- **Syntactic Structure & Negation/Modality**: Question modifiers, constraints, comparison targets, and relational directions are stripped during tokenization and discarded.
- **Referential Context**: References to previous dialogue turns (*"Why is it useful?"*) have no referent tracking and produce arbitrary single-token lookups.

### 2.3 Where Does Ambiguity Disappear?
- In `UnderstandingEngine.understand()` (lines 141-161), when an alias matches multiple concepts (`len(resolved_aliases) > 1`), it appends a string alert to `ambiguities` but immediately returns `aliases[0]`, silently selecting the first match.
- Downstream stages (`ConceptActivationEngine`, `CognitiveReasoningEngine`) never receive the ambiguity signal and reason over the arbitrarily chosen concept as if it were unambiguous truth.

### 2.4 Where Are Assumptions Introduced?
- Intent confidence scores (0.95, 0.90, 0.85, 0.50) are hardcoded in static regex tuples.
- The pipeline assumes every matched token refers to a definitive domain concept rather than checking whether the discourse context supports that interpretation.
- When an entity cannot be resolved, the pipeline simply treats it as an empty concept list rather than generating an explicit `UNRESOLVED_ENTITIES` or `INSUFFICIENT_CONTEXT` situational status.

### 2.5 What Existing Models Can Be Reused?
- `hsci.core.data_types.Concept` & `ConceptStore`: Core UKM concept schemas.
- `hsci.core.data_types.Task`, `TaskType`, `Precondition`, `Postcondition`: HTN task data models.
- `hsci.knowledge.knowledge_manager.IKnowledgeManager`: Authoritative facade for concept search, alias resolution, and relationship traversal.
- `hsci.core.kernel.CognitiveContext` & `WorkingMemory`: Per-request state encapsulation.
- `hsci.response.answer_generation_engine.Answer` & `hsci.response.explanatory_synthesizer.ExplanatoryAnswer`: Structured response types.

### 2.6 What Should Be Authoritative?
- **UKM (`KnowledgeManager` / `ConceptStore`)** is the sole authority on domain concepts, relations, and stored axioms.
- **`GroundingEngine`** is the sole authority on whether a candidate linguistic interpretation is grounded, ambiguous, or ungrounded.
- **`CognitiveReasoningEngine`** remains the sole authority on logical derivation and inference over activated concepts.
- **The LLM (if present)** is strictly an **untrusted hypothesis generator** producing semantic candidates. It has zero authority over knowledge, truth, or final answers.

### 2.7 Where Should `CognitiveSituation` Live?
In a dedicated, clean interpretation package: `hsci/cognition/interpretation/`.
- `models.py`: Defines `RawInput`, `CandidateInterpretation`, `InterpretationSet`, `GroundedEntity`, `CognitiveSituation`, `SituationStatus`, `CognitiveTask`, `TaskAction`.
- `interpreter.py`: `LanguageInterpreter` generating candidate hypotheses from structural analysis and semantic parsers.
- `grounding.py`: `GroundingEngine` evaluating candidates against UKM via `IKnowledgeManager`.
- `task_deriver.py`: `TaskDeriver` translating accepted `CognitiveSituation` into executable `CognitiveTask`.

### 2.8 Where Should `TaskDerivation` Live?
`hsci/cognition/interpretation/task_deriver.py`. It inspects the validated `CognitiveSituation` and deterministically derives structured tasks:
- Single resolved concept $\to$ `Task(action=EXPLAIN_CONCEPT, target=concept_1)`
- Two resolved concepts with comparison intent $\to$ `Task(action=COMPARE_CONCEPTS, targets=[concept_1, concept_2])`
- Two resolved concepts with relation intent $\to$ `Task(action=DERIVE_RELATIONSHIP, targets=[concept_1, concept_2])`
- Unresolved entity $\to$ `Task(action=REPORT_UNKNOWN, status=UNRESOLVED_ENTITIES)`
- Ambiguous entity $\to$ `Task(action=REPORT_AMBIGUITY, status=AMBIGUOUS)`
- Missing referent $\to$ `Task(action=REPORT_INSUFFICIENT_CONTEXT, status=INSUFFICIENT_CONTEXT)`

### 2.9 How Should LLM Output Enter the System?
- When enabled, `LLMParser` acts solely as an untrusted candidate proposer inside `LanguageInterpreter`.
- Its output is parsed strictly into typed `CandidateInterpretation` records.
- If schema validation fails, or if it proposes hallucinated entities/relations, the `GroundingEngine` strips or marks them as ungrounded during the UKM validation phase.

### 2.10 How Should Grounding Reject Unsupported Interpretations?
For every candidate entity and relationship:
1. `GroundingEngine` queries `IKnowledgeManager.get_concept_by_name(name)` and `resolve_alias(alias)`.
2. If 0 matches $\implies$ Classified as `GroundedEntity(status=UNKNOWN)`.
3. If >1 matches $\implies$ Classified as `GroundedEntity(status=AMBIGUOUS, candidates=[...])`.
4. If 1 match $\implies$ Classified as `GroundedEntity(status=RESOLVED, concept=concept)`.
5. If the situation contains UNKNOWN or AMBIGUOUS entities essential to the query goal, `CognitiveSituation.status` becomes `UNRESOLVED_ENTITIES` or `AMBIGUOUS`, halting ungrounded derivation and preventing hallucinations.

---

## 3. Boundary & Responsibility Matrix

| Subsystem | Input | Output | Invariant |
|---|---|---|---|
| `LanguageInterpreter` | `RawInput` (text, context) | `InterpretationSet` (list of hypotheses) | Pure syntactic/semantic extraction; does not invent UKM facts |
| `GroundingEngine` | `InterpretationSet` + `IKnowledgeManager` | `CognitiveSituation` | Every concept checked against UKM; ambiguities explicit |
| `TaskDeriver` | `CognitiveSituation` | `CognitiveTask` | Deterministic mapping from grounded situation to task DAG |
| `CognitivePipeline` | `CognitiveTask` / `RawInput` | `ExplanatoryAnswer` | Executes task via activation, reasoning, and synthesis |

---

## 4. Preflight Verification Status

- [x] Read and analyzed all project rules and architecture constitution.
- [x] Inspected existing parser, pipeline, reasoning, and response engines.
- [x] Identified information loss and ambiguity collapse points.
- [x] Designed additive modular interpretation layer without breaking existing test suites.

**Phase 1 Complete. Ready for Phase 2 Implementation.**
