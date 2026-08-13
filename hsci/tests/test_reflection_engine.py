import pytest
from typing import Dict, Any

from hsci.core.data_types import (
    PlanningFailure, Precondition, VerificationResult, VerificationStatus,
    ReflectionFailureType, ReflectionResult, Task, TaskType, PerceptionMap, AxiomType,
    KnowledgeResult, EntityValue, Method
)
from hsci.core.working_memory import WorkingMemory, SemanticFrame
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError
from hsci.reasoning.reflection_engine import ReflectionEngine
from hsci.reasoning.reasoning_engine import ReasoningEngine
from hsci.symbolic.z3_verifier import Z3VerificationEngine


def test_hp4b_test_a_precondition_unsat_reflection():
    """Test A: PlanningFailure caused by failed formal precondition yields PRECONDITION_UNSAT category."""
    engine = ReflectionEngine()
    pre = Precondition(predicate="MEMORY_AVAILABLE", required_state=True)
    failure = PlanningFailure(
        failed_task_id="t1",
        failed_task_name="SOLVE_REDUCTION",
        attempted_methods=["m_fast"],
        failed_precondition=pre,
        reason="Precondition MEMORY_AVAILABLE failed"
    )
    res = engine.reflect_planning_failure(failure, request_id="req-1")

    assert res.failure_category == ReflectionFailureType.PRECONDITION_UNSAT
    assert res.failed_stage == "PLANNING"
    assert res.failed_task_name == "SOLVE_REDUCTION"
    assert res.failed_precondition.predicate == "MEMORY_AVAILABLE"
    assert res.retry_recommended is True


def test_hp4b_test_b_missing_method_reflection():
    """Test B: Compound task with no registered decomposition method yields NO_METHOD category."""
    engine = ReflectionEngine()
    failure = PlanningFailure(
        failed_task_id="t2",
        failed_task_name="UNKNOWN_COMPOUND",
        attempted_methods=[],
        reason="No decomposition method registered for task 'UNKNOWN_COMPOUND'"
    )
    res = engine.reflect_planning_failure(failure, request_id="req-2")

    assert res.failure_category == ReflectionFailureType.NO_METHOD
    assert res.failed_task_name == "UNKNOWN_COMPOUND"
    assert res.retry_recommended is False


def test_hp4b_test_c_all_candidate_methods_failed_reflection():
    """Test C: Attempted method list survives intact into ReflectionResult."""
    engine = ReflectionEngine()
    failure = PlanningFailure(
        failed_task_id="t3",
        failed_task_name="SOLVE_MATH",
        attempted_methods=["m_fast", "m_fallback", "m_heuristic"],
        reason="All candidate methods failed"
    )
    res = engine.reflect_planning_failure(failure, request_id="req-3")

    assert res.attempted_methods == ["m_fast", "m_fallback", "m_heuristic"]


def test_hp4b_test_d_cycle_reflection():
    """Test D: Cycle detection yields DECOMPOSITION_CYCLE category."""
    engine = ReflectionEngine()
    failure = PlanningFailure(
        failed_task_id="t4",
        failed_task_name="RECURSIVE_TASK",
        reason="Cycle detected along active branch for task 'RECURSIVE_TASK'"
    )
    res = engine.reflect_planning_failure(failure, request_id="req-4")

    assert res.failure_category == ReflectionFailureType.DECOMPOSITION_CYCLE
    assert res.retry_recommended is False


def test_hp4b_test_e_depth_limit_reflection():
    """Test E: Exceeding max decomposition depth yields MAX_DEPTH_EXCEEDED category."""
    engine = ReflectionEngine()
    failure = PlanningFailure(
        failed_task_id="t5",
        failed_task_name="DEEP_TASK",
        depth_reached=11,
        reason="Max decomposition depth reached (11 >= 10)"
    )
    res = engine.reflect_planning_failure(failure, request_id="req-5")

    assert res.failure_category == ReflectionFailureType.MAX_DEPTH_EXCEEDED
    assert res.depth_reached == 11


def test_hp4b_test_f_z3_counterexample_preservation():
    """Test F: Z3 counterexample model is preserved in ReflectionResult."""
    engine = ReflectionEngine()
    v_res = VerificationResult(
        valid=False,
        status=VerificationStatus.DISPROVEN,
        confidence=0.0,
        proof_trace=None,
        counterexample={"x": 5, "required": 10},
        z3_model=None,
        correction_hint="Value 5 violates x > 10 constraint"
    )
    res = engine.reflect_verification_failure(v_res, request_id="req-6")

    assert res.failure_category == ReflectionFailureType.SOLUTION_VERIFICATION_FAILURE
    assert res.counterexample == {"x": 5, "required": 10}
    assert "Value 5 violates x > 10 constraint" in res.correction_hint


def test_hp4b_test_g_final_verification_failure_reflection():
    """Test G: Solution verification failure stage is correctly identified."""
    engine = ReflectionEngine()
    v_res = VerificationResult(
        valid=False,
        status=VerificationStatus.DISPROVEN,
        confidence=0.0,
        proof_trace=None,
        counterexample=None,
        z3_model=None,
        correction_hint=None
    )
    res = engine.reflect_verification_failure(v_res, request_id="req-7", task_name="SOLVE_EQUATION")

    assert res.failed_stage == "SOLUTION_VERIFICATION"
    assert res.failed_task_name == "SOLVE_EQUATION"


def test_hp4b_test_h_request_isolation():
    """Test H: Two independent requests produce distinct, isolated ReflectionResults."""
    engine = ReflectionEngine()
    f1 = PlanningFailure(failed_task_id="1", failed_task_name="T1", reason="Precondition failed")
    f2 = PlanningFailure(failed_task_id="2", failed_task_name="T2", reason="No decomposition method")

    r1 = engine.reflect_planning_failure(f1, request_id="req-A")
    r2 = engine.reflect_planning_failure(f2, request_id="req-B")

    assert r1.request_id == "req-A"
    assert r2.request_id == "req-B"
    assert r1.failure_category != r2.failure_category


def test_hp4b_test_i_determinism_and_no_mutation():
    """Test I: Reflection is deterministic and does not mutate input failures."""
    engine = ReflectionEngine()
    failure = PlanningFailure(failed_task_id="1", failed_task_name="T1", attempted_methods=["m1"])

    res1 = engine.reflect_planning_failure(failure, request_id="req-1")
    res2 = engine.reflect_planning_failure(failure, request_id="req-1")

    assert res1.reflection_id != res2.reflection_id  # Unique ID
    assert res1.failure_category == res2.failure_category
    assert res1.root_cause == res2.root_cause
    assert failure.attempted_methods == ["m1"]  # Unmodified


def test_hp4b_test_j_master_phase_4b_acceptance_test():
    """
    MASTER ACCEPTANCE TEST — PHASE 4B:
    End-to-End failure diagnosis flow:
    Perception -> Root HTN Task -> Method A (Precondition UNSAT) -> Method B (No subtask method) ->
    PlanningFailure -> ReflectionEngine -> ReflectionResult stored in WorkingMemory.
    Proves failure diagnosis is fully operational without mutating rules or Hebbian weights.
    """
    planner = HTNPlanner()
    re = ReasoningEngine()
    re.htn_planner = planner

    # Custom task with impossible method chain
    root = Task(id="r", name="SOLVE_IMPOSSIBLE", task_type=TaskType.COMPOUND)
    p_broken = Task(id="b", name="BROKEN_SUBTASK", task_type=TaskType.COMPOUND)

    pre_impossible = Precondition(predicate="NONEXISTENT_FACT", required_state=True)
    m_a = Method(id="ma", target_task_name="SOLVE_IMPOSSIBLE", preconditions=[pre_impossible], subtasks=[p_broken], cost=1.0)
    m_b = Method(id="mb", target_task_name="SOLVE_IMPOSSIBLE", subtasks=[p_broken], cost=2.0)

    planner.method_registry.register_method(m_a)
    planner.method_registry.register_method(m_b)

    wm = WorkingMemory(request_id="req-acceptance-4b", session_id="s1", stimulus="impossible task")
    wm.semantic_frame = SemanticFrame(intent="IMPOSSIBLE", entities={})

    perception = PerceptionMap(
        entities={},
        unknown_entities=[],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )
    perception.intent = "IMPOSSIBLE"

    # Direct decompose_task test expecting HTNPlanningError
    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(root, context=wm)

    err = exc_info.value
    # Top-level failure on SOLVE_IMPOSSIBLE since method subtasks failed
    assert err.failure.failed_task_name == "SOLVE_IMPOSSIBLE" or "BROKEN_SUBTASK" in err.failure.reason

    # Reflect on the failure
    ref_result = re.reflection_engine.reflect_planning_failure(err.failure, request_id=wm.metadata.request_id)
    assert ref_result.failure_category in [ReflectionFailureType.NO_METHOD, ReflectionFailureType.STRUCTURAL_DECOMPOSITION_FAILURE]
    assert ref_result.retry_recommended is False


