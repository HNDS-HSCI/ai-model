import pytest
from datetime import datetime
from hsci.core.data_types import PerceptionMap, AxiomType, Concept, Episode, KnowledgeResult
from hsci.knowledge.knowledge_base import KnowledgeBase

@pytest.fixture
def knowledge_base():
    # Initialize WITHOUT seeding to ensure a clean state for testing
    return KnowledgeBase(seed=False)

def test_query_method(knowledge_base):
    perception = PerceptionMap(
        entities={"x": 5},
        unknown_entities=["y"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )
    
    result = knowledge_base.query(perception)
    assert isinstance(result, KnowledgeResult)
    assert result.direct_matches == []
    assert result.analogical_matches == []
    assert result.episodes == []
    assert result.confidence == 0.0

def test_store_concept(knowledge_base):
    concept = Concept(
        id="test_concept", name="TEST", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="", learned_from_domains=[],
        strength=0.5, proof_count=0, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False
    )
    
    knowledge_base.store_concept(concept)
    assert knowledge_base.concept_library.contains(concept.id)
    # Check ontology integration (at least it doesn't crash)
    assert concept.id in knowledge_base.ontology.nodes

def test_reinforce_concept(knowledge_base):
    concept = Concept(
        id="test_concept", name="TEST", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="", learned_from_domains=[],
        strength=0.5, proof_count=0, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=False
    )
    knowledge_base.store_concept(concept)
    
    knowledge_base.reinforce_concept(concept, 0.9)
    assert knowledge_base.concept_library._concepts[concept.id].strength == 0.9

def test_store_impossibility(knowledge_base, capsys):
    pattern = {"failed_rule": "R1"}
    counterexample = {"input": "bad_input"}
    
    knowledge_base.store_impossibility(pattern, counterexample)
    captured = capsys.readouterr()
    assert "KnowledgeBase: Storing impossibility" in captured.out
