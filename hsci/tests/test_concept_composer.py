import pytest
from datetime import datetime
from unittest.mock import MagicMock

from hsci.reasoning.concept_composer import ConceptComposer
from hsci.core.data_types import Concept, SubGoal, AxiomType

@pytest.fixture
def concept_composer():
    return ConceptComposer()

@pytest.fixture
def sample_sub_goal():
    return SubGoal(name="SOLVE_EQUATION", description="Solve the mathematical equation.")

@pytest.fixture
def mock_concepts():
    c1 = Concept(
        id="c1", name="ADDITION_DIRECT", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="math", learned_from_domains=[],
        strength=0.9, proof_count=1, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=True
    )
    c2 = Concept(
        id="c2", name="SUBTRACTION_DIRECT", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="math", learned_from_domains=[],
        strength=0.7, proof_count=1, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=True
    )
    c3 = Concept(
        id="c3", name="ANALOGY_FORCE", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="physics", learned_from_domains=[],
        strength=0.8, proof_count=1, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False
    )
    c4 = Concept(
        id="c4", name="ANALOGY_FINANCE", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="finance", learned_from_domains=[],
        strength=0.6, proof_count=1, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False
    )
    return [c1, c2, c3, c4]

def test_find_best_direct_match_priority(concept_composer, sample_sub_goal, mock_concepts):
    direct_matches = [mock_concepts[0], mock_concepts[1]] # c1 (0.9), c2 (0.7)
    analogical_matches = [mock_concepts[2], mock_concepts[3]] # c3 (0.8), c4 (0.6)

    best_concept = concept_composer.find_best(sample_sub_goal, direct_matches, analogical_matches)
    assert best_concept == mock_concepts[0] # Should pick c1 (highest strength direct)

def test_find_best_analogical_fallback(concept_composer, sample_sub_goal, mock_concepts):
    direct_matches = []
    analogical_matches = [mock_concepts[2], mock_concepts[3]] # c3 (0.8), c4 (0.6)

    best_concept = concept_composer.find_best(sample_sub_goal, direct_matches, analogical_matches)
    assert best_concept == mock_concepts[2] # Should pick c3 (highest strength analogical)

def test_find_best_synthesis_fallback(concept_composer, sample_sub_goal):
    direct_matches = []
    analogical_matches = []

    best_concept = concept_composer.find_best(sample_sub_goal, direct_matches, analogical_matches)
    assert best_concept is None # Placeholder synthesize_from_primitives returns None

def test_rank_by_strength(concept_composer, mock_concepts):
    ranked_concepts = concept_composer.rank_by_strength(mock_concepts)
    assert [c.id for c in ranked_concepts] == ["c1", "c3", "c2", "c4"]

def test_compose_analogies_placeholder(concept_composer, sample_sub_goal, mock_concepts, capsys):
    analogical_matches = [mock_concepts[2], mock_concepts[3]] # c3 (0.8), c4 (0.6)
    
    composed = concept_composer.compose_analogies(sample_sub_goal, analogical_matches)
    assert composed == mock_concepts[2] # Should pick the strongest analogical match
    captured = capsys.readouterr()
    assert f"ConceptComposer: Composing analogies for sub-goal '{sample_sub_goal.name}' (placeholder)" in captured.out

def test_synthesize_from_primitives_placeholder(concept_composer, sample_sub_goal, capsys):
    synthesized = concept_composer.synthesize_from_primitives(sample_sub_goal)
    assert synthesized is None
    captured = capsys.readouterr()
    assert f"ConceptComposer: Synthesizing from primitives for sub-goal '{sample_sub_goal.name}' (placeholder)" in captured.out

def test_find_best_empty_lists(concept_composer, sample_sub_goal):
    best_concept = concept_composer.find_best(sample_sub_goal, [], [])
    assert best_concept is None
