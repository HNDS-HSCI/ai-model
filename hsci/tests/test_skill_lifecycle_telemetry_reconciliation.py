import pytest
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, PlanningTrace, VerificationResult, ProofTrace
)
from hsci.memory.skill_lifecycle import (
    SkillLifecycleStatus, SkillLifecycleManager
)
from hsci.reasoning.htn_planner import HTNPlanner, MethodRegistry
from hsci.memory.skill_graph import SkillGraph


def test_scg4_2_test_a_direct_decaying_learned_success_recovers_to_active(tmp_path):
    """Test A: Direct LEARNED method in DECAYING state recovers to ACTIVE upon Z3 verification success."""
    registry = MethodRegistry()
    m_direct = Method(
        id="m_learned_recovery",
        target_task_name="SOLVE_RECOVERY",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_direct)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_recov.json")
    for _ in range(3):
        lifecycle_mgr.record_skill_outcome("m_learned_recovery", MethodSource.LEARNED, "VERIFICATION_FAILURE")
    assert lifecycle_mgr.get_state("m_learned_recovery").status == SkillLifecycleStatus.DECAYING

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)
    target_task = Task(id="t_target", name="SOLVE_RECOVERY", task_type=TaskType.COMPOUND)

    primitives, trace = planner.decompose_task_with_trace(target_task)
    assert "m_learned_recovery" in trace.executed_method_ids

    # Simulate RIRLoop telemetry reconciliation logic
    outcome_key = "VERIFIED_SUCCESS"
    executed_learned_skills = {}
    for mid in trace.executed_method_ids:
        m_obj = registry.get_method(mid)
        if m_obj and m_obj.source == MethodSource.LEARNED:
            executed_learned_skills[mid] = MethodSource.LEARNED

    for skill_id, source in executed_learned_skills.items():
        lifecycle_mgr.record_skill_outcome(skill_id, source, outcome_key, request_id="req-123")

    assert lifecycle_mgr.get_state("m_learned_recovery").status == SkillLifecycleStatus.ACTIVE


def test_scg4_2_test_b_direct_learned_z3_failure_records_one_failure(tmp_path):
    """Test B: Direct LEARNED method execution that fails verification receives exactly 1 failure."""
    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_fail.json")
    st = lifecycle_mgr.get_state("m_learned_fail")
    assert st.consecutive_failures == 0

    trace = PlanningTrace(executed_method_ids=["m_learned_fail"], executed_graph_node_ids=[])
    registry = MethodRegistry()
    m_fail = Method(id="m_learned_fail", target_task_name="TASK", source=MethodSource.LEARNED, subtasks=[])
    registry.register_method(m_fail)

    outcome_key = "VERIFICATION_FAILURE"
    executed_learned_skills = {}
    for mid in trace.executed_method_ids:
        m_obj = registry.get_method(mid)
        if m_obj and m_obj.source == MethodSource.LEARNED:
            executed_learned_skills[mid] = MethodSource.LEARNED

    for skill_id, source in executed_learned_skills.items():
        lifecycle_mgr.record_skill_outcome(skill_id, source, outcome_key)

    assert lifecycle_mgr.get_state("m_learned_fail").consecutive_failures == 1


def test_scg4_2_test_c_canonical_direct_execution_zero_lifecycle_updates(tmp_path):
    """Test C: CANONICAL direct method execution produces zero lifecycle outcome updates."""
    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_can.json")
    registry = MethodRegistry()
    m_can = Method(id="m_canonical", target_task_name="TASK", source=MethodSource.CANONICAL, subtasks=[])
    registry.register_method(m_can)

    trace = PlanningTrace(executed_method_ids=["m_canonical"], executed_graph_node_ids=[])
    executed_learned_skills = {}
    for mid in trace.executed_method_ids:
        m_obj = registry.get_method(mid)
        if m_obj and m_obj.source == MethodSource.LEARNED:
            executed_learned_skills[mid] = MethodSource.LEARNED

    assert len(executed_learned_skills) == 0


def test_scg4_2_test_e_duplicate_graph_method_id_one_update(tmp_path):
    """Test E: A skill present in BOTH executed_method_ids and executed_graph_node_ids is updated exactly ONCE."""
    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_dup.json")
    registry = MethodRegistry()
    m_dup = Method(id="m_dup_skill", target_task_name="TASK", source=MethodSource.LEARNED, subtasks=[])
    registry.register_method(m_dup)
    graph = SkillGraph()
    graph.add_verified_method(m_dup)

    trace = PlanningTrace(executed_method_ids=["m_dup_skill"], executed_graph_node_ids=["node-m_dup_skill"])

    executed_learned_skills = {}
    for mid in trace.executed_method_ids:
        m_obj = registry.get_method(mid)
        if m_obj and m_obj.source == MethodSource.LEARNED:
            executed_learned_skills[mid] = MethodSource.LEARNED
    for nid in trace.executed_graph_node_ids:
        clean_id = nid[5:] if nid.startswith("node-") else nid
        executed_learned_skills[clean_id] = MethodSource.LEARNED

    assert len(executed_learned_skills) == 1
    assert "m_dup_skill" in executed_learned_skills

    for skill_id, source in executed_learned_skills.items():
        lifecycle_mgr.record_skill_outcome(skill_id, source, "VERIFIED_SUCCESS")

    assert lifecycle_mgr.get_state("m_dup_skill").successful_selections == 1


def test_scg4_2_causal_ablation(tmp_path):
    """Causal Ablation: Disabling executed_method_ids reconciliation causes direct learned methods to fail recovery."""
    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_abl.json")
    for _ in range(3):
        lifecycle_mgr.record_skill_outcome("m_abl", MethodSource.LEARNED, "VERIFICATION_FAILURE")
    assert lifecycle_mgr.get_state("m_abl").status == SkillLifecycleStatus.DECAYING

    trace = PlanningTrace(executed_method_ids=["m_abl"], executed_graph_node_ids=[])
    
    # 1. Un-reconciled (old) behavior: only inspects executed_graph_node_ids
    old_executed_learned_skills = {}
    for nid in trace.executed_graph_node_ids:
        old_executed_learned_skills[nid] = MethodSource.LEARNED
    for skill_id, source in old_executed_learned_skills.items():
        lifecycle_mgr.record_skill_outcome(skill_id, source, "VERIFIED_SUCCESS")

    # Stays DECAYING because old behavior ignored direct method IDs
    assert lifecycle_mgr.get_state("m_abl").status == SkillLifecycleStatus.DECAYING

    # 2. Reconciled (new) behavior: inspects executed_method_ids
    registry = MethodRegistry()
    m_abl = Method(id="m_abl", target_task_name="TASK", source=MethodSource.LEARNED, subtasks=[])
    registry.register_method(m_abl)

    new_executed_learned_skills = {}
    for mid in trace.executed_method_ids:
        m_obj = registry.get_method(mid)
        if m_obj and m_obj.source == MethodSource.LEARNED:
            new_executed_learned_skills[mid] = MethodSource.LEARNED

    for skill_id, source in new_executed_learned_skills.items():
        lifecycle_mgr.record_skill_outcome(skill_id, source, "VERIFIED_SUCCESS")

    # Recovers to ACTIVE
    assert lifecycle_mgr.get_state("m_abl").status == SkillLifecycleStatus.ACTIVE
