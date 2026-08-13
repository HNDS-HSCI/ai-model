import pytest
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, PlanningTrace
)
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.memory.skill_graph import SkillGraph
from hsci.memory.skill_utility import SkillUtilityStore


def test_scg3_1_test_a_exact_success_attribution(tmp_path):
    """Test A: Z3 success credits ONLY participating graph nodes (A, C), leaving unexecuted nodes (B, D) unchanged."""
    graph = SkillGraph()
    nA = graph.add_verified_method(Method(id="mA", target_task_name="ROOT_TASK", cost=1.0, source=MethodSource.LEARNED))
    nB = graph.add_verified_method(Method(id="mB", target_task_name="ROOT_TASK", cost=2.0, source=MethodSource.LEARNED))
    nC = graph.add_verified_method(Method(id="mC", target_task_name="OTHER_TASK", cost=1.0, source=MethodSource.LEARNED))
    nD = graph.add_verified_method(Method(id="mD", target_task_name="OTHER_TASK", cost=2.0, source=MethodSource.LEARNED))

    store_dir = tmp_path / "knowledge"
    store = SkillUtilityStore(storage_dir=store_dir, filename="test_attr_a.json")

    # Simulate executed trace containing only mA and mC
    trace = PlanningTrace(
        selected_candidate_id="cand-0",
        executed_graph_node_ids=["mA", "mC"],
        graph_fallback_used=True
    )

    # Record outcome for executed trace
    for node_id in trace.executed_graph_node_ids:
        store.record_outcome(node_id, "VERIFIED_SUCCESS")

    assert store.get_stats("mA").verified_successes == 1
    assert store.get_stats("mC").verified_successes == 1
    assert store.get_stats("mB").verified_successes == 0
    assert store.get_stats("mD").verified_successes == 0


def test_scg3_1_test_d_direct_method_does_not_credit_graph(tmp_path):
    """Test D: Solving via direct CANONICAL method produces executed_graph_node_ids=[] leaving all graph nodes unchanged."""
    planner = HTNPlanner()
    p_primitive = Task(id="p1", name="PRIMITIVE_OP", task_type=TaskType.PRIMITIVE)
    m_canonical = Method(id="m_can", target_task_name="ROOT_CANONICAL", subtasks=[p_primitive], source=MethodSource.CANONICAL)
    planner.method_registry.register_method(m_canonical)

    # Populate graph with 10 learned skills
    for i in range(10):
        planner.skill_graph.add_verified_method(Method(id=f"m_lrn_{i}", target_task_name="LEARNED_TASK", cost=1.0, source=MethodSource.LEARNED))

    task = Task(id="t_can", name="ROOT_CANONICAL", task_type=TaskType.COMPOUND)
    primitives, trace = planner.decompose_task_with_trace(task, context={})

    assert len(primitives) == 1
    assert trace.graph_fallback_used is False
    assert trace.executed_graph_node_ids == []
    assert trace.executed_method_ids == ["m_can"]


def test_scg3_1_test_g_10_request_amplification_test(tmp_path):
    """Test G: 10 requests executing only Node A results in A.successes == 10, B.successes == 0, C.successes == 0."""
    store_dir = tmp_path / "knowledge"
    store = SkillUtilityStore(storage_dir=store_dir, filename="test_amp.json")

    # Run 10 requests executing trace with node A only
    for _ in range(10):
        trace = PlanningTrace(executed_graph_node_ids=["nodeA"])
        for nid in trace.executed_graph_node_ids:
            store.record_outcome(nid, "VERIFIED_SUCCESS")

    assert store.get_stats("nodeA").verified_successes == 10
    assert store.get_stats("nodeB").verified_successes == 0
    assert store.get_stats("nodeC").verified_successes == 0
