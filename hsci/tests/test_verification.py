import pytest
import z3
from datetime import datetime
from hsci.core.data_types import (
    AxiomType, Concept, Expression, InputSignal, PerceptionMap, Relationship,
    PerceiverConfig, ProofTrace, WeightUpdate, Episode, ReasoningPlan,
    VerificationResult
)
from hsci.symbolic.z3_verifier import Z3VerificationEngine
from hsci.symbolic.z3_templates import Z3_TEMPLATES

# Helper function to create a basic PerceptionMap for arithmetic tests
def create_arithmetic_perception(entities: dict) -> PerceptionMap:
    return PerceptionMap(
        entities=entities,
        unknown_entities=[], # Not relevant for simple verification
        relationships=[],    # Not relevant for simple verification
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph=None    # Placeholder
    )

# Helper function to create a basic Concept for arithmetic tests
def create_arithmetic_concept(name: str) -> Concept:
    template_info = Z3_TEMPLATES[name]
    return Concept(
        id=name.lower(),
        name=name,
        axiom_type=AxiomType.REDUCTION,
        abstract_rule=template_info["template"],
        z3_template=template_info["template"], # Using the string form as per the dataclass
        domain=template_info["domain"],
        learned_from_domains=[template_info["domain"]],
        strength=0.5,
        proof_count=0,
        created_at=datetime.now(),
        last_used=datetime.now(),
        generalizes_to=[],
        required_entities=[],
        optional_entities=[],
        z3_verified=False
    )

@pytest.fixture
def verifier():
    return Z3VerificationEngine()

@pytest.fixture
def addition_concept():
    return create_arithmetic_concept("ADDITION")

@pytest.fixture
def subtraction_concept():
    return create_arithmetic_concept("SUBTRACTION")

@pytest.fixture
def multiplication_concept():
    return create_arithmetic_concept("MULTIPLICATION")

def test_verify_addition_valid(verifier, addition_concept):
    # Test: verify("2+3=5") returns valid=True
    
    # Define Z3 variables
    a = z3.Int('a')
    b = z3.Int('b')
    result = z3.Int('result')

    # Create PerceptionMap for "2 + 3 = 5"
    entities = {'a': 2, 'b': 3, 'result': 5}
    perception = create_arithmetic_perception(entities)

    # Create Expression for "a + b == result"
    # This is a critical simplification assuming the Expression.value is already a Z3 expression
    candidate_expression_value = (a + b == result)
    candidate_expression = Expression(value=candidate_expression_value, concepts_used=["ADDITION"])

    verification_result = verifier.verify(candidate_expression, perception, addition_concept)

    assert verification_result.valid is True
    assert verification_result.confidence == 1.0
    assert verification_result.proof_trace is not None
    assert verification_result.counterexample is None

def test_verify_addition_invalid(verifier, addition_concept):
    # Test: verify("2+3=6") returns valid=False with counterexample
    
    # Define Z3 variables
    a = z3.Int('a')
    b = z3.Int('b')
    result = z3.Int('result')

    # Create PerceptionMap for "2 + 3 = 6"
    entities = {'a': 2, 'b': 3, 'result': 6}
    perception = create_arithmetic_perception(entities)

    # Create Expression for "a + b == result"
    candidate_expression_value = (a + b == result)
    candidate_expression = Expression(value=candidate_expression_value, concepts_used=["ADDITION"])

    verification_result = verifier.verify(candidate_expression, perception, addition_concept)

    assert verification_result.valid is False
    assert verification_result.confidence == 0.0
    assert verification_result.proof_trace is None
    assert verification_result.counterexample is not None
    assert "Counterexample extraction not fully implemented." in verification_result.counterexample["error"]

def test_verify_subtraction_valid(verifier, subtraction_concept):
    # Test for subtraction: verify("10-7=3")
    
    a = z3.Int('a')
    b = z3.Int('b')
    result = z3.Int('result')

    entities = {'a': 10, 'b': 7, 'result': 3}
    perception = create_arithmetic_perception(entities)

    candidate_expression_value = (a - b == result)
    candidate_expression = Expression(value=candidate_expression_value, concepts_used=["SUBTRACTION"])

    verification_result = verifier.verify(candidate_expression, perception, subtraction_concept)

    assert verification_result.valid is True
    assert verification_result.confidence == 1.0

def test_verify_multiplication_valid(verifier, multiplication_concept):
    # Test for multiplication: verify("4*6=24")
    
    a = z3.Int('a')
    b = z3.Int('b')
    result = z3.Int('result')

    entities = {'a': 4, 'b': 6, 'result': 24}
    perception = create_arithmetic_perception(entities)

    candidate_expression_value = (a * b == result)
    candidate_expression = Expression(value=candidate_expression_value, concepts_used=["MULTIPLICATION"])

    verification_result = verifier.verify(candidate_expression, perception, multiplication_concept)

    assert verification_result.valid is True
    assert verification_result.confidence == 1.0
