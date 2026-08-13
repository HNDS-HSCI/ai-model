# HSCI VS-3 — Reasoning Derivation Preflight Report

**Type**: Preflight only (no production code, tests, or architecture modified)
**Date**: 2026-08-09
**Predecessors**: `VS1_IMPLEMENTATION_REPORT.md`, `VS2_PREFLIGHT_REPORT.md`, `VS2_IMPLEMENTATION_REPORT.md`, `VS2_INDEPENDENT_AUDIT_REPORT.md`
**Bottleneck being addressed**: Reasoning derivation (independently identified in the VS-2 audit).

---

## 1. Executive Summary

HSCI can retrieve, activate, restate, and explain — but it cannot yet **derive**. Every current "conclusion" is a 1:1 restatement of a single stored edge; no conclusion is produced that is absent from the store, and no rule combines two independent premises.

The smallest architecturally correct way to introduce genuine derivation is a **transitive-closure rule over `Concept.generalizes_to`**, added at the existing **`IInferenceStrategy`** extension point inside `CognitiveReasoningEngine`. The seeded graph already contains a legitimate two-premise chain whose conclusion is **not stored**:

```
Premise 1:  Java Interface  --generalizes_to-->  Interface     (c_java_interface → c_interface)
Premise 2:  Interface       --generalizes_to-->  Abstraction   (c_interface → c_abstraction)
Rule:       Generalization Transitivity
Derived:    Java Interface  --generalizes_to-->  Abstraction   (NOT in c_java_interface.generalizes_to)
```

This requires **no Cognitive Workspace, no Z3, no Learning, no Reflection, no Planning, no LLM, and no new storage**. It requires a small, additive extension of the inference layer plus additive provenance fields on the existing `Inference`/`Conclusion` models.

**Verdict: READY FOR IMPLEMENTATION.**

---

## 2. Current Reasoning Architecture

- **Engine**: `CognitiveReasoningEngine.reason(active_concepts: List[Concept], context, reasoning_context)` (`hsci/reasoning/reasoning_engine.py:186`). Iterative `while` loop bounded by `ReasoningContext.max_steps` (default 10), with `known_statements` dedup, circular-reasoning rejection, and contradiction detection.
- **Strategy pattern**: `IInferenceStrategy.infer(active_concepts, context) -> List[Inference]` (ABC). Current implementation `RuleBasedInferenceStrategy` holds 3 rules. `CognitiveReasoningEngine.inference_strategy = RuleBasedInferenceStrategy()` — a clean, designed injection point.
- **Knowledge shape**: concept-to-concept relationships are expressed **only** as `Concept.generalizes_to: List[str]` (target concept IDs), persisted in the `ukm_concept_generalizes_to` table (FK on `concept_id` only). There is no separate first-class edge object in the V4 path. (`data_types.py:362 Relationship` is a **perception-layer** type for the V3 `RIRLoop` stack, unused by the V4 reasoner.)
- **Iteration caveat**: the loop passes the **same** `active_concepts` every iteration and does **not** feed derived conclusions back as premises, so `infer()` returns the same set each pass; step 2 yields nothing and the loop halts. Multi-step premise chaining across iterations is therefore **not** currently wired.

---

## 3. Current Reasoning Runtime Trace

For *"Explain what a Java interface is."* (captured live in the VS-2 audit):

```
premises entering ReasoningEngine (active_concepts): Java Interface, Interface, Abstraction, Class, Method
rules that fired: GeneralizationTransitivity(×4), NamespaceCohabitation(×1), AliasMapping(×2)
conclusions produced (7):
  Java Interface generalizes to Interface      (restates stored edge)
  Interface generalizes to Abstraction         (restates stored edge)
  Class generalizes to Abstraction             (restates stored edge)
  Method generalizes to Class                  (restates stored edge)
  Concepts [...] co-exist under namespace 'concept.oop'
  Alias 'java interface' -> Java Interface
  Alias 'interface' -> Interface
NOT produced: "Java Interface generalizes to Abstraction"   ← the derivable, unstored fact
```

**Where derivation could occur**: inside `infer()`, when both `Java Interface → Interface` and `Interface → Abstraction` are present in `active_concepts`. Both intermediate concepts (`Interface`, `Abstraction`) are already activated into the workspace list, so the closure is computable from the data the engine already receives.

---

## 4. Existing Rule Inventory

`RuleBasedInferenceStrategy` (`reasoning_engine.py:116`):

| Rule name | Premises | Produces something unstored? | Notes |
|---|---|---|---|
| `GeneralizationTransitivity` | 1 (a single `generalizes_to` edge) | **No** | **Misnomer** — restates each edge as "C generalizes to Parent"; not transitive |
| `NamespaceCohabitation` | N (concepts sharing a namespace) | No | Set-membership statement, not derivation |
| `AliasMapping` | 1 (an alias) | No | Restates alias |

Repo-wide search for `transitiv|closure|derive|inferred|premise|entail|deduc|chain`: the only "chain" machinery is HTN `SkillComposer` skill-chains (task planning, not knowledge inference) and unrelated string content. **No genuine multi-premise derivation exists anywhere.**

---

## 5. Derivation Capability Gap

| Requirement | Present today |
|---|---|
| Rule abstraction | YES (`IInferenceStrategy`) |
| Premises represented separately from conclusions | PARTIAL — `Inference` has `supporting_evidence` (strings) + `concepts_used`, but no explicit premise references |
| Conclusion carries evidence | YES (`Conclusion.evidence`) |
| Conclusion references multiple premises | NO |
| Conclusion carries its rule name | NO — `rule_name` exists on `Inference` but is dropped when building `Conclusion` |
| Derived-vs-stored distinction | NO |
| Derivation depth | NO |
| Multi-premise rule | NO |
| Novel (unstored) conclusion | NO |

The gap is precisely: a rule that consumes **two independent premises** to emit a **novel** conclusion, plus additive provenance fields to make that conclusion traceable and labelled as derived.

---

## 6. Candidate Architectural Homes

| Candidate | Suitable? | Rationale |
|---|---|---|
| **A. ReasoningEngine (`IInferenceStrategy` layer)** | **YES — chosen** | Derivation *is* reasoning; the strategy pattern is the designed extension point; smallest correct change |
| B. RIRLoop | No | Separate V3 stack; not on the V4 conceptual path |
| C. HTN planner | No | Task decomposition/skill-chaining, not knowledge inference |
| D. Cognitive Workspace | No (not yet) | Does not exist; not required for the minimal derivation (see §7) |
| E. KnowledgeManager | No | Must remain a knowledge access/management boundary |
| F. Concept Activation Engine | No | Must remain activation |

**Primary home: ReasoningEngine — a new `TransitiveClosureStrategy` (or an added transitivity rule composed alongside `RuleBasedInferenceStrategy`).** KnowledgeManager, Activation, and Answer Synthesis stay in their lanes.

---

## 7. Cognitive Workspace Assessment

**A minimal derivation engine can be implemented correctly WITHOUT a Cognitive Workspace.**

Evidence: for the target question, activation already places all needed premises — `Java Interface`, `Interface`, **and** `Abstraction` — into the `active_concepts` list handed to the reasoner. Transitive closure over the `generalizes_to` edges *of the activated set* therefore has every premise it needs in memory already. No additional shared state is required.

A Workspace becomes necessary only for **cross-iteration chaining** — feeding newly derived facts back as premises for further derivation beyond the activated set, or multi-rule blackboard interaction. That is explicitly **beyond** minimal VS-3. Recommendation: do **not** introduce a Workspace in VS-3; revisit it only when derivation must chain past the activated concept set.

---

## 8. Derived Knowledge Model

Distinguish stored vs derived by an explicit source tag plus premise provenance:

| Field | Exists today | VS-3 need |
|---|---|---|
| `conclusion` (statement) | YES (`Conclusion.statement`) | keep |
| `rule` | on `Inference` only, dropped at `Conclusion` | **propagate to `Conclusion`** |
| `premises` (identifiable) | NO | **add** (e.g., list of `(source_id, target_id)` or premise statements) |
| `evidence` | YES (`Conclusion.evidence`) | keep |
| `confidence` | YES | keep + propagation formula (§10) |
| `provenance` / `source` (KNOWLEDGE vs REASONING) | NO | **add** a `derived: bool` / `source` marker |
| `derivation_depth` | NO | **add** (int; 1 for a 2-premise closure step) |

All additions are **additive optional fields** on the existing `Inference`/`Conclusion` dataclasses (backward-compatible; existing consumers unaffected). No new storage system; derived conclusions remain transient in the `ReasoningResult` (they are inferred, not asserted, so they must **not** be written into the UKM).

---

## 9. Provenance Model

A derived conclusion is traceable purely from in-memory structures:

```
Derived: "Java Interface generalizes to Abstraction"
  ├── rule:      GeneralizationTransitivity (true transitive form)
  ├── premise 1: (c_java_interface → c_interface)   [stored edge]
  └── premise 2: (c_interface → c_abstraction)      [stored edge]
```

No fabricated proof IDs (none exist in the architecture). Provenance = the two real stored edges + the rule name. The existing `ExplanatoryAnswerSynthesizer.KnowledgeSource` already preserves `reasoning_rule` + `reasoning_evidence`; VS-3 extends it to also carry the premise references so a derived line is distinguishable from a restated one.

---

## 10. Termination Strategy

- **Bounded depth**: `MAX_DERIVATION_DEPTH` (small, e.g. 5) or bound by the number of activated concepts.
- **Duplicate detection**: reuse the engine's `known_statements`; additionally do **not** emit a closure edge that already exists as a stored `generalizes_to` (novelty filter, §11) or was already derived.
- **Cycle detection**: per-path visited-set while walking `generalizes_to` (the generalization hierarchy is expected acyclic; guard anyway).
- **Confidence propagation**: derived confidence = `min(premise confidences) * decay^depth` (or product), documented and tested; must be ≤ the weakest premise so derivation never *increases* certainty.
- **Explosion control**: operate only over the activated set; depth bound + dedup keep the closure O(V·E) small.

---

## 11. Verification Boundary

**Deterministic rule-based derivation can be validated without Z3.** Transitive closure over a partial order is self-justifying from its two premises; correctness is checkable by asserting both premise edges exist and the conclusion edge does not. There is no arithmetic/SMT obligation. **VS-3 should defer Z3.** (Z3 remains reserved for the arithmetic/logic RIRLoop path; adding it here would violate the "no Z3 merely because it exists" rule and add cost with no correctness gain.)

---

## 12. Minimal Derivation Example

Seeded `generalizes_to` graph (from `hsci/knowledge/seeds/oop_concepts.py`):

```
c_java_interface → c_interface → c_abstraction
c_method        → c_class     → c_abstraction
c_class         → c_abstraction
```

Smallest legitimate two-premise derivations (each conclusion absent from the store):

- **Java Interface → Abstraction** (via Interface) — ideal: it is the demonstrator concept and directly enriches its explanation.
- **Method → Abstraction** (via Class) — an independent second example for genericity tests.

Both require two distinct, independently identifiable stored edges and produce an edge that is **not** in the concept's stored `generalizes_to`. Confirmed absent from current output (§3). No artificial facts are added.

---

## 13. Test Strategy (to be written in VS-3, not now)

| # | Test | Precisely |
|---|---|---|
| 1 | Two premises → one new conclusion | With the seeded graph, the reasoner emits "Java Interface generalizes to Abstraction" |
| 2 | Conclusion absent from stored knowledge | Assert the derived target is **not** in `c_java_interface.generalizes_to` yet **is** in the reasoning conclusions |
| 3 | Remove one premise → conclusion disappears | In a harness, drop `c_interface → c_abstraction`; assert the derived conclusion no longer appears |
| 4 | Change a premise → conclusion changes/disappears | Repoint `c_interface.generalizes_to` to another target; assert the derived conclusion tracks/vanishes |
| 5 | Correct provenance | Derived conclusion records rule + both premise edges |
| 6 | No duplicate derivations | Closure emits each derived edge once; never re-emits a stored edge |
| 7 | Cycle terminates safely | Inject A→B→A in a harness; assert termination, no infinite loop, no bogus conclusion |
| 8 | Unknown/incomplete knowledge | If the second premise is missing, **no** conclusion is manufactured |
| 9 | VS-1/VS-2 unchanged | Existing 276 tests stay green; the Java answer still surfaces the definition |

All primary tests use real engines (no mocks), consistent with the VS-2 test standard.

---

## 14. VS-3 Acceptance Criteria

| ID | Requirement |
|---|---|
| VS3-AC1 | ≥1 genuinely NEW conclusion is derived at runtime |
| VS3-AC2 | The conclusion was absent from stored knowledge |
| VS3-AC3 | ≥2 independent premises were required |
| VS3-AC4 | A named reasoning rule produced it |
| VS3-AC5 | Provenance identifies both premises + the rule |
| VS3-AC6 | Removing/altering a premise prevents/changes the conclusion |
| VS3-AC7 | No hardcoded concept-specific logic |
| VS3-AC8 | Missing premise → no unsupported conclusion (no hallucination) |
| VS3-AC9 | Existing regression remains green (≥276) |
| VS3-AC10 | VS-2 answer behavior (definition-first) remains intact |
| VS3-AC11 | Derived confidence never exceeds the weakest premise; not inflated |
| VS3-AC12 | No Z3, Workspace, Learning, Reflection, Planning, LLM, or new storage added |

---

## 15. Recommended Implementation Scope

**Smallest correct VS-3:**

1. Add a `TransitiveClosureStrategy` (implements `IInferenceStrategy`) — or a transitivity rule composed with `RuleBasedInferenceStrategy` — that walks `generalizes_to` over the activated set and emits **novel** two-premise closure edges, skipping any edge already stored. Generic; no concept names in code.
2. Additively extend `Inference` and `Conclusion` with `rule`, `premises`, `derived`, `derivation_depth` (optional, backward-compatible); propagate `rule_name` from `Inference` to `Conclusion`.
3. Wire the strategy into `CognitiveReasoningEngine` (compose with existing rules; do not remove the current rules).
4. Extend `ExplanatoryAnswerSynthesizer.KnowledgeSource` to carry premise references so a derived line is labelled distinct from a restated edge (small, additive).
5. Add the nine VS-3 tests (§13).

**Touched files (anticipated)**: `hsci/reasoning/reasoning_engine.py` (inference layer + additive model fields), `hsci/response/explanatory_synthesizer.py` (additive premise field), `hsci/core/cognitive_pipeline.py` (only if a reasoning-context knob is needed), and new tests. **Not touched**: storage, KnowledgeManager, activation, HTN, Z3, RIRLoop, SkillGraph, lifecycle.

---

## 16. Risks

- **Model extension on `reasoning_engine.py`**: VS-3 is the first sprint permitted to modify reasoning bodies. Keep changes additive/backward-compatible; the 276-test regression is the guardrail.
- **Confidence semantics**: a naive closure could inflate confidence; enforce "≤ weakest premise" with a documented formula (§10).
- **Explosion on larger graphs**: bound depth + operate over the activated set + dedup; the seeded graph is tiny but the rule must be safe for growth.
- **Derived facts leaking into storage**: derived conclusions are inferred, not asserted — they must remain transient in `ReasoningResult` and never be written to the UKM (protects the canonical/learned distinction).
- **Over-labelling restatements as derivations**: the closure rule must exclude edges already present in the store, so "derived" strictly means "unstored".

---

## 17. Explicit Non-Goals

Not in VS-3: Cognitive Workspace, Z3 verification of derivations, Learning, Reflection, Planning, LLM, new storage engine, cross-iteration premise chaining, property-propagation rules beyond generalization transitivity, or seeding additional concepts. Property propagation (Example C) is **deferred** — the current ontology has no first-class "property" relation, so implementing it now would require inventing semantics (prohibited).

---

## 18. Final Recommendation

**Answer to the most important question** — the smallest VS-3 that turns HSCI from "retrieval + shallow reasoning + explanation" into "retrieval + genuine multi-premise derivation + explanation":

> Add a single, generic **transitive-closure inference rule** over `Concept.generalizes_to` at the existing `IInferenceStrategy` extension point, emitting only conclusions that are **not** already stored, each carrying its rule and its two premise edges; extend the `Inference`/`Conclusion` models with additive provenance fields; and label derived lines in the answer. Prove it with the `Java Interface → Interface → Abstraction ⇒ Java Interface → Abstraction` example and the nine tests in §13.

This introduces genuine derivation with the minimum surface area and **no** premature Workspace, Learning, Reflection, Planning, LLM, or Z3.

**FINAL VERDICT: READY FOR IMPLEMENTATION.**

---

*Preflight only. No production code, tests, or architecture modified. Nothing committed.*
