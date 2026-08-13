# HSCI Sprint VS-2 — Pre-Flight Diagnostic Report

**Type**: Read-only runtime inspection (no production code modified)
**Date**: 2026-08-09
**Predecessors**: `docs/design/VERTICAL_COGNITIVE_SLICE_READINESS_REPORT.md`, `docs/design/VS1_IMPLEMENTATION_REPORT.md`
**Method**: The real `CognitivePipeline` was executed end-to-end for *"Explain what a Java interface is."* via a temporary scratchpad harness (no repo test added; instrumentation removed after capture). Every value below is an observed runtime value, not a documentation claim.

---

## 1. Executive Summary

VS-1 is **genuinely integrated and real** — no mocks, no hardcoding, no direct SQLite, no bypass of `KnowledgeManager`. The answer for the Java-interface question **does causally depend on the Reasoning Engine's output** (the Answer Generator iterates the real `ReasoningResult.conclusions`).

However, the pre-flight surfaces one decisive honesty finding:

> **The system does not actually explain what a Java interface *is*.** It emits a list of *structural graph edges* (X generalizes to Y, aliases, namespace cohabitation). The concept's stored definitional text (`Concept.abstract_rule` = "A Java interface is a reference type declaring abstract methods…") is **never read** by the reasoner or the answer generator. The reasoning engine derives **no new knowledge** — all 7 "conclusions" are verbatim restatements of stored relationships.

So VS-1 is a real, correctly-wired **knowledge-graph traversal + serialization** pipeline. It is not yet an **explanation** pipeline. The knowledge to answer the question is present in the store but is dropped before the answer.

Secondary findings: there is **no dedicated Cognitive Workspace class** (an inline `List[Concept]` stands in); `WorkingMemory` is populated by the activation engine but **not consumed** by the reasoner; and the pipeline has **no learning/reflection** path.

---

## 2. Actual VS-1 Runtime Trace

Input: `"Explain what a Java interface is."`

### 2.1 Understanding — `UnderstandingResult` (real)
```
intent            = "ExplainConcept"
confidence        = 0.95
entities          = {"java": "language"}
seed_concepts     = ["Java Interface"]
keywords          = ["explain","what","a","java","interface","is."]
constraints       = []
ambiguities       = []
normalized_query  = "explain what a java interface is."
```
Resolution mechanism: n-gram scan matched the bigram "java interface" against the store (`get_concept_by_name`, COLLATE NOCASE). Intent via regex rule `\b(what is|explain|describe|define)\b`.

### 2.2 KnowledgeManager / UKM (real)
Seed `"Java Interface"` resolved to:
```
id=c_java_interface  name="Java Interface"  namespace=concept.oop
aliases=["java interface"]  status=ACTIVE
provenance = { source_type: CANONICAL_SEED, source_id: hsci.knowledge.seeds.oop_concepts,
               acquisition_method: MANUAL, confidence: 1.0 }
```
All reads flowed through `KnowledgeManager → ConceptStore → ConceptRepository → SQLiteProvider`.

### 2.3 Concept Activation — ordered (real spreading activation)
```
Java Interface  c_java_interface  score=1.0000  reason="Seed input match"
Interface       c_interface       score=0.6500  reason="Generalization target of 'Java Interface'"
Abstraction     c_abstraction     score=0.6500  reason="Namespace sibling under 'concept.oop'"
Class           c_class           score=0.6500  reason="Namespace sibling under 'concept.oop'"
Method          c_method          score=0.6500  reason="Namespace sibling under 'concept.oop'"
```
Decay 0.3 (1.0 → 0.65 at hop 1). Interface reached via `generalizes_to`; the rest via namespace siblings.

### 2.4 Cognitive Workspace / WorkingMemory
- **Dedicated Cognitive Workspace class: NOT IMPLEMENTED / NOT USED.** The facade builds an inline `List[Concept]` by re-resolving activated IDs (`workspace = [manager.get_concept(id) ...]`).
- **WorkingMemory: populated but not consumed by reasoning.** The activation engine wrote:
  ```
  activation_field.activation_strengths = {c_java_interface:1.0, c_interface:0.65, c_abstraction:0.65, c_class:0.65, c_method:0.65}
  attention_buffer (salience)           = same map
  active_skills                         = [c_java_interface, c_interface, c_abstraction, c_class, c_method]
  ```
  The reasoner receives the inline `List[Concept]` directly and **does not read** `WorkingMemory`. The Answer Generator reads only `working_memory.activation_field` keys (for metadata), not concept content.

### 2.5 Reasoning — all 7 conclusions (real, but restatement-only)
```
[1] "Java Interface generalizes to Interface"      rule=GeneralizationTransitivity conf=0.90  ev=[Java Interface.generalizes_to → c_interface]
[2] "Interface generalizes to Abstraction"         rule=GeneralizationTransitivity conf=0.90  ev=[Interface.generalizes_to → c_abstraction]
[3] "Class generalizes to Abstraction"             rule=GeneralizationTransitivity conf=0.90  ev=[Class.generalizes_to → c_abstraction]
[4] "Method generalizes to Class"                  rule=GeneralizationTransitivity conf=0.90  ev=[Method.generalizes_to → c_class]
[5] "Concepts [...5...] co-exist under namespace 'concept.oop'"  rule=NamespaceCohabitation conf=0.85
[6] "Alias 'java interface' points directly to Java Interface"   rule=AliasMapping conf=0.95
[7] "Alias 'interface' points directly to Interface"            rule=AliasMapping conf=0.95
overall confidence = 0.9071   contradictions = []   iterations = 2 (2nd produced nothing → loop halt)
```
Rules fired: `GeneralizationTransitivity`, `NamespaceCohabitation`, `AliasMapping` (from `RuleBasedInferenceStrategy`).
**Provenance of conclusions**: evidence strings only; conclusions are not written back to the UKM and carry no `proof_trace_id`.

### 2.6 Answer Generation (real, derived from §2.5)
```
direct_answer = "Based on formal reasoning, we verified the following connections:"
section "Verified Connections":
   - Alias 'interface' points directly to concept Interface
   - Alias 'java interface' points directly to concept Java Interface
   - Method generalizes to Class
   - Class generalizes to Abstraction
   - Interface generalizes to Abstraction
   - Java Interface generalizes to Interface
   - Concepts [...5...] co-exist under namespace 'concept.oop'
confidence = 0.9071 (High)
explanation.reasoning_summary = "Successfully verified 7 assertions in 2 iterations."
metadata.activation_concepts = [c_java_interface, c_interface, c_abstraction, c_class, c_method]
```
Source dependency confirmed: `AnswerGenerationEngine.generate()` sorts and serializes `ReasoningResult.conclusions`. Remove a conclusion → the answer changes. **Not hardcoded.**

---

## 3. Component-by-Component Integration Audit

| Component | Real implementation invoked? | Integrated into VS-1 path? | Notes |
|---|---|---|---|
| `CognitivePipeline` | Yes | — | Facade; assembly only |
| BrainKernel | **Not used** | No (intentional) | Shell placeholders; VS-1 bypasses it by design |
| WorkingMemory | Yes (populated) | Partially | Written by CAE; **not read** by reasoner |
| KnowledgeManager | Yes | Yes | Sole gateway to UKM reads |
| ConceptStore / Repository / SQLiteProvider | Yes | Yes | Real SQLite, provenance rows |
| ConceptActivationEngine | Yes | Yes | Real spreading activation |
| UnderstandingEngine | Yes | Yes | Rule/regex + n-gram resolution |
| CognitiveReasoningEngine | Yes | Yes | Real, but restatement-only (no new derivation) |
| AnswerGenerationEngine | Yes | Yes | Serializes reasoning conclusions |
| Cognitive Workspace (dedicated) | **NOT IMPLEMENTED** | No | Inline `List[Concept]` substitute |
| LearningEngine / ReflectionEngine | Exist in repo (V3 path) | **No** | Not wired into VS-1 pipeline |

---

## 4. Complete Cognitive Execution Graph (real functions)

```
"Explain what a Java interface is."
   │
   ▼  CognitivePipeline.answer()                         hsci/core/cognitive_pipeline.py
   ▼  UnderstandingEngine.understand()                   hsci/knowledge/understanding_engine.py
        └─ KnowledgeManager.get_concept_by_name()        (n-gram resolution)
   ▼  ConceptActivationEngine.activate_concepts()        hsci/knowledge/concept_activation.py
        └─ GraphSpreadingActivationStrategy.activate()
        └─ KnowledgeManager.get_concept / search_by_namespace / search
        └─ WorkingMemory.activation_field/attention_buffer  (WRITTEN here)
   ▼  [workspace] facade loop: manager.get_concept(id) → List[Concept]   (inline; no class)
   ▼  CognitiveReasoningEngine.reason()                  hsci/reasoning/reasoning_engine.py:186
        └─ RuleBasedInferenceStrategy.infer()            (edges → conclusions; NO WorkingMemory read)
   ▼  AnswerGenerationEngine.generate()                  hsci/response/answer_generation_engine.py
        └─ reads ReasoningResult.conclusions + working_memory.activation_field keys
   ▼  Answer
```

Break points: (a) **Workspace** stage has no component; (b) **WorkingMemory → Reasoning** arrow is not a data dependency; (c) **Concept content (`abstract_rule`) → Answer** arrow does not exist.

---

## 5. Real vs Mocked Component Analysis

| Stage | Actual Component | Actual Function | Real/Mocked | Evidence |
|---|---|---|---|---|
| Understanding | `UnderstandingEngine` | `understand()` | **Real** | intent/entities computed from the text; explanations dict populated |
| Knowledge | `KnowledgeManager`+`ConceptStore`+`ConceptRepository`+`SQLiteProvider` | `get_concept_by_name`, `get_concept`, `search_by_namespace` | **Real** | SQLite rows + provenance record returned |
| Activation | `ConceptActivationEngine` / `GraphSpreadingActivationStrategy` | `activate_concepts` / `activate` | **Real** | scores 1.0/0.65 with hop paths and reasons |
| Workspace | none (inline `List[Concept]`); `WorkingMemory` populated | facade loop; `activation_field.set_activation` | **Real but no dedicated class; not consumed by reasoner** | WM attrs dump; reasoner signature takes `List[Concept]` |
| Reasoning | `CognitiveReasoningEngine` | `reason()` / `RuleBasedInferenceStrategy.infer()` | **Real (shallow)** | 7 conclusions == restated stored edges; no transitive/new fact |
| Answer | `AnswerGenerationEngine` | `generate()` | **Real** | iterates `rr.conclusions`; output tracks conclusion set |

No stage is mocked. No confidence is fabricated (values are deterministic rule constants: 0.90/0.85/0.95, aggregated to 0.9071). No per-question hardcoded text.

---

## 6. Knowledge Coverage

| Structure | Count | Notes |
|---|---|---|
| Canonical concepts | **5** | Abstraction, Class, Method, Interface, Java Interface |
| Aliases | **2** | "interface", "java interface" |
| Relationships (`generalizes_to`) | **4** | JavaInterface→Interface, Interface→Abstraction, Class→Abstraction, Method→Class |
| Facts (distinct fact store) | **0 — NOT IMPLEMENTED** | No fact table/type in the VS-1 path |
| Rules (stored knowledge) | **0** | Inference rules are hardcoded in `RuleBasedInferenceStrategy`, not stored |
| OOP concepts | **5** | Same as canonical set |
| Seeded concepts | **5** | All from `oop_concepts.py`, provenance `CANONICAL_SEED` |
| Definitional text (`abstract_rule`) | Present on all 5 | **Stored but never surfaced in the answer** |

---

## 7. Reasoning Capability

- **Mechanism**: deterministic rule-based edge enumeration (`GeneralizationTransitivity`, `NamespaceCohabitation`, `AliasMapping`).
- **Real**: yes — output is computed from the concept objects.
- **Depth**: shallow. Every conclusion mirrors an existing stored edge. The system does **not** compute transitive closure (e.g., "Java Interface generalizes to Abstraction" is absent), does not combine concepts into new propositions, and does not use definitional knowledge.
- **Verification**: internal consistency only (circular-reasoning + contradiction checks). **No Z3.** Conclusions are not persisted and carry no proof-trace ID.

---

## 8. Learning Capability

| Capability | Classification (VS-1 pipeline) |
|---|---|
| Experience storage | NOT IMPLEMENTED |
| Feedback | NOT IMPLEMENTED |
| Confidence updates | NOT IMPLEMENTED |
| Concept updates | NOT IMPLEMENTED |
| New concept creation | NOT IMPLEMENTED |
| Relationship creation | NOT IMPLEMENTED |
| Reasoning-outcome storage | NOT IMPLEMENTED |
| Reflection | NOT IMPLEMENTED (a `ReflectionEngine` exists in the V3/RIRLoop path but is not wired into VS-1) |
| Skill learning | NOT IMPLEMENTED (a `SkillLearningEngine` exists in the V3 path but is not wired into VS-1) |

The VS-1 pipeline is strictly read-only cognition; the loop never writes back to the UKM.

---

## 9. Architecture Bypass Analysis

| Check | Result | Detail |
|---|---|---|
| Direct SQLite access | **No** | All reads via `KnowledgeManager`/`ConceptStore` |
| Hardcoded answer generation | **No** | Answer serializes real conclusions |
| Hardcoded Java-Interface response | **No** | No per-question branch |
| Mock reasoning | **No** | Real `CognitiveReasoningEngine` |
| Fake confidence | **No** | Deterministic rule constants, aggregated |
| Fake concepts | **No** | Seeded, provenance-tracked |
| Duplicate knowledge stores | **Noted** | The separate V3 `KnowledgeBase` still exists; VS-1 uses the V4 UKM. VS-1 does not duplicate within itself, but the two-stack split (V3 vs V4) persists repo-wide |
| Bypassing KnowledgeManager | **No** | Sole gateway used |
| Bypassing BrainKernel | **Yes (intentional)** | BrainKernel is a shell; VS-1 deliberately does not use it |
| Bypassing WorkingMemory | **Partial** | WM is created and populated by the CAE but is **not** the reasoner's input; reasoner uses the inline `List[Concept]` |

No unauthorized/accidental bypass. The two intentional deviations (BrainKernel unused; WorkingMemory not authoritative for reasoning input) are documented, not hidden.

---

## 10. Current Cognitive Capability Matrix

| # | Capability | Verdict | Runtime evidence |
|---|---|---|---|
| A | Answer from stored knowledge | **PARTIAL** | Retrieves concepts + relationships, but drops the stored definition (`abstract_rule`); answers *about* relations, not the definition |
| B | Identify relevant concepts | **YES** | "java interface" → `c_java_interface` (intent 0.95) |
| C | Activate related concepts | **YES** | 5 concepts with scores/paths/reasons |
| D | Combine multiple concepts | **PARTIAL** | Only a set-membership statement (namespace cohabitation); no genuine synthesis |
| E | Derive a NEW conclusion | **NO** | All 7 conclusions restate stored edges; transitive "JavaInterface→Abstraction" not derived |
| F | Distinguish facts from conclusions | **PARTIAL** | Conclusions carry evidence/confidence, but are actually facts restated; no fact-vs-derived tagging |
| G | Explain WHY an answer is correct | **PARTIAL** | Evidence strings + reasoning trace, but no explanation of the concept itself |
| H | Detect insufficient knowledge | **PARTIAL** | Empty-seed path flags ambiguity + AGE returns "No verified conclusions"; no partial-coverage signal |
| I | Express uncertainty | **PARTIAL** | Confidence scores + High/Medium/Low band; coarse, uncalibrated |
| J | Learn from interaction | **NO** | No write-back; no learning/reflection in the pipeline |

---

## 11. Single Biggest Bottleneck

**Category E — Answer Generation** (starved by shallow Reasoning).

**Why.** The knowledge required to answer *"Explain what a Java interface is."* is already in the store (`abstract_rule` on `c_java_interface`, plus its relationships) and is already activated into the workspace. Yet the final answer contains **none of it** — it lists graph edges. The single change with the largest usefulness payoff is to make the answer stage **synthesize an explanation from the activated concepts' own knowledge** (definition + relationships + reasoning conclusions) with traceable provenance. This is a storage-free, SCG-L5-neutral vertical capability. The deeper cognitive limitation (Category D: reasoning derives no new knowledge) is real and should follow, but it is second-order for making *this* pipeline answer the user's question.

---

## 12. Recommended VS-2 Scope

**VS-2 — Explanatory Answer Synthesis.**

Make the pipeline produce an answer that actually *explains the concept*, composed from knowledge that is already retrieved and activated:

1. Route the activated **`Concept` objects** (which carry `abstract_rule`, aliases, `generalizes_to`) into the answer stage — today only reasoning conclusions + activation-field *keys* reach it.
2. Synthesize a `direct_answer` that states the **primary concept's definition** (`abstract_rule` of the top-scored resolved concept), then supports it with the **relationship conclusions** already produced by the reasoner.
3. Keep it **traceable**: cite source concept IDs + provenance (`CANONICAL_SEED`) and the reasoning evidence for each supporting line.
4. **No new storage engine, no per-question hardcoding, no SCG-L5 change, no Z3 addition.** Composition draws only on already-activated knowledge.
5. (Optional stretch, clearly separable) add transitive-closure inference so "Java Interface generalizes to Abstraction" is *derived* — moving Capability E from NO toward PARTIAL.

Target outcome: for the Java-interface question, the answer opens with a real definition ("A Java interface is a reference type declaring abstract methods…") and explains it via the concept graph, all through the real pipeline.

---

## 13. Risks

- **Retrieval-vs-cognition line**: surfacing `abstract_rule` is composition/retrieval, not derivation. VS-2 must present it honestly (definition = retrieved fact; relationships = reasoned) and must not be mistaken for "new reasoning."
- **Answer-engine scope**: `AnswerGenerationEngine` currently takes only `ReasoningResult` + `CognitiveContext`. Passing concept content risks widening its contract; a thin synthesis adapter may be cleaner than changing the engine's signature. Decide in VS-2 design.
- **Two-stack drift** remains: VS-2 stays in the V4 UKM path; it does not resolve the V3/V4 split.
- **Confidence realism**: composed answers should not inflate confidence; keep the reasoner's aggregate.
- **Scope creep toward learning**: VS-2 must remain read-only; learning (Capability J) is a later milestone.

---

## 14. Acceptance Criteria for VS-2

1. For *"Explain what a Java interface is."*, `pipeline.answer(...)` returns a `direct_answer` (or a primary section) containing the **definitional text** of the resolved primary concept (substring of `c_java_interface.abstract_rule`).
2. The answer additionally includes ≥1 **relationship-based supporting statement** produced by the real reasoner.
3. The answer is **traceable**: it references the source concept ID(s) and provenance and the reasoning evidence.
4. The result is produced **through the real pipeline** — no mocked reasoning result, no per-question hardcoded answer text, no direct SQLite.
5. **No SCG-L5 authority file modified**; no new storage engine; no Z3 added to the conceptual path.
6. Full regression stays green (`pytest hsci/tests/ -q`), plus a new E2E assertion for criteria 1–3.
7. Empty/low-knowledge questions still degrade cleanly (existing "no verified conclusions"/`ValidationError` behavior preserved).

---

## Pre-Flight Verdict

VS-1 is real and correctly integrated, but it **traverses and serializes** the knowledge graph rather than **explaining** it. The stored answer exists and is activated but is discarded before output. VS-2 should close that final arrow — Explanatory Answer Synthesis — without new storage, mocks, or SCG-L5 changes.

**STOP. No VS-2 implementation performed. Awaiting approval.**
