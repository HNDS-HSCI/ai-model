import pytest
from unittest.mock import MagicMock, call
from datetime import datetime
import z3

from hsci.reasoning.reasoning_engine import ReasoningEngine
from hsci.core.data_types import (
    PerceptionMap, KnowledgeResult, ReasoningPlan, SubGoal, Concept,
    AxiomType, Expression, ProofTrace, VerificationResult
)
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.reasoning.concept_composer import ConceptComposer
from hsci.reasoning.solution_builder import SolutionBuilder

@pytest.fixture
def mock_htn_planner():
    planner = MagicMock(spec=HTNPlanner)
    planner.decompose.return_value = [
        SubGoal(name="MOCK_SUBGOAL_1", description="desc1"),
        SubGoal(name="MOCK_SUBGOAL_2", description="desc2")
    ]
    return planner

@pytest.fixture
def mock_concept_composer():
    composer = MagicMock(spec=ConceptComposer)
    composer.find_best.return_value = Concept(
        id="mock_concept", name="MOCK_CONCEPT", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="", learned_from_domains=[],
        strength=0.0, proof_count=0, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=True
    )
    return composer

@pytest.fixture
def mock_solution_builder():
    builder = MagicMock(spec=SolutionBuilder)
    builder.build.return_value = Expression(value=z3.IntVal(1) + z3.IntVal(1) == z3.IntVal(2), concepts_used=["mock_concept"])
    return builder

@pytest.fixture
def reasoning_engine(mock_htn_planner, mock_concept_composer, mock_solution_builder):
    engine = ReasoningEngine()
    engine.htn_planner = mock_htn_planner
    engine.concept_composer = mock_concept_composer
    engine.solution_builder = mock_solution_builder
    return engine

@pytest.fixture
def mock_perception_map():
    return PerceptionMap(
        entities={"a": 1, "b": 1},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=0.9,
        entity_graph={"nodes": ["a", "b", "result"]}
    )

@pytest.fixture
def mock_knowledge_result():
    return KnowledgeResult(
        direct_matches=[],
        analogical_matches=[],
        episodes=[],
        confidence=0.5
    )

def test_reasoning_engine_initialization(reasoning_engine):
    assert isinstance(reasoning_engine.htn_planner, MagicMock)
    assert isinstance(reasoning_engine.concept_composer, MagicMock)
    assert isinstance(reasoning_engine.solution_builder, MagicMock)

def test_reason_method_workflow(reasoning_engine, mock_perception_map, mock_knowledge_result,
                               mock_htn_planner, mock_concept_composer, mock_solution_builder):
    
    reasoning_plan = reasoning_engine.reason(mock_perception_map, mock_knowledge_result)

    # Verify HTNPlanner was called
    mock_htn_planner.decompose.assert_called_once_with(mock_perception_map)
    assert reasoning_plan.sub_goals == mock_htn_planner.decompose.return_value

    # Verify ConceptComposer was called for EACH subgoal
    from unittest.mock import ANY
    assert mock_concept_composer.find_best.call_count == len(reasoning_plan.sub_goals)
    mock_concept_composer.find_best.assert_any_call(
        mock_htn_planner.decompose.return_value[0], # First subgoal
        mock_knowledge_result.direct_matches,
        mock_knowledge_result.analogical_matches,
        context_text=ANY
    )
    # Check that the best concept was assigned to all subgoals
    expected_concept = mock_concept_composer.find_best.return_value
    assert all(concept == expected_concept for concept in reasoning_plan.concept_assignments.values())
    assert reasoning_plan.primary_concept == expected_concept

    # Verify SolutionBuilder was called
    mock_solution_builder.build.assert_called_once_with(
        reasoning_plan.sub_goals,
        reasoning_plan.concept_assignments,
        mock_perception_map.entities,
        ctx=None
    )
    assert reasoning_plan.candidate_solution == mock_solution_builder.build.return_value

    assert isinstance(reasoning_plan, ReasoningPlan)

def test_repair_method_placeholder(reasoning_engine, mock_perception_map, mock_knowledge_result):
    # Create a dummy ReasoningPlan to pass to repair
    subgoals = [SubGoal(name="ORIGINAL", description="original")]
    original_plan = ReasoningPlan(
        sub_goals=subgoals,
        concept_assignments={subgoals[0]: None},
        composition_order=[],
        candidate_solution=Expression(value="original_solution", concepts_used=[]),
        concepts_used=[],
        primary_concept=None,
        perception=mock_perception_map,
        knowledge=mock_knowledge_result
    )
    counterexample = {"error": "test_failure"}
    correction_hint = "try something else"

    repaired_plan = reasoning_engine.repair(original_plan, counterexample, correction_hint)

    # repair just calls reason() with the original perception and knowledge
    # we can check if it returns a new ReasoningPlan correctly
    assert repaired_plan.perception == original_plan.perception
    assert repaired_plan.knowledge == original_plan.knowledge
