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
