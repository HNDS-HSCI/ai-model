import pytest
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.core.data_types import PerceptionMap, AxiomType, SubGoal

@pytest.fixture
def htn_planner():
    return HTNPlanner()

def create_perception_map(intent: AxiomType) -> PerceptionMap:
    return PerceptionMap(
        entities={},
        unknown_entities=[],
        relationships=[],
        intent=intent,
        confidence=1.0,
        entity_graph=None
    )

def test_decompose_reduction_problem(htn_planner):
    perception = create_perception_map(AxiomType.REDUCTION)
    sub_goals = htn_planner.decompose(perception)

    expected_goals = [
        SubGoal(name="IDENTIFY_UNKNOWNS", description="Identify variables to solve for."),
        SubGoal(name="BUILD_EQUATION", description="Construct a mathematical equation."),
        SubGoal(name="SOLVE_EQUATION", description="Solve the mathematical equation.")
    ]
    assert len(sub_goals) == len(expected_goals)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_goals[i].name
        assert goal.description == expected_goals[i].description

def test_decompose_composition_problem(htn_planner):
    perception = create_perception_map(AxiomType.COMPOSITION)
    sub_goals = htn_planner.decompose(perception)

    expected_goals = [
        SubGoal(name="EXTRACT_ENTITIES", description="Extract all relevant entities."),
        SubGoal(name="IDENTIFY_RELATIONSHIPS", description="Determine relationships between entities."),
        SubGoal(name="BUILD_CONSTRAINT_NETWORK", description="Construct a network of constraints.")
    ]
    assert len(sub_goals) == len(expected_goals)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_goals[i].name
        assert goal.description == expected_goals[i].description

def test_decompose_synthesis_problem(htn_planner):
    perception = create_perception_map(AxiomType.SYNTHESIS)
    sub_goals = htn_planner.decompose(perception)

    expected_goals = [
        SubGoal(name="DEFINE_INPUTS_OUTPUTS", description="Define inputs and expected outputs."),
        SubGoal(name="IDENTIFY_ALGORITHM_PATTERN", description="Identify suitable algorithmic patterns."),
        SubGoal(name="BUILD_PROCEDURE", description="Construct the procedural logic."),
        SubGoal(name="VERIFY_INVARIANTS", description="Verify algorithmic invariants.")
    ]
    assert len(sub_goals) == len(expected_goals)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_goals[i].name
        assert goal.description == expected_goals[i].description

def test_decompose_transformation_problem(htn_planner):
    perception = create_perception_map(AxiomType.TRANSFORMATION)
    sub_goals = htn_planner.decompose(perception)

    expected_goals = [
        SubGoal(name="PARSE_SOURCE_STRUCTURE", description="Parse the source information structure."),
        SubGoal(name="IDENTIFY_TARGET_STRUCTURE", description="Identify the target information structure."),
        SubGoal(name="MAP_TRANSFORMATION_RULES", description="Map rules for transformation."),
        SubGoal(name="APPLY_TRANSFORMATION", description="Apply transformation rules.")
    ]
    assert len(sub_goals) == len(expected_goals)
    for i, goal in enumerate(sub_goals):
        assert goal.name == expected_goals[i].name
        assert goal.description == expected_goals[i].description

def test_decompose_unknown_axiom_type(htn_planner):
    # Mock a PerceptionMap with an intent that is not a valid AxiomType
    # This simulates an unexpected intent value for testing the 'else' branch
    mock_perception = PerceptionMap(
        entities={},
        unknown_entities=[],
        relationships=[],
        intent="UNKNOWN_INTENT_TYPE", # Pass a string that is not in AxiomType
        confidence=0.0,
        entity_graph=None
    )
    mock_perception.intent = "UNKNOWN_INTENT_TYPE" # Ensure it's not a valid enum member

    sub_goals = htn_planner.decompose(mock_perception)

    expected_goals = [
        SubGoal(name="UNKNOWN_INTENT_HANDLING", description="Handle unknown or unclassifiable intent.")
    ]
    assert len(sub_goals) == len(expected_goals)
    assert sub_goals[0].name == expected_goals[0].name
    assert sub_goals[0].description == expected_goals[0].description
