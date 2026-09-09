# HSCI Unified Cognitive Architecture (v1)

**Status:** PROPOSED — design only, not implemented. No code in this repository has been changed to produce this document.

**Supersedes, for the scope defined in §0.2:** `ARCHITECTURE_CONSTITUTION.md`, `HSCI_Complete_Master_Document.md`, `HSCI_Architecture_Prompt.md`, the `docs/architecture/cognition/*` RCA-1/SIA-1/MGS-1/ECA-1/CEA-1/WMA-1/GMA-1 suite, `SYSTEM_VS_APPLICATION.md`, `HUMAN_LIKE_COGNITION.md`, `APPLICATION_ARCHITECTURE.md`, `SELF_TEACHING_ARCHITECTURE.md`, and `HSCI_RESEARCH_PAPER.md` — all three prior architecture generations identified in `HSCI_TRUE_STATE_AND_STARTING_POINT.md` §E.1. Those documents remain readable as historical/reference material and are the source of most of what is *kept* below; none of them is discarded wholesale.

**Does not supersede:** anything about learning, self-play, skill/concept formation, or mental models (LAA-1, `SELF_TEACHING_ARCHITECTURE.md`'s learning loop, `Concept_Formation_Theory.md`) — those are out of scope here (§0.2) and remain live reference material for a later design pass.

**Basis:** every claim below is either (a) traced to code that is already real, correct, and connected in the live system, per the audit's §D/§F/§G, or (b) a specification choice with an explicit rationale in §1. Nothing here is aspirational without being labeled so.

---

## 0. Purpose, Method, and Scope

### 0.1 Purpose

The audit (`HSCI_TRUE_STATE_AND_STARTING_POINT.md`) found three complete, mutually unaware, self-declared-canonical architecture generations, plus a fourth, undocumented architecture that is what actually runs. No document in the repository resolves this — the closest attempt, `CRR-1`, only reconciles *within* its own generation and contradicts a sibling document (`MODULE_CLASSIFICATION.md`) while doing so. This document is that resolution: one architecture, one internal representation, one pipeline, with every contradiction the audit found explicitly decided and justified.

### 0.2 Scope

This document designs the **minimum cognitive substrate**: the smallest coherent set of components that takes arbitrary human input and produces a verified (or honestly refused) answer, in one pass:

```
input -> meaning -> reasoning -> verification -> answer
```

**Explicitly out of scope**, per direct instruction and because none of it is a precondition for the loop above to work correctly on a single turn:
- Session/conversation memory (multi-turn context, coreference across turns).
- Lexical resolver internals (how words map to concepts — the *interface* is designed here; the algorithm is not).
- Learning, self-play, skill formation, concept formation, mental models.
- Any distributed-systems infrastructure (Rust runtime, Kafka, Raft, gRPC, Neo4j, Postgres, Kubernetes).

These are named at every point where the substrate must leave a seam for them (§5), so that building them later does not require re-architecting this pass. Designing them now was tried three times already (three document generations) without producing matching code; this pass deliberately stays inside the smallest loop that is actually checkable end to end.

### 0.3 Method — how contradictions are resolved

Where the three generations (and the live, undocumented fourth) disagree, the decision in §1 is made by this precedence, in order:
1. **What is already real, correct, and connected in live code** wins by default — rewriting working code to match an unbuilt spec is not a reconciliation, it's a regression.
2. Where live code has a proven *defect* (the audit's §G/§H findings — the dead `UnderstandingEngine` call, the disjoint math/concept pipelines, the "confidently wrong" verification gap, the raw-span leak into error text), the fix is designed to address the defect specifically, using whichever generation's terminology or mechanism most directly closes it.
3. Where no live code exists and the generations disagree, prefer the version that is **most precisely specified and internally consistent**, scaled down to only what's load-bearing for this scope.
4. **Reject unjustified complexity** — infrastructure with no code and no present-scale justification (RIB-1's distributed stack; SIA-1's 12-subsystem interpreter for a system with 13 seed concepts) is not adopted just because a document specified it.

---

## 1. Decisions — Resolving Every Major Contradiction

| Decision point | Lobe/hnsds (Gen A) | V4 Constitution (Gen B) | V5 RCA-1/Meaning-Graph (Gen C) | Live code today | **DECISION** |
|---|---|---|---|---|---|
| Persistence | Flat JSON/JSONL (`synaptic_weights.json`, `episodes.jsonl`) | Single unified SQLite ("scattered flat files prohibited") | Postgres + Neo4j + Redis, gRPC/Kafka | Real, working SQLite `UniversalKnowledgeModel` (`ConceptStore`/`KnowledgeManager`) | **Single relational store (SQLite), per Gen B — because it already matches live reality.** Gen A's flat files are already dead in the live path. Gen C's polyglot stack has zero code and no volume to justify it (13 seed concepts). Swappable later behind the existing repository interface if scale ever demands it — not a reason to adopt it now. |
| Internal representation ("language of thought") | Implicit (`StructuredInput`/`PerceptionMap`, dataclasses, string `candidate_solution`) | Same as Gen A, `Expression`/`Graph`/`ReasoningTrace` types referenced but never defined | Meaning Graph (MGS-1): typed node/edge graph, precisely specified | `SemanticRequest`/`EntityMention`/`SemanticRelation` (VS-6) for concepts; a **completely separate** string-based path (`UniversalMathEngine`) for quantities/equations — two disjoint representations for one system | **A single typed node/edge Meaning Graph (Gen C's model, trimmed), extended with first-class Quantity/Variable/Operation/Equation node types that MGS-1 never specified.** This is the single highest-leverage decision in this document — see §1.1. |
| Orchestration shape | Implicit 5–7 step `RIRLoop` | 10 numbered "Constitutional" stages | 5 layers plus 6+ orthogonal governed subsystems (Executive Controller, Context Engine, World Model, Goal Manager, each with its own module list) | A 6–7 step `CognitivePipeline` facade, self-described as "not the architecture," with one call whose result is computed and never used | **Five named stages: Interpret → Ground → Reason → Verify → Answer** (§2). Stage-count theater (10 stages; 5 layers + N controllers) is rejected — no version of the extra stages is algorithmically specified anywhere, and the live system already gets adequate results with fewer, clearer stages. |
| Reasoning / solving | `Synthesizer`/`NativeSymbolicEngine`, ad hoc | `SolverRegistry` + `ReasoningEngine` + `HTNPlanner`, dispatch on `AxiomType` | `CRE` + `HTN Task Planner`, dispatch via `ExecutiveController` cost formula | Two **disconnected** solvers: `CognitiveReasoningEngine` (graph rules: generalization/transitivity/alias) and `UniversalMathEngine` (SymPy), selected by regex/neural-classifier voting on **raw text before any structured meaning exists** | **One `Solver` interface, multiple implementations, dispatched on the *shape of the grounded Meaning Graph subgraph*, never on raw text.** See §1.1 and §2.3. HTN as a general planner is not adopted — no generation ever specifies its algorithm; the live `TaskDecomposer`'s fixed compound-shape decomposition is kept as sufficient for this scope. |
| Verification | None specified as a gate | Z3 SMT, absolute gate, CEGIS repair (unimplemented `_parse_solution` stub) | Z3 SMT, same role, same unimplemented gap | **None in the live path at all** for anything (concept answers: provenance-only; math answers: "verified" means only "SymPy didn't error," which the audit caught confidently returning a wrong answer) | **Z3 formally verifies exactly the claims that have formal semantics** (equations, quantity constraints, and the transitive/generalization rule chains already used for concept relationships) **and verification is redefined to check the *meaning-to-formalization mapping*, not just the computed value.** See §1.2. Concept-lookup answers keep their current, already-honest provenance-trace confidence tier — not relabeled as "Z3-verified" when they aren't. |
| Routing / control ("what should handle this?") | Implicit | Not specified beyond stage sequence | `ExecutiveController`: a full governed subsystem — cost formula, Decision Policy Registry (JSON), `ExecutiveTrace` schema | Regex → neural classifier (trained on 30 hardcoded sentences) → BiLSTM tagger fallback, cascading over **raw text**, before grounding or graph construction happens | **Routing is an internal, inspectable decision inside the Reason stage, made over the grounded Meaning Graph, not a separate governed subsystem.** The *idea* of "prefer the cheapest solver that can certify its own answer" is kept from ECA-1; the cost-formula/policy-registry machinery is not, as unjustified for a handful of solver families. |
| Learning / self-play / skills / concepts / mental models | Extensively specified, 3 incompatible ways | Extensively specified | Extensively specified (LAA-1) | Fully implemented, real, tested — but reachable only from the legacy CLI, zero connection to live cognition | **Out of scope for this document** (§0.2). Existing code is untouched, not deleted, and remains the starting material for that future design pass. |
| Distributed/infra stack | N/A | N/A | Rust/gRPC/Kafka/Raft/Neo4j/Postgres/Kubernetes, scored 9–10/10 by a prior self-audit | 192 total lines across two stub Rust crates; zero `raft`/`kafka`/`consul` references anywhere in real code | **Rejected outright**, not merely deferred. No present-scale justification exists, and adopting it now would repeat the exact pattern (infrastructure-as-theater) the audit flagged as drift. |

### 1.1 Why the Meaning Graph must absorb math (the central fix)

This is the audit's sharpest concrete finding, restated as a design problem: **the live system has two disjoint notions of "understanding a question."** A concept question ("Explain Java interfaces") builds a `SemanticRequest` and is answered by graph traversal with real provenance. A math question ("What number becomes 20 after adding 10?") never touches that representation at all — it is detected by regex/neural vote on raw text and handed whole to a string-based CAS engine. This is *why* the audit's worst bug exists: nothing ever checks that "increase by ten, get twenty" was correctly turned into `x + 10 = 20` (correct) versus `x = 20 + 10` (what the live substitution heuristic actually did) — there is no shared representation for a verifier to check the mapping against, because math never produces one.

The fix is not "add a verification step to the math engine." It is: **quantities, variables, operations, and equations become ordinary nodes and edges in the same Meaning Graph that concepts and relationships already use** (schema in §3). Once "20," "10," and the unknown are graph nodes with typed roles (`Variable`, two `Quantity` nodes) connected by an `Operation` edge inferred from "increase"/"adding," verification has something concrete to check: *does the asserted equation subgraph actually match the semantic roles assigned during Interpret?* This is a structural fix, not a patch — it also happens to fix the syllogism-misrouted-to-math bug (§1, "Routing" row) for the same reason: routing decided from graph shape (does this grounded graph contain `Quantity`/`Operation`/`Equation` structure, or `IS_A`/`Rule` structure implying deduction?) cannot make the mistake that routing decided from a tagger voting on raw English can.

### 1.2 Why "Verified" must mean one thing

Today "Verified: 1.00" appears on both a correctly Z3-provable-if-it-were-checked equation and on a confidently wrong substitution guess, and separately, "confidence: 0.89 (High)" appears on an honest, real, provenance-traced graph lookup that was never claimed to be formally verified in the first place. Three different underlying truths, two labels, one of them actively misleading. The unified architecture fixes this by definition, not by convention: **`Verified` is a status that Verify (§2.4) is structurally unable to assign without a Z3 (or bounded-symbolic-rule) proof that the answer's formal structure follows from the grounded Meaning Graph.** Everything else — including every concept/relationship lookup the live system already does well — is labeled `Retrieved (provenance-traced)`, honestly, at whatever confidence its evidence chain supports. `Refused` is the third and only other terminal status. No fourth, blended label is permitted.

---

## 2. The Unified Pipeline

```
Raw human input (arbitrary text)
        |
        v
  [1] INTERPRET   -- text -> candidate Meaning Graph fragment (nodes, edges, hypotheses)
        |
        v
  [2] GROUND       -- candidate fragment -> validated CognitiveSituation
        |            (resolved against UKM; ambiguous/unknown nodes marked, not guessed)
        v
  [3] REASON       -- grounded subgraph -> candidate TaskResult(s)
        |            (one or more Solvers, dispatched on graph shape)
        v
  [4] VERIFY       -- candidate TaskResult -> {Verified | Retrieved | Refused}
        |            (formal proof where the claim has formal semantics;
        |             provenance trace otherwise; honest refusal if neither holds)
        v
  [5] ANSWER       -- verified/retrieved/refused result -> human-readable response
        |            (renders only from typed status + typed result, never from
        |             raw extraction artifacts)
        v
Response
```

Five stages, one representation passed between all of them (the Meaning Graph / grounded subgraph — never a bespoke per-stage string or dict), one honest three-way outcome. No stage may be skipped; no stage may hand a later stage raw text once Interpret has run.

### 2.1 INTERPRET

**Responsibility:** turn raw text into a *candidate* Meaning Graph fragment — nodes and edges the input plausibly describes, each carrying a confidence and a source, exactly as `Evidence`/`InterpretationAssumption` already do in the live `LanguageInterpreter`. Interpret proposes; it does not decide truth and does not query the UKM.

**Kept as-is:** input normalization (whitespace, thousands-separator stripping, filler-word trimming — all real, all correct, all stage-appropriate here).

**Replaced:** the regex-cascade-then-neural-vote-then-tagger-fallback decision tree that currently *decides the communicative goal from raw text* is retired as a decision mechanism. Its constituent pattern-matching logic is not thrown away — it becomes *node/edge proposal* logic (a `COMPARE`-shaped sentence proposes two `Concept` nodes and a `COMPARISON` edge; an `SOLVE_MATH`-shaped sentence proposes `Quantity`/`Variable`/`Operation` nodes and an `Equation` edge) rather than a single early goal label that locks in everything downstream. Both proposals can coexist as low-confidence hypotheses; Ground and Reason, which have more information, are what actually decide.

**Retired from this stage:** `UnderstandingEngine`'s parallel 8-stage pipeline, whose entire output is discarded today (audit §E.3). Its concept-resolution logic (n-gram lookup against the UKM) is genuinely useful — it moves to Ground (§2.2), which is where UKM lookups belong; the dead top-level call in `CognitivePipeline.answer()` is deleted, not preserved as dead code.

**Interface:** `interpret(raw_text: str) -> MeaningGraphFragment` (nodes/edges with confidence + source only — no UKM access, no side effects).

### 2.2 GROUND

**Responsibility:** resolve each candidate node against the UKM (or against numeric/formal parsing for `Quantity`/`Variable` nodes), and produce a `CognitiveSituation`: a graph where every node is one of `RESOLVED`, `AMBIGUOUS`, or `UNKNOWN` — never silently guessed.

**Kept as-is:** `GroundingEngine`'s resolved/ambiguous/unknown distinction (real, working, honest — this is one of the few places the live system already behaves exactly as the architecture requires).

**Extended:** numeric/equation parsing (currently living inside `UniversalMathEngine.normalize_natural_math_phrasing`, called only from the math-only path) moves here, so a `Quantity`/`Variable` node is grounded by the same stage and the same honesty rules as a `Concept` node. There is no longer a separate "did math parsing succeed" fork outside of Ground.

**Explicit seam, not built here:** a context/conversation-history resolution tier is where Gen C's Context Engine (CEA-1) placed cross-turn disambiguation. This document does not design it (§0.2) — Ground's resolution order is defined today as `{current-request workspace} > {UKM/world knowledge}`, with a documented, empty slot for `{conversation history}` to be inserted between them later without changing Ground's contract.

**Interface:** `ground(fragment: MeaningGraphFragment) -> CognitiveSituation`.

### 2.3 REASON

**Responsibility:** given a grounded `CognitiveSituation`, select and run the `Solver`(s) that apply, producing one or more candidate `TaskResult`s with an explicit derivation trace.

**Unified `Solver` interface** (this is the concrete resolution of the "Reasoning/solving" row in §1):

```
class Solver(Protocol):
    def applies_to(self, situation: CognitiveSituation) -> bool: ...
    def solve(self, situation: CognitiveSituation) -> TaskResult: ...
```

Registered solvers, each already real code repositioned behind this one interface instead of being reached by a different mechanism each:
- **GraphRuleSolver** — today's `CognitiveReasoningEngine` (`StoredGeneralization`, `GeneralizationTransitivity`, `NamespaceCohabitation`, `AliasMapping`). `applies_to`: the situation's grounded subgraph contains `Concept`/relationship structure.
- **FormalSolver** — today's `UniversalMathEngine` (SymPy), now operating on the `Quantity`/`Variable`/`Operation`/`Equation` subgraph Ground produced, not on a raw string. `applies_to`: the subgraph contains an `Equation`/`Operation` structure.
- **CompositionSolver** — today's `TaskDecomposer`/`CognitiveTaskGraph` (VS-7), for compound requests ("explain X, compare with Y, relate to Z"). Its dependency-DAG execution is genuinely real and correct (audit §F) and is kept unchanged; it now schedules calls into the two solvers above via the same interface rather than into bespoke executor methods.

**Routing** (the "which solver(s) apply" question) is `applies_to()` evaluated over the grounded graph shape — no text pattern, no classifier vote, ever runs at this stage. This is what makes the syllogism-misrouting bug structurally impossible rather than merely rare: a graph with no `Quantity`/`Operation`/`Equation` nodes cannot trigger `FormalSolver.applies_to()`.

**Not adopted:** a general HTN planner, an `ExecutiveController` cost-formula subsystem, a JSON Decision Policy Registry. `CompositionSolver`'s fixed decomposition shapes are sufficient for the compound-request patterns already proven to work; a general planner is a real future capability, not a precondition of this substrate.

**Interface:** `reason(situation: CognitiveSituation) -> list[TaskResult]` (may be more than one candidate when solvers disagree or partially apply — Verify decides which, if any, survive).

### 2.4 VERIFY

**Responsibility:** assign each `TaskResult` exactly one of three terminal statuses, per §1.2's definitions.

- **`Verified`** — for results from `FormalSolver` or `GraphRuleSolver`, a proof obligation is constructed and checked:
  - `FormalSolver` results: the equation subgraph is compiled to Z3 constraints (the one genuinely new piece of engineering this document identifies — no live code does this today), Z3 checks satisfiability, **and, critically, the compiled constraint is checked against the *originally grounded semantic roles* from Ground** (which node was `known`, which relation was "increase" vs. "decrease," which node is the target) — not merely re-solved. This is the specific mechanism that would have caught "20 after adding 10 → 30": the semantic role said "the known value plus ten equals the target," and the candidate answer must be checked against *that* assertion, not against an independently re-derived equation that could encode the same misparse twice.
  - `GraphRuleSolver` results: the existing bounded transitive-closure/rule check already *is* a real, checkable proof (premises are explicit, the rule is deterministic) — Verify formalizes what Reason already computes rather than adding new machinery.
- **`Retrieved`** — for direct UKM lookups with no derivation claim beyond "this fact is stored and its provenance chain is intact." This is exactly what today's concept-explanation answers already are, honestly relabeled instead of conflated with `Verified`.
- **`Refused`** — when Ground could not resolve required nodes, or no solver's proof/provenance obligation is met. Refusal carries the `CognitiveSituation`'s own typed status (`UNKNOWN`/`AMBIGUOUS`) as its reason — never a serialization of raw extraction spans (this is the direct fix for the audit's garbage-n-gram-in-error-message bug: Answer is structurally barred from rendering anything but a typed reason).

**Interface:** `verify(result: TaskResult, situation: CognitiveSituation) -> VerifiedOutcome` where `VerifiedOutcome` is a closed sum type of exactly the three statuses above, each carrying its evidence (proof trace / provenance chain / refusal reason respectively).

**Not adopted as a hard requirement:** the 5-attempt CEGIS repair loop. A single correct verification pass is the minimum substrate; iterative repair-on-counterexample is a real, valuable enhancement to layer on once a first Z3 integration exists, not a precondition of having one.

### 2.5 ANSWER

**Responsibility:** render exactly one of the three `VerifiedOutcome` variants into a human-readable response, using only typed fields.

**Kept as-is:** `ExplanatoryAnswerSynthesizer`/`AnswerGenerationEngine`'s definition-first, provenance-citing rendering — this is real, good, working code.

**Fixed:** rendering is a `match` over `{Verified, Retrieved, Refused}` — there is no code path by which an `Answer` can be constructed from anything other than these three typed variants, which removes the possibility (present today) of a raw internal artifact leaking into a user-facing string.

**Interface:** `answer(outcome: VerifiedOutcome) -> Answer`.

---

## 3. The Meaning Graph — the actual substrate

One representation, passed through all five stages, materialized as rows in the existing SQLite schema (no new infrastructure — the "graph" is a logical model over relational tables, exactly as the live `ConceptStore` already is; Gen C's Neo4j requirement is explicitly not adopted, per §1's rejection of unjustified infra).

**Node types** (MGS-1's taxonomy, trimmed to what's load-bearing, plus the math extension from §1.1):

| Node type | Source | Purpose |
|---|---|---|
| `Concept` | live (UKM), MGS-1 | Domain concepts (Java Interface, Abstraction) — kept exactly as today |
| `Entity` | MGS-1 | Named things distinct from abstract concepts (kept minimal; not exercised by current use cases but cheap to keep) |
| `Quantity` | **new** | A numeric value + unit + known/unknown flag — the direct promotion of `EntityValue` (already defined in the master docs, already used ad hoc by `UniversalMathEngine`) to a first-class graph citizen |
| `Variable` | **new** | A `Quantity` node with `known=False` that reasoning must solve for — kept distinct from `Quantity` because equations reference it by symbol |
| `Operation` | **new** | A typed arithmetic/logical operator (add/subtract/multiply/divide/compare) connecting operand nodes |
| `Equation`/`Constraint` | **new**, generalizes MGS-1 (which had no math representation at all — an audited gap) | A subgraph asserting a relation must hold among `Quantity`/`Variable` nodes; this is what Verify compiles to Z3 |
| `Goal` | trimmed from GMA-1 | The requested task shape: `EXPLAIN(concept)` / `COMPARE(a,b)` / `RELATE(a,b)` / `SOLVE(equation)` — kept minimal, no strategic/tactical hierarchy (unjustified at this scope) |
| `Rule`/`Hypothesis` | MGS-1, matches live `Inference`/`Assumption` | Bookkeeping for derived conclusions (`GeneralizationTransitivity` etc.) — already real |
| `Event` | MGS-1 | Kept in the schema for future causal/procedural questions ("why can't X extend Y") — **not solved by this pass**; named so the schema doesn't need to change shape when that capability is designed later |

**Edge types** (trimmed from MGS-1's four families, plus math-specific):

| Edge type | Family | Purpose |
|---|---|---|
| `IS_A` / `GENERALIZES` / `SPECIALIZATION` | Taxonomic | Kept, real, used today (`StoredGeneralization`) |
| `PART_OF` | Partitive | Kept, cheap, not yet exercised |
| `CAUSES` / `DEPENDS_ON` / `IMPLIES` | Logical-causal | Kept in schema for future causal reasoning; not solved by this pass |
| `COMPARISON` / `RELATIONSHIP` | — | Kept exactly as today's `SemanticRelation` |
| `ALIAS_OF` | — | Kept, real, used today (`AliasMapping`) |
| `HAS_VALUE` | **new** | `Quantity`/`Variable` → its numeric value |
| `OPERAND_OF` | **new** | `Quantity`/`Variable` → the `Operation` it participates in |
| `CONSTRAINS` | **new** | `Equation` → the `Variable`(s) it bounds |

**Every node and edge carries `confidence: float` and `source: str`**, matching both MGS-1's schema and the live `Evidence`/`Assumption` pattern already in `LanguageInterpreter` — this is not new, just made uniform across the previously-separate math and concept representations.

**Explicitly not adopted from MGS-1**, as unjustified for this scope: the Ambiguity-Branch-Node subgraph-forking mechanism (today's system resolves-or-refuses, which is honest and sufficient for a first pass — branching is a real future capability for handling genuine multi-reading ambiguity, not a precondition), the Emotion/Pragmatic interpreter roles, and Allen's-Interval-Algebra temporal modeling (no current use case needs it).

---

## 4. Component Disposition

What happens to every real module the audit found, mapped onto the five stages. "Kept" means used close to as-is; "Repositioned" means the logic is real and good but moves to a different stage or is reached through the new `Solver`/typed-outcome interfaces instead of its current ad hoc call path; "Retired" means deleted as dead or superseded, not preserved as legacy.

| Module | Disposition |
|---|---|
| `hsci/cognition/interpretation/interpreter.py` (pattern-proposal logic) | Repositioned into INTERPRET as node/edge hypothesis proposal |
| `hsci/cognition/interpretation/neural_semantic_model.py`, `hsci/language/semantic_tagger.py` | Repositioned: their votes become additional low-confidence hypotheses in INTERPRET, not an early goal-locking decision |
| `hsci/knowledge/understanding_engine.py` | Retired as a top-level call (its output is dead today); concept n-gram resolution logic repositioned into GROUND |
| `hsci/cognition/interpretation/grounding.py` | Kept, extended per §2.2 |
| `hsci/reasoning/universal_math_engine.py` (`normalize_natural_math_phrasing`) | Repositioned: normalization moves to GROUND; solving logic becomes `FormalSolver` in REASON |
| `hsci/reasoning/reasoning_engine.py` (`CognitiveReasoningEngine`) | Repositioned as `GraphRuleSolver` |
| `hsci/cognition/workspace/{decomposer,task_graph,workspace}.py` | Kept as `CompositionSolver`, scheduling into the unified `Solver` interface |
| `hsci/response/explanatory_synthesizer.py`, `hsci/response/answer_generation_engine.py` | Kept as ANSWER, extended to render only from the closed `VerifiedOutcome` type |
| `hsci/reasoning/reasoning_engine.py` (`ReasoningEngine`/Z3 class), `hsci/symbolic/*` if present | Repositioned/completed as VERIFY's Z3 compilation target — this is the one genuinely new engineering surface (§2.4) |
| `hsci/core/rir_loop.py` | Not part of this architecture; left as the legacy CLI entrypoint. Its fate (retire vs. keep as a dev tool) is a separate decision, not made here. |
| `hsci/learning/*`, `hsci/memory/skill_*`, `hsci/self_play/*` | Untouched, out of scope (§0.2) |
| `runtime/` (Rust crates) | Untouched; not part of this architecture; no recommendation to delete, simply not adopted |
| `hsci/core/kernel.py` (`EventBus`, `CognitiveContext`) | Kept as the request-scoped plumbing connecting the five stages — matches every generation's "ephemeral per-request state" principle, just not reified as a named `BrainKernel` class |

---

## 5. Explicit Seams for What's Deferred

So that building the excluded items later does not require revisiting this document:

- **Session/conversation memory** attaches at GROUND, as the empty `{conversation history}` tier in the resolution order (§2.2). It also attaches at INTERPRET, where a future `ContextReference` resolution would consult prior turns instead of only the current utterance. Nothing in this design assumes single-turn operation in a way that would need undoing.
- **Lexical resolver** is GROUND's node-resolution algorithm, behind the interface in §2.2 — this document specifies the contract (`RESOLVED`/`AMBIGUOUS`/`UNKNOWN` against the UKM), not the matching algorithm.
- **Learning** attaches after ANSWER: a future `Experience` record is naturally `(situation, result, outcome)` — exactly the typed objects this pipeline already produces at each stage — logged, not re-derived, when that design pass happens.
- **Generalization/skills/concepts** attach to REASON, as new `Solver` implementations registered the same way `GraphRuleSolver`/`FormalSolver`/`CompositionSolver` are — the `Solver` interface is deliberately open for this.
- **Mental models** are, per the audit's own dependency chain, only meaningful once the above accumulate real state to model — no seam is needed now beyond the fact that every stage already produces typed, inspectable output.

---

## 6. What This Document Does Not Do

It does not implement the session-memory seam, the lexical resolver algorithm, the Z3 compilation for `FormalSolver`, or any other code. It does not delete `hsci/core/rir_loop.py`, the learning subsystem, or the Rust crates. It does not resolve which of the existing test suites (VS1–VS7, `hsci/tests`) should be rewritten against the new `Solver`/`VerifiedOutcome` interfaces versus retired — that is an implementation-phase question. It is the single design artifact those decisions should be checked against.
