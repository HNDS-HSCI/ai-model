# HSCI V4 — Thinking Algorithms

**Document:** HSCI_V4_THINKING_ALGORITHMS.md
**Classification:** Cognitive Theory — No Implementation
**Basis:** Architecture Audit, V4 Architecture Spec, V4 Cognitive Specification
**Purpose:** Define every cognitive algorithm used by HSCI with sufficient precision that implementation requires no behavioural invention.

---

## Preamble

A Cognitive Operating System does not merely route inputs to solvers. It thinks. Thinking is not a single operation — it is a repertoire of distinct cognitive algorithms, each suited to a class of problems, each composable with others. This document specifies HSCI's complete thinking repertoire.

Every algorithm here is traceable to a component in the V4 Architecture Specification or the V4 Cognitive Specification. The connection is made explicit in each section. The goal is zero ambiguity: an implementer reading this document should be able to produce a correct implementation without making any cognitive design decisions.

### Algorithm Classification

| Class | Algorithms | Primary V4 Component |
|---|---|---|
| Deductive | Deduction, Verification | Z3VerificationEngine, CEGIS Loop |
| Inductive | Induction, Concept Strengthening | LearningEngine, ConceptEvolutionEngine |
| Abductive | Abduction, Hypothesis Generation | ReasoningEngine, SelfPlayEngine |
| Analogical | Analogy | ConceptActivationEngine (spreading activation) |
| Planning | Planning, Decomposition, Composition | HTNPlanner, GoalManager |
| Reflective | Reflection, Counterfactual Reasoning | ReflectionEngine |
| Communicative | Explanation, Decision Making | ResponseBridge, GoalManager |
| Optimisation | Optimisation | SolverRegistry, CEGIS repair loop |

---

## Algorithm 1: Deduction

### Purpose

Deduction is the process of deriving a necessarily true conclusion from a set of premises and a set of rules. In HSCI, deduction is the primary mechanism for answering questions to which the system already has sufficient knowledge. It is the algorithm executed during Layer 4 (Z3 Verification) of the RIR loop when the premises are fully specified and the unknown is a single value derivable from them.

Deduction in HSCI is **formal**: it is not heuristic inference or statistical likelihood. A deduced conclusion is true in all models that satisfy the premises. The Z3 SMT solver is the deductive engine.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| premises | Dict[str, float] | CognitiveContext.working_memory (entity values) | Known entity values from the input |
| rule | CompiledRule | Concept.compiled_rule | The Z3 constraint encoding the relationship between entities |
| unknown | str | PerceptionMap.unknown_entities[0] | The entity to solve for |
| z3_context | z3.Context | CognitiveContext.z3_context | Isolated per-request Z3 context |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| conclusion | float | The deduced value of the unknown entity |
| is_valid | bool | True if Z3 found a unique satisfying assignment |
| proof_trace | ProofTrace | Step-by-step account of the deduction |
| counterexample | Optional[Dict] | Present only if the rule is unsatisfiable for these premises |

### Internal Process

```
Step 1 — Build Z3 variables
  For each entity e in (premises ∪ {unknown}):
    z3_var[e] = z3.Real(e, ctx=z3_context)

Step 2 — Assert premises
  For each known entity e with value v:
    solver.add(z3_var[e] == v)

Step 3 — Assert rule
  constraint = rule.z3_builder(z3_var)
  solver.add(constraint)

Step 4 — Check satisfiability
  result = solver.check()
  If UNSAT: return counterexample (premises are inconsistent with rule)
  If UNKNOWN: return VerificationStatus.TIMEOUT

Step 5 — Extract model
  model = solver.model()
  conclusion = float(model[z3_var[unknown]])

Step 6 — Verify uniqueness (optional, for COMPOSITION axiom type)
  Add negation: solver.add(z3_var[unknown] != conclusion)
  second_check = solver.check()
  If SAT: conclusion is not unique → return is_unique=False
  If UNSAT: conclusion is provably unique → is_unique=True

Step 7 — Build ProofTrace from model assignments
```

### Data Structures

The rule must be a `CompiledRule` (not a raw string). The `z3_builder` callable takes a `Dict[str, z3.ArithRef]` and returns a `z3.BoolRef`. This is the only form in which rules enter the deduction engine — the ConceptCompiler ensures this.

### Complexity

- Time: O(n^k) where n = number of variables, k = degree of polynomial constraint. For linear arithmetic (most HSCI concepts): O(n^2) in practice via Z3's DPLL(T).
- CEGIS iterations: bounded at 5 by SystemConfig. Each iteration calls deduction once.
- Timeout: 5000ms per Z3 call (SystemConfig.z3_timeout_ms).

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| UNSAT | Premises are inconsistent with rule | Return counterexample; CEGIS repair attempts revised premises |
| TIMEOUT | Problem exceeds Z3 linear arithmetic model | Return VerificationStatus.TIMEOUT; Reflection logs Z3_TIMEOUT |
| Non-unique solution | Problem is under-constrained | Return is_unique=False; ResponseBridge reports ambiguity |
| Rule contains nonlinear terms | Z3 cannot handle `x*y` in general case | ConceptCompiler detects during compilation; CompiledRule.is_linear flag used |

### Benchmarks

- Target: 95% of linear arithmetic deductions complete in < 50ms
- Target: Z3 timeout rate < 2% across standard benchmark suite
- Measured by: benchmarks/constraint/tasks.json (ConstraintMatrixSolver category)

---

## Algorithm 2: Induction

### Purpose

Induction is the process of deriving a general rule from a set of specific observations. In HSCI, induction is the mechanism by which repeated successful problem-solving episodes produce a strengthened, generalised Concept. Unlike deduction (which is certain), induction is probabilistic — an induced rule holds with a confidence score that increases with supporting evidence.

Induction in HSCI operates at two timescales:
- **Per-cycle** (micro-induction): each successful proof increments a Concept's proof_count and increases strength
- **Batch** (macro-induction): the ConceptEvolutionEngine detects patterns across many episodes and proposes generalisation

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| episodes | List[Episode] | UKM.EpisodeStore | N verified episodes from same domain |
| candidate_concept | Concept | UKM.ConceptStore | Concept being evaluated for induction |
| success_threshold | float | SystemConfig | Minimum proof success rate to strengthen |
| generalisation_threshold | float | SystemConfig | Minimum structural similarity to trigger CEE |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| strength_delta | float | How much to change concept.strength (positive or negative) |
| generalisation_proposal | Optional[EvolutionProposal] | If patterns suggest two concepts should merge |
| specialisation_proposal | Optional[EvolutionProposal] | If patterns suggest one concept should split |

### Internal Process

```
MICRO-INDUCTION (per cycle, in LearningEngine):

Step 1 — Retrieve concept from verification result
  concept = verification.proof_trace.concepts_applied[0]

Step 2 — Compute strength delta
  If verification.valid:
    delta = +learning_rate * (1.0 - concept.strength)   [diminishing returns near 1.0]
  Else:
    delta = -learning_rate * concept.strength             [diminishing punishment near 0.0]

Step 3 — Apply delta
  UKM.update_concept_strength(concept.id, concept.strength + delta)

Step 4 — Increment proof_count and update last_used
  UKM.put_concept(concept with proof_count += 1, last_used = now)

MACRO-INDUCTION (nightly, in ConceptEvolutionEngine):

Step 1 — Cluster episodes by structural similarity
  Group episodes where perception.intent matches AND entity_type overlap > 0.7

Step 2 — Identify concept success rates per cluster
  For each cluster: success_rate = verified_episodes / total_episodes

Step 3 — Detect generalisation candidates
  If two concepts have structural similarity > 0.7 AND both success_rate > 0.8:
    Propose GeneralisationProposal

Step 4 — Detect specialisation candidates
  If one concept success_rate_in_domain_A > 0.8 AND success_rate_in_domain_B < 0.3:
    Propose SpecialisationProposal

Step 5 — Route proposals to Z3 verification before committing
```

### Complexity

- Micro-induction: O(1) per cycle — constant-time strength update
- Macro-induction: O(E × C) where E = episodes, C = concepts. With domain partitioning: O(E/D × C/D) per domain

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| Concept strength reaches 1.0 | Concept proven correct every time | Cap at 1.0; stop updating (convergence) |
| Concept strength reaches 0.0 | Concept fails every time | GoalManager creates IMPROVE_DOMAIN goal |
| Generalisation proposal rejected by Z3 | Concepts are structurally similar but logically distinct | CEE logs rejection; concepts remain separate |

### Benchmarks

- Target: concept.strength reflects proof success rate within ±0.1 after 100 cycles
- Target: Generalisation detection produces < 5% false positives (verified by Z3)
- Measured by: benchmarks/concept_evolution/ (to be created in V4)

---

## Algorithm 3: Abduction

### Purpose

Abduction is inference to the best explanation. Given an observation and a set of rules, abduction finds the most plausible hypothesis that, if true, would make the observation follow. In HSCI, abduction is the mechanism behind hypothesis generation: when the system is given an outcome and must determine which causes could have produced it.

Abduction is used by the SelfPlayEngine when generating hypotheses for autonomous self-play, and by the ReasoningEngine when the unknown is not the output of a rule but one of its inputs.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| observation | Dict[str, float] | PerceptionMap.entities (values known) | The observed outcome or result |
| candidate_rules | List[CompiledRule] | ConceptActivationEngine.activate() | Rules that could explain the observation |
| plausibility_priors | Dict[str, float] | UKM.ConceptStore (concept.strength) | Prior probability of each rule being correct |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| best_explanation | CompiledRule | The rule most plausibly explaining the observation |
| abduced_values | Dict[str, float] | The unknown input values implied by the best explanation |
| confidence | float | 0.0 to 1.0 — plausibility of this explanation |
| alternative_explanations | List[Tuple[CompiledRule, float]] | Runner-up explanations with their plausibility scores |

### Internal Process

```
Step 1 — Generate candidate explanations
  For each rule R in candidate_rules:
    Attempt: given observation as output, solve for inputs via Z3
    If Z3 finds satisfying inputs → (R, abduced_inputs) is a candidate explanation

Step 2 — Score each explanation by plausibility
  plausibility(R) = rule.concept.strength * entity_type_match_score
  entity_type_match_score = Jaccard(R.required_entities, perception.entity_types)

Step 3 — Rank and select
  Sort candidates by plausibility descending
  best_explanation = candidates[0]

Step 4 — Verify best explanation
  Re-run deduction with abduced_inputs as premises, rule as constraint
  If verification.valid: confidence = plausibility(best)
  Else: try next candidate

Step 5 — Return ranked list (top 3 explanations for ResponseBridge)
```

### Data Structures

The output `alternative_explanations` is used by ResponseBridge when the system cannot determine a unique best explanation — it reports all plausible explanations and their relative confidence to the user.

### Complexity

- O(R × T_Z3) where R = candidate rules count (bounded by CAE activation field size, typically < 20), T_Z3 = Z3 solve time per rule

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| No candidate produces satisfying inputs | Observation cannot be explained by current knowledge | Return empty explanations; GoalManager creates FILL_KNOWLEDGE_GAP goal |
| All explanations have equal plausibility | Under-determined abduction | Return all equally; Understanding Engine flags for clarification |
| Z3 returns non-unique abduced values | Multiple input sets explain the observation | Mark confidence as low; report ambiguity |

### Benchmarks

- Target: Abduction finds a plausible explanation in < 200ms for standard physics/finance domains
- Target: Best explanation is verified as correct in ≥ 80% of benchmark cases

---

## Algorithm 4: Analogy

### Purpose

Analogy is the cognitive process of recognising that two structurally different situations share an underlying pattern, and transferring knowledge from a known situation to a novel one. In HSCI, analogy is the mechanism that allows the system to solve problems in unfamiliar domains by mapping them to known concepts from familiar domains.

Analogy is implemented through the ConceptActivationEngine's spreading activation: concepts activated via analogical paths (GENERALIZES, IS_A edges) are analogically related to the seed concept. The OntologyGraph is the structural similarity index.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| source_perception | PerceptionMap | Current CognitiveContext | The novel problem to solve |
| activation_field | ActivationField | ConceptActivationEngine.activate() | Activated concepts including analogical matches |
| ontology | OntologyStore | UKM.OntologyStore | The edge graph over all concepts |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| analogical_mapping | Dict[str, str] | Maps novel entities to known entities (e.g., "current" → "flow_rate") |
| source_concept | Concept | The known concept being analogised from |
| adapted_rule | CompiledRule | The source concept's rule with variable names remapped to target domain |
| mapping_confidence | float | Structural similarity score |

### Internal Process

```
Step 1 — Identify analogical candidates
  From activation_field.activations, filter to source_type == "analogical"
  These are concepts reached via GENERALIZES or IS_A edges, not direct match

Step 2 — Compute structural mapping for each candidate
  For each analogical_concept AC:
    Attempt entity-to-entity matching:
    Map novel_entity E_n to known_entity E_k where:
      E_n.type == E_k.type (same entity role: "quantity", "rate", "result")
      AND E_n.domain != E_k.domain (cross-domain mapping)

Step 3 — Score mappings by structural completeness
  score = matched_entities / required_entities_in_AC.required_entities
  Select mapping with highest score

Step 4 — Remap rule
  Take AC.compiled_rule
  Substitute variable names: E_k → E_n for all mapped pairs
  Recompile via ConceptCompiler with new variable names

Step 5 — Verify adapted rule
  Run deduction with adapted_rule and novel premises
  If valid: analogical transfer succeeded
  If invalid: try next analogical candidate

Step 6 — Store successful analogy as Episode with was_analogical=True
```

### Data Structures

The analogical mapping is stored in WorkingMemory.analogical_mapping during the cycle. If the analogy succeeds and is verified, LearningEngine creates a new derived Concept in the target domain referencing the source concept via a DERIVED_FROM edge.

### Complexity

- O(A × E^2) where A = analogical candidates (typically 3-10), E = entities in novel problem (typically 2-6)
- Entity matching is O(E^2) per candidate in the worst case

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| No analogical candidates in activation field | No related concepts in ontology | Abduction attempted as fallback |
| Mapping is incomplete (some entities unmapped) | Structural mismatch too great | Try next analogical candidate |
| Adapted rule fails Z3 verification | Analogy was superficial, not structural | Mark analogy as failed; Reflection logs |
| Circular analogy (A maps to B, B maps to A) | Ontology cycle | OntologyGraph visited-set prevents cycle |

### Benchmarks

- Target: Analogy correctly transfers a concept to a new domain in ≥ 70% of cross-domain benchmark cases
- Target: Analogical mapping computation completes in < 100ms
- Measured by: benchmarks/analogy/ (V4 benchmark category to be created)

---

## Algorithm 5: Planning

### Purpose

Planning is the process of constructing a sequence of cognitive operations that will transform the current state into a goal state. In HSCI, planning is Layer 3 of the RIR loop: the ReasoningEngine decomposes an intent into an ordered sequence of sub-goals that, if solved in order, produce the final answer.

The HTNPlanner (Hierarchical Task Network planner) executes planning. Despite its name in the current codebase (noted in the audit as a misnomer for what is actually a 3-branch if/else), the V4 HTNPlanner is a genuine hierarchical planner guided by DECOMPOSITION_RULES indexed by AxiomType and enriched by SkillMemory.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| goal | SemanticFrame | UnderstandingEngine output | What the system is trying to achieve |
| knowledge | KnowledgeResult | ConceptActivationEngine.activate() | Available concepts and episodes |
| applicable_skill | Optional[ApplicableSkill] | SkillMemory.retrieve() | Pre-defined procedure for this problem class |
| world_state | WorldStateNode | MentalModelEngine.query_world_state() | Current known values for relevant entities |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| plan | ReasoningPlan | Ordered list of SubGoals with concept assignments |
| plan_confidence | float | Estimated probability this plan will succeed |
| alternative_plans | List[ReasoningPlan] | Backup plans if primary fails |

### Internal Process

```
Step 1 — Check SkillMemory for applicable skill
  If applicable_skill exists:
    Use skill.procedure as the ordered SubGoal sequence
    Set plan_confidence = applicable_skill.confidence
    Skip to Step 4

Step 2 — HTN Decomposition (no skill available)
  Select DECOMPOSITION_RULES[goal.core_intent]
  For each rule step (name, description):
    Create SubGoal(name, required_entities=goal.given_entities, target=goal.target_entities)

Step 3 — Assign concepts to sub-goals
  For each SubGoal SG:
    candidates = [c for c in knowledge.direct_matches if c.axiom_type == SG.axiom_type]
    best_concept = max(candidates, key=lambda c: c.strength)
    plan.concept_assignments[SG] = best_concept

Step 4 — Build candidate solution
  candidate = SolutionBuilder.build(
    sub_goals = plan.sub_goals,
    concept_assignments = plan.concept_assignments,
    entities = goal.given_entities
  )
  plan.candidate_solution = candidate

Step 5 — Estimate plan confidence
  plan_confidence = mean([c.strength for c in plan.concept_assignments.values()])
```

### Complexity

- O(S × C) where S = sub-goals (3-5 per axiom type), C = candidate concepts for each sub-goal
- With SkillMemory hit: O(1) for sub-goal construction

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| No concept matches a sub-goal | UKM has no concept for this axiom type | Sub-goal left unassigned; SynthesisSolver invoked for that sub-goal |
| Plan has zero assigned concepts | No knowledge available | Return empty plan; ResponseBridge reports cannot_solve |
| Skill leads to failed plan | Skill was misapplied | Reflection marks skill as failed; HTN decomposition used as fallback |

### Benchmarks

- Target: Planning completes in < 20ms (excluding skill retrieval)
- Target: Plans generated from SkillMemory succeed at ≥ skill.success_rate in benchmark tests
- Measured by: Run benchmark task set, compare plan success rates with/without SkillMemory

---

## Algorithm 6: Decomposition

### Purpose

Decomposition is the process of breaking a complex problem into a set of simpler sub-problems that can be solved independently and whose solutions combine to solve the original. In HSCI, decomposition is the first operation performed by the HTNPlanner and is guided by the AxiomType of the problem's intent.

Decomposition is not planning — it is the structural analysis that makes planning possible. Planning assigns concepts to sub-goals; decomposition identifies what the sub-goals are.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| semantic_frame | SemanticFrame | UnderstandingEngine | Grounded, disambiguated meaning |
| axiom_type | AxiomType | semantic_frame.core_intent | REDUCTION, COMPOSITION, SYNTHESIS, or TRANSFORMATION |
| entities | Dict[str, GroundedEntity] | semantic_frame.given_entities | Known entity values |
| unknown | List[str] | semantic_frame.target_entities | What to solve for |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| sub_goals | List[SubGoal] | Ordered sub-problems to solve |
| dependency_graph | Dict[str, List[str]] | Which sub-goals depend on which (for ordering) |
| is_parallelisable | bool | True if any sub-goals can be solved concurrently |

### Internal Process

```
Step 1 — Select decomposition template by AxiomType
  REDUCTION:       [IDENTIFY_UNKNOWNS, BUILD_EQUATION, SOLVE_EQUATION]
  COMPOSITION:     [EXTRACT_ENTITIES, IDENTIFY_RELATIONSHIPS, BUILD_CONSTRAINT_NETWORK, SOLVE_NETWORK]
  SYNTHESIS:       [DEFINE_INPUTS_OUTPUTS, IDENTIFY_ALGORITHM_PATTERN, BUILD_PROCEDURE, VERIFY_INVARIANTS]
  TRANSFORMATION:  [PARSE_SOURCE_STRUCTURE, IDENTIFY_TARGET_STRUCTURE, MAP_TRANSFORMATION_RULES, APPLY_TRANSFORMATION]

Step 2 — Bind template steps to specific entities
  For each template step:
    required_entities = [e for e in entities if e.type matches step.expected_type]
    target_entity = unknown[0] if step is final step else intermediate_variable

Step 3 — Build dependency graph
  For sequential templates: sub_goal[i] depends on sub_goal[i-1]
  For COMPOSITION: SOLVE_NETWORK depends on BUILD_CONSTRAINT_NETWORK
  is_parallelisable = False for all standard templates (all are sequential in V4)

Step 4 — Apply SkillMemory override if skill provides alternative decomposition
  If applicable_skill.procedure defines different step ordering:
    Replace template with skill procedure
    Rebuild dependency graph from skill step conditions
```

### Complexity

- O(K) where K = template steps (3-4 for all axiom types) — constant time per decomposition

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| AxiomType = UNKNOWN | Intent classification failed | Default to TRANSFORMATION decomposition with single step |
| Entity binding fails (no entity matches expected type) | Parser missed entities | SubGoal created with empty required_entities; SolutionBuilder handles gracefully |

---

## Algorithm 7: Composition

### Purpose

Composition is the inverse of decomposition: given a set of proven sub-solutions, composition assembles them into a complete solution. In HSCI, composition occurs in the SolutionBuilder after all sub-goals of a plan have been assigned concepts and their Z3 expressions built.

Composition is primarily a structural operation — it connects Z3 expressions that represent sub-solutions into a single Z3 assertion that represents the overall solution.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| sub_solutions | List[Expression] | SolutionBuilder (per sub-goal) | Z3 expressions for each sub-goal |
| composition_order | List[int] | ReasoningPlan.composition_order | Order in which to compose |
| entities | Dict[str, GroundedEntity] | WorkingMemory | Shared variable namespace |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| composed_solution | Expression | The combined Z3 expression |
| intermediate_variables | Dict[str, z3.ArithRef] | Variables introduced during composition |

### Internal Process

```
Step 1 — Establish shared Z3 variable namespace
  z3_vars = {entity: z3.Real(entity, ctx) for entity in all_entities}
  Intermediate variables created for sub-goal outputs that feed next sub-goal

Step 2 — Compose sub-solutions in order
  For i in composition_order:
    sub_expr = sub_solutions[i]
    combined = z3.And(combined, sub_expr.value)

Step 3 — Identify intermediate variable bindings
  For each sub-goal output that is consumed by a subsequent sub-goal:
    Add binding: intermediate_var == sub_goal_result to combined

Step 4 — Return composed Expression(value=combined, concepts_used=all_concepts)
```

### Complexity

- O(S) where S = sub-solutions — linear composition via z3.And

---

## Algorithm 8: Hypothesis Generation

### Purpose

Hypothesis generation is the construction of a candidate explanation or solution that has not yet been verified. In HSCI, hypotheses are generated by the SelfPlayEngine (autonomously) and by the ReasoningEngine when abduction is required. A hypothesis is always provisional — it must pass verification before being accepted.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| concept_sample | List[Concept] | UKM.ConceptStore.sample(n=2) | Seed concepts for hypothesis |
| difficulty | float | concept.strength | Lower strength → simpler hypothesis |
| target_domain | Optional[str] | GoalManager active goal | If set, constrains hypothesis domain |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| hypothesis | PerceptionMap | A synthetic problem structured as a real input |
| expected_structure | str | What the solution structure should look like (for grading) |

### Internal Process

```
Step 1 — Sample seed concepts from UKM
  If GoalManager has SELF_IMPROVEMENT goal: sample from goal's concept_assignments
  Else: sample weakest N concepts from UKM

Step 2 — Select concept pair
  concept_A, concept_B = sample(2)
  Determine if they are related in ontology (IS_A, GENERALIZES)
  Related pair → generate single-step hypothesis
  Unrelated pair → generate multi-step hypothesis (more complex)

Step 3 — Generate numeric premise values
  For each required_entity in concept_A.required_entities:
    value = random.uniform(1, 100) scaled by difficulty
    Entity(name=entity, value=value, known=True)
  unknown_entity = concept_A.required_entities[-1] or "result"
  Entity(name=unknown_entity, value=None, known=False)

Step 4 — Build PerceptionMap
  PerceptionMap(
    entities = all entities,
    unknown_entities = [unknown_entity],
    intent = concept_A.axiom_type,
    domain = concept_A.domain,
    entity_graph = {"text": f"Given {premises}, find {unknown}"}
  )

Step 5 — Record expected_structure
  expected_structure = concept_A.abstract_rule with values substituted
```

### Complexity

- O(1) per hypothesis — random sampling and template filling

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| UKM has fewer than 2 concepts | System just started | Generate trivial arithmetic hypothesis (ADDITION of two constants) |
| All sampled concepts are DEPRECATED | Concept library outdated | Force resample from ACTIVE concepts only |

---

## Algorithm 9: Counterfactual Reasoning

### Purpose

Counterfactual reasoning is the process of asking "what would have happened if something had been different?" In HSCI, counterfactual reasoning is performed by the ReflectionEngine after a failed cognitive cycle. It identifies which alternative choice (different concept, different skill, different activation) would have produced a successful proof.

Counterfactuals are not speculative — they are verified. The ReflectionEngine actually runs the alternative scenario through the Z3 engine to confirm that the counterfactual would have succeeded.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| failed_trace | CognitiveTrace | ReflectionEngine | The complete record of the failed cycle |
| alternative_concepts | List[Concept] | UKM.ConceptStore | Concepts that were not selected but could have been |
| original_premises | Dict[str, float] | failed_trace.perception | The entity values from the failed cycle |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| counterfactual | Counterfactual | The best alternative that would have succeeded |
| verification_result | VerificationResult | Proof that the counterfactual actually works |
| confidence | float | How likely the counterfactual would have succeeded |

### Internal Process

```
Step 1 — Identify what was changed in the counterfactual
  The primary change point is the concept that was activated and used
  counterfactual_concepts = [c for c in alternative_concepts
                              if c.axiom_type == failed_trace.perception.intent
                              AND c.id != failed_trace.plan.primary_concept.id]

Step 2 — For each counterfactual concept CC:
  Rebuild plan with CC substituted for the original concept
  Rerun SolutionBuilder with CC's rule
  Rerun Z3VerificationEngine with new candidate_solution
  If verification.valid: candidate_counterfactual = CC; break

Step 3 — Score the counterfactual
  confidence = CC.strength * entity_type_match_score

Step 4 — Build Counterfactual record
  Counterfactual(
    original_top_concept = failed_trace.plan.primary_concept.name,
    counterfactual_concept = CC.name,
    reasoning = "Using {CC.name} with rule {CC.abstract_rule} produces a verified solution",
    probability_of_success = confidence
  )

Step 5 — Emit CorrectionProposal
  CAE.inhibit(original_concept_id, context_fingerprint)
  CAE.prime(CC.id, boost=0.3) for future similar inputs
```

### Complexity

- O(A × T_Z3) where A = alternative concepts tried (typically < 5), T_Z3 = Z3 solve time

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| No alternative concept verifies | UKM lacks correct concept | Counterfactual = None; GoalManager creates LEARN_CONCEPT goal |
| All alternatives timeout | Problem is too complex | FailureCause.Z3_TIMEOUT logged; no counterfactual generated |

---

## Algorithm 10: Reflection

### Purpose

Reflection is the meta-cognitive process of examining a completed cognitive cycle to determine whether it was executed correctly, and if not, why. In HSCI, reflection is always post-hoc (it never delays the response path) and always produces an actionable output — either a correction proposal or a confirmation that the cycle was optimal.

This algorithm is implemented by the ReflectionEngine and its output directly drives self-improvement via the CAE, CEE, and SkillMemory.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| cognitive_trace | CognitiveTrace | BrainKernel post-cycle | Complete record of one cognitive cycle |
| failure_log | List[ReflectionReport] | ReflectionEngine history | Prior reflection reports for systematic detection |
| world_state | SelfModel | MentalModelEngine | System's current self-assessment |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| report | ReflectionReport | Diagnosis + correction proposals |
| systematic_failures | List[SystematicFailure] | Recurring patterns across many reports |

### Internal Process

```
Step 1 — Classify cycle outcome
  If cognitive_trace.was_success: proceed to lightweight reflection (success analysis)
  If NOT cognitive_trace.was_success: proceed to failure analysis

FAILURE ANALYSIS:

Step 2 — Execute diagnosis decision tree (from Cognitive Specification)
  Check: was ActivationField empty? → MISSING_CONCEPT
  Check: was top activation wrong axiom_type? → WRONG_CONCEPT_ACTIVATED
  Check: was top activation correct but Z3 found counterexample? → CONCEPT_RULE_INCORRECT
  Check: was ActivationConflict present? → AMBIGUOUS_INPUT
  Check: was VerificationStatus.TIMEOUT? → Z3_TIMEOUT
  Check: was entity extraction incomplete? → ENTITY_EXTRACTION_FAILURE
  Else: UNKNOWN

Step 3 — Generate counterfactual (for WRONG_CONCEPT_ACTIVATED and CONCEPT_RULE_INCORRECT)
  Run Algorithm 9: Counterfactual Reasoning

Step 4 — Generate correction proposals
  WRONG_CONCEPT_ACTIVATED → CorrectionProposal(target=CAE, action=inhibit)
  CONCEPT_RULE_INCORRECT  → CorrectionProposal(target=CEE, action=CORRECT)
  SKILL_MISAPPLIED        → CorrectionProposal(target=SkillMemory, action=update_outcome)
  MISSING_CONCEPT         → CorrectionProposal(target=GoalManager, action=register_learn_goal)

SUCCESS ANALYSIS (lightweight):

Step 5 — Identify reinforceable patterns
  Which concepts contributed? → strengthen them via LearningEngine (already done in Layer 5)
  Was a Skill applied? → update_skill_outcome(success=True)
  Was it a new domain? → MME.update(new WorldStateNode for domain)

Step 6 — Check systematic patterns
  If len(failure_log) >= 10:
    Group by failure_cause and domain
    Any group with count >= 5 → emit SystematicFailure
```

### Complexity

- Diagnosis: O(1) — constant-time decision tree
- Counterfactual: O(A × T_Z3) — as per Algorithm 9
- Systematic pattern detection: O(F) where F = failure_log size (max 10,000)

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| Reflection itself raises exception | Bug in ReflectionEngine | Log error, skip reflection for this cycle — never block response |
| Diagnosis produces UNKNOWN for > 20 consecutive failures | Unmodelled failure mode | MCC escalates; adds new FailureCause to taxonomy if pattern is identified |

### Benchmarks

- Target: Reflection runs asynchronously — zero latency added to API response time
- Target: 90% of failures classified as non-UNKNOWN after 3 months of operation
- Target: Correction proposals produce measurable improvement within 10 subsequent cycles for same domain

---

## Algorithm 11: Verification

### Purpose

Verification is the process of proving that a candidate solution is correct with respect to a formal constraint. In HSCI, verification is the CEGIS (Counterexample-Guided Inductive Synthesis) loop in Layer 4. It is the most critical algorithm in the system — without it, HSCI is merely plausible rather than provably correct.

Verification is the only gate between a candidate answer and a confirmed answer. Nothing enters permanent memory (UKM) without having passed through verification.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| candidate_solution | Expression | SolutionBuilder | The Z3 expression proposed by ReasoningEngine |
| perception | PerceptionMap | CognitiveContext | The original problem with all entity values |
| concept | Concept | plan.primary_concept | The concept whose rule is being verified |
| max_iterations | int | SystemConfig (5) | Maximum CEGIS repair attempts |
| z3_context | z3.Context | CognitiveContext | Isolated Z3 context |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| result | VerificationResult | valid, status, proof_trace, counterexample |
| iteration_count | int | How many CEGIS iterations were needed |

### Internal Process

```
CEGIS LOOP (repeat up to max_iterations):

  Iteration i:

  Step 1 — Assert premises
    For each known entity e: solver.add(z3_var[e] == entity_value)

  Step 2 — Assert candidate solution
    solver.add(candidate_solution.value)

  Step 3 — Check
    result = solver.check()
    If UNSAT: VERIFICATION FAILED (premises + solution are contradictory)
      counterexample = extract_counterexample(solver)
      If i < max_iterations: goto REPAIR
      Else: return VerificationResult(valid=False, counterexample=counterexample)
    If SAT: extract model → candidate_value
    If UNKNOWN: return VerificationResult(status=TIMEOUT)

  Step 4 — Verify uniqueness
    solver_uniq = new solver with same assertions
    solver_uniq.add(z3_var[unknown] != candidate_value)
    If UNSAT: solution is unique and correct → goto SUCCESS
    If SAT: solution is not unique (ambiguous problem)
      Return VerificationResult(valid=True, is_unique=False)

  SUCCESS:
    Build ProofTrace from solver model
    Return VerificationResult(valid=True, status=PROVEN, proof_trace=...)

REPAIR (after UNSAT on iteration i):

  Step 1 — Extract counterexample
    counterexample = {entity: model[z3_var[entity]] for entity in entities}
    This is the assignment that violates the candidate solution

  Step 2 — Generate correction hint
    correction_hint = f"When {counterexample}, the formula yields {computed_wrong_value} but should yield {correct_value}"

  Step 3 — Call ReasoningEngine.repair(plan, counterexample, correction_hint)
    ReasoningEngine selects next-best concept from knowledge.direct_matches
    Rebuilds candidate_solution with revised concept

  Step 4 — Increment iteration counter and loop
```

### Complexity

- Per-iteration: O(n^2) for linear arithmetic via Z3 DPLL(T)
- Total: O(max_iterations × n^2) = O(5n^2) — bounded

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| All 5 iterations return UNSAT | No concept in knowledge produces a correct formula | Return VerificationResult(valid=False, attempts=5); ResponseBridge reports cannot_solve |
| TIMEOUT on first iteration | Problem too complex for Z3 linear arithmetic | Return VerificationResult(status=TIMEOUT); log Z3_TIMEOUT in Reflection |
| Repair produces same candidate as prior iteration | ReasoningEngine has no better concept | Break early; return failure |

### Benchmarks

- Target: 85% of benchmark problems verified in ≤ 2 CEGIS iterations
- Target: 0% of verified solutions are incorrect (formal guarantee by Z3)
- Measured by: full benchmark suite across all 5 solver categories

---

## Algorithm 12: Optimisation

### Purpose

Optimisation in HSCI is not general mathematical optimisation. It is the process of selecting the best solution from a set of feasible candidates when multiple solutions are valid. It applies when verification returns is_unique=False (multiple assignments satisfy the constraints) and the system must select the most appropriate one.

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| feasible_solutions | List[Dict[str, float]] | Z3 model enumeration | All satisfying assignments found |
| objective | Optional[str] | GoalContext or semantic_frame | What to optimise for (e.g., "minimum cost") |
| concept_priors | Dict[str, float] | concept.strength | Prior probability weights |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| optimal_solution | Dict[str, float] | The selected best assignment |
| optimality_reason | str | Why this solution was selected |

### Internal Process

```
Step 1 — If objective is specified (from semantic_frame or GoalContext):
  Identify the objective variable (e.g., "cost")
  If objective == "minimum": select solution with minimum objective variable value
  If objective == "maximum": select solution with maximum objective variable value
  Add objective constraint to Z3 solver (Z3 OptiSolver variant)

Step 2 — If no objective specified:
  Select solution that is closest to prior expected values from WorldStateGraph
  (prefer the assignment that matches known historical values for these entities)

Step 3 — Return optimal_solution with optimality_reason explaining the selection criterion
```

### Complexity

- Z3 OptiSolver: O(n^3) for linear programming — acceptable for the entity counts in HSCI problems (typically n < 20)

---

## Algorithm 13: Explanation

### Purpose

Explanation is the process of translating a formal proof trace and solution into natural, human-readable language. In HSCI, explanation is performed by the ResponseBridge (Layer 6) and is guided by the cognitive trace — which concepts were used, how many CEGIS iterations were needed, and what the proof steps were.

A good explanation in HSCI is:
- Truthful: it accurately represents what the system actually did
- Calibrated: it communicates confidence levels honestly
- Graded: it adjusts technical depth based on the user's apparent expertise
- Corrective: if the system produced a counterfactual or clarification, the explanation includes it

### Inputs

| Input | Type | Source | Semantics |
|---|---|---|---|
| final_output | FinalOutput | BrainKernel | The complete result of the cognitive cycle |
| cognitive_trace | CognitiveTrace | BrainKernel | How the result was obtained |
| domain | str | perception.domain | For domain-appropriate vocabulary |
| session_history | List[ConversationTurn] | BrainKernel | For follow-up context |

### Outputs

| Output | Type | Semantics |
|---|---|---|
| explanation | str | Natural language explanation of the answer and reasoning |
| confidence_statement | str | Honest characterisation of answer certainty |
| proof_summary | Optional[str] | Human-readable proof steps (for verified answers) |
| clarification | Optional[str] | If clarification was generated by Understanding Engine |

### Internal Process

```
Step 1 — Select explanation template by response type
  VERIFIED + is_unique:       Full explanation with proof steps
  VERIFIED + not is_unique:   Explanation with ambiguity note
  UNVERIFIED (CEGIS failed):  Cannot solve + reason
  NEW_CONCEPT_LEARNED:        Teaching confirmation + usage example
  CLARIFICATION_NEEDED:       Clarification question

Step 2 — Fill template
  answer_str = format_value(final_output.answer, units=perception.entities[unknown].unit)
  concepts_str = ", ".join(final_output.concepts_used)
  iterations_str = "" if final_output.attempts == 1 else f" (verified in {final_output.attempts} iterations)"

Step 3 — Generate proof summary (if is_verified)
  For each ProofStep in proof_trace.steps:
    Line: "Step {i}: Applied {concept_applied} — {operation}({input_values}) = {output_value}"

Step 4 — Append confidence statement
  If final_output.confidence > 0.9: "I am confident this is correct."
  If 0.7-0.9: "This answer is likely correct; verify for critical applications."
  If < 0.7: "This is my best estimate; the problem may be under-constrained."

Step 5 — Append correction hint if present
  If final_output.correction_hint: "Note: {correction_hint}"
```

### Complexity

- O(P) where P = proof steps — linear string construction

---

## Algorithm 14: Decision Making

### Purpose

Decision Making in HSCI is the process of choosing between competing courses of action when the system has multiple options available. This occurs in three contexts:

1. **Concept selection**: when multiple concepts match the input, which one to use first (Algorithm 5, Step 3 — greedy by strength)
2. **Goal prioritisation**: when multiple goals are active, which one to pursue (GoalManager priority tiers)
3. **Clarification vs. best-guess**: when input is ambiguous, whether to ask or proceed (UnderstandingEngine blocking flag)

Unlike planning (which sequences operations), decision making selects between alternatives at a single choice point.

### Decision Rule: Concept Selection

```
Selection criterion: expected_success_probability

expected_success_probability(concept C, perception P) =
  C.strength                           # prior probability of success
  × entity_type_overlap(C, P)          # relevance to current problem
  × (1 - P_inhibited(C, P))           # penalise if recently inhibited for similar input
  × domain_success_rate(C, P.domain)  # historical performance in this domain

Select concept with highest expected_success_probability.
If two concepts have probability within 0.05 of each other:
  Select the one with higher proof_count (more evidence).
```

### Decision Rule: Clarification Threshold

```
Clarify if:
  understanding_confidence < 0.5   AND clarification.blocking == True
  → ALWAYS ask

Proceed with caveat if:
  understanding_confidence in [0.5, 0.7]
  → proceed with best-guess SemanticFrame, flag in response

Proceed silently if:
  understanding_confidence > 0.7
  → normal cycle
```

### Failure Cases

| Failure | Cause | Behaviour |
|---|---|---|
| All concepts have equal expected_success_probability | Completely novel domain | Select highest proof_count; emit low confidence |
| Clarification would loop infinitely | User provides ambiguous answers | GoalManager escalates to BLOCKED status after 3 clarification exchanges |

---

## Cognitive Algorithm Interaction Map

The following table shows which algorithms call which during a standard cognitive cycle:

| Algorithm | Called By | Calls |
|---|---|---|
| Planning | BrainKernel (Layer 3) | Decomposition, Composition, Decision Making |
| Decomposition | Planning | — |
| Composition | Planning, SolutionBuilder | — |
| Verification | BrainKernel (Layer 4, CEGIS) | Deduction |
| Deduction | Verification, Abduction, Analogy | — |
| Induction | LearningEngine (Layer 5) | — |
| Abduction | ReasoningEngine (when unknown is input) | Deduction |
| Analogy | ReasoningEngine (when no direct match) | Deduction, Composition |
| Hypothesis Generation | SelfPlayEngine | Planning, Verification |
| Counterfactual | Reflection (post-cycle) | Deduction, Verification |
| Reflection | BrainKernel (post-cycle, async) | Counterfactual, Decision Making |
| Explanation | ResponseBridge (Layer 6) | — |
| Optimisation | Verification (when is_unique=False) | — |
| Decision Making | Planning, GoalManager, UnderstandingEngine | — |

---

## Algorithm Complexity Summary

| Algorithm | Complexity | Bottleneck | V4 Mitigation |
|---|---|---|---|
| Deduction | O(n²) per call | Z3 DPLL(T) | 5000ms timeout; bounded at 5 CEGIS iterations |
| Induction (micro) | O(1) | — | None needed |
| Induction (macro) | O(E×C/D²) | Episode × Concept scan | Domain partitioning; nightly batch |
| Abduction | O(R × T_Z3) | R × Z3 calls | CAE limits R to ≤ 20 candidates |
| Analogy | O(A × E²) | Entity mapping | A capped at 10 analogical candidates |
| Planning | O(S × C) | Concept assignment | Skill memory reduces to O(1) on hit |
| Decomposition | O(K) | Template lookup | O(1) — 4 fixed templates |
| Composition | O(S) | Z3 And chain | Linear — not a bottleneck |
| Hypothesis Gen | O(1) | — | None needed |
| Counterfactual | O(A × T_Z3) | Alternative concept tries | Capped at 5 alternatives |
| Reflection | O(F) systematic | Failure log scan | Rolling window of 10,000 |
| Verification | O(5 × n²) | CEGIS loop | Bounded iterations; timeout |
| Optimisation | O(n³) | Z3 OptiSolver | Only invoked for non-unique solutions |
| Explanation | O(P) | Proof step string | Not a bottleneck |
| Decision Making | O(C) | Concept scoring | CAE pre-scores; O(1) selection |
