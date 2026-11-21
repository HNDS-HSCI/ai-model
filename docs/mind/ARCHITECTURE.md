# HSCI Mind — Architecture, Review & Roadmap

*Status: working MVP (October 2026). Code: `hsci/mind/`. Tests: `hsci/tests/test_mind.py`.*

## 1. Why a new core was needed

The existing V4 pipeline (`hsci/core/cognitive_pipeline.py`) was probed with seven ordinary questions:

| Input | V4 pipeline result |
|---|---|
| What is a Java interface? | ✅ answered — the concept is in the hand-written seed file |
| solve 2x + 3 = 11 | ✅ answered via SymPy |
| Socrates is a man. All men are mortal. Is Socrates mortal? | ❌ "Unable to resolve concept 'Is Socrates, Socrates man, …'" |
| A dog is a mammal. A mammal is an animal. Is a dog an animal? | ❌ unresolved |
| If mass is 10 kg and acceleration is 2, what is the force? | ❌ unresolved — even though F = m·a is in its own seed |
| Alice is older than Bob. Bob is older than Carol. Who is the youngest? | ❌ unresolved |
| What is photosynthesis? | ❌ (correctly refused, but it cannot be taught) |

**Root cause:** the V4 system *retrieves* pre-written concepts; it does not *reason over what it is told*. Understanding is a ~600-line regex cascade (`interpreter.py`) that maps question shapes to fixed task types, and each task type has its own executor. Every new kind of question needs new code. That is the "hard-coded, sequential workflow" problem.

### Review of the two existing projects

**`hsci/` (V4 cognitive pipeline)**

| Keep / reuse | Retire or replace |
|---|---|
| SQLite storage patterns, provenance idea, event bus | Regex intent cascade (`cognition/interpretation/interpreter.py`) |
| Z3 and SymPy integration | Per-intent executors (`task_executor.py`: explain / compare / relate …) |
| Test discipline (463 tests) | LSTM "neural semantic model" trained on ~30 anchor sentences at every start-up (≈10 s boot, unreliable) |
| | Static numbers in `/health` (`proof_count: 1`, `avg_loss: 0.0`) |
| | README/paper claims ("100 % accuracy", "zero hallucination") measured on 3 cases |

**`hnsds/` (deliberative solvers, closest to the research paper)**

| Keep / reuse | Retire or replace |
|---|---|
| Z3 constraint / graph / dependency / state-machine solvers — good *plug-in solvers* for the planner | `brain/cognitive_core.py` routes on benchmark titles (`"ENTERPRISE DEPLOYMENT TOPOLOGY" in stimulus`) — task-specific hard-coding |
| CEGIS-style enumerative synthesiser (the paper's SY) | Duplicate planners / parsers that overlap with `hsci/` |

**Documentation:** ~200 Markdown files describe dozens of subsystems that do not exist in code. Keep this document plus the paper; archive the rest.

## 2. Design principles of the new core

1. **Knowledge is data, never code.** Everything the system knows arrives as English (from the user or from `data/common_knowledge.txt`) and is compiled into logic. The code contains no nouns, verbs, adjectives or domain facts.
2. **Only grammar is built in.** The parser knows closed-class words — determiners, copulas, quantifiers, "than", "if … then", relative pronouns — which are finite and domain-independent. Any open-class word becomes a symbol on first use. Proof: the evaluation runs entirely on invented words.
3. **Every answer is a proof, and every proof is checked.** The forward chainer records a derivation for every conclusion. Z3 independently re-checks it (premises consistent, and premises ∧ ¬goal is UNSAT). Numeric answers are substituted back into every formula used.
4. **Three-valued honesty.** *Proven yes*, *proven no*, or *I don't know*. Induced patterns can produce an explicitly-labelled "probably", never a "verified" answer.
5. **Neural proposes, symbolic disposes.** Learned vector representations help with perception (typos, inflection) and similarity, but never decide truth.
6. **Full provenance.** Every belief points to the sentence it came from. Any statement can be retracted together with everything it implied.

## 3. Architecture

```
 English text
     │
 ┌───▼──────────────────────────────────────────────────────────────┐
 │ P/F  Semantic parser (parser.py, lexicon.py, quantities.py)       │
 │      construction grammar → facts · rules · defaults · formulas   │
 │      · quantities · definitions · questions (goals + assumptions)│
 │      ambiguity resolved by ranking parses on grounding in the KB  │◄── knowledge feeds perception
 └───┬──────────────────────────────────────────────────────────────┘
     │ logical form (Σ)
 ┌───▼──────────────┐   ┌────────────────────────────────────────────┐
 │ W  Knowledge base │   │ Sub-symbolic layer (semantic_space.py)     │
 │ kb.py — SQLite,   │◄──┤ char-n-gram grounding (typos), PPMI+SVD    │
 │ worlds, provenance│   │ concept embeddings (similarity)            │
 └───┬──────────────┘   └────────────────────────────────────────────┘
     │
 ┌───▼──────────────────────────────────────────────────────────────┐
 │ PL/SO  Mind (mind.py) — chooses solver per goal                  │
 │   deduction · defaults · superlatives · description ·            │
 │   quantity chaining · algebra · similarity · introspection        │
 └───┬───────────────────────────┬──────────────────────────────────┘
 ┌───▼──────────────────────┐ ┌──▼─────────────────────────────────┐
 │ SY Reasoner (reasoner.py) │ │ Quantities (quantities.py)         │
 │ semi-naive forward        │ │ formula chaining + SymPy, units,   │
 │ chaining, strong negation,│ │ substitution check                 │
 │ defaults with exceptions, │ └──┬─────────────────────────────────┘
 │ proof trees               │    │
 └───┬──────────────────────┘    │
 ┌───▼───────────────────────────▼──┐  ┌───────────────────────────────┐
 │ V  Verifier (verifier.py) — Z3    │  │ L  Learner (learner.py)       │
 │ re-checks every proof step        │  │ induce hypotheses; refute them│
 └───┬───────────────────────────────┘  │ on counterexamples (CEGIS)   │
     │                                  └───────────────────────────────┘
 ┌───▼──────────────────────────────┐
 │ Explainer (explain.py) — proofs → │
 │ English with provenance           │
 └──────────────────────────────────┘
```

The letters are the components of the HNS-DS paper (*P* perception, *F* formaliser, *W* world model, *PL* planner, *SO* solver orchestrator, *SY* synthesiser/solver, *V* verifier, *L* learner). The paper's RIR-RI loop appears twice:

- **For knowledge:** a hypothesis is induced, kept as a candidate, and refuted by the first counterexample.
- **For consistency:** a new statement is accepted only if the extended closure has no contradiction. Otherwise it is rejected, with both proofs shown.

### What the logic can express

| Construction | Example | Compiles to |
|---|---|---|
| Category / property | Rex is a big dog. Socrates is mortal. | `is(rex, big dog)`, `is(rex, dog)`, `is(rex, big)` |
| Universal | All men are mortal. Every wug is a blicket. | `is(?x, man) → is(?x, mortal)` |
| Negative universal | No blicket is a dax. | `is(?x, blicket) → ¬is(?x, dax)` |
| **Default (generic)** | Birds can fly. Typically, … | default rule — blocked by known exceptions |
| Conditional with variables | If X is a parent of Y and Y is a parent of Z then X is a grandparent of Z. | Horn rule |
| Relative clause | People who are rich are happy. | `is(?x, rich) → is(?x, happy)` |
| Comparatives | Alice is older than Bob. | relation + grammatical transitivity and asymmetry |
| Opposites | Younger is the opposite of older. | inverse relations |
| Relation properties | Being in is transitive. | transitivity rule |
| Relational nouns / prepositions / verbs | John is the father of Mary. Paris is in France. Alice likes Bob. | binary relations |
| Existentials | Some birds cannot fly. | Skolem individual |
| Definitions | Photosynthesis is the process by which … | gloss + `is(photosynthesis, process)` |
| Formulas / quantities | Force equals mass times acceleration. The mass is 10 kg. | SymPy equations / values with units |
| Questions | Is/Does/Can …? Who/What/Which …? Who is the youngest? How many …? Why …? If …, what is …? | goals, assumptions, superlatives, counts |

## 4. Results

**Nonce-word evaluation** (`python -m hsci.mind.evaluation --n 100 --seed 2026`): 700 freshly generated problems in invented vocabulary, so nothing can be memorised.

| Suite | Accuracy | Answers verified | Median latency |
|---|---|---|---|
| taxonomy (depth 1–5, negation, open world) | 100 % | 100 % | 24 ms |
| conditional (ProofWriter-style, depth 1–4) | 99 % ¹ | 100 % | 17 ms |
| comparative (transitivity, asymmetry, superlatives) | 100 % | 100 % | 24 ms |
| relation (taught transitivity, wh-questions) | 100 % | 100 % | 22 ms |
| default (generics with exceptions) | 100 % | 100 % | 16 ms |
| quantity (two-step formula chains) | 100 % | 100 % | 26 ms |
| algebra | 100 % | 100 % | 9 ms |
| **overall** | **99.9 %** | | |

¹ The single miss was a generated word that happened to be the English irregular plural "men". The generator now excludes such words.

**Caveat:** these suites stay inside the supported grammar by construction. They prove the absence of domain hard-coding, not broad language coverage. The test suite also includes hand-written natural-language cases. Real coverage of free text is the main open problem (see §6).

## 4b. Understanding that grows from experience (`hsci/mind/understanding/`)

The grammar in §3 is hand-written, so on its own it would be a fixed set of rules. The understanding layer turns it into a **bootstrap**, the way a child starts with some innate structure and learns language from experience:

```
utterance ──► grammar reading (innate teacher) ─┐
     │                                          ├─► plausibility check ─► combine ─► confidence
     └─► recall similar experiences ──► align ──┘      (does this meaning      (agreeing readings
         (semantic: neural encoder;     & adapt          fit these words?)       reinforce; close
          structural: frame overlap)    by analogy                               rivals lower it)
                                                                 │
                ┌────────────────────────────────────────────────┼──────────────────────────┐
           ≥ 0.70: act                               0.40–0.70: "Do you mean …?"     < 0.40: "Could you say
                                                                                      it another way?"
                                                     yes → act + remember          rephrase → act + remember
                                                     no  → ask to rephrase          "<original>" = that meaning
```

- **Experience memory** stores every utterance the Mind understood confidently, every confirmed reading, and every taught phrasing, as `sentence → meaning`. Each experience tracks confirmations and rejections, so unreliable ones lose influence.
- **Analogy** aligns a new sentence with a remembered one. Grammar words (articles, quantifiers, negation, prepositions, "is"/"are") form the *frame* and must match exactly, because "each", "no" and "are" carry meaning. Content words are *slots* that take new words. Name slots only take names; fillers ("btw", "kinda") are cheap to skip. The remembered meaning is then rewritten with the new words.
- **Taught beats guessed.** A sentence a person explained wins over the grammar's literal reading. An analogy drawn from the grammar's own past readings is down-weighted as second-hand evidence.
- **Maths never goes through analogy.** It is exact.
- **The neural encoder** (`all-MiniLM-L6-v2`, offline in `models/`) is used only to recall similar experiences. Its word-level similarity proved unreliable, so it never decides meaning. A hashing encoder is the fallback and is what tests use.

**Learning-curve result** (`python -m hsci.mind.understanding.evaluation`). Eight phrasings the grammar cannot read ("{N} is known to be {a}", "I wonder if {N} is {a}", "What place is {N} in?" …), 12 trials each with fresh invented words, three seeds, both encoders:

| | correct | asked | **wrong** |
|---|---|---|---|
| before teaching | 0 % | 100 % | **0 %** |
| after **one** example per phrasing | 99–100 % | 0–1 % | **0 %** |

The reasoning suites (§4) still score 100 % with experience accumulating across all problems in one Mind. Sentences that the grammar previously misread *silently* ("Water boils at 100 degrees", "Alice gave Bob a book yesterday") are now questioned instead of stored.

**Honest limits.** Analogy generalises *phrasings*: it learns new ways to say things the logic can already represent. It cannot invent new kinds of meaning (events, time, numbers inside facts); that is the next step (§7). Understanding a new phrasing still needs one example from a person, which is how people learn idioms too.

## 4c. Neural intuition (`hsci/mind/neural/`)

When proof and induction are both silent, a learned intuition may answer **"probably"**, always labelled and never verified:

- **Concept-graph network:** an R-GCN (2 layers, basis-decomposed relation weights) with a DistMult decoder, trained by link prediction on the Mind's own knowledge graph. It runs on CPU, needs no outside data, and is retrained when knowledge changes.
- **Category statistics:** transparent counting ("13 of the 14 daxes I know about are brave").
- They are combined because each wins where the other is blind (held-out AUC, 8 worlds):

  | pattern | counting | network |
  |---|---|---|
  | class-typical properties | 0.98 | 0.93 |
  | relational ("fans of X's star share X's property") | 0.50 | 0.95 |

- **End to end** (`python -m hsci.mind.neural.evaluation --mind`): about 93% of its "probably" answers are right, and verified answers that were wrong = 0. It speaks only at ≥ 0.80 or ≤ 0.15. The network needs ≥ 40 links, and ≥ 2 links per concept, before its view counts.
- **Next:** an attention network and a reasoning-policy network trained from Z3-verified proofs (the paper's Proof-Guided Learning).

## 4d. Learned semantic parser (`understanding/neural_parser.py`)

The aim is that input is read by **learned** components, with the hand-written grammar only a temporary teacher for the first examples.

- **Constructions** are learned from experience. Every remembered sentence→meaning pair becomes a frame with slots plus a meaning template.
- **A neural network** (BiGRU encoder, about 60k parameters, CPU) learns to (1) recognise which construction a sentence is and (2) tag which words fill which slot. Unknown words are represented by character and shape features, and training is augmented with invented words, so it learns *structure*, not vocabulary.
- Constructions that yield the same meaning pool their probability. Readings still pass the plausibility check and the act/ask policy.
- It retrains in the background whenever experience grows (≈20–40 s today).
- `HSCI_MIND_GRAMMAR=teacher` turns the hand-written grammar **off at inference**. Arithmetic is still read by the exact calculator.

**Measured (grammar off at inference, trained on ~60 starting experiences):**
- Single sentences built from never-seen words, 20 sentence shapes: **90–94 %** read correctly (`python -m hsci.mind.understanding.neural_eval`).
- Full reasoning suites, every sentence read by learned components: **84–86 %** (taxonomy, conditionals, comparatives, quantities, algebra 100 %; relations 33–100 % and defaults 53 %, with high run-to-run variance). With the grammar on: 100 %.

**Bugs found and fixed while measuring:**
- The meaning comparison ignored argument order, so `likes(a, b)` matched `likes(b, a)`. This affected earlier evaluation numbers.
- The grammar teacher produced wrong seed meanings ("Tom eats" as a name). These are now caught by plausibility and not learned.
- A question asked mid-message swallowed the next sentence of the same message.

**Next for this layer:**
- Hand-checked labelled examples for shapes the grammar misreads (data, not rules).
- More examples per shape to reduce variance.
- Faster incremental training.
- Then retire the grammar from the default path.

## 5. Running it

```bash
python -m hsci.mind.api --port 8100        # standalone API + UI (≈2 s boot, no torch)
# open http://127.0.0.1:8100/mind
python run_app.py                          # main app; Mind is mounted at /v2/* and /mind
python -m hsci.mind.evaluation --n 50      # reasoning evaluation
python -m hsci.mind.understanding.evaluation --encoder neural   # learning-curve evaluation
pytest hsci/tests/test_mind.py hsci/tests/test_mind_understanding.py
```

The neural encoder lives in `models/all-MiniLM-L6-v2` (git-ignored, ~88 MB). To fetch it on a machine behind corporate TLS inspection, use the OS trust store:
`python -c "import truststore; truststore.inject_into_ssl(); from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2').save('models/all-MiniLM-L6-v2')"`.
Without it, the Mind runs on the hashing encoder. `HSCI_MIND_ENCODER=auto|neural|hash` selects the encoder; `auto` loads the neural one in the background.

Teaching a phrasing: in conversation (answer the Mind's "Do you mean…?" or rephrase when asked), in the UI's *Teach a phrasing* box, or `POST /v2/teach {"surface": "...", "canonical": "..."}`.

`HSCI_MIND_DB` sets the SQLite path (default `data/hsci_mind.db`). Worlds isolate knowledge: use one per user or per problem. The shared `__common__` world is read-only over the API.

## 6. Known limitations (honest)

- **Language coverage starts from a construction grammar and grows by experience (§4b).** New phrasings are learned from one example. Sentences whose *meaning* the logic cannot express (events, time) are asked about rather than understood. Expect many clarification questions at first; they become rarer as experience accumulates.
- **No events, time or tense.** "Alice gave Bob a book yesterday" is beyond the logic: there are no n-ary events and no temporal reasoning.
- **Quantities are global per world.** "The car's mass" and "the truck's mass" collide.
- **Defaults are resolved greedily.** Conflicting defaults (the Nixon diamond) resolve by order rather than by specificity.
- **Lemmatisation follows agreement.** "is men" and "are men" can normalise differently for irregular words.
- **Single process.** The closure cache is in-process. Run one API worker per database, or move the KB to Postgres with a shared cache.
- **Scale.** Forward chaining is fine for 10⁴–10⁵ facts. Beyond that, use a Datalog engine (Soufflé, DuckDB recursive CTEs) or incremental view maintenance.

## 7. Roadmap — from MVP to the research system

1. **Richer meaning: events with roles, time, numbers in facts (highest value now).** Analogy can only produce meanings the logic can express. "Alice gave Bob a book yesterday" and "Water boils at 100 degrees" need `give(e) ∧ giver(e, Alice) ∧ receiver(e, Bob) ∧ theme(e, book) ∧ time(e, yesterday)`. *Done so far:* experience-driven understanding (§4b) already replaces fixed parsing for phrasings.
1b. **Syntax layer.** A small dependency parser (spaCy, not an LLM) would give the grammar reliable subject/verb/object structure, so the bootstrap reads far more sentences before any teaching is needed.
2. **Document ingestion.** Accept a paragraph or page, report which sentences compiled, and ask clarifying questions for the rest.
3. **Richer logic.** Events with roles (neo-Davidsonian), time, numeric comparisons inside rules, and cardinality ("every person has two parents").
4. **Specificity-based defaults and belief revision** (prioritised defaults; retract the weakest belief on conflict instead of rejecting the newest).
5. **Plug the `hnsds` solvers in as tools.** Constraint / graph / dependency solvers and the CEGIS synthesiser become solvers the planner can choose for goals the deductive engine cannot express. This is the paper's full RIR-RI loop for code and maths.
6. **Real benchmarks.** ProofWriter, RuleTaker, CLUTRR and bAbI (logic / QA), then MiniF2F and HumanEval for the synthesis loop. Report the paper's metrics: success, iterations, time to verification, learning curves.
7. **Learned reasoning control.** Use episode logs to learn which rules and solvers to try first: the paper's learner *L* as a heuristic ranker. Soundness is unaffected because Z3 still checks everything.
