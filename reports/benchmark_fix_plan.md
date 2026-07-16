# HSCI Benchmark Framework Fix Plan (V2)

## Context
The V1 Benchmark Framework successfully established the *scaffolding* for testing, but failed to provide the *mathematical complexity* required to genuinely stress-test LLM attention mechanisms versus HSCI's symbolic Z3 SMT solver. This report outlines the fundamental flaws in V1 and provides the production-ready code to upgrade to Framework V2.

---

## Part 1: Weakness Identification

### 1. Constraint Verification
*   **Weakness:** The generated constraints were isolated. Example: `E0 capacity is 500`. 
*   **Why it fails to test HSCI:** An LLM can hold this single variable in attention. It does not require *constraint propagation* (e.g., if E0 drops capacity, E1 must increase, which triggers a global rule capping E1+E2, which fails because E2 is locked).

### 2. Requirements Analysis
*   **Weakness:** Contradictions were localized to adjacent sentences (`Req1: Admin full access. Req2: Admin no access.`).
*   **Why it fails to test HSCI:** This is basic semantic similarity mapping. True requirements analysis requires multi-hop logical deductions where Rule A implies Rule B, and Rule C limits Rule D, creating an implicit contradiction between B and D.

### 3. Architecture Planning
*   **Weakness:** 3-node linear graphs (`DB -> API -> UI`).
*   **Why it fails to test HSCI:** LLMs have seen millions of 3-tier architecture diagrams in their training data. They answer correctly via pattern recognition, not topological planning.

### 4. State Machine Verification
*   **Weakness:** Simple linear transitions (`NEW -> PROCESSING -> SHIPPED`).
*   **Why it fails to test HSCI:** No conditional paths. Real workflows have recovery states (e.g., `PAYMENT_FAILED -> RETRY_QUEUE -> MANUAL_REVIEW`), terminal constraints, and forbidden recursive loops.

### 5. Dependency Resolution
*   **Weakness:** Shallow 3-node cycles.
*   **Why it fails to test HSCI:** LLMs can easily track an `A->B->C->A` loop. They fail when a cycle spans 20 transitive layers in a 100-node package graph.

---

## Part 2: Exact Code Changes

### Fix: Scoring Logic

**Old Code:**
```python
# Fails because "INVALID" contains "VALID"
is_correct = task["expected"].lower() in str(output).lower()
```
*Reasoning for failure:* Simple substring matching cannot distinguish overlapping keywords.

**New Code:**
```python
import re

def score_output(expected_keyword, llm_output):
    """
    Uses regex word boundaries to ensure exact token matching.
    Prevents 'INVALID' from triggering a false positive for 'VALID'.
    """
    pattern = r'\b' + re.escape(expected_keyword.upper()) + r'\b'
    # Find all matching uppercase boundary words
    matches = re.findall(pattern, str(llm_output).upper())
    
    # Optional strictness: Fail if the model outputs conflicting answers
    # e.g., "The sequence is INVALID, but it could be VALID_ORDER"
    return len(matches) > 0
```
*Reasoning for fix:* Using `\b` (word boundary) ensures that `VALID` is only matched if it is standalone, completely resolving Issue 1.

---

## Part 3: Improved Benchmark Generators (V2 Concept)

To defeat LLM pattern recognition, the generators must create complex, overlapping constraints. Below is the upgraded approach for **Architecture Planning** that introduces regional limits, deep trees, and cyclic logic.

```python
import random

def generate_v2_architecture_planning(nodes=50):
    """
    Generates a 50+ node architecture with multi-region constraints
    and forced cyclic dependency checks.
    """
    regions = ["us-east-1", "eu-west-1", "ap-south-1"]
    prompt = "ENTERPRISE DEPLOYMENT MANIFEST:\n"
    
    # 1. Assign services to regions
    services = {}
    for i in range(nodes):
        reg = random.choice(regions)
        services[f"S{i}"] = reg
        prompt += f"Service S{i} must deploy in {reg}.\n"
        
    # 2. Generate Deep Dependencies (DAG)
    prompt += "\nDEPENDENCY RULES:\n"
    for i in range(1, nodes):
        # S_i depends on a randomly chosen lower S_j
        dep = random.randint(0, i-1)
        prompt += f"S{i} requires S{dep} to be healthy.\n"
        
    # 3. Add Cross-Region Constraints (Constraint Interaction)
    prompt += "\nCOMPLIANCE RULES:\n"
    prompt += "Rule 1: Services in eu-west-1 CANNOT depend on services in us-east-1 due to GDPR.\n"
    
    # 4. Inject Violations (Edge Cases)
    prompt += "\nPROPOSED DEPLOYMENT GRAPH:\n"
    
    expected = "VALID_ORDER"
    # Artificially inject a GDPR violation or Cycle
    if random.choice([True, False]):
        prompt += f"S{nodes-1} (in eu-west-1) now requires S0 (in us-east-1).\n"
        expected = "INVALID_ORDER"
    
    prompt += "\nEvaluate topology. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER."
    return prompt, expected
```

---

## Part 4: Production-Ready Scoring Logic

Replace the loop inside `run_benchmarks.py` with this production-ready extraction and scoring block:

```python
import re

def evaluate_run(task, output):
    expected = task["expected"].upper()
    response = str(output).upper()
    
    # Extract known keywords to check for contradictions
    valid_keywords = [
        "VALID", "INVALID", "CONTRADICTION", 
        "CONSISTENT", "INCONSISTENT", "MISSING_REQUIREMENT",
        "VALID_ORDER", "CYCLIC_DEPENDENCY", "INVALID_ORDER"
    ]
    
    found_keywords = []
    for kw in valid_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', response):
            found_keywords.append(kw)
            
    # Strict Evaluation Rules:
    # 1. Expected keyword must be found.
    # 2. NO OTHER conflicting keywords can be present.
    if expected in found_keywords and len(found_keywords) == 1:
        return True
    return False
```

---

## Part 5: Benchmark Framework V2 Migration Plan

### Step 1: Replace Generators
Delete `generate_research_tasks.py`. Create `generate_v2_tasks.py` implementing the complex graph logic (N=50+ nodes) across all 5 categories.

### Step 2: Implement Regex Scoring
Apply the `evaluate_run` regex scoring function to `run_benchmarks.py` to eliminate false positives.

### Step 3: Deprecate V1
Delete the `/benchmarks/research_grade/` folder entirely. Overwrite the root `/benchmarks/` folder with the V2 JSONs to maintain a single source of truth.

---

## Final Strategic Questions

**1. Which benchmark category should be improved first?**
**Architecture Planning (and Dependency Resolution).** Topological sorting of DAGs is mathematically impossible for an LLM to "fake" when N > 50. It explicitly proves the necessity of HTN planners and SMT solvers.

**2. Which benchmark category should be removed?**
**Requirements Analysis.** Natural language is inherently ambiguous. Translating corporate requirements into formal SMT-LIB constraints requires an intermediary neural step. If the neural step fails parsing the English, Z3 fails the proof. The benchmark tests the *NLP parser*, not the *Symbolic Engine*.

**3. Which benchmark category should receive the most engineering effort?**
**State Machine Verification.** Modeling multi-state workflows with conditional, time-bounded, and recovery transitions is the ultimate test of "hallucination-free" execution. If HSCI can perfectly validate a 100-state payment gateway DFA, it is instantly viable as a commercial B2B compliance tool.

**4. What changes are required before running HSCI vs GPT comparisons?**
1. **Regex Scoring:** Implement the strict `\b` regex boundary scoring immediately. The current tests are producing false positives.
2. **Complexity Floor:** Ensure absolutely zero tasks contain fewer than 20 interconnected entities.
3. **Timeout Controls:** HSCI's Z3 solver will experience exponential time complexity on complex constraints. You must implement a hard 15-second timeout in the benchmark runner, or HSCI will hang indefinitely while GPT returns in 2 seconds.
