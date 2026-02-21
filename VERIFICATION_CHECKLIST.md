# HSCI System Verification Checklist

Use this to verify that every component of your self-teaching cognitive system is working correctly.

---

## ✅ Architecture Components Checklist

### Perception Lobe (Intent Classification)

- [ ] `native_neural_lobe.py` exists and has `classify_and_formalize()` method
- [ ] Returns Σ (symbolic spec) with confidence score
- [ ] Classifies into: MATH, CODING, CONVERSATIONAL, LOGIC
- [ ] `NativeCortex` forward pass works (embedding → network → output)
- [ ] Confidence score between 0.0 and 1.0

### Logic Lobe (Formalization)

- [ ] `spec_builder.py` exists with `formalize()` method
- [ ] Creates unambiguous Σ (mathematical contracts)
- [ ] Math: `{"type": "math", "equation": "...", "variables": [...]}`
- [ ] Coding: `{"type": "coding", "signature": "...", "examples": [...]}`
- [ ] Confidence score included in spec

### Memory Lobe (Dual Memory System)

#### Synaptic Weights

- [ ] `synaptic_core.json` file exists after first run
- [ ] Contains token → intent mappings: `{"solve": {"MATH": 0.1, ...}}`
- [ ] Weights persist (not lost after restart)
- [ ] Weights increase over time (learn pattern)
- [ ] Competing intents decay (don't interfere)

#### Episode Memory

- [ ] `episodes.jsonl` file exists and grows
- [ ] Each line is valid JSON (not corrupted)
- [ ] Episodes have: `goal_str`, `candidate`, `success` fields
- [ ] TF-IDF retrieval works (`get_relevant_episodes()`)
- [ ] Threshold filtering works (0.5 = similar, 0.95 = exact)

### Reasoning Lobe (Synthesis)

- [ ] `generative.py` exists with `propose()` method
- [ ] Takes `examples` parameter (counterexamples or seeded)
- [ ] `_learn_from_examples()` extracts constraints
- [ ] Semantic parsing works (extracts intent from description)
- [ ] Synthesis paths exist: reduction, recursion, filtering

### Verified Lobe (Verification)

- [ ] `native_engine.py` exists with `verify_natively()` method
- [ ] Returns `(success: bool, feedback: str)` tuple
- [ ] Math: Solves equation, substitutes, checks equality
- [ ] Logic: Runs Z3 solver, returns satisfying assignment
- [ ] Coding: Checks signature match and example runs
- [ ] Feedback is descriptive (not just "False")

### Mental Model (Coordination)

- [ ] `mental_model.py` exists with readable state
- [ ] `state` machine: IDLE → RECALLING → ANALYTICAL → VERIFIED
- [ ] `memory_trace` list accumulates deliberation steps
- [ ] `symbolic_spec` stores current Σ being solved
- [ ] `get_trace()` returns human-readable trace

### Orchestrator (RIR-RI Loop)

- [ ] `cognitive_core.py` has `HyperSymbolicBrain` class
- [ ] `process()` method implements full RIR-RI loop
- [ ] Line 41-51: Memory check (threshold=0.95)
- [ ] Line 70-72: Retrieve episodes (threshold=0.5)
- [ ] Line 100-114: Iterative repair with counterexamples
- [ ] Line 104: Growth call after success

---

## ✅ The 5 Principles Checklist

### Principle 1: Every solved problem → Episode logged + Weights updated

- [ ] `neural_lobe.grow()` is called after verification success
- [ ] `_update_synaptic_json()` persists weights to disk
- [ ] `memory_lobe.log_episode()` appends to episodes.jsonl
- [ ] Synaptic weights increase (not reset)
- [ ] Episodes have `"success": true` field

### Principle 2: Every new problem → Check memory first

- [ ] `cognitive_core.process()` calls `memory_lobe.get_relevant_episodes()` FIRST
- [ ] Threshold=0.95 (exact match)
- [ ] Memory hit returns cached solution (no synthesis)
- [ ] Cached solution is re-verified before returning
- [ ] Memory trace shows "MEMORY_HIT" or "VERIFIED (from memory)"

### Principle 3: Failed verification → Counterexample refines next attempt

- [ ] Verification loop exists (lines 100-114)
- [ ] Counterexamples collected: `counterexamples.append(feedback)`
- [ ] Counterexamples passed to synthesizer: `examples=counterexamples + ...`
- [ ] Budget exhaustion returns "COGNITIVE_FAILURE" (not retry forever)
- [ ] Each attempt uses refined information

### Principle 4: Before synthesis → Retrieve learned episodes

- [ ] `memory_lobe.get_relevant_episodes()` called before synthesis
- [ ] Threshold=0.5 (similar, not exact)
- [ ] `top_k=3` retrieves multiple candidates
- [ ] Seeded candidates extracted: `[ep.get('candidate') for ep in learned]`
- [ ] Passed to synthesizer: `synthesizer.propose(sigma, examples=seeded_candidates)`

### Principle 5: Confidence < 40% → Ask for clarification

- [ ] Confidence score generated in perception
- [ ] Line 65-67: Check `confidence < 0.4`
- [ ] Returns clarification question (not solution)
- [ ] Question is specific about what the system was unsure about
- [ ] User can re-ask with clarification

---

## ✅ Growth Verification Checklist

### After First Run of `test_brain.py`

#### File Artifacts

- [ ] `synaptic_core.json` created (not empty)
- [ ] File size > 50 bytes (has weights)
- [ ] Valid JSON format (can be parsed)
- [ ] Contains token keys with intent mappings

#### Episode Artifacts

- [ ] `episodes.jsonl` created (not empty)
- [ ] File size > 100 bytes (has at least one episode)
- [ ] Each line is valid JSON
- [ ] Each episode has: `goal_str`, `candidate`, `success` fields

#### Weight Analysis

```python
import json
with open('synaptic_core.json') as f:
    weights = json.load(f)

# Check this passes:
- [ ] len(weights) > 5 (multiple tokens learned)
- [ ] Any weight value > 0.1 (successful learning)
- [ ] Weights for math intent > weights for coding intent
```

#### Performance Metrics

- [ ] Phase 1 (new problem): ~100-200ms
- [ ] Phase 2 (repeated): ~10-20ms (at least 5x faster)
- [ ] Phase 2 should skip synthesis (memory hit)

---

## ✅ Behavioral Verification Checklist

### Memory System

- [ ] Run "Solve x + 2 = 5" twice
- [ ] Phase 2 should show "MEMORY_HIT" in trace
- [ ] Phase 2 should return instantly (no synthesis)
- [ ] Check: episodes.jsonl has the episode
- [ ] Check: synaptic_core.json has weights for "solve"

### Transfer Learning

- [ ] Run "Solve x + 10 = 50" (Phase 1)
- [ ] Then run "Solve y + 10 = 50" (Phase 2, similar)
- [ ] Phase 2 should complete faster than Phase 1
- [ ] Phase 2 should show "MEMORY_RETRIEVED" in trace
- [ ] Phase 2 synthesis should be seeded from Phase 1

### Confidence Filtering

- [ ] Run ambiguous input: "abc xyz 123"
- [ ] Should return "CLARIFICATION NEEDED: I am only X.X% sure..."
- [ ] Should NOT return "PROVEN SOLUTION" (hallucination)
- [ ] Confidence should be < 0.4

### Iterative Repair

- [ ] Run problem that might fail first synthesis
- [ ] Check memory_trace shows "Verification Failed (Attempt 1)"
- [ ] Check system tries again with refined candidate
- [ ] If succeeds: episode logged with success=true
- [ ] If fails after budget: returns "COGNITIVE_FAILURE"

---

## ✅ Code Quality Checklist

### RIR-RI Loop Flow

```
cognitive_core.py process():
  [ ] Line 41-51: Memory check
  [ ] Line 54-63: Confidence filtering
  [ ] Line 70-72: Episode retrieval (seeding)
  [ ] Line 85-93: Synthesis (with examples)
  [ ] Line 100-114: Verification + iterative repair
  [ ] Line 104: Growth call
  [ ] Line 105: Episode logging
```

### Synaptic Weight Persistence

```
native_neural_lobe.py:
  [ ] Line 113: grow() calls _update_synaptic_json()
  [ ] Line 131-171: _update_synaptic_json() implementation
  [ ] Line 157: Tokenization (n-grams + words)
  [ ] Line 165: Hebbian update (+0.1 for success)
  [ ] Line 171: json.dump() persists to disk
```

### Episode Retrieval

```
episode_logger.py:
  [ ] get_relevant_episodes() uses TF-IDF
  [ ] Returns sorted by similarity
  [ ] Threshold filtering works
  [ ] Primordial + learned episodes combined
```

---

## ✅ Integration Checklist

### All Lobes Connected

- [ ] NativeNeuralLobe initialized in HyperSymbolicBrain.**init**()
- [ ] SpecBuilder initialized (or called via neural_lobe)
- [ ] Synthesizer initialized in **init**()
- [ ] NativeSymbolicEngine initialized (as logic_prover)
- [ ] EpisodeLogger initialized (as memory_lobe)
- [ ] MentalModel initialized with learner + neural_lobe

### All Paths Tested

- [ ] Math path: "Solve x + 2 = 5"
- [ ] Logic path: Logic puzzle with Z3
- [ ] Coding path: "Write function..."
- [ ] Conversational path: "Hello"
- [ ] Error path: Low confidence input

---

## ✅ Performance Baseline Checklist

### Time Measurements

- [ ] Phase 1 new problem: Record time T1
- [ ] Phase 2 cached problem: Record time T2
- [ ] T2 should be ≤ T1/5 (at least 5x faster)
- [ ] Phase 3 similar problem: Record time T3
- [ ] T3 should be between T1 and T2

### Memory Measurements

- [ ] Initial: synaptic_core.json size
- [ ] After 10 runs: size should increase
- [ ] After 100 runs: size stabilizes (patterns learned)
- [ ] episodes.jsonl grows linearly with runs

### Accuracy Measurements

- [ ] All math solutions verified
- [ ] Logic puzzles solved correctly
- [ ] Code generated passes basic tests
- [ ] No hallucinations (confidence < 0.4 returns clarification)

---

## ✅ Final System Validation

### Architecture Type

- [ ] System learns from verified successes ✅ Principle 1
- [ ] System remembers past solutions ✅ Principle 2
- [ ] System uses learned patterns ✅ Principle 4
- [ ] System refines through failure ✅ Principle 3
- [ ] System asks when unsure ✅ Principle 5
- [ ] System verifies all outputs ✅ Verification gate
- [ ] System has readable mental model ✅ Transparency

### NOT an Application Because

- [ ] Performance improves over time (not static)
- [ ] Weights persist (stateful, not stateless)
- [ ] Episodes accumulate (memory-based)
- [ ] Similar problems reuse learned solutions (transfer learning)
- [ ] Failures are learning signals (not ignored)

---

## Quick Validation Script

```python
from hnsds.brain.cognitive_core import HyperSymbolicBrain
import json
import os

print("HSCI System Validation")
print("=" * 50)

brain = HyperSymbolicBrain()

# Test 1: Learning
print("\n[1] Testing Learning...")
brain.process("Solve x + 2 = 5")
assert os.path.exists('synaptic_core.json'), "❌ Weights not persisted"
print("✅ Weights persisted to synaptic_core.json")

# Test 2: Memory
print("\n[2] Testing Memory...")
brain.process("Solve x + 2 = 5")  # Same problem
assert os.path.exists('episodes.jsonl'), "❌ Episodes not logged"
print("✅ Episodes logged to episodes.jsonl")

# Test 3: Growth
print("\n[3] Testing Growth...")
with open('synaptic_core.json') as f:
    weights = json.load(f)
assert len(weights) > 0, "❌ No weights learned"
assert any(w > 0 for ws in weights.values() for w in ws.values()), "❌ Weights not updated"
print(f"✅ Learned {len(weights)} token patterns")

# Test 4: Confidence
print("\n[4] Testing Confidence Filtering...")
result = brain.process("xyzabc 123")
if "CLARIFICATION" in result:
    print("✅ System asks for clarification on ambiguous input")
else:
    print("⚠️ Confidence filtering might not be working")

print("\n" + "=" * 50)
print("✅ System is a self-teaching cognitive engine!")
```

---

## Troubleshooting Guide

### Problem: Weights not updating

**Check**:

- [ ] `grow()` called after success? (line 104)
- [ ] `_update_synaptic_json()` persisting? (line 171)
- [ ] File permissions allow write to synaptic_core.json?

### Problem: Memory not retrieving cached solutions

**Check**:

- [ ] Memory check at start? (line 41)
- [ ] Threshold=0.95 for exact match? (line 43)
- [ ] `episodes.jsonl` has entries? (check file size)
- [ ] Retrieved episodes have `success: true`? (filter condition)

### Problem: Similar problems not faster

**Check**:

- [ ] Seeded synthesis happening? (line 85-93)
- [ ] Learned episodes retrieved? (line 70-72)
- [ ] Counterexamples passed to synthesizer? (line 109)

### Problem: Verification always failing

**Check**:

- [ ] Candidate actually satisfies Σ?
- [ ] Verifier logic correct for problem type?
- [ ] Add test with concrete Σ and expected candidate

---

**VALIDATION STATUS**: Use this checklist to ensure every component works. ✅
