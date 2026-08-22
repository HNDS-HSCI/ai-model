# HSCI VS-6 — Preflight Reality Audit Report
## Semantic Representation → Grounded Cognitive Situation → Task Derivation

**Date**: August 2026  
**Auditor**: Antigravity Cognitive Architecture Team  
**Scope**: Reality audit of existing linguistic interpretation, semantic loss, syntactic pattern dependencies, and representation boundaries across `LanguageInterpreter`, `CandidateInterpretation`, `GroundingEngine`, `TaskDeriver`, and `CognitivePipeline`.

---

## 1. Executive Summary

In VS-4 and VS-5, HSCI established a working deterministic boundary:
`RawInput` $\rightarrow$ `LanguageInterpreter` $\rightarrow$ `InterpretationSet` $\rightarrow$ `GroundingEngine` $\rightarrow$ `CognitiveSituation` $\rightarrow$ `TaskDeriver` $\rightarrow$ `CognitiveTask` $\rightarrow$ `CognitiveTaskExecutor`.

However, an in-depth audit of the language interpretation layer reveals that it relies primarily on **surface syntactic frames (regexes)** and **heuristic sliding-window token chunking**. While effective for seeded syntactic canonical forms, this architecture has critical semantic limitations:
1. **Linguistic Form vs Cognitive Meaning**: Requests with identical communicative goals (e.g. `"I don't understand interfaces"`, `"Give me an explanation of interfaces"`, `"What is an interface?"`) require explicit regex patterns rather than mapping into a canonical semantic communicative goal.
2. **Missing Granular Semantic Structure**: `CandidateInterpretation` only stores flat lists: `candidate_entity_mentions: List[str]`, `constraints: List[str]`, `assumptions: List[InterpretationAssumption]`. It lacks structured representations for **Semantic Goals**, **Entity Mentions with Spans & Resolution State**, **Untyped Semantic Relations**, **Polarity/Negation/Modality**, **Output Requirements**, and **Context References**.
3. **Loss of Negation and Modality**: Inputs like `"Don't explain X; compare X and Y"` or `"X is not Y"` risk dropping negation or misclassifying intents because negation is not modeled as a first-class property in the representation.
4. **Fragile Compound Multi-Intent Parsing**: Multi-clause queries (e.g. `"Explain X, compare it with Y, and tell me why the difference matters"`) pick the first matching sentence and discard remaining semantic directives.

---

## 2. Answers to the 16 Audit Questions

| # | Question | Current System Reality & Finding |
|---|:---|:---|
| **1** | **Which parts depend on regex?** | `LanguageInterpreter._analyze_structure()` uses 12 regex patterns for Comparison, Relationship, Purpose, and Explanation frames, plus pronoun detection. |
| **2** | **Which parts depend on keywords?** | Sentence focus selection searches for keywords (`["explain", "what", "how", "compare", "why", "difference", "relate"]`). GroundingEngine checks UKM concept names/aliases. |
| **3** | **Which parts depend on exact phrase structures?** | Patterns like `how is X different from Y`, `difference between X and Y`, `why do X exist`, `what purpose does X serve`. |
| **4** | **Which information is lost?** | Modality (can/should/must), negation (not/never), temporal/conditional clauses (if/before/after), granular output format desires (definition vs summary vs proof). |
| **5** | **Which semantic information survives?** | Intent name (`ExplainConcept`, `CompareConcepts`, `FindRelationship`), extracted entity mention substrings, deictic pronoun presence flag. |
| **6** | **Which linguistic variations produce different results?** | Active vs passive phrasings without specific verbs can fail syntactic frame matching and fall back to token-chunk sliding windows. |
| **7** | **Which variations incorrectly produce the same result?** | `"Why does X exist"` and `"What is X"` both currently collapse to `ExplainConcept` with identical single-concept extraction. |
| **8** | **How are entities identified?** | Through regex capture groups (`group(1)`, `group(2)`) or heuristic 1-to-3 token sliding windows over the query text. |
| **9** | **How are relations identified?** | By specific framing markers (`"between X and Y"`, `"X relates to Y"`). No independent semantic relational graph exists prior to grounding. |
| **10** | **How are constraints represented?** | Flat `List[str]`; no structured operator (`ONLY`, `EXCLUDE`, `AT_LEAST`), polarity, or target entity linkage. |
| **11** | **How is desired answer type represented?** | Not represented in interpretation; downstream defaults to definition + supporting relationships. |
| **12** | **How is uncertainty represented?** | Numeric confidence floats (0.0 to 1.0) and textual `InterpretationAssumption` objects. |
| **13** | **How is conversational context represented?** | Boolean flag `requires_context: bool` and deictic evidence objects. No conversational session history resolution. |
| **14** | **Can multiple candidate interpretations coexist?** | Yes, `InterpretationSet.candidates` holds a list of hypotheses, but GroundingEngine currently only evaluates candidate `[0]`. |
| **15** | **Does the current representation have enough expressive power?** | **No**. It lacks structured goal schemas, explicit entity mention metadata (spans/surface forms), semantic relation tuples, negation/modality, and output constraints. |
| **16** | **Where would a semantic intermediate representation fit?** | Between `RawInput` and `CognitiveSituation`: `RawInput` $\rightarrow$ `SemanticRequest` $\rightarrow$ `InterpretationSet` $\rightarrow$ `GroundingEngine` $\rightarrow$ `CognitiveSituation`. |

---

## 3. Recommended Minimal Semantic Architecture for VS-6

1. **Implement `CognitiveRequestRepresentation` / `SemanticRequest`** (`hsci/cognition/interpretation/semantic_model.py`):
   - **`CommunicativeGoal`**: `EXPLAIN`, `COMPARE`, `RELATE`, `IDENTIFY`, `VERIFY`, `SUMMARIZE`, `ANALYZE`, `CLARIFY`, `UNKNOWN`.
   - **`EntityMention`**: `surface_form`, `normalized_form`, `candidate_identity`, `span_start`, `span_end`, `confidence`, `status`.
   - **`SemanticRelation`**: `source_mention`, `relation_type` (`COMPARISON`, `RELATIONSHIP`, `ASSOCIATION`, `INHERITANCE`), `target_mention`, `confidence`.
   - **`SemanticConstraint`**: `constraint_type` (`EXCLUSION`, `RESTRICTION`, `CONDITION`, `SCOPE`), `operator`, `value`, `polarity`.
   - **`OutputRequirement`**: `output_type` (`DEFINITION`, `COMPARISON`, `PROOF_TRACE`, `EXPLANATION`, `VERIFICATION`), `depth`, `style`.
   - **`ContextReference`**: `marker`, `reference_type` (`PRONOUN`, `DEFINITE_NP`, `ANAPHORA`), `is_resolved`.
   - **`Modality` & `Negation`**: `is_negated: bool`, `modality: str` (`ASSERTION`, `HYPOTHETICAL`, `DEONTIC`, `EPISTEMIC`).

2. **Semantic Normalizer & Semantic Interpreter (`SemanticInterpreter`)**:
   - Converts natural linguistic variations to canonical `SemanticRequest` hypotheses without regex explosions.
   - Preserves negation (`"not X"`, `"don't explain X"`), modal operators, and context references.

3. **Untrusted Semantic Proposer Interface**:
   - Formal schema for external/LLM semantic proposals (strictly typed; cannot invent UKM concepts or domain facts).

4. **Multi-Hypothesis Grounding & Task Derivation**:
   - `GroundingEngine` grounds entity mentions and validates semantic relations against UKM.
   - `TaskDeriver` deterministically maps verified semantic requests to `CognitiveTask`.

---

## 4. Explicit Non-Goals

- NO regex pattern proliferation.
- NO hardcoded phrase dictionaries.
- NO LLM answer generation or hallucinated domain authority.
- NO bypassing the Universal Knowledge Model.
- NO implementation of `LearningEngine`, `ReflectionEngine`, or `MentalModelEngine`.
