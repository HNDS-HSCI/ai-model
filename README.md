# HSCI Mind

A small reasoning system that is **taught**, not trained on a text corpus. You tell it facts, rules and formulas in plain English, or show it a few examples of a concept, and it reasons over what it was taught. Every answer is a proof that is checked (Z3, or by substituting numbers back). When it can't prove something it says "I don't know".

It is a research prototype, not a general assistant. It only knows what it has been taught.

## What works today (measured)

| | Result | How to reproduce |
|---|---|---|
| Reasoning over taught knowledge (taxonomy, if-then rules, comparatives, relations, defaults with exceptions, formula chains, algebra) | 210/210 problems, all verified | `python -m hsci.mind.evaluation --n 30 --seed 7` |
| Learning a new phrasing from one example | 0% → 99–100% correct, 0% wrong | `python -m hsci.mind.understanding.evaluation` |
| Learning concepts as small programs from 4–12 examples (even, prime, factorial, gcd, plural, article …) | 13 of 16 fully correct on fresh tests | `python -m hsci.mind.concept_core` |
| Same, asking the teacher when two rules disagree | 76/89 fresh-test cases right; gcd fixed, plural lost | `HSCI_CURIOUS=1 python -m hsci.mind.concept_core` |

Evaluation problems use invented words, which shows no domain facts are in the code. They stay inside the supported grammar, so they do **not** measure coverage of ordinary English.

## What does not work yet

- Word problems that put numbers inside sentences ("A train travels 120 km in 2 hours…").
- Events and time ("Alice gave Bob a book yesterday").
- Connecting English to the concept learner ("the plural of cat is cats" should become an example).
- Concept search slows down as the library grows. This is the main open problem.

See [docs/mind/ARCHITECTURE.md](docs/mind/ARCHITECTURE.md) for the design, the limits and the roadmap.

## Run it

```bash
pip install -r requirements.txt
python run_app.py                 # opens http://127.0.0.1:8000/mind
pytest                            # tests (set HSCI_MIND_ENCODER=hash to skip the neural encoder)
```

Example conversation:

```
Socrates is a man. All men are mortal. Is Socrates mortal?
→ Yes. Socrates is mortal, because Socrates is a man.   [deduction + Z3]
```

## Layout

```
hsci/mind/                 the system
  parser.py, lexicon.py    English → logic (grammar words only, no domain words)
  kb.py                    SQLite knowledge base with provenance
  reasoner.py, verifier.py forward chaining with proofs; Z3 re-check
  quantities.py            formulas and units (SymPy)
  learner.py               induced hypotheses, refuted by counterexamples
  understanding/           learning new phrasings from experience
  neural/                  "probably" answers from a small graph network, never verified
  concept_core.py          concepts as small programs learned from examples (prototype)
  data/                    seed knowledge, written in English
hsci/tests/                tests
ui/mind.html               web UI
```

Earlier versions (the `hnsds` solvers, the V4 pipeline and their documents) are kept at the git tag `v4-legacy`.

License: Apache 2.0.
