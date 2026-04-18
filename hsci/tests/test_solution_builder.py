import pytest
from datetime import datetime
import z3

from hsci.reasoning.solution_builder import SolutionBuilder
from hsci.core.data_types import SubGoal, Concept, Expression, AxiomType

@pytest.fixture
def solution_builder():
    return SolutionBuilder()

@pytest.fixture
def sample_sub_goal_solve():
    return SubGoal(name="SOLVE_EQUATION", description="Solve the mathematical equation.")

@pytest.fixture
def sample_concept_addition():
    return Concept(
        id="addition", name="ADDITION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="a + b = result", z3_template="a + b == result",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.8, proof_count=10, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=["result"], z3_verified=True
    )

@pytest.fixture
def sample_concept_subtraction():
    return Concept(
        id="subtraction", name="SUBTRACTION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="a - b = result", z3_template="a - b == result",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.7, proof_count=8, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=["result"], z3_verified=True
    )

@pytest.fixture
def sample_concept_multiplication():
    return Concept(
        id="multiplication", name="MULTIPLICATION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="a * b = result", z3_template="a * b == result",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.9, proof_count=12, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=["result"], z3_verified=True
    )

def test_build_generic_expression(solution_builder):
    sub_goals = [SubGoal(name="GENERIC_TASK", description="Generic task")]
    concept_assignments = {sub_goals[0]: Concept(id="generic", name="GENERIC", axiom_type=AxiomType.REDUCTION, abstract_rule="", z3_template="", domain="", learned_from_domains=[], strength=0.5, proof_count=0, created_at=datetime.now(), last_used=datetime.now(), generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False)}
    entities = {}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    assert expression.value == "dummy_solution_expression"
    assert expression.concepts_used == ["generic"]

def test_build_addition_expression(solution_builder, sample_sub_goal_solve, sample_concept_addition):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_addition}
    entities = {'a': 2, 'b': 3, 'result': 5}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    # Verify the Z3 expression
    a_val, b_val, result_val = entities['a'], entities['b'], entities['result']
    a_z3, b_z3, result_z3 = z3.Int(str(a_val)), z3.Int(str(b_val)), z3.Int(str(result_val))
    expected_z3_expr = (a_z3 + b_z3 == result_z3)
    
    # We cannot directly compare Z3 expressions for equality, but we can check if they are equivalent
    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat # Assert that expression.value and expected_z3_expr are equivalent
    assert expression.concepts_used == ["addition"]

def test_build_subtraction_expression(solution_builder, sample_sub_goal_solve, sample_concept_subtraction):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_subtraction}
    entities = {'a': 10, 'b': 7, 'result': 3}

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    
    a_val, b_val, result_val = entities['a'], entities['b'], entities['result']
    a_z3, b_z3, result_z3 = z3.Int(str(a_val)), z3.Int(str(b_val)), z3.Int(str(result_val))
    expected_z3_expr = (a_z3 - b_z3 == result_z3)
    
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
    
    a_val, b_val, result_val = entities['a'], entities['b'], entities['result']
    a_z3, b_z3, result_z3 = z3.Int(str(a_val)), z3.Int(str(b_val)), z3.Int(str(result_val))
    expected_z3_expr = (a_z3 * b_z3 == result_z3)
    
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
    
    a_val, b_val, result_val = entities['a'], entities['b'], entities['result']
    a_z3, b_z3, result_z3 = z3.Real(str(a_val)), z3.Real(str(b_val)), z3.Real(str(result_val))
    expected_z3_expr = (a_z3 + b_z3 == result_z3)
    
    s = z3.Solver()
    s.add(expression.value)
    s.add(z3.Not(expected_z3_expr))
    assert s.check() == z3.unsat

def test_build_with_missing_entities_fallback(solution_builder, sample_sub_goal_solve, sample_concept_addition):
    sub_goals = [sample_sub_goal_solve]
    concept_assignments = {sample_sub_goal_solve: sample_concept_addition}
    entities = {'a': 2, 'b': 3} # Missing 'result'

    expression = solution_builder.build(sub_goals, concept_assignments, entities)
    assert isinstance(expression, Expression)
    assert expression.value == "dummy_solution_expression" # Should fall back to generic
