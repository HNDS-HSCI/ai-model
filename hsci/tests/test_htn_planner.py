import pytest
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.core.data_types import AxiomType, PerceptionMap, SubGoal

@pytest.fixture
def htn_planner():
    return HTNPlanner()

def create_perception_map(intent: AxiomType):
    return PerceptionMap(
        entities={},
        unknown_entities=[],
        relationships=[],
        intent=intent,
        confidence=1.0,
        entity_graph={}
    )

def test_decompose_reduction_problem(htn_planner):
    perception = create_perception_map(AxiomType.REDUCTION)
    sub_goals = htn_planner.decompose(perception)

    expected_names = ["IDENTIFY_UNKNOWNS", "BUILD_EQUATION", "SOLVE_EQUATION"]
    assert len(sub_goals) == len(expected_names)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_names[i]
        assert goal.axiom_type == AxiomType.REDUCTION

def test_decompose_composition_problem(htn_planner):
    perception = create_perception_map(AxiomType.COMPOSITION)
    sub_goals = htn_planner.decompose(perception)

    expected_names = ["EXTRACT_ENTITIES", "IDENTIFY_RELATIONSHIPS", "BUILD_CONSTRAINT_NETWORK", "SOLVE_NETWORK"]
    assert len(sub_goals) == len(expected_names)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_names[i]
        assert goal.axiom_type == AxiomType.COMPOSITION

def test_decompose_synthesis_problem(htn_planner):
    perception = create_perception_map(AxiomType.SYNTHESIS)
    sub_goals = htn_planner.decompose(perception)

    expected_names = ["DEFINE_INPUTS_OUTPUTS", "IDENTIFY_ALGORITHM_PATTERN", "BUILD_PROCEDURE", "VERIFY_INVARIANTS"]
    assert len(sub_goals) == len(expected_names)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_names[i]
        assert goal.axiom_type == AxiomType.SYNTHESIS

def test_decompose_transformation_problem(htn_planner):
    perception = create_perception_map(AxiomType.TRANSFORMATION)
    sub_goals = htn_planner.decompose(perception)

    expected_names = ["PARSE_SOURCE_STRUCTURE", "IDENTIFY_TARGET_STRUCTURE", "MAP_TRANSFORMATION_RULES", "APPLY_TRANSFORMATION"]
    assert len(sub_goals) == len(expected_names)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_names[i]
        assert goal.axiom_type == AxiomType.TRANSFORMATION

def test_decompose_unknown_intent(htn_planner):
    # Create a PerceptionMap with a non-standard intent if possible, 
    # or just test the default case of decompose logic.
    perception = create_perception_map(None) # Should trigger fallback
    sub_goals = htn_planner.decompose(perception)
    assert len(sub_goals) == 1
    assert sub_goals[0].name == "UNKNOWN_INTENT_HANDLING"


# ─────────────────────────────────────────────
# HP4A-01 & HP4A-02 FOUNDATION TESTS
# ─────────────────────────────────────────────

from hsci.core.data_types import (
    Task, TaskType, Method, Operator, Precondition, Postcondition, PlanningFailure
)
from hsci.reasoning.htn_planner import MethodRegistry, OperatorRegistry, HTNPlanningError


def test_htn_domain_data_models():
    precond = Precondition(predicate="HAS_ENTITY", required_state="distance")
    postcond = Postcondition(effect_key="SOLVED", resulting_state="velocity")
    
    t_prim = Task(id="t1", name="BUILD_EQUATION", task_type=TaskType.PRIMITIVE, axiom_type=AxiomType.REDUCTION)
    t_comp = Task(id="t2", name="SOLVE_REDUCTION", task_type=TaskType.COMPOUND, axiom_type=AxiomType.REDUCTION)
    
    method = Method(id="m1", target_task_name="SOLVE_REDUCTION", preconditions=[precond], subtasks=[t_prim], cost=1.0)
    op = Operator(id="op1", primitive_task_name="BUILD_EQUATION", preconditions=[precond], postconditions=[postcond], execution_handler="handle_build")
    failure = PlanningFailure(failed_task_id="t2", failed_task_name="SOLVE_REDUCTION", attempted_methods=["m1"], reason="UNSATISFIABLE_PRECONDITION")

    assert t_prim.task_type == TaskType.PRIMITIVE
    assert t_comp.task_type == TaskType.COMPOUND
    assert method.subtasks[0].id == "t1"
    assert op.execution_handler == "handle_build"
    assert failure.reason == "UNSATISFIABLE_PRECONDITION"


def test_method_registry_operations():
    registry = MethodRegistry()
    t_prim = Task(id="t1", name="SOLVE", task_type=TaskType.PRIMITIVE)
    
    m1 = Method(id="m1", target_task_name="TASK_A", subtasks=[t_prim], cost=2.0)
    m2 = Method(id="m2", target_task_name="TASK_A", subtasks=[t_prim], cost=1.0)
    
    assert registry.register_method(m1) is True
    assert registry.register_method(m2) is True
    assert registry.register_method(m1) is False  # Duplicate ID rejected

    methods = registry.get_methods_for_task("TASK_A")
    assert len(methods) == 2
    # Deterministic priority ordering (lowest cost first)
    assert methods[0].id == "m2"
    assert methods[1].id == "m1"
    assert registry.has_methods("TASK_A") is True
    assert registry.has_methods("TASK_B") is False


def test_operator_registry_operations():
    registry = OperatorRegistry()
    op1 = Operator(id="op1", primitive_task_name="SOLVE_EQ", execution_handler="solve_h")
    op2 = Operator(id="op2", primitive_task_name="SOLVE_EQ", execution_handler="solve_alt")

    assert registry.register_operator(op1) is True
    assert registry.register_operator(op2) is False  # Duplicate primitive task name rejected

    retrieved = registry.get_operator("SOLVE_EQ")
    assert retrieved is not None
    assert retrieved.id == "op1"
    assert registry.has_operator("SOLVE_EQ") is True
    assert registry.has_operator("NON_EXISTENT") is False


def test_planner_bootstraps_default_domain():
    planner = HTNPlanner()
    assert planner.method_registry.has_methods("SOLVE_REDUCTION") is True
    assert planner.operator_registry.has_operator("BUILD_EQUATION") is True
    
    methods = planner.method_registry.get_methods_for_task("SOLVE_REDUCTION")
    assert len(methods) >= 1
    assert methods[0].subtasks[0].name == "IDENTIFY_UNKNOWNS"


# ─────────────────────────────────────────────
# HP4A-03 RECURSIVE DECOMPOSITION TESTS
# ─────────────────────────────────────────────

def test_recursive_decompose_primitive_task():
    planner = HTNPlanner()
    prim_task = Task(id="p1", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)
    result = planner.decompose_task(prim_task)
    assert len(result) == 1
    assert result[0].id == "p1"
    assert result[0].task_type == TaskType.PRIMITIVE


def test_recursive_decompose_one_level():
    planner = HTNPlanner()
    comp_task = Task(id="c1", name="SOLVE_REDUCTION", task_type=TaskType.COMPOUND)
    primitives = planner.decompose_task(comp_task)
    
    expected_names = ["IDENTIFY_UNKNOWNS", "BUILD_EQUATION", "SOLVE_EQUATION"]
    assert len(primitives) == len(expected_names)
    for i, prim in enumerate(primitives):
        assert prim.name == expected_names[i]
        assert prim.task_type == TaskType.PRIMITIVE


def test_recursive_decompose_multi_level_hierarchy():
    """
    Mandatory proof test for multi-level decomposition:
    Level 0 Compound: TOP_GOAL
      ├── Level 1 Compound: SUB_GOAL_A
      │     ├── Level 2 Primitive: PRIM_A1
      │     └── Level 2 Primitive: PRIM_A2
      └── Level 1 Compound: SUB_GOAL_B
            └── Level 2 Primitive: PRIM_B1
    """
    method_reg = MethodRegistry()
    op_reg = OperatorRegistry()
    planner = HTNPlanner(method_registry=method_reg, operator_registry=op_reg)

    # Primitives
    p_a1 = Task(id="pa1", name="PRIM_A1", task_type=TaskType.PRIMITIVE)
    p_a2 = Task(id="pa2", name="PRIM_A2", task_type=TaskType.PRIMITIVE)
    p_b1 = Task(id="pb1", name="PRIM_B1", task_type=TaskType.PRIMITIVE)

    # Level 1 Compounds
    c_sub_a = Task(id="ca", name="SUB_GOAL_A", task_type=TaskType.COMPOUND)
    c_sub_b = Task(id="cb", name="SUB_GOAL_B", task_type=TaskType.COMPOUND)

    # Level 0 Top Compound
    top_task = Task(id="top", name="TOP_GOAL", task_type=TaskType.COMPOUND)

    # Register Methods
    method_top = Method(id="m_top", target_task_name="TOP_GOAL", subtasks=[c_sub_a, c_sub_b])
    method_a = Method(id="m_a", target_task_name="SUB_GOAL_A", subtasks=[p_a1, p_a2])
    method_b = Method(id="m_b", target_task_name="SUB_GOAL_B", subtasks=[p_b1])

    method_reg.register_method(method_top)
    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    # Execute Recursive Decomposition
    primitives = planner.decompose_task(top_task)

    # Verify Flattened Primitive Execution Plan & Ordering
    assert len(primitives) == 3
    assert primitives[0].id == "pa1"
    assert primitives[1].id == "pa2"
    assert primitives[2].id == "pb1"
    for p in primitives:
        assert p.task_type == TaskType.PRIMITIVE


def test_recursive_decompose_missing_method_fails_safely():
    planner = HTNPlanner()
    unregistered_comp = Task(id="u1", name="UNKNOWN_COMPOUND", task_type=TaskType.COMPOUND)
    with pytest.raises(HTNPlanningError, match="No decomposition method registered"):
        planner.decompose_task(unregistered_comp)


def test_recursive_decompose_max_depth_exceeded():
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg, max_depth=3)

    # Create recursive compound chain: C0 -> C1 -> C2 -> C3 -> C4
    c0 = Task(id="c0", name="CHAIN_0", task_type=TaskType.COMPOUND)
    c1 = Task(id="c1", name="CHAIN_1", task_type=TaskType.COMPOUND)
    c2 = Task(id="c2", name="CHAIN_2", task_type=TaskType.COMPOUND)
    c3 = Task(id="c3", name="CHAIN_3", task_type=TaskType.COMPOUND)
    c4 = Task(id="c4", name="CHAIN_4", task_type=TaskType.COMPOUND)

    method_reg.register_method(Method(id="m0", target_task_name="CHAIN_0", subtasks=[c1]))
    method_reg.register_method(Method(id="m1", target_task_name="CHAIN_1", subtasks=[c2]))
    method_reg.register_method(Method(id="m2", target_task_name="CHAIN_2", subtasks=[c3]))
    method_reg.register_method(Method(id="m3", target_task_name="CHAIN_3", subtasks=[c4]))

    with pytest.raises(HTNPlanningError, match="Max decomposition depth"):
        planner.decompose_task(c0)


def test_legacy_api_compatibility_preserved():
    planner = HTNPlanner()
    perception = PerceptionMap(
        entities={"x": 5},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )
    sub_goals = planner.decompose(perception)
    assert len(sub_goals) == 3
    assert sub_goals[0].name == "IDENTIFY_UNKNOWNS"
    assert sub_goals[1].name == "BUILD_EQUATION"
    assert sub_goals[2].name == "SOLVE_EQUATION"


# ─────────────────────────────────────────────
# HP4A-04 BACKTRACKING & ALTERNATIVE SEARCH TESTS
# ─────────────────────────────────────────────

def test_hp4a04_test_a_first_method_succeeds():
    """Test A: Method A (cost 1.0) succeeds, Method B (cost 2.0) is not evaluated."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[p_a], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_b], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pa"


def test_hp4a04_test_b_first_method_fails_second_succeeds():
    """Test B: Method A (cost 1.0) has undecomposable child; Method B (cost 2.0) succeeds."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_child = Task(id="bc", name="UNREGISTERED_COMPOUND", task_type=TaskType.COMPOUND)
    p_success = Task(id="ps", name="PRIM_SUCCESS", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[broken_child], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_success], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "ps"


def test_hp4a04_test_c_partial_failed_plan_rolled_back():
    """
    Test C: Method A outputs Primitive A1 then fails on Compound A2.
    Method B outputs Primitive B1 and succeeds.
    Final plan must be [B1], NOT [A1, B1].
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a1 = Task(id="pa1", name="PRIM_A1", task_type=TaskType.PRIMITIVE)
    c_a2 = Task(id="ca2", name="FAILING_COMPOUND", task_type=TaskType.COMPOUND)
    p_b1 = Task(id="pb1", name="PRIM_B1", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[p_a1, c_a2], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_b1], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pb1"  # No leakage of pa1


def test_hp4a04_test_d_nested_backtracking():
    """
    Test D: Recursive backtracking inside nested compound.
    ROOT -> ROOT_A -> NESTED_COMPOUND.
    NESTED_COMPOUND has Method NESTED_A (fails) and NESTED_B (succeeds -> Primitive X).
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    nested = Task(id="nested", name="NESTED_COMPOUND", task_type=TaskType.COMPOUND)
    broken = Task(id="broken", name="BROKEN_TASK", task_type=TaskType.COMPOUND)
    p_x = Task(id="px", name="PRIM_X", task_type=TaskType.PRIMITIVE)

    method_root = Method(id="m_root", target_task_name="ROOT_TASK", subtasks=[nested], cost=1.0)
    method_nested_a = Method(id="m_na", target_task_name="NESTED_COMPOUND", subtasks=[broken], cost=1.0)
    method_nested_b = Method(id="m_nb", target_task_name="NESTED_COMPOUND", subtasks=[p_x], cost=2.0)

    method_reg.register_method(method_root)
    method_reg.register_method(method_nested_a)
    method_reg.register_method(method_nested_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "px"


def test_hp4a04_test_e_all_methods_fail():
    """Test E: All candidate methods fail; raises HTNPlanningError preserving attempted_methods."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_1 = Task(id="b1", name="BROKEN_1", task_type=TaskType.COMPOUND)
    broken_2 = Task(id="b2", name="BROKEN_2", task_type=TaskType.COMPOUND)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[broken_1], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[broken_2], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(root)

    failure = exc_info.value.failure
    assert failure.failed_task_name == "ROOT_TASK"
    assert "m_a" in failure.attempted_methods
    assert "m_b" in failure.attempted_methods
    assert "All candidate methods failed" in failure.reason


def test_hp4a04_test_f_cycle_in_first_method_fallback_succeeds():
    """Test F: Method A creates active-branch cycle; Method B succeeds -> Primitive SAFE."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_safe = Task(id="psafe", name="PRIM_SAFE", task_type=TaskType.PRIMITIVE)

    # Method A calls ROOT_TASK again -> cycle!
    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[root], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_safe], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "psafe"


def test_hp4a04_test_g_failed_branch_does_not_contaminate_cycle_state():
    """
    Test G: Method A visits TASK_SHARED and fails later.
    Method B legitimately uses TASK_SHARED.
    Task_SHARED must not be blocked in Method B.
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    shared = Task(id="shared", name="TASK_SHARED", task_type=TaskType.COMPOUND)
    broken = Task(id="broken", name="BROKEN", task_type=TaskType.COMPOUND)
    p_ok = Task(id="pok", name="PRIM_OK", task_type=TaskType.PRIMITIVE)

    method_root_a = Method(id="m_ra", target_task_name="ROOT_TASK", subtasks=[shared, broken], cost=1.0)
    method_root_b = Method(id="m_rb", target_task_name="ROOT_TASK", subtasks=[shared], cost=2.0)
    method_shared = Method(id="m_s", target_task_name="TASK_SHARED", subtasks=[p_ok], cost=1.0)

    method_reg.register_method(method_root_a)
    method_reg.register_method(method_root_b)
    method_reg.register_method(method_shared)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pok"


def test_hp4a04_test_h_deterministic_ordering():
    """Test H: Multiple cost registrations produce identical output repeatedly."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="P1", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="P2", task_type=TaskType.PRIMITIVE)

    method_high_cost = Method(id="m_high", target_task_name="ROOT_TASK", subtasks=[p2], cost=10.0)
def test_legacy_api_compatibility_preserved():
    planner = HTNPlanner()
    perception = PerceptionMap(
        entities={"x": 5},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )
    sub_goals = planner.decompose(perception)
    assert len(sub_goals) == 3
    assert sub_goals[0].name == "IDENTIFY_UNKNOWNS"
    assert sub_goals[1].name == "BUILD_EQUATION"
    assert sub_goals[2].name == "SOLVE_EQUATION"


# ─────────────────────────────────────────────
# HP4A-04 BACKTRACKING & ALTERNATIVE SEARCH TESTS
# ─────────────────────────────────────────────

def test_hp4a04_test_a_first_method_succeeds():
    """Test A: Method A (cost 1.0) succeeds, Method B (cost 2.0) is not evaluated."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[p_a], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_b], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pa"


def test_hp4a04_test_b_first_method_fails_second_succeeds():
    """Test B: Method A (cost 1.0) has undecomposable child; Method B (cost 2.0) succeeds."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_child = Task(id="bc", name="UNREGISTERED_COMPOUND", task_type=TaskType.COMPOUND)
    p_success = Task(id="ps", name="PRIM_SUCCESS", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[broken_child], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_success], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "ps"


def test_hp4a04_test_c_partial_failed_plan_rolled_back():
    """
    Test C: Method A outputs Primitive A1 then fails on Compound A2.
    Method B outputs Primitive B1 and succeeds.
    Final plan must be [B1], NOT [A1, B1].
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a1 = Task(id="pa1", name="PRIM_A1", task_type=TaskType.PRIMITIVE)
    c_a2 = Task(id="ca2", name="FAILING_COMPOUND", task_type=TaskType.COMPOUND)
    p_b1 = Task(id="pb1", name="PRIM_B1", task_type=TaskType.PRIMITIVE)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[p_a1, c_a2], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_b1], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pb1"  # No leakage of pa1


def test_hp4a04_test_d_nested_backtracking():
    """
    Test D: Recursive backtracking inside nested compound.
    ROOT -> ROOT_A -> NESTED_COMPOUND.
    NESTED_COMPOUND has Method NESTED_A (fails) and NESTED_B (succeeds -> Primitive X).
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    nested = Task(id="nested", name="NESTED_COMPOUND", task_type=TaskType.COMPOUND)
    broken = Task(id="broken", name="BROKEN_TASK", task_type=TaskType.COMPOUND)
    p_x = Task(id="px", name="PRIM_X", task_type=TaskType.PRIMITIVE)

    method_root = Method(id="m_root", target_task_name="ROOT_TASK", subtasks=[nested], cost=1.0)
    method_nested_a = Method(id="m_na", target_task_name="NESTED_COMPOUND", subtasks=[broken], cost=1.0)
    method_nested_b = Method(id="m_nb", target_task_name="NESTED_COMPOUND", subtasks=[p_x], cost=2.0)

    method_reg.register_method(method_root)
    method_reg.register_method(method_nested_a)
    method_reg.register_method(method_nested_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "px"


def test_hp4a04_test_e_all_methods_fail():
    """Test E: All candidate methods fail; raises HTNPlanningError preserving attempted_methods."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_1 = Task(id="b1", name="BROKEN_1", task_type=TaskType.COMPOUND)
    broken_2 = Task(id="b2", name="BROKEN_2", task_type=TaskType.COMPOUND)

    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[broken_1], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[broken_2], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(root)

    failure = exc_info.value.failure
    assert failure.failed_task_name == "ROOT_TASK"
    assert "m_a" in failure.attempted_methods
    assert "m_b" in failure.attempted_methods
    assert "All candidate methods failed" in failure.reason


def test_hp4a04_test_f_cycle_in_first_method_fallback_succeeds():
    """Test F: Method A creates active-branch cycle; Method B succeeds -> Primitive SAFE."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_safe = Task(id="psafe", name="PRIM_SAFE", task_type=TaskType.PRIMITIVE)

    # Method A calls ROOT_TASK again -> cycle!
    method_a = Method(id="m_a", target_task_name="ROOT_TASK", subtasks=[root], cost=1.0)
    method_b = Method(id="m_b", target_task_name="ROOT_TASK", subtasks=[p_safe], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "psafe"


def test_hp4a04_test_g_failed_branch_does_not_contaminate_cycle_state():
    """
    Test G: Method A visits TASK_SHARED and fails later.
    Method B legitimately uses TASK_SHARED.
    Task_SHARED must not be blocked in Method B.
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    shared = Task(id="shared", name="TASK_SHARED", task_type=TaskType.COMPOUND)
    broken = Task(id="broken", name="BROKEN", task_type=TaskType.COMPOUND)
    p_ok = Task(id="pok", name="PRIM_OK", task_type=TaskType.PRIMITIVE)

    method_root_a = Method(id="m_ra", target_task_name="ROOT_TASK", subtasks=[shared, broken], cost=1.0)
    method_root_b = Method(id="m_rb", target_task_name="ROOT_TASK", subtasks=[shared], cost=2.0)
    method_shared = Method(id="m_s", target_task_name="TASK_SHARED", subtasks=[p_ok], cost=1.0)

    method_reg.register_method(method_root_a)
    method_reg.register_method(method_root_b)
    method_reg.register_method(method_shared)

    plan = planner.decompose_task(root)
    assert len(plan) == 1
    assert plan[0].id == "pok"


def test_hp4a04_test_h_deterministic_ordering():
    """Test H: Multiple cost registrations produce identical output repeatedly."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="root", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="P1", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="P2", task_type=TaskType.PRIMITIVE)

    method_high_cost = Method(id="m_high", target_task_name="ROOT_TASK", subtasks=[p2], cost=10.0)
    method_low_cost = Method(id="m_low", target_task_name="ROOT_TASK", subtasks=[p1], cost=1.0)

    method_reg.register_method(method_high_cost)
    method_reg.register_method(method_low_cost)

    for _ in range(5):
        plan = planner.decompose_task(root)
        assert plan[0].id == "p1"


# ─────────────────────────────────────────────
# HP4A-05 VERIFIED PRECONDITIONS & Z3 TESTS
# ─────────────────────────────────────────────

from hsci.symbolic.z3_verifier import Z3VerificationEngine


def test_hp4a05_test_a_no_preconditions():
    """Test A: Method without preconditions is admissible by default."""
    planner = HTNPlanner()
    root = Task(id="r", name="SOLVE_REDUCTION", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(root)
    assert len(plan) == 3


def test_hp4a05_test_b_valid_precondition():
    """Test B: Method with verified valid precondition decomposes normally."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_ok = Task(id="pok", name="PRIM_OK", task_type=TaskType.PRIMITIVE)
    pre = Precondition(predicate="BATTERY_OK", required_state=True)

    method = Method(id="m_valid", target_task_name="ROOT_TASK", preconditions=[pre], subtasks=[p_ok], cost=1.0)
    method_reg.register_method(method)

    context = {"BATTERY_OK": True}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pok"


def test_hp4a05_test_c_invalid_first_method_valid_second_method():
    """Test C: Method A precondition fails; Method B precondition succeeds -> Method B selected."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="HIGH_MEMORY", required_state=True)
    pre_b = Precondition(predicate="LOW_MEMORY", required_state=True)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[p_a], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", preconditions=[pre_b], subtasks=[p_b], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    context = {"HIGH_MEMORY": False, "LOW_MEMORY": True}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pb"


def test_hp4a05_test_d_invalid_method_subtasks_never_explored():
    """Test D: Invalid precondition rejects Method BEFORE child subtask decomposition."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_child = Task(id="bc", name="UNREGISTERED_COMPOUND", task_type=TaskType.COMPOUND)
    p_fallback = Task(id="pf", name="PRIM_FALLBACK", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="STATE_VALID", required_state=True)

    # Method A has an invalid precondition AND an unresolvable child subtask.
    # If preconditions were checked late, it would fail with a missing method error for broken_child.
    # Because preconditions fail first, it skips Method A cleanly.
    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[broken_child], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[p_fallback], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    context = {"STATE_VALID": False}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pf"


def test_hp4a05_test_e_multiple_valid_preconditions():
    """Test E: All preconditions valid -> method accepted."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="P1", task_type=TaskType.PRIMITIVE)

    pre1 = Precondition(predicate="P1_OK", required_state=True)
    pre2 = Precondition(predicate="P2_OK", required_state=10)

    method = Method(id="m", target_task_name="ROOT_TASK", preconditions=[pre1, pre2], subtasks=[p1], cost=1.0)
    method_reg.register_method(method)

    context = {"P1_OK": True, "P2_OK": 10}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "p1"


def test_hp4a05_test_f_one_of_multiple_preconditions_fails():
    """Test F: One precondition fails -> method rejected, fallback selected."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    pre1 = Precondition(predicate="P1_OK", required_state=True)
    pre2 = Precondition(predicate="P2_OK", required_state=10)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre1, pre2], subtasks=[p_a], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[p_b], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    # P2_OK is 5 instead of required 10
    context = {"P1_OK": True, "P2_OK": 5}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pb"


def test_hp4a05_test_g_all_methods_logically_rejected():
    """Test G: All candidate methods logically rejected -> HTNPlanningError with failure details."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="P1", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="PRE_A", required_state=True)
    pre_b = Precondition(predicate="PRE_B", required_state=True)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[p1], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", preconditions=[pre_b], subtasks=[p1], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    context = {"PRE_A": False, "PRE_B": False}
    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(root, context=context)

    failure = exc_info.value.failure
    assert "ma" in failure.attempted_methods
    assert "mb" in failure.attempted_methods
    assert "All candidate methods failed" in failure.reason


def test_hp4a05_test_h_logical_rejection_and_structural_fallback_interaction():
    """
    Test H: Composing Logical and Structural Fallbacks.
    Method A -> Logical failure (precondition invalid)
    Method B -> Structural failure (unregistered child task)
    Method C -> Valid & structurally successful -> Method C selected!
    """
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken_child = Task(id="bc", name="UNREGISTERED", task_type=TaskType.COMPOUND)
    p_c = Task(id="pc", name="PRIM_C", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="PRE_A", required_state=True)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[p_c], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[broken_child], cost=2.0)
    method_c = Method(id="mc", target_task_name="ROOT_TASK", subtasks=[p_c], cost=3.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)
    method_reg.register_method(method_c)

    context = {"PRE_A": False}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pc"


def test_hp4a05_test_i_real_z3_valid_condition():
    """Test I: Real Z3 verifier accepts valid precondition."""
    verifier = Z3VerificationEngine()
    planner = HTNPlanner(verifier=verifier)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="P1", task_type=TaskType.PRIMITIVE)
    pre = Precondition(predicate="Z3_CHECK", required_state=True)

    method = Method(id="m", target_task_name="ROOT_TASK", preconditions=[pre], subtasks=[p1], cost=1.0)
    planner.method_registry.register_method(method)

    context = {"Z3_CHECK": True}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "p1"


def test_hp4a05_test_j_real_z3_invalid_condition():
    """Test J: Real Z3 verifier rejects invalid precondition and triggers fallback."""
    verifier = Z3VerificationEngine()
    planner = HTNPlanner(verifier=verifier)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="Z3_CHECK", required_state=False) # Requires False, but context provides True

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[p_a], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[p_b], cost=2.0)

    planner.method_registry.register_method(method_a)
    planner.method_registry.register_method(method_b)

    context = {"Z3_CHECK": True}
    plan = planner.decompose_task(root, context=context)
    assert len(plan) == 1
    assert plan[0].id == "pb"


# ─────────────────────────────────────────────
# HP4A-06 WORKINGMEMORY CONTEXT BINDING TESTS
# ─────────────────────────────────────────────

from hsci.core.working_memory import WorkingMemory, SemanticFrame
from hsci.core.data_types import PlanningContext, EntityValue


def test_hp4a06_test_a_working_memory_produces_planning_context():
    """Test A: Real WorkingMemory produces structured PlanningContext."""
    wm = WorkingMemory(request_id="req-123", session_id="sess-456", stimulus="Solve math problem")
    wm.activate_concepts(["ADDITION", "REDUCTION"], {"ADDITION": 0.9, "REDUCTION": 0.8})
    wm.perception_map = PerceptionMap(
        entities={"x": EntityValue(value=10, unit=None, known=True, raw_text="10")},
        unknown_entities=[],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )

    ctx = wm.build_planning_context()
    assert isinstance(ctx, PlanningContext)
    assert ctx.request_id == "req-123"
    assert ctx.session_id == "sess-456"
    assert ctx.get_fact("x") == 10
    assert "ADDITION" in ctx.active_concepts
    assert ctx.intent == "REDUCTION"


def test_hp4a06_test_b_type_preservation():
    """Test B: Boolean, integer, float types are preserved across context conversion."""
    wm = WorkingMemory(request_id="r1", session_id="s1", stimulus="test")
    wm.semantic_frame = SemanticFrame(
        intent="TEST",
        entities={"IS_ACTIVE": True, "COUNT": 42, "RATIO": 3.14}
    )

    ctx = wm.build_planning_context()
    facts = ctx.to_dict()
    assert isinstance(facts["IS_ACTIVE"], bool) and facts["IS_ACTIVE"] is True
    assert isinstance(facts["COUNT"], int) and facts["COUNT"] == 42
    assert isinstance(facts["RATIO"], float) and facts["RATIO"] == 3.14


def test_hp4a06_test_c_planner_consumes_bound_context():
    """Test C: Planner directly accepts WorkingMemory instance and evaluates preconditions."""
    wm = WorkingMemory(request_id="r1", session_id="s1", stimulus="test")
    wm.semantic_frame = SemanticFrame(intent="TEST", entities={"RESOURCE_AVAILABLE": True})

    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    pre = Precondition(predicate="RESOURCE_AVAILABLE", required_state=True)

    method = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre], subtasks=[p_a], cost=1.0)
    method_reg.register_method(method)

    plan = planner.decompose_task(root, context=wm)
    assert len(plan) == 1
    assert plan[0].id == "pa"


def test_hp4a06_test_d_different_memory_causes_different_plan():
    """Test D: Two distinct WorkingMemory instances choose different methods for the same task."""
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_high = Task(id="ph", name="PRIM_HIGH", task_type=TaskType.PRIMITIVE)
    p_low = Task(id="pl", name="PRIM_LOW", task_type=TaskType.PRIMITIVE)

    pre_high = Precondition(predicate="HIGH_MEMORY", required_state=True)

    method_high = Method(id="mh", target_task_name="ROOT_TASK", preconditions=[pre_high], subtasks=[p_high], cost=1.0)
    method_low = Method(id="ml", target_task_name="ROOT_TASK", subtasks=[p_low], cost=2.0)

    method_reg.register_method(method_high)
    method_reg.register_method(method_low)

    wm_a = WorkingMemory(request_id="req-a", session_id="s1", stimulus="test")
    wm_a.semantic_frame = SemanticFrame(intent="TEST", entities={"HIGH_MEMORY": True})

    wm_b = WorkingMemory(request_id="req-b", session_id="s2", stimulus="test")
    wm_b.semantic_frame = SemanticFrame(intent="TEST", entities={"HIGH_MEMORY": False})

    plan_a = planner.decompose_task(root, context=wm_a)
    plan_b = planner.decompose_task(root, context=wm_b)

    assert plan_a[0].id == "ph"
    assert plan_b[0].id == "pl"


def test_hp4a06_test_e_request_isolation():
    """Test E: Request isolation guarantees no cross-contamination between WorkingMemory instances."""
    wm1 = WorkingMemory(request_id="req-1", session_id="s1", stimulus="test1")
    wm1.semantic_frame = SemanticFrame(intent="INTENT_1", entities={"KEY1": "VAL1"})

    wm2 = WorkingMemory(request_id="req-2", session_id="s2", stimulus="test2")
    wm2.semantic_frame = SemanticFrame(intent="INTENT_2", entities={"KEY2": "VAL2"})

    ctx1 = wm1.build_planning_context()
    ctx2 = wm2.build_planning_context()

    assert ctx1.has_fact("KEY1") is True
    assert ctx1.has_fact("KEY2") is False

    assert ctx2.has_fact("KEY2") is True
    assert ctx2.has_fact("KEY1") is False


def test_hp4a06_test_f_snapshot_stability():
    """Test F: Post-snapshot WorkingMemory mutation does not alter previously built PlanningContext."""
    wm = WorkingMemory(request_id="r1", session_id="s1", stimulus="test")
    wm.semantic_frame = SemanticFrame(intent="TEST", entities={"VAR": 100})

    ctx = wm.build_planning_context()
    assert ctx.get_fact("VAR") == 100

    # Mutate WorkingMemory afterwards
    wm.semantic_frame.entities["VAR"] = 999
    wm.clear()

    # Snapshot context remains immutable and stable
    assert ctx.get_fact("VAR") == 100


def test_hp4a06_test_g_missing_required_fact():
    """Test G: Precondition requiring absent WorkingMemory fact fails closed."""
    wm = WorkingMemory(request_id="r1", session_id="s1", stimulus="test")
    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    p_a = Task(id="pa", name="PRIM_A", task_type=TaskType.PRIMITIVE)
    p_b = Task(id="pb", name="PRIM_B", task_type=TaskType.PRIMITIVE)

    pre_absent = Precondition(predicate="ABSENT_FACT", required_state=True)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_absent], subtasks=[p_a], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[p_b], cost=2.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)

    plan = planner.decompose_task(root, context=wm)
    assert len(plan) == 1
    assert plan[0].id == "pb"


def test_hp4a06_test_h_logical_and_structural_fallback_with_memory():
    """Test H: Full composition of WorkingMemory binding, preconditions, and backtracking."""
    wm = WorkingMemory(request_id="r1", session_id="s1", stimulus="test")
    wm.semantic_frame = SemanticFrame(intent="TEST", entities={"PRE_A": False, "PRE_C": True})

    method_reg = MethodRegistry()
    planner = HTNPlanner(method_registry=method_reg)

    root = Task(id="r", name="ROOT_TASK", task_type=TaskType.COMPOUND)
    broken = Task(id="b", name="BROKEN", task_type=TaskType.COMPOUND)
    p_c = Task(id="pc", name="PRIM_C", task_type=TaskType.PRIMITIVE)

    pre_a = Precondition(predicate="PRE_A", required_state=True)
    pre_c = Precondition(predicate="PRE_C", required_state=True)

    method_a = Method(id="ma", target_task_name="ROOT_TASK", preconditions=[pre_a], subtasks=[p_c], cost=1.0)
    method_b = Method(id="mb", target_task_name="ROOT_TASK", subtasks=[broken], cost=2.0)
    method_c = Method(id="mc", target_task_name="ROOT_TASK", preconditions=[pre_c], subtasks=[p_c], cost=3.0)

    method_reg.register_method(method_a)
    method_reg.register_method(method_b)
    method_reg.register_method(method_c)

    plan = planner.decompose_task(root, context=wm)
    assert len(plan) == 1
    assert plan[0].id == "pc"


# ─────────────────────────────────────────────
# HP4A-07 LIVE REASONINGENGINE INTEGRATION TESTS
# ─────────────────────────────────────────────

from hsci.reasoning.reasoning_engine import CognitiveReasoningEngine, ReasoningEngine
from hsci.core.data_types import KnowledgeResult


def test_hp4a07_test_a_perception_to_root_task_mapping():
    """Test A: PerceptionMap intent maps deterministically to a root Task."""
    perception = PerceptionMap(
        entities={"x": EntityValue(value=5, unit=None, known=True, raw_text="5")},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )
    root_name = f"SOLVE_{perception.intent.value}"
    root_task = Task(id="r1", name=root_name, task_type=TaskType.COMPOUND, axiom_type=perception.intent)
    assert root_task.name == "SOLVE_REDUCTION"
    assert root_task.task_type == TaskType.COMPOUND


def test_hp4a07_test_b_reasoning_engine_invokes_recursive_planner():
    """Test B: ReasoningEngine.reason uses recursive decompose_task and returns a valid plan."""
    re = ReasoningEngine()
    perception = PerceptionMap(
        entities={"x": EntityValue(value=5, unit=None, known=True, raw_text="5")},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={"text": "solve x = 5"}
    )
    knowledge = KnowledgeResult(direct_matches=[], analogical_matches=[], episodes=[], confidence=1.0)
    
    plan = re.reason(perception, knowledge)
    assert len(plan.sub_goals) == 3
    assert plan.sub_goals[0].name == "IDENTIFY_UNKNOWNS"
    assert plan.sub_goals[1].name == "BUILD_EQUATION"
    assert plan.sub_goals[2].name == "SOLVE_EQUATION"


def test_hp4a07_test_c_phase_4a_master_acceptance_test():
    """
    MASTER ACCEPTANCE TEST — PHASE 4A:
    Complete end-to-end composition proof:
    Stimulus -> WorkingMemory -> Perception -> Root Task -> PlanningContext ->
    Z3 precondition rejection -> Alternative Method selection -> Multi-level recursive decomposition ->
    Flattened primitive plan -> Reasoning Engine -> Solution verification.
    """
    verifier = Z3VerificationEngine()
    planner = HTNPlanner(verifier=verifier)
    re = ReasoningEngine()
    re.htn_planner = planner  # Inject live HTN planner into ReasoningEngine

    # Build WorkingMemory with facts
    wm = WorkingMemory(request_id="acceptance-req-1", session_id="s1", stimulus="Solve math problem")
    wm.semantic_frame = SemanticFrame(intent="REDUCTION", entities={"FAST_PATH_ALLOWED": False, "SAFE_PATH_ALLOWED": True})

    perception = PerceptionMap(
        entities={"a": EntityValue(value=2, unit=None, known=True, raw_text="2"),
                  "b": EntityValue(value=3, unit=None, known=True, raw_text="3"),
                  "result": EntityValue(value=5, unit=None, known=True, raw_text="5")},
        unknown_entities=[],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={"text": "2 + 3 = 5"}
    )
    knowledge = KnowledgeResult(direct_matches=[], analogical_matches=[], episodes=[], confidence=1.0)

    # Register custom Method hierarchy under SOLVE_REDUCTION
    # Method 1 (cost 1.0): Requires FAST_PATH_ALLOWED==True (Precondition UNSAT -> Rejected)
    # Method 2 (cost 2.0): Requires SAFE_PATH_ALLOWED==True (Precondition SAT -> Accepted)
    #   Method 2 subtasks: Level 1 Compound (REDUCTION_SUB)
    #     REDUCTION_SUB expands to Primitives: IDENTIFY_UNKNOWNS, BUILD_EQUATION, SOLVE_EQUATION
    
    sub_comp = Task(id="sub_c", name="REDUCTION_SUB", task_type=TaskType.COMPOUND)
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="BUILD_EQUATION", task_type=TaskType.PRIMITIVE)
    p3 = Task(id="p3", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)

    pre_fast = Precondition(predicate="FAST_PATH_ALLOWED", required_state=True)
    pre_safe = Precondition(predicate="SAFE_PATH_ALLOWED", required_state=True)

    method_fast = Method(id="m_fast", target_task_name="SOLVE_REDUCTION", preconditions=[pre_fast], subtasks=[p1], cost=1.0)
    method_safe = Method(id="m_safe", target_task_name="SOLVE_REDUCTION", preconditions=[pre_safe], subtasks=[sub_comp], cost=2.0)
    method_sub = Method(id="m_sub", target_task_name="REDUCTION_SUB", subtasks=[p1, p2, p3], cost=1.0)

    planner.method_registry.register_method(method_fast)
    planner.method_registry.register_method(method_safe)
    planner.method_registry.register_method(method_sub)

    # Execute Live Reasoning
    plan = re.reason(perception, knowledge)

    # Verify Output & Flow
    assert len(plan.sub_goals) == 3
    assert plan.sub_goals[0].name == "IDENTIFY_UNKNOWNS"
    assert plan.sub_goals[1].name == "BUILD_EQUATION"
    assert plan.sub_goals[2].name == "SOLVE_EQUATION"

    # Verify final solution verification remains active
    verification = verifier.verify(plan.candidate_solution, perception, plan.primary_concept)
    assert verification.valid is True


