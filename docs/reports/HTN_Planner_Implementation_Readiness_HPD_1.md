# HSCI V5 — Phase 4A: HTN Planner Implementation Readiness & Design Audit (HPD-1)

**Version**: 1.0  
**Status**: Authoritative Technical Design & Implementation Readiness Audit  
**Authority**: Principal Cognitive Architecture Engineer, HSCI V5  
**Scope**: Read-Only Analysis & Architectural Design (Zero Code Modifications)  

---

## 1. Executive Summary

This report delivers **HTN_Planner_Implementation_Readiness_HPD_1**, the authoritative technical audit and structural design for **Phase 4A: Genuine Hierarchical Task Network (HTN) Planning**.

### Primary Findings:
1. **Existing Planner Audit**: The current planning codebase contains two distinct implementations:
   * [`hnsds/brain/lobes/native_planner.py`](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_planner.py): A Jaccard similarity keyword matcher over `skills.json` template strings.
   * [`hsci/reasoning/htn_planner.py`](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py): A static dictionary lookup (`DECOMPOSITION_RULES`) mapping an `AxiomType` enum directly to a flat, 3-or-4 element array of `SubGoal` objects.
2. **HTN Classification Verdict**: **Neither implementation is a genuine HTN planner**. There is no recursive goal decomposition, no method precondition/postcondition evaluation, no search tree expansion, no state tracking, no backtracking on failure, and no Z3 validation during plan synthesis.
3. **Target Design Strategy**: We design a native, verification-first HTN planning algorithm that extends [`hsci/reasoning/htn_planner.py`](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py). The new planner will recursively expand compound tasks into primitive operators, validate method preconditions against request-scoped `WorkingMemory` state, interface with Z3 for precondition satisfiability checks, and output a structured `PlanningFailure` payload upon exhaustion to feed Phase 4B (Reflection Engine).
4. **Implementation Constraints**: Strictly zero code modifications are executed during this audit. Rust porting, multi-node clustering (Raft/Kafka), and PostgreSQL migrations are explicitly excluded from Phase 4A.

---

## 2. Existing Planner Architecture & Code Audit

The repository contains two historical layers of planning logic:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. LEGACY PROTOTYPE PLANNER: native_planner.py                                         │
│    • Method: _find_best_skill(goal_desc)                                              │
│    • Mechanism: Tokenizes string using NativeGraph synonyms, computes Jaccard similarity  │
│      against tags in `hnsds/brain/knowledge/skills.json`.                             │
│    • Output: Returns raw template code string or `# TODO: Implement ...` fallback.     │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. REASONING ENGINE PLANNER: hsci/reasoning/htn_planner.py                              │
│    • Method: decompose(perception: PerceptionMap) -> List[SubGoal]                     │
│    • Mechanism: Static map lookup (DECOMPOSITION_RULES[perception.intent]).            │
│    • Output: Returns static array of 3 or 4 SubGoal objects (e.g. BUILD_EQUATION).     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why Current Implementations Are Not Genuine HTN Planners:
* **No Hierarchy or Recursion**: `htn_planner.py` performs a single, non-recursive dictionary lookup. SubGoals are never further decomposed into finer sub-tasks.
* **No Preconditions / Postconditions**: Tasks lack state predicates. The planner cannot evaluate whether `BUILD_EQUATION` is valid given the current environment state.
* **No Alternative Methods**: There are no alternative branches or search tree choices for achieving a goal.
* **No Backtracking**: If a step fails, the system cannot backtrack to select an alternative method.
* **No Dynamic Verification**: Z3 logic checking is invoked *after* planning in `ReasoningEngine`, rather than verifying candidate decompositions *during* plan generation.

---

## 3. HSCI HTN Domain Model Design

To align with HSCI's cognitive architecture (`RCA-1`, `ECA-1`, `VVA-1`), the HTN domain model will be defined using clean data structures:

```python
# Types to be defined in hsci/core/data_types.py / hsci/reasoning/htn_planner.py

class TaskType(Enum):
    COMPOUND = "COMPOUND"    # Requires HTN decomposition via Method selection
    PRIMITIVE = "PRIMITIVE"  # Executable operator (maps directly to CRE/Z3 action)

@dataclass
class Task:
    id: str
    name: str
    task_type: TaskType
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Precondition:
    predicate: str           # e.g., "KNOWN_ENTITY" or "Z3_SATISFIABLE"
    required_state: Any

@dataclass
class Postcondition:
    effect_key: str          # e.g., "EQUATION_BUILT"
    resulting_state: Any

@dataclass
class Method:
    id: str
    target_task_name: str    # Compound task this method satisfies
    preconditions: List[Precondition]
    subtasks: List[Task]     # Ordered sequence of sub-tasks
    cost: float = 1.0

@dataclass
class Operator:
    id: str
    primitive_task_name: str
    preconditions: List[Precondition]
    postconditions: List[Postcondition]
    execution_handler: str   # Function name in CRE/Z3Verifier
```

---

## 4. Proposed HTN Algorithm & Execution Flow

The genuine HTN algorithm follows a recursive task-network reduction model with depth-budget protection and Z3 constraint checking:

```
                          [ Input Goal Task ]
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Is Task PRIMITIVE or         │
                   │  COMPOUND?                    │
                   └───────────────┬───────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                │ COMPOUND                            │ PRIMITIVE
                ▼                                     ▼
   ┌───────────────────────────┐         ┌───────────────────────────┐
   │ Find Applicable Methods   │         │ Validate Operator         │
   │ (Evaluate Preconditions)  │         │ Preconditions via Z3      │
   └────────────┬──────────────┘         └────────────┬──────────────┘
                │                                     │
                ▼                                     ▼
   ┌───────────────────────────┐         ┌───────────────────────────┐
   │ Select Method & Expand    │         │ Append to Executable Plan │
   │ Subtasks (Recurse)        │         └───────────────────────────┘
   └────────────┬──────────────┘
                │ (If Precondition / Z3 fails)
                ▼
   ┌───────────────────────────┐
   │ Backtrack to Next Method  │
   │ (If all fail -> Failure)  │
   └───────────────────────────┘
```

### Depth & Cycle Safeguards (OPA-1 Compliant):
* **Max Decomposition Depth**: Capped at `10` recursive levels.
* **Max Branching Limit**: Capped at `5` alternative methods per compound task.
* **Cycle Detection**: Tracks visited `(Task.id, Method.id)` tuples in the active recursion stack; throws a `CycleDetected` error if repeated.
* **Time Budget**: Overall planning loop bound to a `50ms` execution budget.

---

## 5. Z3 Verification & WorkingMemory Integration

### Z3 Integration Boundary:
1. **Precondition Proving**: Before selecting a candidate `Method` or executing a primitive `Operator`, candidate preconditions (e.g. $x + y = z$ variable consistency) are sent to `Z3VerificationEngine`.
2. **Branch Pruning**: If Z3 returns `UNSAT`, the candidate Method is immediately marked invalid without expanding its child nodes, pruning dead-end search paths.

### WorkingMemory Integration (Request-Scoped):
The HTN planning state will be encapsulated inside `WorkingMemory.planner_context`:
* `active_task_stack`: `List[Task]` (Current unexpanded task queue).
* `chosen_plan_nodes`: `List[Task]` (Accepted primitive actions).
* `explored_methods`: `Set[str]` (Visited method IDs for backtracking).
* `failure_log`: `Optional[PlanningFailure]` (Structured failure trace for Phase 4B Reflection).

---

## 6. Reflection Boundary (Preparing for Phase 4B)

When all candidate methods for a compound task fail, the HTN planner creates a structured `PlanningFailure` payload:

```python
@dataclass
class PlanningFailure:
    failed_task_id: str
    failed_task_name: str
    attempted_methods: List[str]
    failed_precondition: Optional[str]
    z3_counterexample: Optional[Dict[str, Any]]
    depth_reached: int
    reason: str  # "UNSATISFIABLE_PRECONDITION", "CYCLE_DETECTED", "MAX_DEPTH_EXCEEDED"
```

This failure object is attached to `WorkingMemory` so that the Phase 4B **Reflection Engine** can analyze the exact cause of failure and update Hebbian weights or issue diagnostic hints.

---

## 7. Preserve / Extend / Refactor / Replace Matrix

| Module / File | Action | Rationale |
|---|---|---|
| [`hsci/reasoning/htn_planner.py`](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py) | **EXTEND** | Upgrade from static dict lookup to full recursive HTN tree search. Preserve backwards compatibility for legacy `AxiomType` inputs. |
| [`hnsds/brain/lobes/native_planner.py`](file:///C:/Work/P/ai-model/hnsds/brain/lobes/native_planner.py) | **PRESERVE** | Keep intact as the prototype reference skill template matcher. |
| [`hsci/core/data_types.py`](file:///C:/Work/P/ai-model/hsci/core/data_types.py) | **EXTEND** | Add `Task`, `Method`, `Operator`, `Precondition`, `Postcondition`, and `PlanningFailure` data classes. |
| [`hsci/reasoning/reasoning_engine.py`](file:///C:/Work/P/ai-model/hsci/reasoning/reasoning_engine.py) | **EXTEND** | Pass `WorkingMemory` context into `htn_planner.decompose()` and execute returned primitive plans. |
| [`hsci/tests/test_htn_planner.py`](file:///C:/Work/P/ai-model/hsci/tests/test_htn_planner.py) | **EXTEND** | Retain existing 5 unit tests; add 6 new tests for multi-level decomposition, backtracking, cycle detection, and Z3 rejection. |

---

## 8. File-by-File Implementation Map for Phase 4A

### Step 1: Data Model Extension
* **Target**: [`hsci/core/data_types.py`](file:///C:/Work/P/ai-model/hsci/core/data_types.py)
* **Changes**: Define `TaskType`, `Task`, `Method`, `Operator`, `Precondition`, `Postcondition`, and `PlanningFailure`.

### Step 2: HTN Domain & Method Registry
* **Target**: [`hsci/reasoning/htn_planner.py`](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py)
* **Changes**: Build `MethodRegistry` and `OperatorRegistry` populated with multi-step domain rules (for `REDUCTION`, `COMPOSITION`, `SYNTHESIS`, `TRANSFORMATION`).

### Step 3: Recursive Decomposition Engine
* **Target**: [`hsci/reasoning/htn_planner.py`](file:///C:/Work/P/ai-model/hsci/reasoning/htn_planner.py)
* **Changes**: Implement `_decompose_task_recursive()` with backtracking, depth check ($\le 10$), cycle tracking, and Z3 precondition validation hooks.

### Step 4: ReasoningEngine Integration
* **Target**: [`hsci/reasoning/reasoning_engine.py`](file:///C:/Work/P/ai-model/hsci/reasoning/reasoning_engine.py)
* **Changes**: Update `CRE.process()` to pass `WorkingMemory` into `htn_planner.decompose_recursive()` and handle `PlanningFailure` gracefully.

### Step 5: Test Suite Expansion
* **Target**: [`hsci/tests/test_htn_planner.py`](file:///C:/Work/P/ai-model/hsci/tests/test_htn_planner.py)
* **Changes**: Add multi-level recursive decomposition, backtracking, depth limit, and Z3 rejection test cases.

---

## 9. Exact Implementation Tasks (Sequence for Execution)

* **HP4A-01**: Extend `hsci/core/data_types.py` with `Task`, `Method`, `Operator`, and `PlanningFailure` dataclasses.
* **HP4A-02**: Implement `MethodRegistry` and `OperatorRegistry` in `hsci/reasoning/htn_planner.py`.
* **HP4A-03**: Implement core recursive task decomposition algorithm in `hsci/reasoning/htn_planner.py`.
* **HP4A-04**: Implement backtracking and cycle detection logic in `hsci/reasoning/htn_planner.py`.
* **HP4A-05**: Connect Z3 precondition verification hooks to `htn_planner.py`.
* **HP4A-06**: Integrate request-scoped state tracking with `WorkingMemory`.
* **HP4A-07**: Update `ReasoningEngine` (`hsci/reasoning/reasoning_engine.py`) to invoke recursive decomposition.
* **HP4A-08**: Author multi-level HTN unit tests in `hsci/tests/test_htn_planner.py`.
* **HP4A-09**: Execute `pytest` across all 206+ tests to verify zero regressions.

---

## 10. Phase 4A Definition of Done

1. **Multi-Level Decomposition**: Planner successfully decomposes a top-level compound task into at least 2 levels of sub-tasks down to primitive operators.
2. **Backtracking & Verification**: Planner backtracks to an alternative method when Z3 rejects a method precondition.
3. **Structured Failure Output**: Emits a valid `PlanningFailure` payload when search space is exhausted.
4. **Safety Limits**: Capped at depth 10 with cycle detection and sub-50ms execution budget.
5. **Zero Regressions**: All existing 206 pytest unit/integration tests pass without failures.

---

## 11. Answers to Final Required Questions

1. **What does the existing planner actually do?**  
   It performs either a keyword Jaccard similarity search (`native_planner.py`) or a static map lookup based on `AxiomType` (`htn_planner.py`) returning a flat list of 3–4 sub-goals.

2. **Why is it not yet a genuine HTN planner?**  
   It lacks recursive task reduction, method preconditions/postconditions, alternative search branches, backtracking, and inline Z3 precondition validation.

3. **Which existing code should be reused?**  
   `hsci/reasoning/htn_planner.py` (to be extended), `SubGoal`/`AxiomType` data structures, and `Z3VerificationEngine`.

4. **Which code must change?**  
   `hsci/reasoning/htn_planner.py` (upgraded to recursive search) and `hsci/reasoning/reasoning_engine.py` (to call recursive decomposition).

5. **What new code is genuinely necessary?**  
   `Task`, `Method`, `Operator`, and `PlanningFailure` dataclasses in `hsci/core/data_types.py` plus method/operator registries in `htn_planner.py`.

6. **What exact data model should represent HTN tasks/methods/plans?**  
   Typed dataclasses (`Task`, `Method`, `Operator`, `Precondition`, `Postcondition`, `PlanningFailure`).

7. **How should recursive decomposition work?**  
   A stack-based or recursive function (`_decompose_task_recursive`) that checks task types; if compound, it iterates over applicable methods, evaluates preconditions, and recursively expands child sub-tasks.

8. **How should backtracking work?**  
   If child decomposition or Z3 precondition verification fails, the algorithm pops state, restores `WorkingMemory.planner_context`, and attempts the next applicable `Method`.

9. **Where should Z3 verification occur?**  
   During method selection (evaluating preconditions) and primitive operator execution validation.

10. **How does WorkingMemory participate?**  
    It stores the active task stack, chosen plan nodes, explored method IDs, and any resulting `PlanningFailure` payload.

11. **What structured failures must be exposed for future Reflection?**  
    `PlanningFailure` containing `failed_task_name`, `attempted_methods`, `failed_precondition`, `z3_counterexample`, and failure `reason`.

12. **What exact tests prove we have a genuine HTN planner?**  
    Tests verifying 2+ level recursive tree expansion, alternative method backtracking, cycle detection abortion, and Z3 precondition rejection.

13. **What is the FIRST implementation task after HPD-1?**  
    **Task HP4A-01**: Extend `hsci/core/data_types.py` with `Task`, `Method`, `Operator`, and `PlanningFailure` dataclasses.
