# HSCI Cognitive Substrate — Final Design Review

**Status:** REVIEW ONLY. No source code was modified to produce this document. It refines `HSCI_UNIFIED_ARCHITECTURE.md` — it does not replace it; it narrows it to a buildable first slice, using mechanism-level evidence gathered by reading the exact code paths involved (not previously read at this depth in the audit).

---

## 1. Executive Conclusion

The audit's worst bug ("what number becomes 20 after adding 10?" → confidently answered 30) and the Unified Architecture's central diagnosis (math and concept-understanding are two disjoint representations) are the same fact, traced this session to three specific, small pieces of code:

1. `GroundingEngine._ground_candidate()` does not ground math at all — for any `SolveMathematics` interpretation it unconditionally fabricates one fake `GroundedEntity(concept_id="c_mathematics", status=RESOLVED)` and returns `GROUNDED` (`hsci/cognition/interpretation/grounding.py:135-144`). Grounding for math is a rubber stamp, not a check.
2. `TaskDeriver.derive()` then hands the `SOLVE_MATHEMATICS` task nothing but `{"raw_text": situation.raw_input.original_text}` (`hsci/cognition/interpretation/task_deriver.py:73-79`) — every entity, role, and relation that `Interpret` and `Ground` produced is discarded, and solving starts over from the raw string.
3. `UniversalMathEngine._infer_formula()` (`hsci/reasoning/universal_math_engine.py:472-509`), the fallback that ran on this exact question, decides the operation by **substring presence of a keyword anywhere in the text** — `"add" in text` is true because "add" is a substring of "add**ing**" — and then returns `sum(vals)` over whichever known numbers it found, with **no representation of which number is the target, which is an operand, or which direction the relation goes**. "Becomes 20 *after* adding 10" and "*is* 20 *plus* 10" are indistinguishable to this code.

Separately, even where Z3 already exists and is wired (the legacy, disconnected `ReasoningEngine → Z3VerificationEngine` path), `Z3VerificationEngine.verify()` contains an explicit early return: *"Handle non-Z3 expressions (e.g. solved values from the universal engines)"* (`hsci/symbolic/z3_verifier.py:71-106`) — if the candidate isn't already a `z3.ExprRef`, it is declared `PROVEN, confidence=1.0` **without running Z3 at all**. `UniversalMathEngine` always returns a plain Python float, so this path is not a fallback — it's the path every math answer in the codebase has always taken, live or legacy. Z3 code exists in this repository and has never actually verified a `UniversalMathEngine` result.

**Conclusion:** the fix is not "add more math phrasings" or "add a verification pass." It is that no representation currently survives from language to solver to verifier — each stage either re-parses raw text or accepts an unchecked scalar. The minimum cognitive substrate is the smallest change that makes a **typed structure survive intact from Interpret through Verify**, for both math and concepts, using the same representation. §17 identifies the precise, small first component that provides this.

---

## 2. Current Architectural Baseline (delta since the original audit)

`HSCI_TRUE_STATE_AND_STARTING_POINT.md` established the live pipeline (`CognitivePipeline`: Interpret → Ground → Task-derive → Workspace-execute → Answer) and that Z3/learning are disconnected. This review adds three mechanism-level findings not previously traced to exact code (§1, items 1–3, plus the `z3_verifier.py` auto-PROVE escape hatch), which sharpen *why* the disjoint-pipeline problem is the correct thing to fix first, and *how small* the fix can be — see §15 and §17.

One correction to `HSCI_UNIFIED_ARCHITECTURE.md`: that document proposed session/context memory as the first implementation step. On direct instruction and after this deeper read, that recommendation is withdrawn, not merely deferred — session memory is a real gap, but it is not what produced any bug the audit found; the representation-unification gap in §1 produced the worst one. §17 replaces it.

---

## 3. What "Cognitive Substrate" Actually Means

Not "nodes and edges." A cognitive substrate is the **process by which a predicate-argument reading of language becomes a checkable formal claim**, and the data shape that reading is written into along the way.

Concretely, for *"A value is doubled and then increased by 6 to produce 30. What was the original value?"*, the process is:

1. **Predicate recognition.** "doubled" denotes a unary operation `MULTIPLY(_, 2)`; its implicit argument is whatever the sentence's subject is ("a value"). "increased by 6" denotes `ADD(_, 6)`, chained onto the previous result (signaled by "and then"). "to produce 30" denotes an equality: the final chained result `EQUALS 30`. "What was the original value?" denotes that the *first* argument in the chain is the unknown being solved for, not the answer itself.
2. **Role assignment, not keyword lookup.** The word "doubled" maps to an operation *type with defined arity and an argument role* (one operand, known multiplier 2, unknown base) — this is closed-class lexical knowledge, exactly as unavoidable as knowing "add" is a verb. It is categorically different from asking "does the word 'add' appear in the string anywhere" (§1, item 3) — that check has no concept of argument role, direction, or arity, which is precisely why it computed `20 + 10` for a question whose correct operation was `20 − 10`.
3. **Chaining into one formal object.** The three recognized operations compose, by their explicit chaining language ("and then," "to produce"), into a single equation: `2x + 6 = 30`. This composition is mechanical once each piece carries its role — it does not require a new rule for "doubled-then-increased" as a whole; it requires only that each piece's role survive to be composed.
4. **The equation, not the sentence, is what gets solved and what gets verified.** SymPy solves `2x + 6 = 30 → x = 12`. Verification's job is to confirm this equation is what the sentence actually asserted (§9) — checkable only because step 1–3 produced a structure to check, not because the final number happens to look plausible.

**What must never be lost, from raw language through to the answer:** which surface span produced which node (`source`), what role that node plays (operand / result / target-unknown), the direction/order of each operation (order-sensitive operations — subtraction, division — cannot be represented as a bag of numbers the way `_infer_formula` currently does), and the confidence/assumption trail that produced each node. Losing any of these is exactly what happens today at the `TaskDeriver` boundary (§1, item 2).

---

## 4. Meaning Representation Model (revised from the Unified Architecture)

**Correction to the prior document:** `HSCI_UNIFIED_ARCHITECTURE.md` proposed a new node/edge graph type modeled on MGS-1. Reading the live data models this session (`hsci/cognition/interpretation/semantic_model.py`, `models.py`) shows this is mostly unnecessary — **a real, working, graph-shaped representation already exists**: `EntityMention` (node), `SemanticRelation` (typed edge between two mentions), `SemanticConstraint` (edge-like modifier), all carrying `confidence`/`source` already, aggregated into `SemanticRequest` and then `CognitiveSituation`. This is not a rewrite target; it is 80% of the target representation already, minus one thing: **it has no way to represent a quantity, a variable, or an operation** — `EntityMention` has no numeric-value field and no known/unknown flag, and `SemanticRelation.relation_type` is an open string never populated with operation semantics.

**The minimum extension (not a new class hierarchy):**
- `EntityMention` gains: `role: EntityRole` (`CONCEPT | QUANTITY | VARIABLE`, default `CONCEPT` — fully backward compatible with every existing concept-question code path), `numeric_value: Optional[float]`, `is_known: Optional[bool]`.
- `SemanticRelation.relation_type` gains a **closed** vocabulary member for operations and equality, used only when `role != CONCEPT` on both ends: `OPERATION:ADD`, `OPERATION:SUBTRACT`, `OPERATION:MULTIPLY`, `OPERATION:DIVIDE`, `EQUALS`. Order matters: `source_mention`/`target_mention` are positional (`source − target`, not `target − source`), which is exactly the information `_infer_formula`'s `sum(vals)` currently throws away.
- Nothing else changes. `SemanticConstraint`, `ContextReference`, `CognitiveSituation`, `CognitiveTask` are untouched.

This is deliberately smaller than the Unified Architecture's proposal. No `Entity`/`Event`/`Rule`/`Hypothesis` node types, no `CAUSES`/`PART_OF`/`DEPENDS_ON` edges, no confidence-branching ambiguity graph — none of that is exercised by anything in scope here (§20), and adding it now would be exactly the "architectural completeness for its own sake" this review was told to avoid.

**Observed / interpreted / grounded / derived / hypothetical**, mapped to fields that already exist and need no new machinery: `Evidence.confidence` + `source_method` already distinguish how a candidate arose (interpreted/hypothetical); `GroundedEntity.status` (`RESOLVED`/`AMBIGUOUS`/`UNKNOWN`) already distinguishes grounded from not; a `TaskResult` (VS-7, already real) marked with `provenance_type` already distinguishes `CANONICAL_KNOWLEDGE`/`DERIVED_CONCLUSION` from `TASK_EXECUTION`. The vocabulary this review needs already exists; only quantity/operation typing is missing.

---

## 5. Interpretation Process

**Responsibility unchanged from the Unified Architecture (§2.1 there):** propose role-typed hypotheses; decide nothing.

**What changes concretely:** `LanguageInterpreter._analyze_semantic_request()`'s math path currently does two things conflated into one — (a) decide "this is math" and (b) hand the whole string to `UniversalMathEngine`. It must instead only do (a)'s *proposal* half: recognize operation-denoting predicates (a small, closed lexicon — "double"/"twice" → `MULTIPLY(_,2)`; "increase by N"/"add N" → `ADD(_,N)`; "decrease by N"/"less than N" → `SUBTRACT` with the correct operand order; "becomes Y"/"gives Y"/"produce Y" → `EQUALS(_,Y)`) and emit typed `EntityMention`(`role=QUANTITY`/`VARIABLE`) and `SemanticRelation`(`OPERATION:*`/`EQUALS`) hypotheses — the same shape COMPARE/RELATE already produce for concepts, just with the new role/relation vocabulary from §4. It does not call `UniversalMathEngine`, does not decide the final equation string, and does not require a template per phrasing (§12).

The regex-cascade for COMPARE/RELATE/EXPLAIN is otherwise unchanged — it already does exactly this job correctly for concepts (verified working live in the audit) and is not being redesigned here.

---

## 6. Grounding Model

**Responsibility unchanged (Unified §2.2).** What changes: `_ground_candidate`'s `SolveMathematics` special case (§1, item 1) is deleted. Quantity/Variable mentions are grounded like any other mention, just against a different resolver than the UKM: a `QUANTITY` mention resolves by parsing its numeral (already-normalized text — comma-stripping etc. already happens upstream and is reused, not duplicated); a `VARIABLE` mention resolves by being marked `known=False` with no numeric value required. Both produce ordinary `GroundedEntity` records with `status=RESOLVED` — grounding for a number is "this parses as a number," exactly as grounding for a concept is "this resolves in the UKM." No fabricated placeholder entity is produced.

**A genuine, previously-unflagged gap found this session:** `_ground_candidate`'s status logic is `has_unknown or resolved_count == 0 → UNRESOLVED_ENTITIES`. This means a two-entity `COMPARE` where *one* side resolves and the other doesn't (e.g. "compare Java interfaces with abstract classes," and `Abstract Class` isn't seeded) is refused **as a whole**, exactly like a zero-entity failure, rather than answered partially with an honest "I don't have `Abstract Class` defined" note attached to the one side that failed. This is a real, small, in-scope fix: `CognitiveSituation.status` needs a `PARTIALLY_GROUNDED` value distinct from `UNRESOLVED_ENTITIES`, so Answer can render what's known and honestly flag what isn't, instead of an all-or-nothing refusal. Included in the MVP (§15) because it is cheap and is a direct instance of the project's own "fail honestly" principle currently being violated by an overly coarse status enum, not by any solver.

**Explicit seam, unchanged from the Unified Architecture:** conversation-history resolution tier remains an empty, documented slot — out of scope (§20).

---

## 7. Goal / Problem Representation

Already real and correct: `TaskDeriver` mapping `CognitiveSituation → CognitiveTask(action: TaskAction, primary_target, parameters)` is kept as-is, structurally. The only change is *what* `parameters` carries for `SOLVE_MATHEMATICS`: the grounded `Quantity`/`Variable`/`Operation` mentions and relations from Ground (§6), not `{"raw_text": ...}`. `TaskAction` (`EXPLAIN_CONCEPT`/`COMPARE_CONCEPTS`/`DERIVE_RELATIONSHIP`/`SOLVE_MATHEMATICS`/`ANSWER_GENERAL`/the three refusal actions) is a correct, sufficient goal vocabulary for this scope — no `Goal`/strategic-hierarchy addition from the Unified Architecture is needed; that was more machinery than this substrate requires (pruned, per §20).

---

## 8. Reasoning Model

Unchanged from the Unified Architecture's `Solver` protocol (`applies_to(situation) -> bool`, `solve(situation) -> TaskResult`), with routing decided over the grounded structure, never raw text:

- **GraphRuleSolver** = today's `CognitiveReasoningEngine`, unchanged internally (`StoredGeneralization`/`GeneralizationTransitivity`/`NamespaceCohabitation`/`AliasMapping` are all real, correct, evidenced code — §F of the audit). `applies_to`: grounded `Concept`-typed entities with taxonomic relations present.
- **FormalSolver** = `UniversalMathEngine`'s SymPy core (`_solve_equation`/`_evaluate_expression` — the CAS solving itself is real and correct, verified live for well-formed equations), now driven by the grounded `Operation`/`EQUALS` relations from Ground instead of `_infer_formula`'s keyword-substring guessing, which is retired entirely (§12). `applies_to`: grounded `QUANTITY`/`VARIABLE`-typed entities connected by `OPERATION:*`/`EQUALS` relations.
- **CompositionSolver** = today's `TaskDecomposer`/`CognitiveTaskGraph`, unchanged (real, correct — audit §F).

**One addition this session's code-reading makes necessary:** the transitivity rule in `GraphRuleSolver` currently reasons only over UKM-stored `generalizes_to` edges. The syllogism example (§13) requires it to also reason over `IS_A`/`GENERALIZES` edges **asserted by the current utterance itself** ("All bloops are razzles" is a premise, not a retrieval target). This is a data-source change, not a rule change — the same `GeneralizationTransitivity` code runs over `{UKM edges} ∪ {utterance-asserted edges}`; the rule itself is untouched. Scoped into MVP because the rule already exists and the change is additive.

---

## 9. Verification Model

Unchanged in intent from the Unified Architecture §2.4/§1.2 (`Verified` / `Retrieved` / `Refused`, closed sum type). Sharpened by this session's reading of `z3_verifier.py`:

**Hard requirement, stated as a contract `Verify` must enforce, not merely aspire to:** a `TaskResult` from `FormalSolver` is only eligible for `Verified` if it carries a Z3-compilable constraint. If it doesn't, `Verify` must return `Refused` (or, transitionally, `Retrieved` at reduced confidence with an explicit "not formally checked" flag) — it must **never** fall through to an unconditional `PROVEN` the way `z3_verifier.py:72-106` currently does for any non-`z3.ExprRef` candidate. This single contract closes the exact hole that let a wrong answer be labeled "Confidence: 1.00 (Verified)."

**What "checked," concretely, means here (the meaning-to-formalization match from the Unified Architecture, now precise):** Z3 is given the grounded roles directly — `known` quantities become fixed `z3.Real` constraints (`_build_constraints` in `z3_verifier.py` already does exactly this, correctly, and is reused unchanged), the `OPERATION`/`EQUALS` relations from Ground become the equation Z3 checks satisfiability of, and the *result variable* is whichever `VARIABLE`-role node Ground marked unknown — not re-inferred, not re-guessed. Because the equation is built from the same grounded roles §4–§6 produced (not re-derived from text a second time), there is only one place a misreading of "becomes 20 after adding 10" could occur — in Interpret's predicate recognition (§5) — and it is checkable there by inspection of the typed relation, not hidden behind a solver's opaque heuristic.

`GraphRuleSolver` results: unchanged from the Unified Architecture — the existing transitive-closure derivation with explicit premises already constitutes a real, checkable proof; `Verify` formalizes it as `Verified` rather than adding new machinery.

---

## 10. Ambiguity / Uncertainty Model

Minimum mechanism, not the Unified Architecture's deferred ambiguity-branch-node graph (still out of scope, §20):

- **Multiple grounded readings that fully resolve differently** (e.g. two UKM concepts share an alias): today's `GroundingEngine` already refuses to silently pick one (`AMBIGUOUS` status, both candidates preserved) — kept unchanged, it is correct.
- **Partial resolution** (§6's finding): a new `PARTIALLY_GROUNDED` status, rendered as an honest partial answer plus an explicit gap statement — this is the one genuinely new ambiguity-handling behavior in scope.
- **Unresolvable** (no grounding at all): `REPORT_UNKNOWN`, unchanged, already correct and honest (verified live in the audit — "capital of France" refused cleanly).
- **Interpret-level competing hypotheses** (e.g. text that could be `COMPARE` or `EXPLAIN`): `Ground` already evaluates every candidate and keeps the best-grounding one (`GroundingEngine.ground()`'s loop over `candidates`) — kept unchanged.

**Decision rule, made explicit (not stated anywhere in code today):** HSCI proceeds automatically only when exactly one interpretation reaches full or partial grounding; it reports ambiguity when two or more candidates ground equally well; it refuses when none ground; it **never** silently takes the highest-confidence guess when grounding itself is contested — confidence from Interpret is a ranking signal for *which candidate Ground evaluates first*, never a substitute for Ground actually resolving it. Clarification-request and hypothesis-branching (asking the user, or exploring multiple readings in parallel) are explicitly not built now — refusal is the correct MVP behavior for genuine ambiguity, exactly as it already is for genuine unknowns.

---

## 11. Learned-Model Boundary

Sharpened from the Unified Architecture §1 ("Routing" row) using the exact code involved: `NeuralSemanticModel` (a from-scratch 30-sentence classifier, retrained identically every process boot) and `TrainableSemanticParser` (the BiLSTM tagger) remain permitted, unchanged internally, but strictly as **INTERPRET-stage hypothesis proposers** — their vote contributes a low-confidence candidate `EntityMention`/`SemanticRelation` set, exactly like a regex match does. Neither may gate `Solver.applies_to()`, because that decision is made from *grounded* structure that neither classifier ever sees. This is what makes the audited syllogism-misrouted-to-math bug structurally impossible rather than merely reduced: a classifier vote can propose that a sentence "looks mathematical," but only the presence of actual grounded `QUANTITY`/`OPERATION` structure after Ground makes `FormalSolver.applies_to()` return true.

**What a learned model may never do:** decide `Verified`, decide grounding (resolve a mention against the UKM), or supply a `TaskResult`'s content directly. **What it may do:** propose candidates for Interpret to include alongside deterministic pattern matches, at whatever confidence it has earned — Ground and Verify treat a neural proposal and a regex proposal identically, by grounding and (where applicable) proof, never by which mechanism produced the hypothesis.

---

## 12. Hardcoding Boundary

Precise version of the boundary the review asked for, calibrated against real code found this session:

**Illegitimate (must be eliminated, not merely avoided in new code):** `_infer_formula`'s `"add" in text → sum(vals)` (§1, item 3) — a keyword's bare *presence*, checked with no argument-role, arity, or direction information, driving a numeric operation over "whatever known values happen to exist." This is why it is wrong on the audited example and would be wrong on any input where the keyword's role isn't "the two known values should simply be summed" — which is most of them. The same category includes any future "if 'Java' → knowledge lookup" text-level special case (per §1's routing fix, this category cannot exist post-fix, because routing runs on grounded shape, not text).

**Legitimate (required, and not the same thing):** a closed lexicon mapping operation-denoting predicates to `(operation_type, arity, argument_roles)` — "double" → `(MULTIPLY, arity=1, roles=[implicit_subject])`, exactly as unavoidable as knowing "add"/"class"/"interface" are words with fixed grammatical categories. The test that distinguishes the two categories, stated as a rule an implementer can apply directly: **a mapping is legitimate linguistic knowledge if it produces a *role-typed* structure that a downstream stage must still combine and check (per §3–§9); it is hardcoding if it produces a *final numeric or textual answer*, or an operation choice blind to which value plays which role, directly from a keyword match.** `_infer_formula` fails this test on both counts. The COMPARE/RELATE/EXPLAIN regex patterns in `LanguageInterpreter` pass it — they produce role-typed entity/relation hypotheses (two concepts + a comparison edge), which Ground and the answer synthesizer still have to resolve and compose; they never emit a final answer string from a keyword match.

This boundary also settles the review's explicit worry: the redesigned substrate cannot silently become `if "double" → multiply` in a different file, because `multiply` under this design is never a final answer — it is one typed edge in a graph that still has to be composed with every other edge and then independently checked by Z3 (§9) before anything is asserted to the user. A keyword-to-answer shortcut has nowhere left to hide once verification requires the compiled equation, not the keyword match, to satisfy Z3.

---

## 13. Unseen-Input Validation Examples (architectural traces, not handlers)

### Mathematics — four phrasings, one structure

All four below must ground to the identical equation subgraph (`x + 10 = 20`, `x` unknown) before reaching `FormalSolver` — convergence of *structure*, not merely of final answer, is the actual test (§8's last point):

```
"x + 10 = 20"                                  "What number becomes 20 when 10 is added to it?"
INTERPRET: Operation nodes read directly        INTERPRET: "becomes Y when Z is added" ->
  from symbols "+", "="                           EQUALS(ADD(x, 10), 20); "what number" -> x is VARIABLE
MEANING:  Variable(x) --OPERATION:ADD(10)-->    MEANING:  Variable(x) --OPERATION:ADD(10)--> r1
            r1 --EQUALS--> Quantity(20)                    r1 --EQUALS--> Quantity(20)
GROUND:   x=VARIABLE(unknown), 10/20=QUANTITY   GROUND:   identical
GOAL:     SOLVE(x)                              GOAL:     SOLVE(x)
REASON:   FormalSolver.applies_to -> True        REASON:   identical subgraph -> same solver call
VERIFY:   Z3: x+10=20 sat, x=10; matches          VERIFY:   identical proof
          grounded roles (10 is operand,
          20 is result, x is target)
ANSWER:   Verified, x = 10                      ANSWER:   Verified, x = 10

"Ten more than an unknown value gives twenty."   "A value is doubled and then increased by 6
INTERPRET: "N more than X gives Y" ->             to produce 30. What was the original value?"
  EQUALS(ADD(x, 10), 20) — same predicate         INTERPRET: MULTIPLY(x,2) -> r1; ADD(r1,6) -> r2;
  class as "increased by", different surface        EQUALS(r2, 30); "original value" -> x is target
  order, same role assignment                     MEANING: chained Operation nodes, per §3
MEANING/GROUND/GOAL: identical to above          GROUND:  x unknown, 2/6/30 known quantities
REASON/VERIFY/ANSWER: identical to above,        REASON:  FormalSolver composes 2x+6=30
  x = 10                                         VERIFY:  Z3: 2x+6=30 sat, x=12; matches roles
                                                  ANSWER:  Verified, x = 12 (NEW — fails outright today)
```

The first three converge on identical structure using only the existing MVP lexicon (§12). The fourth is a genuinely new capability (chaining) — included in MVP scope (§15) specifically because it is the direct generalization test the review asked for, not because it is easy.

### Knowledge

```
"Explain Java interfaces."                       "Compare Java interfaces with abstract classes."
INTERPRET: EXPLAIN(concept="Java Interface")     INTERPRET: COMPARE(concept="Java Interface",
GROUND:    RESOLVED (seeded)                       concept="Abstract Class")
REASON:    GraphRuleSolver: definition +          GROUND:    "Java Interface" RESOLVED,
  StoredGeneralization + GeneralizationTransitivity  "Abstract Class" UNKNOWN (not seeded) ->
VERIFY:    Retrieved (provenance chain, not         PARTIALLY_GROUNDED (§6/§10, new status)
  formally proven — honestly labeled as such)      REASON:    GraphRuleSolver runs on the resolved side only
ANSWER:    real, working today, unchanged         VERIFY:    Retrieved for the resolved half
                                                   ANSWER:    "Here is Java Interface: ... I don't have
                                                     'Abstract Class' defined, so I can't compare it yet."
                                                     (honest partial answer, not a blanket refusal)

"Why can't a Java class extend two classes?"
INTERPRET: EXPLAIN with a causal/design-rule reading ("why can't" implies a CAUSES/rule claim)
GROUND:    "Java class" RESOLVED; the causal claim itself has no grounded CAUSES fact in the UKM
STATUS:    UNRESOLVED (honest) — no CAUSES edge type exists in this MVP's schema (§4, explicitly
             out of scope) and no such fact is seeded
ANSWER:    Refused, honestly, exactly as today — this is a knowledge-seeding gap, not a substrate
             gap, and this review does not claim to close it (§20)
```

### Reasoning (unseen syllogism)

```
"All bloops are razzles. All razzles are lazzles. Therefore, are all A C?"
INTERPRET: two utterance-asserted GENERALIZES edges (bloop->razzle, razzle->lazzle) proposed as
  premises, not retrieval targets (§8's addition) + a VERIFY-goal query (bloop->lazzle?)
GROUND:    all three terms RESOLVED as ad hoc Concept nodes scoped to this request (no UKM entry
  required — they are defined by the utterance itself)
REASON:    GraphRuleSolver.applies_to -> True (GENERALIZES edges present); the existing, unmodified
  GeneralizationTransitivity rule runs over {utterance edges}, derives bloop->lazzle
VERIFY:    Verified — premises explicit, rule deterministic, exactly as today's concept-relationship
  proofs already are
ANSWER:    "Yes: every bloop is a lazzle, because bloop generalizes to razzle and razzle
  generalizes to lazzle (transitivity)."
```
Critically, this input contains no digits, no `=`, no arithmetic operator — under the current live system it was misrouted to `FormalSolver` by a tagger vote and only "correctly" refused because SymPy choked on it (audit finding, §G). Under this design it never reaches `FormalSolver.applies_to()` at all, because no `QUANTITY`/`OPERATION` structure exists in its grounded graph — routing is a structural fact, not a probability.

### Unknown

```
"Tell me about an imaginary concept that does not exist in the knowledge base."
INTERPRET: EXPLAIN(concept=<mention>)
GROUND:    UNKNOWN (no UKM match, no alias, no singularization candidate)
STATUS:    UNRESOLVED_ENTITIES
ANSWER:    Refused, honestly — unchanged from today's already-correct behavior (audit-verified live)
```

---

## 14. HSCI vs. External/Pretrained Model

```
External/pretrained model (NeuralSemanticModel, TrainableSemanticParser, any future LLM)
        |  proposes: candidate role-typed nodes/edges, at a stated confidence, as one voice
        |  among several (regex, tagger, neural) feeding INTERPRET (§11)
        v
HSCI cognitive representation   -- role-typed EntityMention/SemanticRelation (§4); no learned
        |                          model's output is ever this representation directly, only a
        |                          proposal toward it
        v
HSCI reasoning                  -- Solver.applies_to() dispatches on GROUNDED structure the
        |                          learned model never sees post-proposal (§8, §11)
        v
HSCI verification                -- Z3/rule proof against grounded roles; a learned model's
        |                          confidence is never itself evidence admissible here (§9)
        v
HSCI answer                     -- rendered only from the closed Verified/Retrieved/Refused type
```

**The research contribution is not "we called Z3 somewhere."** It is the structural requirement, enforced at the type level (§9's hard contract, §12's boundary test), that nothing reaches `Verified` without a proof checked against the *same grounded roles* that produced the candidate — which forecloses exactly the failure mode "LLM/classifier proposes something plausible, and plausibility alone becomes the answer." `LLM + graph database + solver` is not this architecture unless the solver's input is provably derived from grounded structure and the output is checked back against that same structure before being labeled true — most systems that combine those three pieces do not do the "checked back against the same structure" part, and that is precisely the part `z3_verifier.py`'s current escape hatch (§1, §9) shows this codebase has never actually done for math either. Building that check is the actual research content of this substrate.

---

## 15. Minimum Viable Cognitive Substrate

**In scope, concretely:**
1. `EntityMention.role`/`numeric_value`/`is_known` fields (§4).
2. `SemanticRelation`'s closed `OPERATION:*`/`EQUALS` vocabulary (§4).
3. `LanguageInterpreter`'s math path emits typed proposals instead of routing to a bypass (§5).
4. `GroundingEngine` actually grounds `QUANTITY`/`VARIABLE` mentions; the `SolveMathematics` rubber stamp is deleted (§6).
5. `CognitiveSituation.status` gains `PARTIALLY_GROUNDED` (§6, §10).
6. `Solver` protocol; `GraphRuleSolver`/`FormalSolver`/`CompositionSolver` repositioned behind it, `FormalSolver` consuming grounded structure instead of raw text and instead of `_infer_formula` (§8).
7. `GraphRuleSolver`'s transitivity rule runs over utterance-asserted edges in addition to UKM-stored ones (§8).
8. `Verify`'s hard contract: no `Verified` without a checked proof; `z3_verifier.py`'s auto-PROVE-on-non-Z3-value path is removed (§9).
9. Chained-operation composition (multi-step equations) in `FormalSolver` (§13, math example 4).
10. Answer renders only from the closed `{Verified, Retrieved, PartiallyGrounded, Refused}` outcome type — no raw entity-span text ever reaches a user-facing string (closes the audited garbage-leak bug).

**Explicitly not required for this MVP, confirmed against the review's own checklist:** session memory, self-play, mental models, autonomous learning, distributed infrastructure, a general planner — none of items 1–10 depend on any of these, and none of the worked examples in §13 require them.

---

## 16. Dependency Graph

```
[Representation Extension]           (§4: role/relation vocabulary)
        |   nothing downstream has typed data to consume without this — it is not
        |   optional scaffolding, it is the only place "which value is the operand
        |   vs. the target" can be recorded at all
        v
[Grounding Extension]                (§6: real math grounding, PARTIALLY_GROUNDED)
        |   Reason must not re-parse raw text (§1's item 2) — it needs *grounded*
        |   quantities (parsed, known/unknown-flagged), which only Ground can produce
        v
[Solver Interface + FormalSolver]     (§8: replaces _infer_formula and the raw-text path)
        |   Verify needs a solver output shaped as a checkable equation over grounded
        |   roles, not a bare float — FormalSolver is what produces that shape
        v
[Verify Extension]                    (§9: Z3 compilation + hard no-auto-PROVE contract)
        |   Answer needs a *closed, typed* outcome to render uniformly — without this,
        |   "Verified" keeps meaning two different things (§1.2 of the Unified doc)
        v
[Answer Extension]                    (§15 item 10: render from typed outcome only)
        |
        v
[Solver-interface generalization for GraphRuleSolver/CompositionSolver]
        (mechanical repositioning of already-correct code; no logic changes;
         can happen in parallel with the chain above once the Solver protocol exists)
```

Each arrow is an **implementation** dependency (the later step has nothing correct to consume without the earlier one's output shape), not merely an **architectural** one (the Unified Architecture's five named stages are all "architecturally related" to each other, but, e.g., `Answer`'s renderer could technically be rewritten before `Verify`'s contract is tightened — it would just have nothing to render yet). The chain above is ordered strictly by data availability, which is why it differs from a simple restatement of the five pipeline stages.

---

## 17. True First Implementation Component

**The Representation Extension (§4 / §16, first box): add `role`/`numeric_value`/`is_known` to `EntityMention` and the closed `OPERATION:*`/`EQUALS` vocabulary to `SemanticRelation.relation_type`, in `hsci/cognition/interpretation/semantic_model.py`.**

This is not "session memory" (excluded by direct instruction, and, per §2, not implicated in any audited bug) and not "the whole Meaning Graph" (per §4, most of it already exists — this is a two-field, one-enum extension to two existing dataclasses, not a new subsystem).

- **Inputs:** none — this is a pure data-model change with no new runtime dependency.
- **Outputs:** a strictly backward-compatible extension — every existing `EntityMention`/`SemanticRelation` construction site continues to work unchanged (`role` defaults to `CONCEPT`, matching current behavior exactly).
- **Invariants:** `numeric_value`/`is_known` are only meaningful when `role != CONCEPT`; `OPERATION:*`/`EQUALS` relation types are only meaningful when both endpoints have `role != CONCEPT`. Nothing enforces these invariants at the type level yet — that enforcement belongs to the next component (Grounding Extension), not this one.
- **Responsibilities:** define the shape. Nothing else.
- **Non-responsibilities:** does not parse text, does not resolve anything against the UKM, does not solve anything, does not touch `LanguageInterpreter`, `GroundingEngine`, `UniversalMathEngine`, or `z3_verifier.py` — those are the next four components in §16, each unlocked by this one but each a separate, reviewable change.
- **Dependencies:** none upstream. Everything in §16 downstream depends on it.
- **Acceptance criteria:** (a) existing test suite (418 `hsci/tests`, verified passing this session) is unaffected — a pure additive dataclass change should not touch any existing assertion; (b) a new unit test constructs an `EntityMention(role=QUANTITY, numeric_value=10, is_known=True)` and a `SemanticRelation(relation_type="OPERATION:ADD", ...)` and confirms `to_dict()` round-trips correctly (both classes already have this method — extend it, don't replace it); (c) no behavior of the live system changes yet, because nothing yet constructs these — this component's acceptance is purely structural, deliberately, so it can be reviewed and merged independently of the four components that give it meaning.

This is the smallest change that is still real: it is the one place identified in this entire review (§1, §3, §12) where the *absence* of a field is the direct, traceable cause of a confirmed wrong-answer bug, and every other component in §16 is unbuildable without it.

---

## 18. Runtime Acceptance Criteria

Not "tests pass." Behavioral, adversarial, checked against the live `/process` endpoint once the full §16 chain lands:

1. **The exact audited bug is fixed and mechanically explained, not just patched around:** "What number becomes 20 after adding 10?" → `x = 10`, `Verified`, with a rendered proof trace citing the grounded roles (20=result, 10=operand, x=target) — not merely a different final number.
2. **Generalization, not phrase-table growth:** "Twelve less than a number is nine. What is the number?" (a phrasing with no pattern anywhere in the current or proposed lexicon beyond the closed operation-predicate list in §12) resolves correctly (`x = 21`) without any new regex or phrase added to route it.
3. **Structural routing, not classifier voting:** the syllogism example (§13) never invokes `FormalSolver.applies_to() == True` — verified by inspecting which solver actually ran, not just by checking the final answer is correct (a correct-by-luck refusal, as today's system produces, must fail this criterion even though the visible output looks similar).
4. **No silent auto-PROVE:** a `FormalSolver` result that is *not* Z3-compilable (constructed adversarially in a test, e.g. by feeding a candidate whose equation references an ungrounded symbol) is rejected by `Verify`, not passed through as `Verified` — direct regression test against the exact `isinstance` escape hatch in `z3_verifier.py:72`.
5. **No internal-artifact leakage:** every `Refused`/`PartiallyGrounded` outcome, across all examples in §13, renders human-readable text sourced only from `CognitiveSituation.status` and `GroundedEntity.mention` — a fuzz test asserting no rendered answer ever contains a comma-joined n-gram list (regression against the audited "value doubled, doubled then, ..." leak).
6. **Structural convergence, checked directly:** the four math phrasings in §13 produce equation subgraphs that are structurally identical (same operation types, same operand roles, same target) before reaching `FormalSolver` — asserted on the grounded structure itself, not only on the final numeric answer, because identical final answers can be produced by different (and differently wrong-on-other-inputs) heuristics.
7. **Partial honesty:** the "Compare Java interfaces with abstract classes" example produces a `PartiallyGrounded` outcome with a real definition of `Java Interface` and an explicit, correctly-worded statement that `Abstract Class` is not known — not a blanket refusal (regression against §6's finding) and not a fabricated definition of `Abstract Class`.

---

## 19. Future Learning Seam

Unchanged in spirit from the Unified Architecture §5, now traceable to concrete typed objects this substrate actually produces at each stage: `RawInput` (input), `InterpretationSet` (interpretation hypotheses), `CognitiveSituation` (grounded meaning), `CognitiveTask` (goal), the chosen `Solver` + its `TaskResult` (strategy + execution), and the `VerifiedOutcome` (result + outcome, per §9's closed type). A future `Experience` record is exactly the tuple of these six objects, already produced, already typed, already carrying provenance — logging them (not redesigning them) is the entire scope of a future learning-seam design pass. Pattern extraction, generalization, and skill/concept formation (LAA-1, `Concept_Formation_Theory.md`) remain undesigned here, deliberately (§20) — they have real objects to consume once this substrate exists, which is the only claim this section makes.

---

## 20. Explicit Non-Goals

Session/conversation memory; lexical-resolver algorithm internals beyond the contract in §6; learning, self-play, skill formation, concept formation, mental models; any general HTN planner; distributed infrastructure of any kind; the full SIA-1 12-subsystem interpreter (Emotion/Pragmatic/Spatial/Temporal-Allen-Algebra interpreters); MGS-1's ambiguity-branch-node subgraph forking; `Entity`/`Event`/`Rule`/`Hypothesis` node types and `CAUSES`/`PART_OF`/`DEPENDS_ON` edge types from the Unified Architecture's schema (pruned here, §4, as unused by anything in scope); `ExecutiveController` cost-formula governance; `ResponseBridge`-style domain/tone formatting; rewriting `GraphRuleSolver` or `CompositionSolver` internals (both already correct — only their calling convention changes, §8); the CEGIS repair loop (a single correct verification pass is the MVP requirement, per the Unified Architecture §2.4, unchanged); resolving `hsci/core/rir_loop.py`'s fate.

---

## RECOMMENDED NEXT IMPLEMENTATION STEP

Implement the **Representation Extension** (§17): add `role: EntityRole` (`CONCEPT | QUANTITY | VARIABLE`), `numeric_value: Optional[float]`, and `is_known: Optional[bool]` to `EntityMention`, and add the closed `OPERATION:ADD | OPERATION:SUBTRACT | OPERATION:MULTIPLY | OPERATION:DIVIDE | EQUALS` vocabulary to `SemanticRelation.relation_type`, in `hsci/cognition/interpretation/semantic_model.py`. Purely additive, backward-compatible, no behavior change on its own, independently reviewable and testable per §17's acceptance criteria, and it is the single upstream dependency every other item in §16 requires before it can do anything real.
