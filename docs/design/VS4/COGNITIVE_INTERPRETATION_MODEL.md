# HSCI Cognitive Interpretation & Task Derivation Model (VS-4)

## Conceptual Architecture & Contract Specification

```text
                               Arbitrary Human Language Input
                                             ↓
                                    [ RawInput Model ]
                               (Verbatim Text, Normalized, Context)
                                             ↓
                                [ LanguageInterpreter ]
                      ┌──────────────────────┴──────────────────────┐
                      │                                             │
             Structural Frame Parsing                      Untrusted LLM Proposal
         (Compare, Relate, Purpose, Explain)              (Semantic Hypotheses Only)
                      │                                             │
                      └──────────────────────┬──────────────────────┘
                                             ↓
                                  [ InterpretationSet ]
                              (CandidateInterpretations)
                                             ↓
                                    [ GroundingEngine ]
                              (Authoritative UKM Validation)
                      ┌──────────────────────┼──────────────────────┐
                      │                      │                      │
                   Resolved              Ambiguous               Unknown
                   Entities               Aliases               Entities
                      │                      │                      │
                      └──────────────────────┬──────────────────────┘
                                             ↓
                                  [ CognitiveSituation ]
                      (SituationStatus, GroundedEntities, Assumptions)
                                             ↓
                                     [ TaskDeriver ]
                       (Deterministic State Machine Derivation)
                                             ↓
                                     [ CognitiveTask ]
                  (EXPLAIN, COMPARE, RELATE, REPORT_REFUSAL / DIAGNOSTIC)
                                             ↓
                                [ HSCI Cognitive Stack ]
                     (CAE Activation → CRE Reasoning → Synthesizer)
```

---

## 1. Core Principles

1. **Non-Destructive Interpretation**: Raw user input is never discarded. Interpretations are candidate hypotheses that declare their assumptions, evidence, and confidence.
2. **Authoritative UKM Grounding**: The Universal Knowledge Model is the sole authority on domain truth, concept definitions, and relationship validity. No language parser or LLM can assert the existence of concepts without UKM verification.
3. **Explicit Ambiguity Preservation**: When an alias or term maps to multiple competing concepts, the system preserves all candidate matches and reports ambiguity rather than silently picking an arbitrary index.
4. **Deterministic Task Derivation**: Grounded situations are mapped to executable tasks through deterministic transition rules, ensuring reproducible behavior and explainable provenance.
5. **Calibrated Confidence & Refusal**: The system cleanly distinguishes between unknown knowledge, ambiguous phrasing, missing conversational context, and verified reasoning.
