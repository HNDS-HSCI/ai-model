# HSCI Sprint VS-2 — Explanatory Answer Synthesis — Implementation Report

**Sprint**: VS-2 — Explanatory Answer Synthesis
**Date**: 2026-08-09
**Type**: Answer-synthesis milestone (read-only, deterministic, traceable, SCG-L5-neutral)
**Predecessors**: `docs/design/VS2_PREFLIGHT_REPORT.md`, `docs/design/VS1_IMPLEMENTATION_REPORT.md`

> **Honesty framing.** VS-2 makes the pipeline **surface stored concept knowledge** (a retrieved definition) and present it **alongside** the real reasoning relationships. The definition is classified as *retrieved* knowledge, never as newly reasoned knowledge. No learning, no reflection, no Z3, no new storage.

---

## 1. Executive Summary

The VS-2 pre-flight showed the VS-1 pipeline retrieves and activates the correct concept but discards its stored definition (`Concept.abstract_rule`) before the answer — so the answer listed graph edges instead of explaining the concept.

VS-2 closes that final arrow with a **thin, additive** synthesis step (`ExplanatoryAnswerSynthesizer`) that runs **after** the existing `AnswerGenerationEngine`. For explanation intents it composes a **definition-first** answer:

```
direct_answer = <the concept's stored abstract_rule, retrieved verbatim>
+ "Supporting Relationships" from the REAL ReasoningResult
+ full traceability (retrieved definition vs reasoned relationships)
```

For *"Explain what a Java interface is."* the answer now opens with the real stored
definition ("A Java interface is a reference type declaring abstract methods…") and
supports it with 7 real reasoning relationships, at the **unchanged** reasoning
confidence (0.9071 — not inflated). Non-explanation intents and unknown-concept
questions return the existing behaviour unchanged (no fabrication).

**Verdict: COMPLETE.**

---

## 2. Problem Identified in VS-1

- Understanding resolved `c_java_interface`; activation reached the right 5 concepts.
- `Concept.abstract_rule` (the definition) was **never read** by reasoning or answer generation.
- The answer serialized graph edges only. Capability A ("answer from stored knowledge") was PARTIAL; the user's actual question was not answered.

---

## 3. Architecture Change

Minimal and additive — no engine rewritten, no answer-engine contract changed.

| Change | File | Nature |
|---|---|---|
| New synthesizer component | `hsci/response/explanatory_synthesizer.py` (new) | Adds `ExplanatoryAnswerSynthesizer`, `ExplanatoryAnswer` (subclass of `Answer`), `KnowledgeSource` |
| Wire into pipeline | `hsci/core/cognitive_pipeline.py` (modified) | Construct synthesizer; capture activation scores; call synthesizer after `AnswerGenerationEngine.generate()` |

`AnswerGenerationEngine`, `CognitiveReasoningEngine`, `ConceptActivationEngine`,
`UnderstandingEngine`, `KnowledgeManager`, storage, HTN, Z3, SkillGraph, lifecycle —
**unchanged**. The synthesizer consumes the base `Answer` and only enriches it, so the
public answer-engine contract is untouched (chosen over widening `generate()`'s
signature, per the VS-2 brief).

---

## 4. Answer Synthesis Design

`ExplanatoryAnswerSynthesizer.synthesize(understanding, workspace_concepts, activation_scores, reasoning_result, base_answer, context)`:

1. If `understanding.intent` is not an explanation intent (`ExplainConcept`) → return `base_answer` unchanged.
2. **Primary concept** = the highest-activation concept (`max` over `activation_scores`) — i.e., the concept the user asked about (seed, score 1.0). Re-resolved fresh via `KnowledgeManager.get_concept()` so answers track knowledge updates.
3. **Definition** = `primary.abstract_rule` (verbatim). If present → `direct_answer` = the definition; add a "Definition" section. If absent → do **not** fabricate; keep the base answer's `direct_answer`.
4. **Supporting relationships** = every conclusion in the real `ReasoningResult`, primary-related first, rendered as a "Supporting Relationships" section.
5. If neither a definition nor any relationship exists → return `base_answer` (graceful degradation).
6. Return an `ExplanatoryAnswer` (subclass of `Answer`; fully back-compatible).

No question-specific logic exists anywhere — the same code path serves "class",
"method", "inheritance", etc.

---

## 5. Retrieved Knowledge vs Reasoned Knowledge

The result explicitly separates the two, in structure and in provenance:

- **Definition** → `KnowledgeSource(knowledge_type="definition", source_concept_id, source_concept_name, source_provenance, content)`. Presented as *retrieved from concept knowledge*.
- **Relationships** → `KnowledgeSource(knowledge_type="reasoned_relationship", reasoning_conclusion, reasoning_rule, reasoning_confidence, reasoning_evidence)`. Presented as *produced by the ReasoningEngine*.

The definition is never labelled as reasoning output. The reasoning rule is recovered
deterministically from each conclusion's fixed statement format (the reasoner does not
propagate its rule name onto `Conclusion`); the reasoner's evidence strings are
preserved verbatim.

---

## 6. Traceability Model

Every emitted statement answers "where did this come from?":

| Emitted content | Traceability fields |
|---|---|
| Definition | `source_concept_id`, `source_concept_name`, `source_provenance` (e.g. `CANONICAL_SEED`, confidence 1.0), `knowledge_type="definition"` |
| Relationship | `reasoning_conclusion`, `reasoning_rule`, `reasoning_confidence`, `reasoning_evidence`, `knowledge_type="reasoned_relationship"` |

No proof-trace IDs are invented (the architecture has none on `Conclusion`); the
available evidence is preserved instead, as the VS-2 brief allows.

---

## 7. Runtime Demonstration

Real pipeline, `Explain what a Java interface is.` (no mocks):

```
UNDERSTANDING
  intent: ExplainConcept
  seed concepts: ['Java Interface']

ACTIVATION
  Java Interface  score=1.00  reason=Seed input match
  Interface       score=0.65  reason=Generalization target of 'Java Interface'
  Abstraction     score=0.65  reason=Namespace sibling under 'concept.oop'
  Class           score=0.65  reason=Namespace sibling under 'concept.oop'
  Method          score=0.65  reason=Namespace sibling under 'concept.oop'

KNOWLEDGE
  primary concept: c_java_interface (Java Interface)
  definition: A Java interface is a reference type declaring abstract methods
              (and constants) that implementing classes must fulfil.
  provenance: CANONICAL_SEED (confidence 1.0)

REASONING
  Java Interface generalizes to Interface   ev=[...c_interface]      conf=0.90
  Interface generalizes to Abstraction      ev=[...c_abstraction]    conf=0.90
  Class generalizes to Abstraction          ev=[...c_abstraction]    conf=0.90
  (7 conclusions total, overall confidence=0.9071)

ANSWER
  direct_answer: A Java interface is a reference type declaring abstract methods
                 (and constants) that implementing classes must fulfil.

TRACEABILITY
  definition source: c_java_interface / Java Interface / CANONICAL_SEED / knowledge_type=definition
  reasoning sources: 7 reasoned relationships (rule + evidence preserved)
  confidence: 0.9071 (High)   [unchanged reasoning confidence — not inflated]
```

This demonstrates: **stored concept knowledge + real reasoning conclusions → explanatory answer.**

---

## 8. Test Results

`hsci/tests/test_vs2_explanatory_answer.py` — **10 passed** (`pytest ... -q → 10 passed in 0.40s`). All primary tests use real engines (no mocked reasoning):

| Test | Verifies |
|---|---|
| `test_java_interface_definition_appears` | AC1–AC5: real path; intent; `c_java_interface`; stored `abstract_rule` in answer; ≥1 reasoned relationship |
| `test_generic_concept_definition_appears` (×3) | AC15: generic — resolved concept's own definition surfaced |
| `test_class_definition_is_generic` | AC15: "class" explanation works with no Java-specific logic |
| `test_traceability_definition_and_reasoning` | AC6, AC7: definition = retrieved w/ provenance; relationships keep rule + evidence |
| `test_answer_tracks_changed_definition_no_hardcoding` | AC8: changing the stored definition changes the answer (no hardcoding) |
| `test_unknown_concept_no_fabricated_definition` | AC13: unknown concept → no fabricated definition |
| `test_confidence_not_inflated` | AC16: answer confidence == reasoning confidence, < 1.0 |
| `test_non_explanation_intent_returns_base_answer` | non-explanation intents unchanged |

---

## 9. Regression Results

`pytest hsci/tests/ -q`

```
276 passed, 489 warnings in 349.88s (0:05:49)   [exit code 0]
```

Zero failures. This is the VS-1 baseline (266) plus the 10 new VS-2 tests. All
pre-existing tests remain green (VS2-AC14). Warnings are pre-existing and unrelated.

---

## 10. Architecture Integrity

- **No SCG-L5 authority file modified**: reasoning bodies, Z3, HTN, SkillGraph, lifecycle, storage, `BrainKernel`, `RIRLoop` — untouched.
- **No new storage engine, no direct SQLite** (provenance read via `ConceptStore.get_history`, a public API).
- **No per-question hardcoding** (proven by `test_answer_tracks_changed_definition_no_hardcoding`).
- **No Z3 added** to the conceptual path. **No LLM.**
- **No learning, no reflection** implemented.
- Confidence preserved from the reasoner (not inflated).
- Files modified: `hsci/core/cognitive_pipeline.py`; Files added: `hsci/response/explanatory_synthesizer.py`, `hsci/tests/test_vs2_explanatory_answer.py`.

---

## 11. Limitations

- The definition is a **retrieved** stored string, not a synthesised/paraphrased explanation. This is intentional and labelled as such.
- Reasoning remains shallow (edge restatement); VS-2 did not deepen it. Relationships are structurally true but not pedagogically rich.
- Knowledge breadth is still the 5 canonical OOP concepts.
- `WorkingMemory` is still populated by the CAE but not the reasoner's input; the dedicated Cognitive Workspace remains a future milestone (explicitly out of VS-2 scope).

---

## 12. Remaining Cognitive Gaps

- **Derivation (Capability E)**: still NO — no new knowledge is inferred (e.g., transitive closure).
- **Learning (Capability J)**: still NO — the pipeline is read-only.
- **Explanation depth**: definitions are surfaced but not elaborated; multi-concept synthesis is minimal.
- **Confidence calibration**: coarse rule-constant confidences remain.

---

## 13. Acceptance Criteria Matrix

| ID | Requirement | Result |
|---|---|---|
| VS2-AC1 | Java question runs through the real `CognitivePipeline` | PASS |
| VS2-AC2 | Intent = `ExplainConcept` | PASS |
| VS2-AC3 | `c_java_interface` resolved | PASS |
| VS2-AC4 | Real `abstract_rule` appears in the answer | PASS |
| VS2-AC5 | ≥1 real reasoning-supported relationship | PASS (7) |
| VS2-AC6 | Definition classified as retrieved, not reasoned | PASS (`knowledge_type="definition"`) |
| VS2-AC7 | Reasoning statements preserve rule/evidence | PASS |
| VS2-AC8 | No per-question hardcoding | PASS (definition-change test) |
| VS2-AC9 | No mock reasoning in primary E2E | PASS |
| VS2-AC10 | No direct SQLite access | PASS |
| VS2-AC11 | No new storage engine | PASS |
| VS2-AC12 | No Z3 added | PASS |
| VS2-AC13 | Empty/unknown degrades safely | PASS |
| VS2-AC14 | Existing regression green | PASS (276 passed, 0 failed) |
| VS2-AC15 | Generic across another seeded concept | PASS (class/method) |
| VS2-AC16 | Confidence not inflated | PASS (== reasoning confidence, <1.0) |
| VS2-AC17 | SCG-L5 authority untouched | PASS |

---

## 14. Final Verdict

**COMPLETE.**

The pipeline now produces an explanatory, definition-first, fully traceable answer for
concept-explanation questions, drawing the definition from stored concept knowledge and
supporting it with the real reasoning result — generically, deterministically, and
without touching SCG-L5 authority, storage, Z3, or introducing learning/reflection.
