import pytest
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition
)
from hsci.memory.skill_graph import SkillGraph
from hsci.memory.skill_lifecycle import (
    SkillLifecycleStatus, SkillLifecycleManager, SkillLifecyclePolicy, SkillLifecycleState
)
from hsci.memory.skill_utility import SkillUtilityStore, GraphPlanEvaluator


def test_scg4_test_a_h_canonical_cannot_decay(tmp_path):
    """Test A & H: CANONICAL methods remain immutably ACTIVE regardless of failure telemetry."""
    mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_can_life.json")

    # Record 100 verification failures for CANONICAL method
    for _ in range(100):
        status = mgr.record_skill_outcome("m_canonical", MethodSource.CANONICAL, "VERIFICATION_FAILURE")
        assert status == SkillLifecycleStatus.ACTIVE

    st = mgr.get_state("m_canonical")
    assert st.status == SkillLifecycleStatus.ACTIVE
    assert mgr.is_eligible_for_retrieval("m_canonical", MethodSource.CANONICAL) is True


def test_scg4_test_b_c_d_learned_lifecycle_transitions(tmp_path):
    """Test B, C, D: Learned skill transitions ACTIVE -> DECAYING -> DEPRECATED and Verified Recovery -> ACTIVE."""
    mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_life_trans.json")

    # Initially ACTIVE
    assert mgr.get_state("m_learned").status == SkillLifecycleStatus.ACTIVE

    # Record 3 failures -> DECAYING
    for _ in range(3):
        mgr.record_skill_outcome("m_learned", MethodSource.LEARNED, "VERIFICATION_FAILURE")

    assert mgr.get_state("m_learned").status == SkillLifecycleStatus.DECAYING

    # 1 verified success -> Verified Recovery to ACTIVE
    mgr.record_skill_outcome("m_learned", MethodSource.LEARNED, "VERIFIED_SUCCESS")
    assert mgr.get_state("m_learned").status == SkillLifecycleStatus.ACTIVE

    # Record 6 consecutive failures -> DEPRECATED
    for _ in range(6):
        mgr.record_skill_outcome("m_learned", MethodSource.LEARNED, "VERIFICATION_FAILURE")

    assert mgr.get_state("m_learned").status == SkillLifecycleStatus.DEPRECATED
    assert mgr.is_eligible_for_retrieval("m_learned", MethodSource.LEARNED) is False


def test_scg4_test_f_g_deprecated_excluded_decaying_penalized(tmp_path):
    """Test F & G: DEPRECATED candidates are excluded from evaluation, DECAYING candidates receive ranking penalty."""
    graph = SkillGraph()
    m_active = Method(id="m_act", target_task_name="SOLVE_TASK", cost=1.0, source=MethodSource.LEARNED)
    m_decaying = Method(id="m_dec", target_task_name="SOLVE_TASK", cost=1.0, source=MethodSource.LEARNED)
    m_deprecated = Method(id="m_dep", target_task_name="SOLVE_TASK", cost=1.0, source=MethodSource.LEARNED)

    n_act = graph.add_verified_method(m_active)
    n_dec = graph.add_verified_method(m_decaying)
    n_dep = graph.add_verified_method(m_deprecated)

    mgr = SkillLifecycleManager(storage_dir=tmp_path / "knowledge", filename="test_eval.json")
    # Transition m_dec to DECAYING (3 failures) and m_dep to DEPRECATED (6 failures)
    for _ in range(3):
        mgr.record_skill_outcome("m_dec", MethodSource.LEARNED, "VERIFICATION_FAILURE")
    for _ in range(6):
        mgr.record_skill_outcome("m_dep", MethodSource.LEARNED, "VERIFICATION_FAILURE")

    evaluator = GraphPlanEvaluator(
        utility_store=SkillUtilityStore(storage_dir=tmp_path / "knowledge", filename="test_util_eval.json"),
        lifecycle_manager=mgr
    )

    # DEPRECATED node candidate chain receives score -999 and authority rank 99 (Ineligible)
    score_dep = evaluator.evaluate_chain([n_dep])
    assert score_dep.authority_rank == 99

    # DECAYING node candidate chain receives ranking penalty (-0.25)
    score_dec = evaluator.evaluate_chain([n_dec])
    score_act = evaluator.evaluate_chain([n_act])
    assert score_act.utility_score > score_dec.utility_score


def test_scg4_test_l_restart_preserves_lifecycle_state(tmp_path):
    """Test L: Lifecycle state survives process restart across file reloads."""
    store_dir = tmp_path / "knowledge"
    mgr1 = SkillLifecycleManager(storage_dir=store_dir, filename="restart_life.json")

    for _ in range(3):
        mgr1.record_skill_outcome("m_restart", MethodSource.LEARNED, "VERIFICATION_FAILURE")

    assert mgr1.get_state("m_restart").status == SkillLifecycleStatus.DECAYING

    # Instantiate fresh manager simulating process restart
    mgr2 = SkillLifecycleManager(storage_dir=store_dir, filename="restart_life.json")
    assert mgr2.get_state("m_restart").status == SkillLifecycleStatus.DECAYING
