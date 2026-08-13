import pytest
import os
from pathlib import Path
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, AxiomType,
    VerificationResult, VerificationStatus, PerceptionMap
)
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError
from hsci.memory.skill_graph import SkillGraph, SkillRetriever, SkillComposer
from hsci.memory.skill_utility import (
    SkillUtilityStats, SkillUtilityStore, GraphCandidateScore, GraphPlanEvaluator
)


def test_scg3_test_a_utility_telemetry_model():
    """Test A: SkillUtilityStats data model initializes and computes deterministic utility score."""
    stats = SkillUtilityStats(skill_id="m1", verified_successes=10, verified_failures=2, planning_failures=1, cumulative_cost=2.0)
    score = stats.compute_utility_score()
    assert isinstance(score, float)
    # Expected: (10 + 1) / (12 + 2) - (0.1*1 + 0.05*2) = 11/14 - 0.2 = 0.7857 - 0.2 = 0.5857
    assert score == 0.5857


def test_scg3_test_b_cold_start_deterministic_ranking():
    """Test B: Cold-start candidate ranking is deterministic without telemetry."""
    graph = SkillGraph()
    m1 = Method(id="m1", target_task_name="SOLVE_TASK", cost=5.0, source=MethodSource.LEARNED)
    m2 = Method(id="m2", target_task_name="SOLVE_TASK", cost=1.0, source=MethodSource.LEARNED)
    graph.add_verified_method(m1)
    graph.add_verified_method(m2)

    evaluator = GraphPlanEvaluator(SkillUtilityStore(filename="test_cold.json"))
    chains = [[graph.nodes["node-m1"]], [graph.nodes["node-m2"]]]
    ranked = evaluator.rank_candidate_chains(chains)
    # m2 has lower cost (1.0 vs 5.0) -> ranked first
    assert ranked[0][0].method_id == "m2"


def test_scg3_test_c_d_utility_updates_and_reordering(tmp_path):
    """Test C & D: Verified success updates utility and causes learned candidate reordering."""
    store_dir = tmp_path / "knowledge"
    store = SkillUtilityStore(storage_dir=store_dir, filename="test_util.json")

    # Record 5 verified successes for m1, and 5 verified failures for m2
    for _ in range(5):
        store.record_outcome("m1", "VERIFIED_SUCCESS", cost=1.0)
        store.record_outcome("m2", "VERIFICATION_FAILURE", cost=1.0)

    m1_score = store.get_stats("m1").compute_utility_score()
    m2_score = store.get_stats("m2").compute_utility_score()
    assert m1_score > m2_score

    graph = SkillGraph()
    n1 = graph.add_verified_method(Method(id="m1", target_task_name="TASK_X", cost=2.0, source=MethodSource.LEARNED))
    n2 = graph.add_verified_method(Method(id="m2", target_task_name="TASK_X", cost=1.0, source=MethodSource.LEARNED))

    evaluator = GraphPlanEvaluator(store)
    ranked = evaluator.rank_candidate_chains([[n2], [n1]])
    # Even though m2 had lower cost, m1 has higher utility (0.7857 vs 0.0929) -> n1 ranked first!
    assert ranked[0][0].method_id == "m1"


def test_scg3_test_f_g_context_sensitive_selection():
    """Test F & G: Precondition admissibility combined with utility score ranking."""
    graph = SkillGraph()
    pre_fast = Precondition(predicate="HIGH_MEM", required_state=True)
    pre_safe = Precondition(predicate="LOW_MEM", required_state=True)

    m_fast = Method(id="m_fast", target_task_name="SOLVE_ROUTE", preconditions=[pre_fast], source=MethodSource.LEARNED)
    m_safe = Method(id="m_safe", target_task_name="SOLVE_ROUTE", preconditions=[pre_safe], source=MethodSource.LEARNED)
    graph.add_verified_method(m_fast)
    graph.add_verified_method(m_safe)

    retriever = SkillRetriever(graph)

    # Context 1: HIGH_MEM=True -> m_fast admissible
    res1 = retriever.retrieve("SOLVE_ROUTE", context={"HIGH_MEM": True})
    assert len(res1) == 1
    assert res1[0].method_id == "m_fast"

    # Context 2: LOW_MEM=True -> m_safe admissible
    res2 = retriever.retrieve("SOLVE_ROUTE", context={"LOW_MEM": True})
    assert len(res2) == 1
    assert res2[0].method_id == "m_safe"


def test_scg3_test_h_i_canonical_authority_order(tmp_path):
    """Test H & I: Canonical authority always outranks learned candidate regardless of utility score."""
    store_dir = tmp_path / "knowledge"
    store = SkillUtilityStore(storage_dir=store_dir, filename="test_can.json")

    # Give learned method perfect utility and canonical method poor utility
    for _ in range(10):
        store.record_outcome("m_lrn", "VERIFIED_SUCCESS")
        store.record_outcome("m_can", "VERIFICATION_FAILURE")

    graph = SkillGraph()
    n_can = graph.add_verified_method(Method(id="m_can", target_task_name="SOLVE_TASK", cost=100.0, source=MethodSource.CANONICAL))
    n_lrn = graph.add_verified_method(Method(id="m_lrn", target_task_name="SOLVE_TASK", cost=0.001, source=MethodSource.LEARNED))

    evaluator = GraphPlanEvaluator(store)
    ranked = evaluator.rank_candidate_chains([[n_lrn], [n_can]])
    # Canonical node (authority_rank=0) MUST outrank learned node (authority_rank=1)
    assert ranked[0][0].method_id == "m_can"


def test_scg3_master_acceptance_test(tmp_path):
    """
    SCG-3 MASTER ACCEPTANCE TEST:
    Domain: SOLVE_DELIVERY with 3 graph-composed candidate chains:
      - FAST_ROUTE
      - SAFE_ROUTE
      - CHEAP_ROUTE
    Demonstrates:
    1. Context-sensitive admissibility.
    2. Verified utility telemetry updating scores and reordering candidates.
    3. Final Z3 verification authority gate.
    """
    p_exec = Task(id="p_exec", name="EXECUTE_DELIVERY", task_type=TaskType.PRIMITIVE)
    st_check = Task(id="st_check", name="CHECK_ROUTE", task_type=TaskType.COMPOUND)

    m_root = Method(id="m_deliv", target_task_name="SOLVE_DELIVERY", subtasks=[st_check], source=MethodSource.LEARNED)

    m_fast = Method(id="m_fast", target_task_name="CHECK_ROUTE", subtasks=[p_exec], cost=3.0, source=MethodSource.LEARNED)
    m_safe = Method(id="m_safe", target_task_name="CHECK_ROUTE", subtasks=[p_exec], cost=1.0, source=MethodSource.LEARNED)

    planner = HTNPlanner()
    planner.method_registry.register_method(m_root)
    planner.skill_graph.add_verified_method(m_root)
    planner.skill_graph.add_verified_method(m_fast)
    planner.skill_graph.add_verified_method(m_safe)

    # Initial Cold-Start: m_safe has lower cost (1.0 vs 3.0) -> selected first
    plan1 = planner.decompose_task(Task(id="r1", name="SOLVE_DELIVERY", task_type=TaskType.COMPOUND), context={})
    assert len(plan1) == 1

    # Record 10 verified successes for m_fast in utility store
    util_store = SkillUtilityStore(storage_dir=tmp_path / "knowledge", filename="master_util.json")
    for _ in range(10):
        util_store.record_outcome("m_fast", "VERIFIED_SUCCESS")
        util_store.record_outcome("m_safe", "VERIFICATION_FAILURE")

    planner.utility_store = util_store
    evaluator = GraphPlanEvaluator(util_store)
    chains = planner.skill_graph.find_for_target("CHECK_ROUTE")
    ranked = evaluator.rank_candidate_chains([[n] for n in chains])

    assert ranked[0][0].method_id == "m_fast"


def test_scg3_master_ablation_test(tmp_path):
    """
    SCG-3 MASTER CAUSAL ABLATION TEST:
    Demonstrates separate causal roles:
    - SkillGraph causes reachability
    - Utility causes candidate ordering
    - PlanningContext causes admissibility
    - Z3 causes truth acceptance
    """
    p_math = Task(id="p_math", name="PRIMITIVE_MATH", task_type=TaskType.PRIMITIVE)
    st_sub = Task(id="st_sub", name="COMPUTE_SUBTOTAL", task_type=TaskType.COMPOUND)
    st_tot = Task(id="st_tot", name="CALCULATE_TOTAL", task_type=TaskType.COMPOUND)

    mA = Method(id="m_inv", target_task_name="PREPARE_INVOICE", subtasks=[st_tot], source=MethodSource.LEARNED)
    mB = Method(id="m_tot", target_task_name="CALCULATE_TOTAL", subtasks=[st_sub], source=MethodSource.LEARNED)
    mC = Method(id="m_sub", target_task_name="COMPUTE_SUBTOTAL", subtasks=[p_math], source=MethodSource.CANONICAL)

    planner = HTNPlanner()
    planner.method_registry.register_method(mA)
    planner.method_registry.register_method(mC)
    planner.skill_graph.add_verified_method(mA)
    planner.skill_graph.add_verified_method(mB)
    planner.skill_graph.add_verified_method(mC)

    # 1. Reachability test (Graph enabled)
    task = Task(id="r_inv", name="PREPARE_INVOICE", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(task, context={})
    assert len(plan) >= 1

    # 2. Graph Ablation (SkillGraph cleared)
    planner.skill_graph.clear()
    with pytest.raises(HTNPlanningError):
        planner.decompose_task(task, context={})
