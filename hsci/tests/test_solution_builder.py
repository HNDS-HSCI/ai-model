import pytest
import z3
from datetime import datetime
from hsci.core.data_types import SubGoal, Concept, Expression, AxiomType, EntityValue
from hsci.reasoning.solution_builder import SolutionBuilder

@pytest.fixture
def solution_builder():
    return SolutionBuilder()

@pytest.fixture
def sample_sub_goal_solve():
    return SubGoal(
        name="SOLVE_EQUATION",
        description="Solve the mathematical equation.",
        required_entities=[],
        target_entity="",
        axiom_type=AxiomType.REDUCTION
    )

@pytest.fixture
def sample_concept_addition():
    return Concept(
        id="addition",
        name="ADDITION",
        axiom_type=AxiomType.REDUCTION,
        abstract_rule="a + b = result",
        z3_template="result == a + b",
        domain="arithmetic",
        learned_from_domains=["arithmetic"],
        strength=1.0,
        proof_count=100,
        created_at=datetime.now(),
        last_used=datetime.now(),
        generalizes_to=[],
        required_entities=["a", "b"],
        optional_entities=["result"],
        z3_verified=True
    )

@pytest.fixture
def sample_concept_subtraction():
    return Concept(
        id="subtraction",
        name="SUBTRACTION",
        axiom_type=AxiomType.REDUCTION,
        abstract_rule="a - b = result",
        z3_template="result == a - b",
        domain="arithmetic",
        learned_from_domains=["arithmetic"],
        strength=1.0,
        proof_count=100,
        created_at=datetime.now(),
        last_used=datetime.now(),
        generalizes_to=[],
        required_entities=["a", "b"],
        optional_entities=["result"],
        z3_verified=True
    )

@pytest.fixture
def sample_concept_multiplication():
    return Concept(
        id="multiplication",
        name="MULTIPLICATION",
        axiom_type=AxiomType.REDUCTION,
        abstract_rule="a * b = result",
        z3_template="result == a * b",
        domain="arithmetic",
        learned_from_domains=["arithmetic"],
        strength=1.0,
        proof_count=100,
        created_at=datetime.now(),
        last_used=datetime.now(),
        generalizes_to=[],
        required_entities=["a", "b"],
        optional_entities=["result"],
        z3_verified=True
    )

def test_build_generic_expression(solution_builder):
    sub_goals = [SubGoal(name="GENERIC_TASK", description="Generic task")]
    concept_assignments = {sub_goals[0]: Concept(id="generic", name="GENERIC", axiom_type=AxiomType.REDUCTION, abstract_rule="", z3_template="", domain="", learned_from_domains=[], strength=0.5, proof_count=0, created_at=datetime.now(), last_used=datetime.now(), generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False)}
    entities = {}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    assert expression.value == "dummy_solution_expression"
    assert expression.concepts_used == [] # Matches implementation fallback

def test_build_addition_expression(solution_builder, sample_sub_goal_solve, sample_concept_addition):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_addition}
    entities = {'a': 2, 'b': 3, 'result': 5}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    
    # Use real variables for expected expression
    a, b, result = z3.Reals('a b result')
    expected_z3_expr = (result == a + b)

    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat 
    assert expression.concepts_used == ["addition"]

def test_build_subtraction_expression(solution_builder, sample_sub_goal_solve, sample_concept_subtraction):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_subtraction}
    entities = {'a': 10, 'b': 7, 'result': 3}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)

    a, b, result = z3.Reals('a b result')
    expected_z3_expr = (result == a - b)

    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat
    assert expression.concepts_used == ["subtraction"]

def test_build_multiplication_expression(solution_builder, sample_sub_goal_solve, sample_concept_multiplication):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_multiplication}
    entities = {'a': 4, 'b': 6, 'result': 24}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)

    a, b, result = z3.Reals('a b result')
    expected_z3_expr = (result == a * b)

    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat
    assert expression.concepts_used == ["multiplication"]

def test_build_with_float_entities(solution_builder, sample_sub_goal_solve, sample_concept_addition):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_addition}
    entities = {'a': 2.5, 'b': 3.5, 'result': 6.0}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)

    a, b, result = z3.Reals('a b result')
    expected_z3_expr = (result == a + b)

    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat
    assert expression.concepts_used == ["addition"]

def test_build_with_missing_entities_fallback(solution_builder, sample_sub_goal_solve, sample_concept_addition):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_addition}
    entities = {'a': 2, 'b': 3} # Missing 'result'

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    assert expression.value == "dummy_solution_expression" # Should fall back to generic
