# HSCI VS-5 — Preflight Reality Audit Report
## Cognitive Task Execution & Real User Interaction

**Date**: August 2026  
**Auditor**: Antigravity Cognitive Architecture Team  
**Scope**: Preflight audit of existing cognitive task derivation and execution pathways across `CognitiveTask`, `TaskDeriver`, `CognitivePipeline`, `ExplanatoryAnswerSynthesizer`, `CognitiveReasoningEngine`, `brain_api.py`, and test suites.

---

## 1. Executive Summary

Sprint VS-4 successfully implemented the front-end cognitive boundary (`RawInput` $\rightarrow$ `LanguageInterpreter` $\rightarrow$ `InterpretationSet` $\rightarrow$ `GroundingEngine` $\rightarrow$ `CognitiveSituation` $\rightarrow$ `TaskDeriver` $\rightarrow$ `CognitiveTask`).

However, our audit of the execution phase reveals a **semantic execution gap**:
1. **Task Execution is Inlined**: In `CognitivePipeline.answer()`, once a `CognitiveTask` is produced, it is not passed to a dedicated `CognitiveTaskExecutor`. Instead, execution logic is partially hardcoded inside `answer()` and partly routed through legacy explanation-specific pipelines.
2. **Comparison Tasks Lack Dedicated Execution**: For `COMPARE_CONCEPTS` (`TaskAction.COMPARE_CONCEPTS`), both concepts are grounded and activated, but `ExplanatoryAnswerSynthesizer` picks only **one** primary concept via `_select_primary()` and outputs only that concept's definition in the main section. It does not perform a structured multi-concept comparison across both concepts' definitions and relationship graphs.
3. **Relationship Tasks Lack Target Filtering**: For `DERIVE_RELATIONSHIP` (`TaskAction.DERIVE_RELATIONSHIP`), the reasoning engine derives transitive generalizations (e.g. `Java Interface -> Abstraction`), but the response lists all workspace relationships without highlighting the specific derived path between source and target concepts.
4. **API Intent Hardcoding**: In `brain_api.py` line 153, the response payload hardcodes `"intent": "ExplainConcept"`, ignoring the derived `CognitiveTask` action (`COMPARE_CONCEPTS`, `DERIVE_RELATIONSHIP`, etc.).

---

## 2. Current Runtime Call Graph

```text
User / HTTP Request
      ↓
[ brain_api.py /process ]
      ↓
[ CognitivePipeline.answer(question) ]
      ↓
[ RawInput.from_text ]
      ↓
[ LanguageInterpreter.interpret ]
      ↓
[ GroundingEngine.ground ]
      ↓
[ TaskDeriver.derive ] → emits CognitiveTask (action, primary_target, secondary_targets)
      ↓
[ Inlined Pipeline Logic in answer() ]
 ├─ If REPORT_INSUFFICIENT_CONTEXT → returns Answer (refusal)
 ├─ If REPORT_AMBIGUITY → returns Answer (refusal)
 ├─ If REPORT_UNKNOWN → returns Answer (refusal)
 └─ If Grounded (EXPLAIN / COMPARE / DERIVE):
      ↓
    [ ConceptActivationEngine.activate_concepts ]
      ↓
    [ CognitiveReasoningEngine.reason ]
      ↓
    [ AnswerGenerationEngine.generate ]
      ↓
    [ ExplanatoryAnswerSynthesizer.synthesize ]
```

---

## 3. Detailed Audit Findings by Task Action

| TaskAction | Grounding Status | Current Execution Path | Current Limitations |
| :--- | :--- | :--- | :--- |
| **`EXPLAIN_CONCEPT`** | Fully Grounded | Actives primary seed $\rightarrow$ Reasons $\rightarrow$ Synthesizes definition-first answer | Fully working and verified. |
| **`COMPARE_CONCEPTS`** | Fully Grounded (2+ concepts) | Activates all seeds $\rightarrow$ Reasons $\rightarrow$ Single-concept synthesizer | **GAP**: Synthesizer chooses `max(score)` and formats only one definition. Does not contrast Concept A vs Concept B. |
| **`DERIVE_RELATIONSHIP`** | Fully Grounded (2 concepts) | Activates all seeds $\rightarrow$ Reasons (Transitive rules) $\rightarrow$ Synthesizer | **GAP**: Lists general relationships; does not isolate and highlight the causal path between Source and Target. |
| **`REPORT_UNKNOWN`** | Entity Unresolved | Direct refusal `Answer(confidence=0.0)` | Fully working (Zero hallucination). |
| **`REPORT_AMBIGUITY`** | Ambiguous Alias | Direct refusal `Answer(confidence=0.0)` | Fully working (Preserves all candidates). |
| **`REPORT_INSUFFICIENT_CONTEXT`** | Missing Referent | Direct refusal `Answer(confidence=0.0)` | Fully working (No guessing). |

---

## 4. Reusable Existing Components

1. `hsci/cognition/interpretation/models.py`: Strongly typed `CognitiveTask`, `TaskAction`, `CognitiveSituation`, `GroundedEntity`.
2. `hsci/cognition/interpretation/interpreter.py`: Structural frame extraction.
3. `hsci/cognition/interpretation/grounding.py`: Authoritative UKM grounding.
4. `hsci/cognition/interpretation/task_deriver.py`: Deterministic task construction.
5. `hsci/knowledge/knowledge_manager.py`: Authoritative UKM facade.
6. `hsci/knowledge/concept_activation.py`: Spreading activation.
7. `hsci/reasoning/reasoning_engine.py`: Rule-based reasoning with transitive closure.
8. `hsci/response/answer_generation_engine.py`: Structured base answer generation.
9. `hsci/response/explanatory_synthesizer.py`: Provenance-aware answer synthesis.

---

## 5. Architectural Recommendation for VS-5

To make the system truly execute distinct cognitive tasks without breaking existing contracts:

1. **Implement `CognitiveTaskExecutor`** in `hsci/cognition/execution/task_executor.py`:
   - Receives `CognitiveTask`, `CognitiveSituation`, `IKnowledgeManager`, `ConceptActivationEngine`, `CognitiveReasoningEngine`, `AnswerGenerationEngine`, `ExplanatoryAnswerSynthesizer`, and `CognitiveContext`.
   - Dispatches cleanly to task handlers:
     - `_execute_explain_concept(task, situation, context)`
     - `_execute_compare_concepts(task, situation, context)`
     - `_execute_derive_relationship(task, situation, context)`
     - `_execute_report_refusal(task, situation, context)`
2. **Multi-Concept Comparison Execution**:
   - For `COMPARE_CONCEPTS`, retrieve definitions and generalizations for *both* Target A and Target B.
   - Contrast shared generalizations (e.g. both generalize to `Abstraction`) vs distinct characteristics (e.g. `Java Interface` declares abstract methods; `Class` provides concrete implementation).
   - If one concept lacks stored definition or relationships, honestly report degraded/insufficient comparison knowledge.
3. **Targeted Relationship Derivation Execution**:
   - For `DERIVE_RELATIONSHIP`, filter reasoning conclusions for paths connecting `source_concept` and `target_concept`.
   - Report the exact derivation rule, premises, and depth.
4. **Wire `CognitivePipeline` to `CognitiveTaskExecutor`**:
   - Delegate all task execution from `CognitivePipeline.answer()` directly to `CognitiveTaskExecutor.execute(task, situation, context)`.
5. **Update `brain_api.py`**:
   - Pass dynamic task action as `intent` and forward complete deliberation and provenance.

---

## 6. Explicit Non-Goals

- NO replacement or modification of `LanguageInterpreter` or `GroundingEngine`.
- NO LLM integration for response generation.
- NO `LearningEngine`, `ReflectionEngine`, or `MentalModelEngine`.
- NO direct SQLite access bypassing `KnowledgeManager`.
- NO question-specific hardcoded responses.
