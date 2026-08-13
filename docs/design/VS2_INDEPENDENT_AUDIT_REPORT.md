# HSCI VS-2 — Independent Adversarial Audit Report

**Type**: Read-only adversarial audit (no production code, tests, or architecture modified)
**Date**: 2026-08-09
**Method**: The real pipeline was executed under adversarial probes (mutation, reasoning-removal, genericity sweep, negative knowledge, no-definition concept) via a temporary scratchpad harness; production was grepped for hardcoding; both pytest commands were run. Temporary instrumentation removed after capture.
**Subject**: `hsci/response/explanatory_synthesizer.py`, `hsci/core/cognitive_pipeline.py` (VS-2), and their real integration.

---

## 1. Executive Verdict

**VERIFIED WITH MINOR FINDINGS.**

VS-2 is **genuinely integrated, generic, traceable, and honest**. The final definition is really retrieved from `c_java_interface.abstract_rule` through `KnowledgeManager` (a mutation of the stored value changes the answer verbatim), the supporting relationships really come from the `ReasoningResult` (removing a conclusion removes exactly that supporting line while the definition survives), confidence is inherited unchanged from the reasoner (not inflated), and unknown concepts degrade with no fabrication. No hardcoded question-specific logic exists.

The findings are **test-quality gaps, not integration defects**: one parametrized generic test has conditional assertions (and a mislabeled parameter), and the "existing concept without a definition" negative case is exercised in this audit but not by the committed suite. Neither weakens the production behavior, which is correct.

Honest capability framing: VS-2 delivers **RETRIEVAL + COMPOSITION** on top of the pre-existing **shallow REASONING**. It does **not** add derivation, verification, or learning — and does not claim to.

---

## 2. Scope

Audited VS-2's production files and their real runtime behavior; the reasoning/knowledge/activation engines as consumed; and the 10 VS-2 tests. Read-only. No fixes applied.

---

## 3. Runtime Trace (real, no mocks)

`Explain what a Java interface is.`
```
answer type   : ExplanatoryAnswer
direct_answer : A Java interface is a reference type declaring abstract methods (and constants) that implementing classes must fulfil.
primary       : c_java_interface / Java Interface
definition == c_java_interface.abstract_rule : True
knowledge_sources : 1 definition, 7 reasoned_relationship
confidence    : 0.9071 (High)
```
Causal chain confirmed: Understanding (`ExplainConcept`, seed `Java Interface`) → KnowledgeManager resolution → ConceptActivation (5 concepts) → workspace `List[Concept]` → CognitiveReasoningEngine (7 conclusions) → AnswerGenerationEngine (base) → ExplanatoryAnswerSynthesizer (definition-first).

---

## 4. Definition Provenance Audit

- `answer.definition` is **identical** to `c_java_interface.abstract_rule` (runtime equality `True`).
- Retrieved via `KnowledgeManager.get_concept()` → `ConceptStore` → `ConceptRepository` → `SQLiteProvider`; provenance via `ConceptStore.get_history()` → `source_type=CANONICAL_SEED`.
- **No direct SQLite** in VS-2 code; **no duplicated definition** stored; **no hardcoded Java text** (grep of both production files found only the word "hardcoding" in a comment).
- **Mutation test** (harness, in-memory DB): changed the stored `abstract_rule` to `"MUT4TED definition body for audit only"` → the answer's `direct_answer` became exactly that string; restoring reverted it. **Proves real retrieval, not hardcoding.**

---

## 5. Genericity Audit

Grep of `explanatory_synthesizer.py` and `cognitive_pipeline.py` for `java`, `c_java_interface`, `interface`, `inheritance`, `polymorph`: **no question-specific logic** (only a comment). Runtime sweep over all seeded concepts:

| Question | Explanatory? | Primary | Definition matches store |
|---|---|---|---|
| Explain what a Java interface is. | Yes | c_java_interface | Yes |
| Explain what an interface is. | Yes | c_interface | Yes |
| Explain what a class is. | Yes | c_class | Yes |
| Explain what a method is. | Yes | c_method | Yes |
| Explain what abstraction is. | Yes | c_abstraction | Yes |
| Explain what inheritance is. | No (base answer) | — | — (not seeded) |
| Explain what polymorphism is. | No (base answer) | — | — (not seeded) |

**Generic: PASS.** Observation (not a VS-2 defect): the audit brief's example concepts *inheritance* and *polymorphism* are **not in the UKM** (only 5 OOP concepts are seeded), so they correctly return the non-fabricating base answer. Knowledge breadth — not VS-2 synthesis — is the limiter there.

---

## 6. Reasoning Independence Audit

Adversarial harness: captured the full synthesis (7 reasoned sources), then dropped the first conclusion from a copied `ReasoningResult` and re-synthesized.
```
reasoned sources: full=7  partial=6
dropped conclusion present:  full=True  partial=False
definition survives removal: True
```
This proves the required dependency structure:
```
Supporting relationship  ← ReasoningResult   (disappears when the conclusion is removed)
Definition               ← UKM               (survives)
```
The answer is **not** a hardcoded synthesizer output.

---

## 7. Traceability Audit

- **Definition** `KnowledgeSource`: `knowledge_type="definition"`, `source_concept_id=c_java_interface`, `source_concept_name="Java Interface"`, `source_provenance={source_type: CANONICAL_SEED, confidence: 1.0, ...}`, `content=<definition>`. ✔
- **Reasoned** `KnowledgeSource` (×7): `knowledge_type="reasoned_relationship"`, `reasoning_conclusion`, `reasoning_rule` (deterministically recovered from the conclusion's fixed statement format), `reasoning_confidence`, `reasoning_evidence` (verbatim from the reasoner). ✔
- **No fabricated proof IDs**: none are invented; the code preserves the reasoner's evidence instead (architecture has no proof-trace ID on `Conclusion`). ✔

---

## 8. Confidence Audit

```
reasoning_result.confidence = 0.907143
answer.confidence.score     = 0.907143   (equal, < 1.0)
```
When reasoning conclusions exist, the synthesizer **inherits** the base answer's reasoning confidence unchanged — verified by reading `_confidence()` and by runtime equality. The definition's own retrieval confidence (1.0, CANONICAL_SEED) is recorded on its `KnowledgeSource` but does **not** raise the overall answer confidence. **No inflation.** (Definition-only edge: confidence would use the retrieval provenance confidence, clearly labeled retrieval; not exercised by the Java case.)

---

## 9. Negative Knowledge Audit

- **Unknown concept** ("Explain what Quantum Computer Xyzabc is."): returns a base `Answer` (not `ExplanatoryAnswer`), `definition=None`, `direct_answer="Reasoning Engine was unable to resolve the query."` — **no fabricated definition, no invented relationship, no fake confidence.**
- **Existing concept with no definition** (harness emptied `c_method.abstract_rule`): returns `ExplanatoryAnswer` with `definition=None` and falls back to the reasoned-relationship listing — **no fabricated definition**, graceful degradation. ✔

---

## 10. Architecture Boundary Audit

`git diff` confirms VS-2 modified **no** protected file. Untouched (verified no diff): `answer_generation_engine.py`, `concept_activation.py`, `understanding_engine.py`, `knowledge_manager.py`, `storage.py`, `concept_store.py`. Not edited by VS-2: `reasoning_engine.py`, `z3_verifier.py`, `htn_planner.py`, `BrainKernel`, `RIRLoop`, SkillGraph, lifecycle (pre-existing working-tree diffs on the first three predate this whole session).

| Check | Result |
|---|---|
| New storage engine | None |
| Duplicate knowledge database | None |
| Direct SQLite | None |
| LLM dependency | None |
| Z3 added to this path | None |
| Learning / reflection / planning path | None |
| KnowledgeManager gateway bypass | None (sole gateway used) |
| BrainKernel bypass | Yes — intentional and pre-existing (shell), not introduced by VS-2 |

VS-2 is a purely additive answer-synthesis layer.

---

## 11. WorkingMemory Audit

Current, unchanged relationship (VS-2 did not alter it):
```
ConceptActivationEngine → WorkingMemory   (populated: activation_field keys = 5 concept IDs)
CognitiveReasoningEngine.reason(active_concepts: List[Concept], context, reasoning_context)  → ReasoningResult
                                  └─ takes List[Concept], NOT WorkingMemory
ExplanatoryAnswerSynthesizer → Concept knowledge (fresh get_concept) + ReasoningResult
```
`reason()`'s signature confirms `WorkingMemory` is **not** the reasoner's concept source. VS-2 did **not** make WorkingMemory appear authoritative — the synthesizer reads concept objects directly via `KnowledgeManager`, not from WorkingMemory. The `AnswerGenerationEngine` still reads only `working_memory.activation_field` keys for metadata (unchanged).

---

## 12. Test Audit (exact output)

`pytest hsci/tests/test_vs2_explanatory_answer.py -q`
```
10 passed in 0.50s        [exit code 0]
```

`pytest hsci/tests/ -q`
```
276 passed, 489 warnings in 323.23s (0:05:23)    [exit code 0]
```
(passed=276, failed=0, errors=0, warnings=489, exit=0. Full-suite exact line reproduced in §18.)

---

## 13. Test Quality Assessment

All 10 VS-2 tests use **real engines** (no mocks; the only mock-based test, orchestration ordering, lives in the VS-1 file). A broken definition-retrieval integration would fail the mutation and traceability tests, so the suite cannot pass while the core integration is broken.

| Test | Real? | Strength |
|---|---|---|
| `test_java_interface_definition_appears` | Real | STRONG |
| `test_generic_concept_definition_appears` (×3) | Real | **WEAK** — assertions guarded by `if isinstance(...) and ans.definition`; one param (`"What is inheritance" → c_interface`) does not resolve, so its body is skipped |
| `test_class_definition_is_generic` | Real | STRONG (unconditional genericity) |
| `test_traceability_definition_and_reasoning` | Real | STRONG |
| `test_answer_tracks_changed_definition_no_hardcoding` | Real | STRONG (mutation) |
| `test_unknown_concept_no_fabricated_definition` | Real | STRONG (negative) |
| `test_confidence_not_inflated` | Real | STRONG |
| `test_non_explanation_intent_returns_base_answer` | Real | ADEQUATE |

**Overall: STRONG**, with two minor gaps:
- **Finding A (minor)**: the parametrized generic test is soft (conditional asserts; mislabeled `inheritance→c_interface` param). Genericity is nonetheless strongly covered by `test_class_definition_is_generic` and this audit's 5-concept sweep.
- **Finding B (minor)**: no committed test for "existing concept with no stored definition" (the VS-2 brief's Test 5b). Behavior is correct (verified here) but unguarded by CI.

Neither can mask a broken integration; both are test-coverage hygiene items.

---

## 14. Usefulness Assessment

Answer for *"Explain what a Java interface is."*, judged against the HSCI architecture (not as an LLM answer):

| Dimension | Verdict |
|---|---|
| Definition correctness | Good — the retrieved definition is accurate and on-topic |
| Relevance | Good — primary concept correctly identified |
| Supporting reasoning | Fair — true but shallow (edge restatements, incl. an off-topic "namespace cohabitation" line) |
| Clarity | Good — definition-first, then labeled supporting relationships |
| Traceability | Strong — every line has a typed source (retrieved vs reasoned) with provenance/evidence |
| Honesty | Strong — retrieval and reasoning are separated; no inflation; unknowns not fabricated |

Net: a **useful, honest, retrieval-plus-shallow-reasoning explanation** — a real improvement over VS-1's edge dump, and correctly scoped to what the architecture can actually do.

---

## 15. Cognitive Capability Matrix (observed)

| Capability | Verdict | Evidence |
|---|---|---|
| Understand user question | YES | intent `ExplainConcept`, entities extracted |
| Retrieve stored knowledge | YES | definition == stored `abstract_rule` (mutation-verified) |
| Identify relevant concepts | YES | seed `Java Interface` resolved |
| Activate related concepts | YES | 5 concepts, scored spreading activation |
| Use stored definitions | YES | **new in VS-2** — surfaced in the answer |
| Combine knowledge | PARTIAL | definition + relationships juxtaposed, not fused into new statements |
| Derive NEW knowledge | NO | drop-test shows 1:1 edge restatement; no transitive/derived facts |
| Reason over relationships | PARTIAL | deterministic edge enumeration only |
| Explain WHY | PARTIAL | definition + evidence, but no causal explanation |
| Verify conclusions | NO (this path) | internal consistency only; no Z3 |
| Detect insufficient knowledge | PARTIAL | unknown → graceful "unable to resolve"; no partial-coverage signal |
| Express uncertainty | PARTIAL | confidence + High/Med/Low band; coarse |
| Learn from interaction | NO | read-only pipeline |
| Reflect on errors | NO | no reflection path |
| Plan multi-step actions | NO | no planner in this path |

---

## 16. Remaining Bottleneck

**Reasoning derivation.**

Runtime evidence: the reasoning-independence probe shows every conclusion is a verbatim restatement of a stored edge; no transitive closure (e.g., "Java Interface generalizes to Abstraction") and no multi-concept synthesis are produced. VS-2 correctly solved the *surfacing* gap, so the system is now a solid **retrieval + composition** engine — but "Derive NEW knowledge" and "Combine knowledge" remain NO/PARTIAL. The single next architectural capability to move HSCI toward a *genuinely reasoning* system is a reasoning engine that **derives new propositions** (transitive/relational inference, property inheritance, multi-concept synthesis) rather than enumerating edges. This is neither storage, workspace, nor learning.

---

## 17. Recommendation

Pursue **reasoning derivation** next (a bounded, deterministic inference upgrade: transitive closure over `generalizes_to`, property inheritance, and multi-concept synthesis), keeping it SCG-L5-neutral and traceable. A minimal Cognitive Workspace may be introduced only insofar as it serves derivation. Defer Learning (see §18). Optionally close the two minor test gaps (Findings A/B) as hygiene.

---

## 18. Learning Readiness

**NOT READY — do not begin the Learning Engine now.**

Learning needs something meaningful to learn from: derived conclusions, an experience/feedback representation, an error representation, and reflection. The current pipeline has **none** — reasoning only restates stored edges, there is no reflection or error model, and nothing is persisted back. Reinforcing edge-restatement would learn nothing of value and would risk polluting the canonical store. Learning should follow **after** reasoning derivation (and ideally verification + an experience/error model) exist. Its presence on the roadmap is not sufficient justification to start.

Exact full-regression line:
```
276 passed, 489 warnings in 323.23s (0:05:23)
```

---

## Acceptance Criteria (audit)

| Audit check | Result |
|---|---|
| Definition genuinely retrieved from UKM | PASS (mutation-verified) |
| No hardcoded / question-specific logic | PASS (grep + runtime sweep) |
| Genericity across seeded concepts | PASS (5/5) |
| Relationships depend on ReasoningResult | PASS (drop-test) |
| Retrieved vs reasoned classification explicit | PASS |
| Traceability complete, no fake provenance | PASS |
| Confidence not inflated | PASS (inherited, <1.0) |
| Negative/empty knowledge degrades safely | PASS |
| Architecture boundaries intact | PASS |
| WorkingMemory not falsely authoritative | PASS |
| Tests pass (file + full suite) | PASS (10; 276) |
| Test quality | STRONG with 2 minor gaps (Findings A, B) |

---

## 19. Final Verdict

**VERIFIED WITH MINOR FINDINGS.**

VS-2 is real, generic, traceable, honest, and architecturally clean. It delivers retrieval + composition over the existing shallow reasoning, without overclaiming. The only findings are two minor test-quality gaps (soft parametrized generic test; missing automated "existing-concept-without-definition" case) — both correct at runtime, neither able to mask a broken integration. The next architectural priority is **reasoning derivation**; **learning is not yet warranted**.

**AUDIT ONLY — no production code, tests, or architecture modified. No fixes applied. Not proceeding to VS-3. Nothing committed.**
