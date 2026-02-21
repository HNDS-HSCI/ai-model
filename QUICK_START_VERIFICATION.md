# HSCI System Quick-Start Verification Guide

Run these tests to confirm your system is a **self-teaching cognitive engine**, not just an app.

---

## Test Setup

```bash
cd c:\Work\P\ai
python test_brain.py
```

This will run 4 scenarios that prove the system learns and grows.

---

## What to Verify After Each Test

### **TEST 1: First-Time Problem (Learning Phase)**

**Command**: Inside `test_brain.py`, runs `"Solve x + 2 = 5"`

**What should happen**:

1. ✅ Perception: Classifies as MATH
2. ✅ Memory: No match (new problem)
3. ✅ Synthesis: Generates candidate `x = 3`
4. ✅ Verification: Proves `3 + 2 = 5` ✓
5. ✅ **GROWTH**: Updates `synaptic_core.json`
6. ✅ **LOGGING**: Adds episode to `episodes.jsonl`

**How to verify**:

```bash
# After test runs, check these files exist and were updated:
type synaptic_core.json  # Should have weights like {"solve": {"MATH": 0.1}}
type episodes.jsonl      # Should have episode entry
```

**Expected output from test**:

```
--- TEST 1: INTUITION (Known Problem) ---
PROVEN SOLUTION:
x=3

=== COGNITIVE TRACE (HSCI) ===
[00] STIMULUS: Solve x + 2 = 5
[01] NEURAL_INTUITION: Classified as MATH
[02] USING_INTUITION_SPEC: math
[03] SOLUTION_FINALIZED
```

---

### **TEST 2: Complex New Problem (Deliberation Phase)**

**Command**: Inside `test_brain.py`, runs `"Solve x + y = 30, x - y = 10"`

**What should happen**:

1. ✅ Perception: Classifies as MATH (system type)
2. ✅ Memory: No exact match (new)
3. ✅ Synthesis: Generates candidate for system of equations
4. ✅ Verification: Proves solution ✓
5. ✅ **GROWTH**: Weights now include "system of equations" pattern

**Expected output**:

```
--- TEST 2: DELIBERATION (New Problem) ---
PROVEN SOLUTION:
x = 20, y = 10  (or similar valid solution)
```

---

### **TEST 3: Growth Test (Learning Phase 1)**

**Command**: Inside `test_brain.py`, runs `"Solve x + 10 = 50"`

**What should happen**:

1. ✅ Perception: MATH
2. ✅ Memory: No match (first time)
3. ✅ Synthesis → Verification → **GROWTH**
4. ✅ Solution stored: `x = 40`

**Expected**:

```
--- TEST 3: GROWTH (Phase 1: Learning) ---
PROVEN SOLUTION:
x=40

Brain just solved a new problem and stored it in long-term memory.
```

---

### **TEST 3 Phase 2: Growth Test (Mastery Phase)**

**Command**: Inside `test_brain.py`, runs same problem AGAIN: `"Solve x + 10 = 50"`

**CRITICAL TEST**: This proves the system LEARNED

**What should happen**:

1. ✅ Perception: MATH
2. ✅ **Memory Check**: FINDS EXACT MATCH (threshold=0.95)
3. ✅ **SKIPS SYNTHESIS ENTIRELY**
4. ✅ Returns cached solution instantly

**Expected output**:

```
--- TEST 3: GROWTH (Phase 2: Mastery) ---
Providing the same stimulus again...
VERIFIED (from memory):
x=40

=== COGNITIVE TRACE (HSCI) ===
[00] STIMULUS: Solve x + 10 = 50
[01] MEMORY_HIT: Using cached verified solution
```

**KEY INDICATOR**: If you see "MEMORY_HIT" in Phase 2, the system **LEARNED**. ✅

---

## Manual Verification Tests

### **Test A: Check Synaptic Weights File**

```bash
# After running test_brain.py:
cat synaptic_core.json

# Expected: JSON like:
# {
#   "solve": { "MATH": 0.2, "CODING": 0.0 },
#   "equation": { "MATH": 0.3, "CODING": 0.0 },
#   "solve equation": { "MATH": 0.4, "CODING": 0.0 }
# }
```

**What this proves**:

- Tokens like "solve" and "equation" now have high weights for MATH intent
- Next time you say "solve...", the system recognizes it as MATH with higher confidence
- **System is learning the language of math problems**

---

### **Test B: Check Episode Memory**

```bash
# After running test_brain.py:
type episodes.jsonl

# Expected: Multiple lines, each a JSON episode:
# {"goal_str": "Solve x + 2 = 5", "solution": "x=3", ...}
# {"goal_str": "Solve x + 10 = 50", "solution": "x=40", ...}
```

**What this proves**:

- System stores every solved problem
- TF-IDF retrieval can find similar problems
- **System has long-term episodic memory**

---

### **Test C: Transfer Learning Manual Test**

Run this Python code:

```python
from hnsds.brain.cognitive_core import HyperSymbolicBrain

brain = HyperSymbolicBrain()

# Phase 1: Solve "x + 10 = 50"
result1 = brain.process("Solve x + 10 = 50")
print("Phase 1 (NEW PROBLEM):")
print(result1)
print(f"Memory trace length: {len(brain.mind.memory_trace)}")

print("\n" + "="*50 + "\n")

# Phase 2: Solve similar "y + 10 = 50"
brain2 = HyperSymbolicBrain()
result2 = brain2.process("Solve y + 10 = 50")
print("Phase 2 (SIMILAR PROBLEM - should use seeded synthesis):")
print(result2)
print(f"Memory trace length: {len(brain2.mind.memory_trace)}")

# Phase 2 should have FEWER steps than Phase 1 because it uses learned episodes
if len(brain2.mind.memory_trace) < len(brain.mind.memory_trace):
    print("\n✅ TRANSFER LEARNING CONFIRMED: Similar problem solved faster!")
```

**Expected**: Phase 2 solves faster (fewer deliberation steps)

---

## Checklist: Is This a Self-Teaching System?

After running tests, check these:

- [ ] **Synaptic weights file** (`synaptic_core.json`) was **created/updated**
- [ ] **Episodes file** (`episodes.jsonl`) contains **multiple entries**
- [ ] **Phase 2 output** shows **"VERIFIED (from memory)"** (not re-synthesis)
- [ ] **Memory trace** shows **"MEMORY_HIT"** on repeated problems
- [ ] **Weights increase** with each successful solve (Hebbian learning visible)

---

## If Tests Fail, Check These:

### ❌ **Weights not updating**

**Check**: `native_neural_lobe.py` line 156 - is `json.dump(weights, f)` being called?

```python
with open(self.weight_path, 'w') as f:
    json.dump(weights, f, indent=2)  # Must persist
```

### ❌ **Memory not retrieving cached solutions**

**Check**: `cognitive_core.py` line 41 - is memory check BEFORE synthesis?

```python
recalled = self.memory_lobe.get_relevant_episodes(stimulus, top_k=1, threshold=0.95)
if recalled and recalled[0].get('success'):
    # Must return here, skip synthesis
```

### ❌ **Counterexamples not refining**

**Check**: `cognitive_core.py` line 109 - are counterexamples passed to synthesizer?

```python
candidate = self.synthesizer.propose(sigma, examples=counterexamples + seeded_candidates)
```

### ❌ **Growth not called**

**Check**: `cognitive_core.py` line 104 - is `grow()` called after success?

```python
if success:
    self.neural_lobe.grow(stimulus, sigma, sigma.get("type"))  # Must happen
```

---

## Performance Expectations

### First Problem: "Solve x + 2 = 5"

- **Steps**: Perceive → Formalize → Synthesize → Verify → Grow → Log
- **Time**: ~100-200ms
- **Trace length**: ~5-7 steps

### Repeated Problem: "Solve x + 2 = 5" (second time)

- **Steps**: Perceive → Memory Hit → Verify Cached → Return
- **Time**: ~10-20ms (10x faster)
- **Trace length**: ~3 steps

### Similar Problem: "Solve y + 2 = 5"

- **Steps**: Perceive → Memory Retrieval (seeded) → Synthesize → Verify → Return
- **Time**: ~50-100ms (faster than first)
- **Trace length**: ~4-6 steps

---

## System is Working If:

✅ Repeated problems return **"VERIFIED (from memory)"**  
✅ Similar problems complete **faster** than first time  
✅ **synaptic_core.json** grows in size and weight values increase  
✅ **episodes.jsonl** accumulates new entries  
✅ Memory trace shows **different cognitive states** (RECALLING vs ANALYTICAL vs VERIFIED)  
✅ **No external API calls** happen (all local, native reasoning)

---

## Next: Advanced Testing

### Test Failed Synthesis Recovery

```python
# Problem that might fail first attempt
brain.process("Write a function to sum all even numbers in a list")
# Check: Does it iterate on failure? Check memory_trace for "Attempt 2"
```

### Test Confidence Filtering

```python
# Ambiguous problem
brain.process("xyz abc 123")
# Expected: "CLARIFICATION NEEDED: I am only X.X% sure..."
# NOT: "PROVEN SOLUTION" (hallucination)
```

### Test Cross-Domain Learning

```python
# Phase 1: Solve math
brain.process("Solve x + 2 = 5")

# Phase 2: Similar pattern in coding
brain.process("Write code: if x + 2 == 5: print('yes')")
# Check: Does synthesizer use insights from Phase 1?
```

---

**Status**: Run `test_brain.py` and check for MEMORY_HIT on Phase 2. If you see it, your system is **learning**. 🧠
