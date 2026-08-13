import pytest
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition
)
from hsci.memory.skill_graph import SkillGraph
from hsci.memory.skill_lifecycle import (
    SkillLifecycleStatus, SkillLifecycleManager
)
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError, MethodRegistry
from hsci.memory.skill_utility import SkillUtilityStore, GraphPlanEvaluator


def test_scg4_1_test_a_direct_deprecated_method_blocked(tmp_path):
    """Test A: Direct LEARNED method in MethodRegistry marked DEPRECATED must be BLOCKED by HTNPlanner."""
    registry = MethodRegistry()
    m_direct = Method(
        id="m_learned_direct_dep",
        target_task_name="SOLVE_DIRECT_LIFECYCLE",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_direct)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_reg_gate.json")
    st = lifecycle_mgr.get_state("m_learned_direct_dep")
    st.status = SkillLifecycleStatus.DEPRECATED
    assert lifecycle_mgr.is_eligible_for_retrieval("m_learned_direct_dep", MethodSource.LEARNED) is False

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)

    target_task = Task(id="t_target", name="SOLVE_DIRECT_LIFECYCLE", task_type=TaskType.COMPOUND)

    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task_with_trace(target_task)

    assert "DEPRECATED" in exc_info.value.failure.reason


def test_scg4_1_test_b_active_direct_method_succeeds(tmp_path):
    """Test B: Direct LEARNED method in MethodRegistry marked ACTIVE succeeds in HTNPlanner."""
    registry = MethodRegistry()
    m_direct = Method(
        id="m_learned_direct_act",
        target_task_name="SOLVE_DIRECT_LIFECYCLE",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_direct)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_reg_act.json")
    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)

    target_task = Task(id="t_target", name="SOLVE_DIRECT_LIFECYCLE", task_type=TaskType.COMPOUND)
    primitives, trace = planner.decompose_task_with_trace(target_task)

    assert len(primitives) == 1
    assert primitives[0].name == "PRIMITIVE_STEP"
    assert "m_learned_direct_act" in trace.executed_method_ids


def test_scg4_1_test_c_decaying_direct_method_succeeds(tmp_path):
    """Test C: Direct LEARNED method in MethodRegistry marked DECAYING remains executable."""
    registry = MethodRegistry()
    m_direct = Method(
        id="m_learned_direct_dec",
        target_task_name="SOLVE_DIRECT_LIFECYCLE",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_direct)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_reg_dec.json")
    for _ in range(3):
        lifecycle_mgr.record_skill_outcome("m_learned_direct_dec", MethodSource.LEARNED, "VERIFICATION_FAILURE")
    assert lifecycle_mgr.get_state("m_learned_direct_dec").status == SkillLifecycleStatus.DECAYING

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)
    target_task = Task(id="t_target", name="SOLVE_DIRECT_LIFECYCLE", task_type=TaskType.COMPOUND)
    primitives, trace = planner.decompose_task_with_trace(target_task)

    assert len(primitives) == 1
    assert primitives[0].name == "PRIMITIVE_STEP"


def test_scg4_1_test_d_canonical_immunity(tmp_path):
    """Test D: CANONICAL direct method remains immune and executable despite failure evidence."""
    registry = MethodRegistry()
    m_can = Method(
        id="m_canonical_direct",
        target_task_name="SOLVE_DIRECT_LIFECYCLE",
        cost=1.0,
        source=MethodSource.CANONICAL,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_can)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_can_immunity.json")
    for _ in range(100):
        lifecycle_mgr.record_skill_outcome("m_canonical_direct", MethodSource.CANONICAL, "VERIFICATION_FAILURE")

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)
    target_task = Task(id="t_target", name="SOLVE_DIRECT_LIFECYCLE", task_type=TaskType.COMPOUND)
    primitives, trace = planner.decompose_task_with_trace(target_task)

    assert len(primitives) == 1
    assert "m_canonical_direct" in trace.executed_method_ids


def test_scg4_1_test_k_nested_htn_direct_bypass_blocked(tmp_path):
    """Test K: Nested HTN decomposition blocks direct learned method if DEPRECATED."""
    registry = MethodRegistry()
    # Root method -> SUBTASK_A
    m_root = Method(
        id="m_root",
        target_task_name="ROOT_TASK",
        cost=1.0,
        source=MethodSource.CANONICAL,
        subtasks=[Task(id="t_sub_a", name="SUBTASK_A", task_type=TaskType.COMPOUND)]
    )
    # Subtask A method -> LEARNED / DEPRECATED
    m_sub_a = Method(
        id="m_sub_a_dep",
        target_task_name="SUBTASK_A",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_root)
    registry.register_method(m_sub_a)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_nested_gate.json")
    st = lifecycle_mgr.get_state("m_sub_a_dep")
    st.status = SkillLifecycleStatus.DEPRECATED

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)
    root_task = Task(id="t_root", name="ROOT_TASK", task_type=TaskType.COMPOUND)

    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task_with_trace(root_task)

    assert "DEPRECATED" in exc_info.value.failure.reason


def test_scg4_1_test_m_master_cross_path_acceptance(tmp_path):
    """Test M: Master Cross-Path Acceptance Test — Deprecated in BOTH MethodRegistry & SkillGraph is BLOCKED."""
    graph = SkillGraph()
    registry = MethodRegistry()

    m_dual = Method(
        id="m_dual_dep",
        target_task_name="SOLVE_DUAL_TASK",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_dual)
    graph.add_verified_method(m_dual)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_dual_gate.json")
    st = lifecycle_mgr.get_state("m_dual_dep")
    st.status = SkillLifecycleStatus.DEPRECATED

    planner = HTNPlanner(method_registry=registry, skill_graph=graph, lifecycle_manager=lifecycle_mgr)
    target_task = Task(id="t_target", name="SOLVE_DUAL_TASK", task_type=TaskType.COMPOUND)

    with pytest.raises(HTNPlanningError):
        planner.decompose_task_with_trace(target_task)


def test_scg4_1_causal_ablation(tmp_path):
    """Causal Ablation Test: Proves _is_method_lifecycle_eligible is causally responsible for exclusion."""
    registry = MethodRegistry()
    m_ablated = Method(
        id="m_ablated_dep",
        target_task_name="SOLVE_ABLATION_TASK",
        cost=1.0,
        source=MethodSource.LEARNED,
        subtasks=[Task(id="t_prim", name="PRIMITIVE_STEP", task_type=TaskType.PRIMITIVE)]
    )
    registry.register_method(m_ablated)

    lifecycle_mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_ablation.json")
    st = lifecycle_mgr.get_state("m_ablated_dep")
    st.status = SkillLifecycleStatus.DEPRECATED

    planner = HTNPlanner(method_registry=registry, lifecycle_manager=lifecycle_mgr)
    target_task = Task(id="t_target", name="SOLVE_ABLATION_TASK", task_type=TaskType.COMPOUND)

    # 1. With gate active: planning fails
    with pytest.raises(HTNPlanningError):
        planner.decompose_task_with_trace(target_task)

    # 2. Temporarily neutralize gate in test environment: planning succeeds
    original_gate = planner._is_method_lifecycle_eligible
    planner._is_method_lifecycle_eligible = lambda m: True

    primitives, _ = planner.decompose_task_with_trace(target_task)
    assert len(primitives) == 1

    # Restore gate
    planner._is_method_lifecycle_eligible = original_gate
