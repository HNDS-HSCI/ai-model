# HSCI Codebase Guide for AI Agents

## Core Architecture: Beyond LLMs

**HSCI** (Hyper-Symbolic Cognitive Invention) is a **self-verifying cognitive architecture**, not an LLM. It replaces probabilistic guessing with **formal verification** using symbolic reasoning. Key distinction: outputs must be **mathematically proven**, not merely predicted.

### The Functional Brain Architecture

The system uses a biological metaphor with specialized **lobes** working through a shared **Mental Model**:

1. **Perception Lobe** (`native_neural_lobe.py`): Fast, pattern-based intent classification using synaptic weights matrix (`synaptic_core.json`). Implements System 1 thinking.
2. **Logic Lobe** (`SpecBuilder` in `formalizer/`): Translates classified intents into rigid **Symbolic Specifications (Σ)**—the mathematical "contract" any solution must satisfy.
3. **Reasoning Lobe** (`generative.py`, `enumerative.py`): Proposes candidate solutions through template synthesis or systematic search, not token prediction.
4. **Verified Lobe** (`native_engine.py`): The deterministic judge using axiomatic reduction. Provides binary verification + counterexamples for repairs.
5. **Memory Lobe** (`episode_logger.py`): Stores solved episodes to build "symbolic intuition" via TF-IDF episodic retrieval.

All lobes communicate through `MentalModel` (`mental_model.py`), the AI's explicit readable internal state (state, memory_trace, symbolic_spec, final_proof).

## Critical Cognitive Loop: RIR-RI (Reinforced Iterative Repair)

```
Stimulus → Perception → Formalization → Planning → Synthesis → Verification
                                                        ↑______________|
                                                     (counterexample)

Success → Hebbian Reinforcement (synaptic weight update)
```

**Always trace this loop when debugging**:

- If output is wrong, check which lobe failed: Did Perception misclassify? Is Σ malformed? Does Verifier reject the candidate?
- New features must fit this loop: What does it perceive (input)? What does it verify (correctness metric)?

## Project-Specific Patterns

### 1. Native (Zero-Dependency) Architecture

- **NO external APIs or LLM calls**. All reasoning happens locally.
- Avoid imports from `transformers`, `openai`, `anthropic`. The codebase intentionally avoids third-party neural models.
- The system uses **small, interpretable heuristics** (regex, bag-of-words, simple templates) instead of black-box models.

### 2. Symbolic Specification as Contract

Every problem must be formalized as a **Symbolic Spec (Σ)** before solving:

```python
# Examples of Σ (from synthesizer/generative.py)
{"type": "math", "equation": "x + 2 = 5", "variables": ["x"]}
{"type": "coding", "signature": "def add(a, b) -> int", "examples": [(1, 2, 3)]}
```

- **Your responsibility**: Ensure Σ is unambiguous and complete. Vague specs = failed verification.
- Specs are **JSON contracts**, not prose. Ambiguity = synthesis failure.

### 3. Hebbian Learning Through Episodes

When verification succeeds, the system **strengthens synaptic weights** between input tokens and successful cognitive paths:

```python
# In hnsds/brain/lobes/native_neural_lobe.py
def grow(self, stimulus, successful_state):
    # Update synaptic_core.json weights to reinforce this path
```

- **Growth is automatic** when `HyperSymbolicBrain.process()` finds a proven solution.
- Episodes are logged in `hnsds/learner/episode_logger.py` and retrieved via TF-IDF for future intuition.
- **Don't override growth manually**—trust the Hebbian update unless debugging a specific wrong learned pattern.

### 4. Two-System Cognition: Neural (Fast) vs. Symbolic (Verified)

- **Weak confidence (<40%)?** The system asks for clarification rather than guessing (see `cognitive_core.py` line ~55).
- **Conversational context?** Neural Lobe answers directly; Symbolic Engine only needed for logic/math/code.
- **Pattern already learned?** Episode retrieval bypasses costly synthesis (check `memory_trace` in MentalModel).

### 5. Failure Handling: Counterexamples Drive Repair

When verification fails, the **counterexample becomes the learning signal**:

```python
for attempt in range(budget):
    candidate = self.synthesizer.propose(sigma, examples)  # examples = [counterexample1, counterexample2, ...]
    success, feedback = self.verifier.verify(candidate, sigma)
    if not success:
        examples.append(feedback)  # Prune search space for next iteration
```

- **Bounded search**: If no solution found after `budget` attempts, report cognitive failure (not graceful fallback).
- This is **Not retry-with-sleep**; it's systematic pruning.

## Key Files by Responsibility

- **Orchestration**: `hnsds/brain/cognitive_core.py` (HyperSymbolicBrain), `hnsds/orchestrator.py`
- **Intent Classification**: `hnsds/brain/lobes/native_neural_lobe.py` (synaptic_core.json)
- **Problem Formalization**: `hnsds/formalizer/spec_builder.py`
- **Solution Generation**: `hnsds/synthesizer/{generative,enumerative}.py`
- **Proof Verification**: `hnsds/brain/lobes/native_engine.py` (Z3 optional)
- **Episode Memory**: `hnsds/learner/episode_logger.py` (TF-IDF retrieval)
- **Mental State**: `hnsds/mental_model.py` (the readable "mind")
- **API/UI**: `brain_api.py`, `run_app.py`, `ui/index.html`

## Development Workflows

### Testing & Validation

- **Unit tests**: `test_brain.py`, `test_hnsds.py` execute the full RIR-RI loop end-to-end.
- **Run single test**: `python test_brain.py` (instantiates HyperSymbolicBrain and exercises key paths).
- **Verify output**: Check `mind.memory_trace` and `mind.final_proof` for reasoning details, not just final answer.

### Running the System

- **Full app with UI**: `python run_app.py` (starts FastAPI backend + browser dashboard).
- **Headless**: `python run_mind.py` or `python demonstrate_intelligence.py` (direct Python API).
- **Dashboard**: Displays live Mental Model state (current_goal, memory_trace, symbolic_spec)—invaluable for debugging.

### Adding New Problem Types

1. **Add perception heuristic** in `native_neural_lobe.classify_and_formalize()` to recognize new intent.
2. **Define Σ schema** in `spec_builder.py` (what must the spec contain for this problem type?).
3. **Add synthesis strategy** in `generative.py` or `enumerative.py` (how to generate candidates?).
4. **Add verification logic** in `native_engine.py` (how to prove correctness?).
5. **Test end-to-end** with `test_brain.py` or dashboard.

## Non-Obvious Conventions

- **Cognitive State Machine**: `mental_model.state` tracks "IDLE" → "RECALLING" → "ANALYTICAL" → "VERIFIED". Use these states to control behavior, don't create new states.
- **Confidence Scores**: Any spec generation should include `"confidence"` (0.0–1.0). <0.4 triggers clarification, not assumptions.
- **Episode Format**: `{"goal_str": "...", "solution": "...", "timestamp": "..."}` in `primordial_knowledge.jsonl`. Keep consistent for TF-IDF to work.
- **Synaptic Weights**: JSON keys are token n-grams (e.g., "solve + equation") mapped to intent scores. Weights emerge from Hebbian updates, not hardcoded.
- **Logical Verification**: Prefer native symbolic reduction (in `native_engine.py`) over Z3 for local determinism. Z3 is optional enhancement.

## Debugging Checklist

1. **Wrong answer?** Check `memory_trace` for which lobe failed (perception misclassified? Σ malformed? Verification too strict?).
2. **Verification always fails?** Ensure the synthesizer's candidate actually satisfies Σ. Add test case with concrete Σ and expected candidate.
3. **Weak confidence downstream?** Fix perception heuristics in `native_neural_lobe.py`, not workarounds in downstream lobes.
4. **Episodes not improving performance?** Check episode relevance in `episode_logger.get_relevant_episodes()` (threshold=0.8 might be too high).
5. **New feature feels "bolted on"?** It probably is. Trace it through the full RIR-RI loop—if any lobe is skipped, rethink the design.

## Avoid Anti-Patterns

- ❌ Calling external LLM APIs or using `transformers` library.
- ❌ Hardcoding ad-hoc fixes per problem; add them to Σ schema or synthesizer templates.
- ❌ Ignoring confidence scores or verification failures silently.
- ❌ Creating new cognitive modes outside `available_modes` in MentalModel.
- ❌ Treating episodes as training data; they're repair signals for iterative synthesis.
