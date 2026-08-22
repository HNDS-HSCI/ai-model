# HSCI VS-6 — Runtime Trace Report
## Semantic Request Interpretation & Execution Traces

**Date**: August 2026  
**Status**: `VERIFIED`

---

## 1. Trace 1: Adversarial Paraphrase Convergence (EXPLAIN)

### Input:
`"I don't understand interfaces in Java."`

### 1. RawInput
- `original_text`: `"I don't understand interfaces in Java."`
- `normalized_text`: `"i don't understand interfaces in java"`

### 2. LanguageInterpreter & SemanticRequest
- `goal`: `CommunicativeGoal.EXPLAIN`
- `entity_mentions`: `[EntityMention(surface_form='interfaces in Java', normalized_form='java interface', confidence=0.92)]`
- `output_requirements`: `[OutputRequirement(output_type='EXPLANATION', depth=1)]`
- `is_negated`: `False` (pedagogical statement of incomprehension rather than query negation)
- `confidence`: `0.92`
- `source_method`: `"structural_explanation_frame"`

### 3. GroundingEngine
- `mention`: `"java interface"`
- `status`: `GroundingStatus.RESOLVED`
- `canonical_name`: `"Java Interface"` (`c_java_interface`)
- `situation.status`: `SituationStatus.GROUNDED`

### 4. TaskDeriver
- `action`: `TaskAction.EXPLAIN_CONCEPT`
- `primary_target`: `"Java Interface"`
- `parameters`: `{'concept_id': 'c_java_interface'}`

### 5. CognitiveTaskExecutor
- `direct_answer`: `"A Java interface is a reference type declaring abstract methods (and constants) that implementing classes must fulfil."`
- `derived_conclusions`: Transitive generalization to `Abstraction`.

---

## 2. Trace 2: Compound Negation & Exclusion Constraint

### Input:
`"Don't explain Java interface; compare Java interface and class."`

### 1. SemanticRequest
- `goal`: `CommunicativeGoal.COMPARE`
- `entity_mentions`: `[EntityMention(surface_form='Java interface', normalized_form='java interface'), EntityMention(surface_form='class', normalized_form='class')]`
- `relations`: `[SemanticRelation(source='java interface', relation_type='COMPARISON', target='class')]`
- `constraints`: `[SemanticConstraint(type='EXCLUSION', operator='NOT', value='explain Java interface', polarity=False)]`
- `output_requirements`: `[OutputRequirement(output_type='COMPARISON', depth=1)]`

### 2. GroundingEngine
- `Java interface` $\rightarrow$ `Java Interface` (`c_java_interface`) [RESOLVED]
- `class` $\rightarrow$ `Class` (`c_class`) [RESOLVED]
- `situation.status`: `SituationStatus.GROUNDED`

### 3. TaskDeriver
- `action`: `TaskAction.COMPARE_CONCEPTS`
- `primary_target`: `"Java Interface"`
- `secondary_targets`: `["Class"]`

### 4. CognitiveTaskExecutor
- Contrasts structural definitions, interfaces vs classes, and shared generalization (`Abstraction`).

---

## 3. Trace 3: Untrusted LLM Proposal Grounding & Rejection

### Input:
`"What is DarkMatterQuantumWarp?"`

### 1. Untrusted Proposal
- Proposer generates: `goal="EXPLAIN"`, `entities=["DarkMatterQuantumWarp"]`, `confidence=0.99`.

### 2. Sanitizer (`UntrustedSemanticProposer`)
- Strips fake identity metadata.
- Wraps into unverified `CandidateInterpretation` with `source_method="llm_untrusted_proposal"`.

### 3. GroundingEngine
- Evaluates mention `"DarkMatterQuantumWarp"`.
- UKM lookup returns NO match.
- `ge.status = GroundingStatus.UNKNOWN`.
- `situation.status = SituationStatus.UNRESOLVED_ENTITIES`.

### 4. TaskDeriver & Executor
- `action`: `TaskAction.REPORT_UNKNOWN`
- Response: Transparent refusal reporting missing concept without hallucination. Confidence: `0.0`.
