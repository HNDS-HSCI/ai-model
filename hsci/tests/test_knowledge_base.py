import pytest
from datetime import datetime
from unittest.mock import MagicMock

from hsci.core.data_types import Concept, AxiomType, PerceptionMap, KnowledgeResult, Episode
from hsci.knowledge.knowledge_base import KnowledgeBase
from hsci.knowledge.concept_library import ConceptLibrary
from hsci.knowledge.ontology_graph import OntologyGraph
from hsci.knowledge.episode_memory import EpisodeMemory
from hsci.core.config import SystemConfig

@pytest.fixture
def knowledge_base():
    return KnowledgeBase()

@pytest.fixture
def mock_perception_map():
    return PerceptionMap(
        entities={"x": 10, "y": 20},
        unknown_entities=["z"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=0.8,
        entity_graph={"nodes": ["x", "y", "z"]}
    )

@pytest.fixture
def sample_concept():
    return Concept(
        id="arithmetic_add", name="ADDITION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a + b", z3_template="result == a + b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.8, proof_count=10, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )

@pytest.fixture
def sample_episode():
    return Episode(
        input=MagicMock(spec=PerceptionMap), # Mocked PerceptionMap
        solution=MagicMock(spec=Expression), # Mocked Expression
        proof=MagicMock(spec=ProofTrace),    # Mocked ProofTrace
        concepts_used=["concept_id"],
        timestamp=datetime.now()
    )


def test_knowledge_base_initialization(knowledge_base):
    assert isinstance(knowledge_base.concept_library, ConceptLibrary)
    assert isinstance(knowledge_base.ontology, OntologyGraph)
    assert isinstance(knowledge_base.episode_memory, EpisodeMemory)

def test_query_method(knowledge_base, mock_perception_map):
    # Mock components to control their return values
    knowledge_base.concept_library.find_by_intent = MagicMock(return_value=[])
    knowledge_base.ontology.find_structural_analogies = MagicMock(return_value=[])
    knowledge_base.episode_memory.find_similar = MagicMock(return_value=[])

    result = knowledge_base.query(mock_perception_map)

    assert isinstance(result, KnowledgeResult)
    assert result.direct_matches == []
    assert result.analogical_matches == []
    assert result.episodes == []
    assert result.confidence == 0.0

    # Verify mocks were called
    knowledge_base.concept_library.find_by_intent.assert_called_once()
    knowledge_base.ontology.find_structural_analogies.assert_called_once()
    knowledge_base.episode_memory.find_similar.assert_called_once()


def test_store_concept(knowledge_base, sample_concept):
    # Mock component methods
    knowledge_base.concept_library.add = MagicMock()
    knowledge_base.ontology.integrate = MagicMock()

    knowledge_base.store_concept(sample_concept)

    knowledge_base.concept_library.add.assert_called_once_with(sample_concept)
    knowledge_base.ontology.integrate.assert_called_once_with(sample_concept)

def test_reinforce_concept(knowledge_base, sample_concept):
    # Mock component methods
    knowledge_base.concept_library.update_strength = MagicMock()
    knowledge_base.ontology.strengthen_edges = MagicMock()

    knowledge_base.reinforce_concept(sample_concept, 0.9)

    knowledge_base.concept_library.update_strength.assert_called_once_with(sample_concept.id, 0.9)
    knowledge_base.ontology.strengthen_edges.assert_called_once_with(sample_concept.id, 0.9)

def test_store_impossibility(knowledge_base, capsys):
    pattern = {"failed_rule": "R1"}
    counterexample = {"input": "bad_input"}

    knowledge_base.store_impossibility(pattern, counterexample)
    captured = capsys.readouterr()
    assert "KnowledgeBase: Storing impossibility" in captured.out
