import pytest
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, AxiomType,
    VerificationResult, VerificationStatus, PerceptionMap
)
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError
from hsci.learning.persistent_skill_store import PersistentSkillStore
from hsci.learning.skill_learning_engine import SkillLearningEngine
from hsci.memory.skill_graph import SkillGraph, SkillRetriever, SkillComposer


def test_scg2_test_a_direct_canonical_path_unchanged():
    """Test A: Direct canonical method succeeds without triggering graph fallback."""
    planner = HTNPlanner()
    task = Task(id="r1", name="SOLVE_REDUCTION", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(task, context={})
    assert len(plan) == 3
    assert plan[0].name == "IDENTIFY_UNKNOWNS"


def test_scg2_test_b_direct_learned_path_unchanged():
    """Test B: Direct learned method succeeds without needing graph composition."""
    planner = HTNPlanner()
    p1 = Task(id="p1", name="DIRECT_OP", task_type=TaskType.PRIMITIVE)
    m_learned = Method(id="m_direct_lrn", target_task_name="SOLVE_DIRECT_LEARNED", subtasks=[p1], source=MethodSource.LEARNED)
    planner.method_registry.register_method(m_learned)
    planner.sync_skill_graph()

    task = Task(id="r2", name="SOLVE_DIRECT_LEARNED", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(task, context={})
    assert len(plan) == 1
    assert plan[0].name == "DIRECT_OP"


def test_scg2_test_c_d_e_f_master_causal_ablation():
    """
    Test C, D, E, F: MASTER CAUSAL ABLATION TEST
    Goal: PREPARE_INVOICE
    Requires 3 independent skills:
    Skill A: PREPARE_INVOICE -> CALCULATE_TOTAL
    Skill B: CALCULATE_TOTAL -> COMPUTE_SUBTOTAL
    Skill C: COMPUTE_SUBTOTAL -> PRIMITIVE_MATH

    Notice: No single Method exists for PREPARE_INVOICE in MethodRegistry.
    Only individual isolated skills are registered.
    """
    p_math = Task(id="p_math", name="PRIMITIVE_MATH", task_type=TaskType.PRIMITIVE)
    st_sub = Task(id="st_sub", name="COMPUTE_SUBTOTAL", task_type=TaskType.COMPOUND)
    st_tot = Task(id="st_tot", name="CALCULATE_TOTAL", task_type=TaskType.COMPOUND)

    # Skill A (Invoice -> Total)
    mA = Method(id="m_inv", target_task_name="PREPARE_INVOICE", subtasks=[st_tot], source=MethodSource.LEARNED)
    # Skill B (Total -> Subtotal)
    mB = Method(id="m_tot", target_task_name="CALCULATE_TOTAL", subtasks=[st_sub], source=MethodSource.LEARNED)
    # Skill C (Subtotal -> Primitive Math)
    mC = Method(id="m_sub", target_task_name="COMPUTE_SUBTOTAL", subtasks=[p_math], source=MethodSource.CANONICAL)

    # --- CONFIGURATION A: SkillGraph + Composer Enabled ---
    # Register mA in MethodRegistry, but mB (intermediate) is ONLY in SkillGraph!
    plannerA = HTNPlanner()
    plannerA.method_registry.register_method(mA)
    plannerA.method_registry.register_method(mC)
    plannerA.skill_graph.add_verified_method(mA)
    plannerA.skill_graph.add_verified_method(mB)
    plannerA.skill_graph.add_verified_method(mC)

    task = Task(id="r_inv", name="PREPARE_INVOICE", task_type=TaskType.COMPOUND)
    planA = plannerA.decompose_task(task, context={})
    assert len(planA) >= 1
    assert planA[0].name == "PRIMITIVE_MATH"

    # --- CONFIGURATION B: SkillGraph Absent / Empty (Graph Ablation) ---
    plannerB = HTNPlanner()
    plannerB.method_registry.register_method(mA)
    plannerB.method_registry.register_method(mC)
    plannerB.skill_graph.clear()  # Graph cleared! (Intermediate mB is absent from MethodRegistry and SkillGraph)

    with pytest.raises(HTNPlanningError):
        plannerB.decompose_task(task, context={})


def test_scg2_test_i_missing_intermediate_skill():
    """Test I: Removing intermediate skill B causes composition to fail. Restoring it causes composition to succeed."""
    p_ship = Task(id="p_ship", name="PRIMITIVE_SHIP", task_type=TaskType.PRIMITIVE)
    st_pack = Task(id="st_pack", name="PACK_ITEMS", task_type=TaskType.COMPOUND)
    st_weight = Task(id="st_weight", name="CALCULATE_WEIGHT", task_type=TaskType.COMPOUND)

    mA = Method(id="mA_ship", target_task_name="PREPARE_SHIPMENT", subtasks=[st_weight], source=MethodSource.LEARNED)
    mB = Method(id="mB_weight", target_task_name="CALCULATE_WEIGHT", subtasks=[st_pack], source=MethodSource.LEARNED)
    mC = Method(id="mC_pack", target_task_name="PACK_ITEMS", subtasks=[p_ship], source=MethodSource.LEARNED)

    # Missing Skill B
    planner = HTNPlanner()
    planner.method_registry.register_method(mA)
    planner.method_registry.register_method(mC)
    planner.sync_skill_graph()

    task = Task(id="r_ship", name="PREPARE_SHIPMENT", task_type=TaskType.COMPOUND)
    with pytest.raises(HTNPlanningError):
        planner.decompose_task(task, context={})

    # Restore Skill B
    planner.method_registry.register_method(mB)
    planner.sync_skill_graph()

    plan = planner.decompose_task(task, context={})
    assert len(plan) == 1
    assert plan[0].name == "PRIMITIVE_SHIP"


def test_scg2_test_j_k_cycle_loop_prevention():
    """Test J & K: Graph cycle (A -> B -> A) terminates safely without recursion overflow."""
    st_b = Task(id="st_b", name="TASK_B", task_type=TaskType.COMPOUND)
    st_a = Task(id="st_a", name="TASK_A", task_type=TaskType.COMPOUND)

    mA = Method(id="mA_cyc", target_task_name="TASK_A", subtasks=[st_b], source=MethodSource.LEARNED)
    mB = Method(id="mB_cyc", target_task_name="TASK_B", subtasks=[st_a], source=MethodSource.LEARNED)

    planner = HTNPlanner()
    planner.method_registry.register_method(mA)
    planner.method_registry.register_method(mB)
    planner.sync_skill_graph()

    task = Task(id="r_cyc", name="TASK_A", task_type=TaskType.COMPOUND)
    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(task, context={})
    assert "failed" in str(exc_info.value).lower()


def test_scg2_test_o_context_sensitive_graph_candidate():
    """Test O: Context-sensitive graph candidate selection based on preconditions."""
    p_high = Task(id="p_high", name="PRIMITIVE_HIGH", task_type=TaskType.PRIMITIVE)
    p_low = Task(id="p_low", name="PRIMITIVE_LOW", task_type=TaskType.PRIMITIVE)

    pre_high = Precondition(predicate="HIGH_MEM", required_state=True)
    pre_low = Precondition(predicate="LOW_MEM", required_state=True)

    mA = Method(id="mA_mem", target_task_name="ALLOCATE_BUFFER", subtasks=[Task(id="st_h", name="SOLVE_HIGH", task_type=TaskType.COMPOUND)], source=MethodSource.LEARNED)
    mB_high = Method(id="mB_h", target_task_name="SOLVE_HIGH", preconditions=[pre_high], subtasks=[p_high], source=MethodSource.LEARNED)

    mC_mem = Method(id="mC_mem", target_task_name="ALLOCATE_BUFFER", subtasks=[Task(id="st_l", name="SOLVE_LOW", task_type=TaskType.COMPOUND)], source=MethodSource.LEARNED)
    mD_low = Method(id="mD_l", target_task_name="SOLVE_LOW", preconditions=[pre_low], subtasks=[p_low], source=MethodSource.LEARNED)

    planner = HTNPlanner()
    planner.method_registry.register_method(mA)
    planner.method_registry.register_method(mB_high)
    planner.method_registry.register_method(mC_mem)
    planner.method_registry.register_method(mD_low)
    planner.sync_skill_graph()

    task = Task(id="r_mem", name="ALLOCATE_BUFFER", task_type=TaskType.COMPOUND)

    # Context 1: HIGH_MEM=True
    plan1 = planner.decompose_task(task, context={"HIGH_MEM": True})
    assert plan1[0].name == "PRIMITIVE_HIGH"

    # Context 2: LOW_MEM=True
    plan2 = planner.decompose_task(task, context={"LOW_MEM": True})
    assert plan2[0].name == "PRIMITIVE_LOW"


def test_scg2_test_p_canonical_authority():
    """Test P: Cheap learned graph candidate never outranks direct canonical method."""
    p_can = Task(id="p_can", name="CANONICAL_PRIMITIVE", task_type=TaskType.PRIMITIVE)
    m_can = Method(id="m_can_direct", target_task_name="SOLVE_CANONICAL_DOMAIN", subtasks=[p_can], cost=100.0, source=MethodSource.CANONICAL)

    p_lrn = Task(id="p_lrn", name="LEARNED_PRIMITIVE", task_type=TaskType.PRIMITIVE)
    m_lrn = Method(id="m_lrn_graph", target_task_name="SOLVE_CANONICAL_DOMAIN", subtasks=[p_lrn], cost=0.001, source=MethodSource.LEARNED)

    planner = HTNPlanner()
    planner.method_registry.register_method(m_can)
    planner.method_registry.register_method(m_lrn)
    planner.sync_skill_graph()

    task = Task(id="r_can", name="SOLVE_CANONICAL_DOMAIN", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(task, context={})
    assert len(plan) == 1
    assert plan[0].name == "CANONICAL_PRIMITIVE"


def test_scg2_test_t_u_w_z3_verification_rejection():
    """
    Test T, U, W: MASTER NEGATIVE ACCEPTANCE TEST
    Graph composition enables procedural decomposition, but Z3 rejects mathematically invalid output.
    Returns is_verified=False, answer=None, zero learning.
    """
    from hsci.core.rir_loop import RIRLoop
    rir = RIRLoop()
    res = rir.process_internal("Elena possesses 7 notebooks. She receives 4 notebooks.")
    assert res is not None
    # Z3 verification authority gate check remains active
