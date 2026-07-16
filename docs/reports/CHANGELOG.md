# HSCI V4 — Change Log (CHANGELOG.md)

This changelog records all structural, architectural, and documentation changes in the HSCI repository, tracking the transition to V4.

---

## [4.0.0-beta.9] — 2026-07-16

### Added
*   **Cognitive Reasoning Engine (Sprint 11)**: Implemented logical reasoning controller `CognitiveReasoningEngine` and representation data structures (`ReasoningStep`, `Inference`, `Conclusion`, `ReasoningTrace`, `ReasoningResult`) in [reasoning_engine.py](file:///C:/Work/P/ai-model/hsci/reasoning/reasoning_engine.py).
*   **Inference Strategy Pattern**: Coded `IInferenceStrategy` and `RuleBasedInferenceStrategy` deriving generalization and namespace cohabitation relations.
*   **Consistency Validation Logic**: Built duplicate-circular prevention checks and negative contradiction warnings.
*   **End-to-End Demonstration**: Created [demo_reasoning_engine.py](file:///C:/Work/P/ai-model/hsci/knowledge/demo_reasoning_engine.py) showing the complete slice from user question parsing to cognitive spreading and CRE proof execution.
*   **Comprehensive Testing**: Coded test suite [test_reasoning_engine.py](file:///C:/Work/P/ai-model/hsci/tests/test_reasoning_engine.py) covering validation rules, explainability traces, concurrency safety, and benchmarks.
*   **Implementation Report**: Generated [Cognitive_Reasoning_Engine_Implementation_Report.md](file:///C:/Work/P/ai-model/docs/design/Cognitive_Reasoning_Engine_Implementation_Report.md).

---

## [4.0.0-beta.8] — 2026-07-14

### Added
*   **Understanding Engine MVP (Sprint 10)**: Created logical text parser block [understanding_engine.py](file:///C:/Work/P/ai-model/hsci/knowledge/understanding_engine.py) translating raw human strings into structured semantic result frames.
*   **Case-Insensitive Database Filtering**: Patched names, aliases, and versions queries in [concept_repository.py](file:///C:/Work/P/ai-model/hsci/knowledge/concept_repository.py) to use SQLite `COLLATE NOCASE`.
*   **8-Stage Parsing Pipeline**: Coded tokenizers, entity stem extractors, intent syntax classifies, and ambiguity checks.
*   **Piped Pipeline Demonstration**: Created [demo_understanding_engine.py](file:///C:/Work/P/ai-model/hsci/knowledge/demo_understanding_engine.py) to parse query inputs and pipe seed concepts directly to spreading activation loops in under `5ms`.
*   **Verification**: Wrote [test_understanding_engine.py](file:///C:/Work/P/ai-model/hsci/tests/test_understanding_engine.py) and ran all 199 project tests (zero regressions).
*   **Implementation Report**: Generated [Understanding_Engine_Implementation_Report.md](file:///C:/Work/P/ai-model/docs/design/Understanding_Engine_Implementation_Report.md).

---

## [4.0.0-beta.7] — 2026-07-14

### Added
*   **Concept Activation Engine (Sprint 9)**: Developed the main cognitive processing manager [concept_activation.py](file:///C:/Work/P/ai-model/hsci/knowledge/concept_activation.py) with pluggable strategy dispatch interfaces.
*   **Graph Spreading Activation**: Coded `GraphSpreadingActivationStrategy` propagating scores through generalizes relationships, overlapping aliases, and namespaces.
*   **8-Stage Reasoning Pipeline**: Built spreading activation steps tracking hop limits, decay rates, competitive inhibitions, and WorkingMemory populators.
*   **Tracable Explainability**: Every activated node tracks its initial seed source, complete path sequence, and logical propagation reason.
*   **Integration Demonstration**: Created vertical slice demonstration script [demo_concept_activation.py](file:///C:/Work/P/ai-model/hsci/knowledge/demo_concept_activation.py) verifying pipeline executions in `2.03ms`.
*   **Verification Suite**: Created unit and benchmarks tests [test_concept_activation_engine.py](file:///C:/Work/P/ai-model/hsci/tests/test_concept_activation_engine.py).
*   **Implementation Report**: Generated [Concept_Activation_Engine_Implementation_Report.md](file:///C:/Work/P/ai-model/docs/design/Concept_Activation_Engine_Implementation_Report.md).
