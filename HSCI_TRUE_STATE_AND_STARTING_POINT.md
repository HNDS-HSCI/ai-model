# HSCI True State & Starting Point

**Type:** REPORT (this document itself). Produced by reading the repository's documentation corpus, tracing the live code path, and exercising the actual running application with unseen inputs — not by inference from class names or from other documents' self-assessments.

**Date of this audit:** 2026-09-08, against commit `1a051ee` (main).

**Method:** Five parallel research passes read the full documentation corpus (root-level "constitution" docs, the two master architecture prompts, the 15-document cognition-architecture spec suite, the meta-audit/roadmap reports, and the POST_VS7_REALITY audit series). In parallel, I traced the live code path by hand from the actual deployment entrypoint (`render.yaml` → `run_app.py` → `brain_api.py`) through every module it imports, and ran the live FastAPI server against unseen inputs across math, knowledge, reasoning, and conversational categories. Findings below are labeled by source: **[DOC]** = claimed in documentation, **[CODE]** = verified by reading source, **[RUNTIME]** = verified by executing the live server.

---

## A. What HSCI is

Stripped of the specific vocabulary of whichever document you read, every generation of HSCI's documentation converges on the same four-part thesis, stated most directly in `SYSTEM_VS_APPLICATION.md` and `HSCI_RESEARCH_PAPER.md`:

HSCI is meant to be a system that **(1) formally verifies every claim it makes before surfacing it** ("the Z3 SMT solver is the final arbiter of truth" — `ARCHITECTURE_CONSTITUTION.md` Tenet 2.1), **(2) learns persistently from each interaction** rather than running frozen weights, **(3) exposes an inspectable reasoning trace** rather than being a black box, and **(4) fails honestly** ("COGNITIVE_FAILURE" rather than a guess) instead of hallucinating. Verification is the one concept every document generation defines identically and treats as non-negotiable; learning is the one every document calls "the core research contribution."

The project's own terms, as actually used in its documents (not normalized to generic AI vocabulary):
- **Understanding** = the `UnderstandingEngine` / Semantic Interpreter (SIA-1) step that turns surface syntax into a structured frame — explicitly *not* the same as answering.
- **Reasoning** = symbolic derivation (HTN decomposition + rule application), explicitly contrasted with "pattern matching" (`HSCI_Architecture_Prompt.md`: "This is REASONING — not pattern matching").
- **Knowledge** = concepts stored as abstract, reusable rule templates ("`result = a + b`, not `5 = 2 + 3`" — a "Critical Non-Negotiable Rule" in both master documents), never raw examples.
- **Verification** = Z3 SMT satisfiability check; `sat` → PROVEN, `unsat` → DISPROVEN with a counterexample fed back into a CEGIS repair loop.
- **Learning** = update triggered *only* by a verified proof outcome — called "Hebbian" in one generation, "Proof-Guided Learning (PGL)" in another, generic `LearningEngine` in a third; never standard gradient descent on prediction loss.
- **Generalization** = analogical composition over an `OntologyGraph`, illustrated as deriving a never-seen finance formula (`TAX_DEDUCTION = base - base*rate`) purely from already-proven arithmetic primitives (`SUBTRACTION`, `MULTIPLICATION`).
- **Concepts / Skills / Mental models** = defined inconsistently across generations (see §E) — "concepts" are graph nodes in one generation and JSON-file pattern weights in another; "skills" appear as an architectural noun in exactly one of eight root documents; "mental model" has three incompatible meanings across the corpus.
- **Intelligence** = never formally defined anywhere except one theoretical aside (`Intelligence_Theory.md`) framing it as entropy-minimizing utility over an active workspace — not otherwise operationalized.

## B. What HSCI is NOT

The documentation is explicit and consistent that HSCI is not meant to be "ChatGPT + verification," an "expert system with a database," or a "rule engine + learning" bolted together (`SYSTEM_VS_APPLICATION.md`). The distinguishing claim is structural: verification and learning are supposed to be *load-bearing* parts of the cognitive loop itself (gating what enters permanent memory, driving weight updates), not a post-hoc check on an LLM's output. No canonical document positions HSCI relative to RAG or tool-calling architectures specifically — the contrast target is always "LLMs" and "traditional stateless AI applications" in the abstract.

**This distinction is aspirational, not yet actual.** As detailed in §D–§H below, the system that is actually live behind the FastAPI server does not use Z3 at all, and its "neural" component is decorative. The gap between B (what HSCI claims not to be) and what is running today is the central finding of this audit.

## C. Canonical architecture (as documented)

There is no single canonical architecture — there are **three non-communicating architecture generations**, each self-declaring its own supremacy, plus a fourth (undocumented) architecture that is what actually runs. This is itself the most important finding of this audit and is detailed in §E.

The most complete individual specification is the **V4 Constitution's 10-stage BrainKernel pipeline** (`ARCHITECTURE_CONSTITUTION.md`):

```
Stage 0   LanguageBridge          — raw text → structured input
Stage 0.5 UnderstandingEngine     — resolve context → SemanticFrame
Stage 1   NeuralPerceiver         — GNN embeddings + intent tags
Stage 1.5 MentalModelEngine       — detect gaps in WorldStateGraph
Stage 2   ConceptActivationEngine — spreading activation over OntologyGraph
Stage 2.5 SkillMemory             — retrieve applicable procedural skills
Stage 3   SolverRegistry/ReasoningEngine — HTN planning + solver selection
Stage 4   Z3VerificationEngine    — CEGIS-loop proof
Stage 5   LearningEngine          — update weights/concepts in UKM
Stage 6   ResponseBridge          — natural-language rendering
```
governed by: exactly two structural blocks (BrainKernel + a single unified SQLite "Universal Knowledge Model"), mandatory `proof_trace_id` provenance on every stored fact, statelessness of all services (all request state in `WorkingMemory`), and an explicit prohibition on flat-file storage ("scattered flat files are prohibited").

The separate "V5" cognition-architecture suite (RCA-1, SIA-1, MGS-1, LAA-1, ECA-1, CEA-1, WMA-1, GMA-1 — 15 documents under `docs/architecture/cognition/`) gives a related but not identical 5-layer picture, centered on a **Meaning Graph** (a language-independent, typed node/edge semantic graph, MGS-1) that compiles into a **Language of Thought** (predicate-logic + Z3 constraints, per ADR-0002) before touching persistent memory. Its own canonical flow, reconciled from RCA-1 §3–§7:

```
Acquisition (KAL) → Understanding (UE) → Meaning (SIA-1 → Meaning Graph)
  → Context (CEA-1) → Knowledge compilation/validation (Z3)
  → Memory write (KnowledgeManager) → Activation (CAE) → Reasoning (CRE + Z3)
  → Planning (HTN, conditional) → Reflection → Learning (LAA-1) → Answer Generation (AGE)
```
with the Executive Controller (ECA-1) choosing among Memory-Lookup / Reason-and-Verify / Plan / Acquire / Clarify strategies by a stated cost formula, and the Goal Manager (GMA-1) owning intent/goal formation (explicitly *not* task decomposition, which belongs to an HTN planner that **no document in this suite ever actually specifies an algorithm for**).

## D. Actual architecture (what the live runtime does)

**The live user-facing system does not implement either of the above.** Verified by direct trace:

- `render.yaml` deploys `python run_app.py` **[CODE]**, which serves `brain_api:app` **[CODE]** — this is the actual, sole production entrypoint, confirmed live by starting it and exercising `/health` and `/process` **[RUNTIME]**.
- `brain_api.py` imports `hsci.core.cognitive_pipeline.CognitivePipeline` **[CODE]** — a class its own docstring calls an "**ASSEMBLY facade**" and which explicitly states: *"The facade does NOT... introduce a formal Z3 verification step... This facade never claims Z3 verification for conceptual answers."* **[CODE, quoted verbatim]**
- The real live pipeline, as actually wired in `hsci/core/cognitive_pipeline.py::CognitivePipeline.answer()` **[CODE]**:

```
Raw text
  → UnderstandingEngine.understand()   [CODE: result computed, then never read again — dead]
  → LanguageInterpreter.interpret()    [regex cascade + tiny hardcoded-anchor NN + BiLSTM fallback]
  → GroundingEngine.ground()           [validates entity mentions against seeded SQLite UKM]
  → TaskDeriver.derive()               [maps situation -> CognitiveTask]
  → CognitiveWorkspace.execute()       [VS-7 task-graph DAG execution]
  → CognitiveTaskExecutor              [dispatches to SOLVE_MATH / EXPLAIN / COMPARE / RELATE / GENERAL / REFUSAL handlers]
  → Answer object -> brain_api.py formats markdown
```

None of: BrainKernel, WorkingMemory-as-scratchpad, SolverRegistry, MentalModelEngine, SkillMemory, Z3VerificationEngine, LearningEngine, ResponseBridge (V4 Constitution names) — or Meaning Graph, Language of Thought, Executive Controller, World Model, Goal Manager, HTN Task Planner (V5 RCA-1 names) — appear anywhere in this live call path. **[CODE]** A separate, legacy orchestrator (`hsci/core/rir_loop.py`, a "7-layer RIR loop" matching neither documented generation but closest to a third, older "Lobe/hnsds"-vocabulary generation described in `gemini.md`/`SYSTEM_VS_APPLICATION.md`) exists and *does* wire up Z3 verification and the entire learning/skill subsystem — but it is reachable only from the interactive CLI (`hsci/cli/main.py`) and test files, never from the deployed API. **[CODE, confirmed by grep: zero references to `ReasoningEngine()`/Z3 CEGIS repair, `learning_engine`, `skill_graph`, `skill_lifecycle`, or `htn_planner` anywhere in `cognitive_pipeline.py` or anything it imports.]**

So there are, in effect, **four architectures in this repository**: three documented-but-unbuilt ones (Lobe/hnsds era, V4 BrainKernel/Constitution era, V5 RCA-1/Meaning-Graph era) and one undocumented one that is what a real user actually talks to (the `CognitivePipeline` facade). No document in the repository describes the `CognitivePipeline`/`LanguageInterpreter`/`CognitiveWorkspace` architecture as the system's identity — it is referred to in its own source only as an "assembly facade" delivering a "conceptual slice."

## E. Architecture gaps

1. **Three self-declared-canonical, mutually unaware document generations**, confirmed by an independent meta-audit pass (`CRR-1`'s own "Document Authority Matrix") plus direct git-date cross-checking:
   - *Generation A ("Lobe/hnsds")* — `hnsds/` package, flat JSON/JSONL persistence, no version marker. `SYSTEM_VS_APPLICATION.md` ("HSCI is not an application") directly contradicts `APPLICATION_ARCHITECTURE.md` ("Short answer: YES ✅ It's structured as a complete full-stack application") — same repository, opposite answers to the same question, neither aware of the other. Even within this one generation, the weights filename is given four different names across four documents (`mental_intelligence.json`, `synaptic_core.json`, `synaptic_weights.json`, `cognitive_weights.json`).
   - *Generation B ("V4 Constitution")* — `hsci/` package, single unified SQLite ("scattered flat files are prohibited" — directly outlawing Generation A's own persistence model, unacknowledged). 10-stage BrainKernel pipeline.
   - *Generation C ("V5 / RCA-1 Meaning-Graph")* — Meaning Graph / Language-of-Thought representation, Executive Controller, Rust/gRPC/Kafka/Neo4j/Postgres implementation blueprint (`RIB-1`). **This entire distributed-systems stack is prose only**: `grep` for `raft|kafka|consul` across all Python and Rust source returns 2 incidental matches, and the Rust `runtime/` workspace MRG-1 scores "9-10/10" and treats as implemented totals **192 lines across two crates** (a 70-line verifier stub and a 61-line sandbox stub). `CRR-1` (part of this same generation) demotes the distributed-systems half of its own generation to "SUPERSEDED / FUTURE," but does so silently, with no cross-reference to Generation A or B, and directly contradicts a same-generation sibling document (`MODULE_CLASSIFICATION.md`) on whether `hsci/core/rir_loop.py` should be kept or replaced.
   - The root `DOCUMENTATION_INDEX.md` (v2.1.0) is arguably a *fourth* index generation, pointing to `gemini.md` and "the RIR-RI loop" and naming none of the above three by their own vocabulary.
   - **None of these documents are marked historical, deprecated, or superseded in the text itself.** An agent instructed to "read all immutable specification documents" has no textual signal to prefer one generation over another, and the V4 Constitution's own supremacy claim ("Code changes that drift... must be rejected") is neither enforced anywhere in code nor even followed by the codebase's own most recent commits, which build a fifth thing (§D) that the Constitution never mentions.

2. **Every meta-audit document in the repository predates the code it would need to audit.** All 14 meta/roadmap documents I sampled (`MRG-1`, `CRR-1`, `MBR-1`, `SDB-1`, `BACKLOG.md`, `MODULE_CLASSIFICATION.md`, etc.) are git-dated 2026-07-16 or 2026-08-13; the most recent real engineering work (`hsci/cognition/interpretation/`, the trainable semantic parser, math-query routing) landed 2026-09-07/08 and is invisible to all of them. Three different "current sprint" documents give three incompatible answers to "what phase is the project in" (Phase 4/HTN-Planner per `CRR-1`; Sprint 12/Answer-Generation-Engine per `BACKLOG.md`; "POST-VS7 complete, 156/156" per `CURRENT_SPRINT.md`) — none of which is what the git log shows actually happened next.

3. **A dead computation on every live request.** `CognitivePipeline.answer()` calls `self.understanding_engine.understand(question, context)` first and stores the result in a local variable that is never read again — the entire "8-stage" `UnderstandingEngine` (its own docstring: normalization → segmentation → tokenization → entity extraction → concept resolution → intent classification → ambiguity detection → result assembly) runs on every single request and its output goes nowhere. **[CODE, verified directly against `hsci/core/cognitive_pipeline.py` lines 112–117.]** This is architecture drift no document anywhere flags — a genuinely disconnected component sitting in the middle of the live path, not off to the side.

4. **Z3/CEGIS verification, the one concept every document generation treats as the system's core non-negotiable identity, is entirely absent from the live path.** The pipeline that a real user's browser actually calls has no formal verification step of any kind for non-arithmetic answers; correctness for concept lookups rests on the fact that the underlying knowledge-graph traversal (§F, positive finding) is deterministic and the seed data is hand-authored — not on any proof.

5. **The entire learning/skill subsystem is disconnected from live cognition** — confirmed both by code trace (§D) and independently by two of the meta-audit documents (`CRR-1`: HTN Task Planner is "STUB/MOCK," Reflection Engine is "DOCUMENTATION ONLY"; VS5/VS6 acceptance reports: *"development halts here and does NOT proceed into ungrounded learning engines or autonomous self-play loops"*). Nothing a real user does through the API changes the system's future behavior in any way.

## F. Capability matrix

Evidence-based, combining code inspection, my own live runtime tests (this session, 2026-09-08, against the actual `/process` endpoint), and the POST_VS7_REALITY audit series (as-of Aug 22, treated as historical corroboration where still consistent with current code).

| Capability | Intended (per docs) | Implemented | Connected to live path | Actually works | Generalizes |
|---|---|---|---|---|---|
| Language understanding | Full NL → semantic frame (SIA-1, 12 subsystems) | Regex-cascade frame matcher (`LanguageInterpreter`, ~600 lines of hand-written patterns) + a from-scratch-trained-on-30-sentences LSTM classifier | Partially — `UnderstandingEngine`'s parallel "8-stage" version runs but its output is discarded (§E.3) | Works for phrasings the regex patterns anticipate; fails or misroutes on novel phrasing (see runtime traces below) | No — new pattern coverage is added by hand, one named regex at a time (`rel_m8`, `comp_m6`, `comp_m7`, per the Aug-22 stabilization log) |
| Semantic representation | Meaning Graph / Language of Thought (typed predicate graph) | A much simpler `SemanticRequest` dataclass (goal, entity mentions, relations, constraints) | Yes | Works within its scope | N/A — no LoT/Meaning-Graph code exists anywhere in the repo |
| Lexical resolution | Ontology-based synonym/alias resolution | `resolve_alias()` against a 13-concept seeded SQLite table (5 OOP + 8 science concepts) | Yes | Works only for the 13 seeded concepts and their pre-registered aliases | No — unseeded vocabulary refuses outright (verified live, see below) |
| Entity grounding | Full UKM validation, ambiguity detection | `GroundingEngine` — real, does distinguish RESOLVED/AMBIGUOUS/UNKNOWN | Yes | Works | No — bounded by seed data |
| Context / coreference | Cross-turn conversational memory (CEA-1: 5-level context priority) | Only *within-the-same-input-string* anaphora regexes; `StimulusRequest` API schema carries no session/conversation ID at all | Partially | **Fails** — verified live: a genuine two-turn follow-up ("What is a Java class?" then "How does it relate to abstraction?") returns a refusal, treating "it" as a literal unresolved concept name | No |
| Problem/goal formation | Goal Manager + Executive Controller strategy selection | `TaskDeriver` — direct situation→task mapping, no goal hierarchy, no strategy cost model | Yes | Works for the situations the interpreter classifies correctly | No |
| Capability/knowledge discovery | KnowledgeBase query with direct/analogical/episodic ranking | Direct SQLite lookup only; "analogical" structural-similarity search is specified in the master docs but its body is an explicit unimplemented stub (`pass # IMPLEMENT`) there and does not exist in the live code at all | Partially | Works for direct matches only | No |
| Task decomposition | HTN planning (referenced ~everywhere, algorithm specified nowhere) | `TaskDecomposer`/`CognitiveTaskGraph` (VS-7) — a real DAG with cycle detection for a small, fixed set of compound-request shapes | Yes | Works for the shapes it targets (explain+compare+relate compounds) | No — not a general planner |
| Reasoning | General symbolic inference | Exactly one bounded rule, `GeneralizationTransitivity` (2-hop transitive closure over a single `generalizes_to` edge type), plus namespace/alias bookkeeping rules | Yes | Correct within its narrow scope | No — cannot reason about anything outside the `generalizes_to` relation |
| Mathematics | Z3-verified symbolic solving | `UniversalMathEngine` (real SymPy CAS) | Yes | **Correct for well-formed equations** (verified live: `x+10=20`→10, `3x+7=25`→6); **confidently wrong on natural-language word problems it misparses** (verified live: "What number becomes 20 after adding 10?" → answered 30, "Confidence: 1.00 (Verified...)" — computed 20+10 instead of 20−10, no verification caught the semantic inversion); fails outright on two-step word problems and multi-clause syllogisms (see traces) | No |
| Logical reasoning | Full logic engine | None | No | A syllogism ("All bloops are razzles...") was misrouted to the math solver by the trainable-tagger fallback and correctly refused there — but only because SymPy couldn't parse it, not because any logic capability exists | No |
| Knowledge retrieval | Full USM with provenance | Real, working, SQLite-backed, in-memory and reseeded every process boot (no persistence across restarts) | Yes | Works for seeded concepts; genuinely produces multi-hop derived relationships with premise traces (a real positive) | No — bounded by 13 seed concepts |
| Verification | Z3 SMT, absolute gate | None in the live path (§D, §E.4) | No | The only "verification" a live user sees is deterministic-computation-equals-verification for math, and refusal-on-missing-data for concepts; neither is a proof of the interpretation's correctness | No |
| Answer generation | Domain-aware NL templates + conversation manager | `ExplanatoryAnswerSynthesizer` — real, templated, cites provenance | Yes | Works, and is honest about its sourcing | N/A |
| Experience capture | Episodic memory of every interaction | None in the live path | No | No episode is stored anywhere when a live request is served | No |
| Learning | Continuous, verification-gated weight/concept updates | Fully implemented (`hsci/learning/*`, `hsci/memory/skill_*`) but reachable only from the legacy CLI/RIRLoop and test suite | **No** | N/A for live users | N/A |
| Generalization | Cross-domain analogical transfer | Not implemented anywhere in currently-live code; the one "generalization" test in the Aug-22 audit reused 3 synthetic concepts built with the identical relation structure as the seed data, not a genuine unseen-structure test | No | No | No |
| Skill formation | HTN action schemas from experience | Code exists (`skill_graph.py`, `skill_learning_engine.py`) | No (same disconnection as Learning) | N/A | N/A |
| Concept formation | Merge/split/create from repeated observation (`Concept_Formation_Theory.md`) | Specified in detail (0.70 creation threshold, 90% merge threshold, 0% split threshold); **no corresponding code found anywhere in the repository** | No | No | No |
| Mental models | Gap-detection over world state (V4) / live cognitive-state trace (Lobe era) — two incompatible definitions | Neither exists in live code | No | No | No |

## G. Real runtime traces

All against the live server (`python run_app.py`, `POST http://127.0.0.1:8010/process`), same commit as this audit, 2026-09-08.

**Correct, and honestly verified within scope:**
- `"x + 10 = 20"` → `x = 10.0`, execution mode `sympy_solve`, confidence 1.00. Correct.
- `"3x + 7 = 25"` → `x = 6.0`. Correct.
- `"Explain Java interfaces."` → real multi-hop knowledge-graph traversal: retrieved definition, `StoredGeneralization` and derived `GeneralizationTransitivity` conclusions with explicit premise lists, confidence 0.89. This is a genuine, non-fake positive — a real symbolic derivation over real stored facts, not a canned string.
- `"What is the capital of France?"` → refused outright ("Concept definition... is not stored... No verified conclusions can be derived"), confidence 0.0. **No hallucination** — this is the one place the "fail honestly" principle is genuinely upheld in the live system.

**Confidently wrong (the most serious class of failure):**
- `"What number becomes 20 after adding 10?"` → answered **`result = 30.0`**, labeled *"Confidence: 1.00 (Verified: Computed via substitution)"*. The correct answer is 10 (20 − 10); the system computed 20 + 10 and reported it as verified truth. The word "Verified" here means only "SymPy's arithmetic was internally consistent," not "the interpretation of the question was checked" — there is no semantic verification step, contradicting the entire "hallucination impossible" claim in the documentation for exactly the case that claim is supposed to cover.

**Outright failures, with implementation detail leaking into the user-facing response:**
- `"A value is doubled and then increased by 6 to produce 30. What was the value?"` → the entity-span extractor's raw n-gram bag ("value doubled, doubled then, then increased, increased by, by 6, 6 produce, produce 30, 30 was, was value, value, doubled, then, increased, by, produce, 30, was") was passed whole to the UKM lookup as if it were a single concept name, then echoed verbatim into the refusal message shown to the user.
- `"Why can't a Java class extend two classes?"` → same failure mode: a raw garbage entity-span list is dumped into the "Missing Knowledge" error text. There is no capability to explain *why* a design rule holds beyond what's pre-authored in the seed graph — nothing resembling causal/design reasoning exists.

**No cross-turn memory:**
- `"What is a Java class?"` (correct, real answer) followed by `"How does it relate to abstraction?"` → refused: *"Unable to resolve concept 'it'..."* The interpreter's own `RELATE` pattern fired and correctly identified "it" as needing anaphora resolution, but its resolution logic only searches the *current* input string for an antecedent clause — the API (`StimulusRequest{stimulus: str}`) doesn't even carry a session ID, so cross-turn context is architecturally impossible regardless of the interpreter's internal machinery.

**Misrouting from the trainable-tagger fallback:**
- `"All bloops are razzles. All razzles are lazzles. Is every bloop a lazzle?"` → routed to `SOLVE_MATHEMATICS` (the trainable BiLSTM tagger, trained only on arithmetic/word-problem phrasing, voted REDUCTION with confidence ≥0.6 on a syllogism with zero math content) and then correctly refused only because SymPy couldn't parse it as an equation — not because any logic-reasoning capability recognized the syllogism as out of scope.

Unit-test corroboration: the full `hsci/tests` suite passes cleanly (**418 passed, 0 failed**, verified this session by direct execution), and the codebase's own commit history reports "489/489" for its complete suite. **None of the five live-runtime failures above are caught by that suite** — they involve phrasings the unit tests don't happen to cover. This is the report's most direct, first-hand confirmation of the audit's central instruction: test-pass is not cognition-works.

## H. Hardcoding / drift audit

- **Regex-cascade "understanding."** `LanguageInterpreter._analyze_semantic_request()` is ~600 lines dominated by hand-written regular expressions for specific English phrasings (`compare X and Y`, `relationship between X and Y`, `how does X relate to Y`, `why do X exist`, etc.), extended one named pattern at a time as failures are discovered (`comp_m1`...`comp_m7`, `rel_m1`...`rel_m8` — the numbering itself is the historical record of ad hoc patching). This is real, working code for the phrasings it anticipates, and it is the honest current state of "semantic interpretation" — not a placeholder, but also not what any of the three documented architectures describe as the Semantic Interpreter/SIA-1/Language Bridge.
- **A neural network that trains itself identically on every process boot from 30 hardcoded sentences.** `NeuralSemanticModel._get_shared_classifier()` constructs a BiLSTM, trains it for 25 epochs on a fixed in-source list of 30 example sentences across 5 classes, every time the module is imported. This has the mechanical form of learning (backprop, a fixed random seed for reproducibility) but functions as a decorative, deterministic lookup table — there is no persistence of learned weights, no exposure to real user traffic feeding back into it, and (per the code's own comment) the actual math-routing decision is made by a separate deterministic regex check *before* the neural classifier is even invoked for math-vs-not-math. The "neural" component only adjudicates the EXPLAIN/COMPARE/RELATE/GENERAL split, on 30 training examples.
- **A dead 8-stage engine on every request** — see §E.3. Worth restating here because it is a live-code fact, not a documentation claim: `UnderstandingEngine.understand()` runs in full on every `/process` call and its `UnderstandingResult` is discarded.
- **A previously-hardcoded concept whitelist, since replaced but instructive of the pattern.** The Aug-22 audit series documents (and I did not re-verify in current code, since it predates the interpretation rewrite) a `known_lexical_anchors = ["interface", "class", "method", "abstraction", ...]` word list that gated whether a demonstrative like "this X" was treated as a real noun phrase or a bare, context-requiring referent — meaning any concept not on that fixed list would incorrectly refuse. The audit's own fix is described only as "generic syntactic demonstrative parsing," itself still hand-built heuristic logic, not a general solution — the pattern of "find a failing phrasing, add one more hand-written rule" is the dominant engineering mode visible across the whole interpretation layer's history, right through to the current commits ("filler-word and comma-split bugs," "strip thousands-separator commas").
- **Self-graded audits.** The entire POST_VS7_REALITY document set (7 files) was authored in a single commit, by a single self-appointed "Antigravity Cognitive Architecture Team" persona, moving from "4 gaps found" to "0 gaps, 100% green" within that one commit, with no evidence of an independent or adversarial second pass, and testing confined to two closely related toy domains (Java OOP concepts; 3 synthetic "QuantumBit" concepts built with the identical relation shape as the seed data). This is not necessarily dishonest, but it is architecturally indistinguishable from grading one's own homework, and every subsequent roadmap document treats its "100% GREEN" verdict as settled fact.
- **LLM used only as an out-of-band development tool, never as the runtime's answer authority.** Worth stating explicitly since the task asks for this distinction: nothing in the live `CognitivePipeline` path calls an external LLM API at inference time (`LanguageInterpreter(enable_llm=False)` in the pipeline's own constructor). Any LLM involved in *building* this codebase (e.g., the "Gemini CLI" byline on `HSCI_RESEARCH_PAPER.md`, or whichever agent authored the POST_VS7_REALITY docs and the Sept commits) is a development-time tool, not a component of HSCI's runtime cognition. This separation is currently honored in the live code — it is not a gap.

## I. Learning architecture status

**What is specified:** LAA-1 gives the most complete account — `Task Executed → Outcome Logged → Reflection Manager → Z3 Validator → USM Update`, with a `Pattern Discovery Engine` and `Generalization Engine` proposing and a `Specialization Engine` narrowing candidate rules, gated by a Z3/consistency check before commit, and an Ebbinghaus-decay forgetting curve (`Activation(t) = Activation_0 · e^(−t/S)`) for retiring unused knowledge. The master documents give a second, code-level account (`ConceptExtractor`, `ProofGuidedWeightUpdater`, Hebbian strengthening) that is broadly compatible but not identical in vocabulary.

**What exists in code:** A substantial, real implementation — `hsci/learning/learning_engine.py`, `concept_extractor.py`, `proof_guided_updater.py`, `skill_learning_engine.py`, `persistent_skill_store.py`, and `hsci/memory/skill_graph.py`, `skill_lifecycle.py`, `skill_utility.py` — all with dedicated unit/integration tests that pass.

**What actually participates in live cognition: none of it.** As established in §D and §E.5 by direct import-graph tracing, every one of these modules is reachable only from `hsci/core/rir_loop.py` (the CLI-only legacy orchestrator) or from test files. A real user talking to the deployed API triggers zero experience capture, zero weight update, zero concept reinforcement, and zero skill formation — Its output space is exactly as large today as it was at the moment the SQLite seed data was written, and no less. The self-play engine (`hsci/self_play/hypothesis_builder.py`) that both master documents call the mechanism for continuous background learning is also only reachable from `RIRLoop`, has its `build_from_concepts`/`build_for_concept` methods left as unimplemented stubs in the documentation itself, and is not running behind the live API. `Concept_Formation_Theory.md`'s create/merge/split algorithm has no corresponding code anywhere in the repository at all.

## J. True MVP definition

Not "tests pass." A genuine MVP must show, on inputs not specifically anticipated by any hand-written pattern:

1. A single conversational session (shared session/context state — currently does not exist even as a data field on the API request) across multiple turns, where a pronoun or elided reference in turn N correctly resolves against turn N−1.
2. At least one instance where an answer's *correctness*, not just its arithmetic consistency, is checked against the question's actual semantics before being labeled "Verified" — i.e., closing the gap demonstrated by the "20 after adding 10 → 30" failure.
3. At least one instance of an interaction changing the system's behavior on a *later, different* interaction — i.e., closing the "zero episodes captured" gap in §I. This does not need to be the full Z3-gated learning loop from the master documents; it needs to be *any* observable persistence of experience that a live user's next question can benefit from.
4. Graceful, non-leaking failure — the current garbage-n-gram-in-error-message behavior (§G) is a UX/robustness bug worth fixing regardless of the deeper architecture question, because it currently makes real failures look like internal bugs rather than honest "I don't know."

None of these four require re-adopting the V4 BrainKernel or V5 Meaning-Graph specifications wholesale. They are achievable as direct extensions of the architecture that is *actually running today* (§D).

## K. FIRST IMPLEMENTATION STEP

**Do not resume building toward any of the three documented architectures (BrainKernel/V4, Meaning-Graph/V5, or the Rust/Kafka/Raft distributed blueprint) as a next step, and do not start a fourth rewrite.** All three are unbuilt specifications sitting on top of a running system that already went a different, fourth direction and works, within its narrow scope, honestly. Reconciling the documents before writing code, as several of the meta-audit documents (`MRG-1`) recommend, has already been tried repeatedly (three full document generations exist) and has not once resulted in code that matches any of them — the pattern to break is spec-writing substituting for cognition-building.

**Recommended first step: give the live `CognitivePipeline` a real, persistent, request-spanning session/context state, and use it to make cross-turn coreference actually work (MVP item 1).**

**Why this must come first, over the other three MVP gaps:** Everything else in the capability matix (§F) — task decomposition, grounding, reasoning, verification, learning — currently operates on a single, isolated utterance. But cognition, by this project's own definition (`Intelligence_Theory.md`'s "entropy-minimizing utility over an *active workspace*," and every architecture generation's insistence on a `WorkingMemory`/Context Engine/Meaning-Graph-with-persistent-scope), presupposes that an "understanding" of the current input is built *in the context of* what came before. Right now that presupposition is silently false — the `LanguageInterpreter` already contains real machinery for detecting that a pronoun needs resolution (`ContextReference`, `requires_context`, `InterpretationAssumption`), but has nothing to resolve it *against*, because the API throws away all state between calls. This is the one gap that is a genuine *precondition* for the others to mean anything: fixing the "confidently wrong" math-verification gap (MVP item 2) or the learning gap (MVP item 3) inside a stateless single-turn model still leaves a system that cannot be said to be reasoning "with" a user, only "at" a sequence of disconnected strangers. Conversely, once turn-to-turn state exists, the very same experience-persistence mechanism becomes the natural place to start hanging episode capture (MVP item 3) — they are the same piece of missing infrastructure (a persistent, request-spanning store) viewed from two angles.

**What depends on it:** MVP item 3 (experience capture / minimal learning) is a direct extension of the same persistent-state mechanism. MVP item 2 (semantic verification) benefits because a context-aware interpreter has more signal to catch its own misparses (e.g., a clarifying follow-up becomes possible instead of a silent wrong answer). The eventual reconciliation of *which* documented architecture (if any) to formally adopt becomes a much better-informed decision once there's a second real data point (a working stateful loop) beyond the current single-turn one.

**What files/components should be involved:**
- `brain_api.py` — add a session identifier to `StimulusRequest` (or accept one via header) and persist a per-session store across requests (in-process dict is sufficient for a first cut; the "ephemeral, request-scoped WorkingMemory" constitutional principle applies to *intra*-request state, not to the legitimate need for *inter*-request conversational memory, which every architecture generation also calls for via `ConversationManager`/Context Engine/`ConversationTurn` — this is not a constitutional violation, it is a currently-missing constitutional requirement).
- `hsci/core/cognitive_pipeline.py::CognitivePipeline.answer()` — accept and thread a session context object through to the interpreter and grounding stages instead of constructing a fresh `CognitiveContext` with a hardcoded `session_id="vs7-cognitive-pipeline"` every call.
- `hsci/cognition/interpretation/interpreter.py` and `grounding.py` — the anaphora-detection code already exists (`ContextReference`, `is_bare_referent`, `requires_context`); it needs an actual antecedent store to resolve against instead of only re-scanning the current utterance.
- `hsci/cognition/interpretation/models.py` — check whether `ContextReference`/`GroundingStatus` already have fields shaped for this (per the VS-6/VS-7 design docs they do) before adding new ones.

**What must NOT be changed:** Do not touch `UniversalMathEngine`/SymPy solving paths, the knowledge-graph traversal in `reasoning_engine.py`, or the VS-7 task-graph/workspace machinery — all three are genuinely working within their scope (§F, §G) and are not implicated in this gap. Do not resurrect `rir_loop.py`, Z3, or the learning subsystem as part of this step — wiring those in is a separate, larger decision this report deliberately does not make. Do not attempt to reconcile or rewrite the documentation generations as a prerequisite — validate against the running system, not against any one document.

**How it will be validated:** A live, unseen two-turn (and three-turn) conversation test through the actual `/process` endpoint — not a unit test with mocked context — where turn 2 uses a bare pronoun referring to turn 1's subject and gets a substantively correct answer, plus a regression check that all currently-passing single-turn behaviors (§F's "works" rows) are unchanged.

## L. Subsequent dependency chain

Using the repository's own terminology where a documented term genuinely fits the current architecture, and plain description where it would misleadingly borrow from an unbuilt generation:

```
FOUNDATION        Session-scoped context/state (K, above) — the only currently-missing
                   precondition for the rest of this chain to be meaningful.
     ↓
UNDERSTANDING      Extend LanguageInterpreter's existing ContextReference/anaphora
                   machinery to resolve against the new session state (closes MVP-1).
     ↓
VERIFICATION       Add a semantic self-check to UniversalMathEngine's word-problem path:
                   at minimum, cheaply re-derive the answer a second, independent way
                   (e.g. dimensional/sign sanity check) before labeling a substitution-
                   inferred answer "Verified" — closes the "20 after adding 10 -> 30"
                   failure class (MVP-2) without requiring a full Z3 CEGIS loop.
     ↓
EXPERIENCE         Persist each session's (question, interpretation, answer, outcome)
                   as a real record, reusing the session store from FOUNDATION
                   (closes MVP-3, "experience capture" in the capability matrix).
     ↓
LEARNING           Only once EXPERIENCE produces real records: decide, with the user,
                   whether to wire the existing (but currently disconnected) LAA-1-style
                   learning subsystem in `hsci/learning/` against them, or design a
                   smaller mechanism scoped to what CognitivePipeline actually needs.
                   Do not resurrect the RIRLoop/Z3/skill-graph machinery wholesale
                   just because it already exists in the repo.
     ↓
GENERALIZATION     Only meaningful once LEARNING produces more than one reinforced
                   pattern: revisit ontology-graph analogical composition (currently
                   an unimplemented stub in every generation of the docs) as the
                   mechanism for genuine cross-concept transfer.
     ↓
SKILLS / CONCEPTS  Only meaningful once GENERALIZATION exists: decide whether
                   Concept_Formation_Theory.md's create/merge/split thresholds (which
                   currently have zero corresponding code anywhere) are still the
                   right model, informed by what real accumulated experience looks like.
     ↓
MENTAL MODELS      Last, and only worth defining once the system has actually
                   accumulated the state (session history, learned patterns, formed
                   concepts) that a "mental model" would need to be a model of —
                   building this first, as the Lobe-era documents' `MentalModel`
                   class attempted, produces a trace of a system that isn't there yet.
```

Each arrow above is a hard dependency, not a suggested order: none of the later stages currently has anything real to operate on, because the stage before it does not yet exist in the live path. The single highest-leverage action available today is the FOUNDATION step — it is small, low-risk (additive, touches no working code), and is the one piece of infrastructure every other gap in this audit ultimately traces back to.
