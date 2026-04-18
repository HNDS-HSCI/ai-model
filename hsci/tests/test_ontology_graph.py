import pytest
from datetime import datetime
from hsci.core.data_types import Concept, AxiomType, Graph
from hsci.knowledge.ontology_graph import OntologyGraph
import random

@pytest.fixture
def ontology_graph():
    return OntologyGraph()

@pytest.fixture
def sample_concepts():
    concept1 = Concept(
        id="arithmetic_add", name="ADDITION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a + b", z3_template="result == a + b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.8, proof_count=10, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )
    concept2 = Concept(
        id="arithmetic_sub", name="SUBTRACTION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a - b", z3_template="result == a - b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.5, proof_count=5, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )
    concept3 = Concept(
        id="physics_force", name="FORCE_CALC", axiom_type=AxiomType.REDUCTION,
        abstract_rule="F = m * a", z3_template="F == m * a",
        domain="physics", learned_from_domains=[],
        strength=0.7, proof_count=7, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["m", "a"],
        optional_entities=["F"], z3_verified=False # Not yet verified
    )
    return [concept1, concept2, concept3]

def test_add_concept(ontology_graph, sample_concepts):
    concept = sample_concepts[0]
    ontology_graph.add_concept(concept)
    assert concept.id in ontology_graph.nodes
    assert ontology_graph.nodes[concept.id] == concept
    assert concept.id in ontology_graph.edges
    assert len(ontology_graph.nodes) == 1

def test_integrate_concept(ontology_graph, sample_concepts):
    concept = sample_concepts[0]
    ontology_graph.integrate(concept)
    assert concept.id in ontology_graph.nodes
    assert len(ontology_graph.nodes) == 1

def test_add_duplicate_concept_warns(ontology_graph, sample_concepts, capsys):
    concept = sample_concepts[0]
    ontology_graph.add_concept(concept)
    ontology_graph.add_concept(concept) # Add same concept again
    captured = capsys.readouterr()
    assert f"Warning: Concept with ID '{concept.id}' already exists in ontology." in captured.out
    assert len(ontology_graph.nodes) == 1 # Should not add as new entry

def test_add_relationship(ontology_graph, sample_concepts):
    c1, c2 = sample_concepts[0], sample_concepts[1]
    ontology_graph.add_concept(c1)
    ontology_graph.add_concept(c2)
    ontology_graph.add_relationship(c1.id, c2.id, "IS_A")
    assert c2.id in ontology_graph.edges[c1.id]
    assert "IS_A" in ontology_graph.edges[c1.id][c2.id]

def test_add_multiple_relationships_same_edge(ontology_graph, sample_concepts):
    c1, c2 = sample_concepts[0], sample_concepts[1]
    ontology_graph.add_concept(c1)
    ontology_graph.add_concept(c2)
    ontology_graph.add_relationship(c1.id, c2.id, "IS_A")
    ontology_graph.add_relationship(c1.id, c2.id, "COMPOSES")
    assert "IS_A" in ontology_graph.edges[c1.id][c2.id]
    assert "COMPOSES" in ontology_graph.edges[c1.id][c2.id]
    assert len(ontology_graph.edges[c1.id][c2.id]) == 2

def test_add_relationship_non_existent_source(ontology_graph, sample_concepts):
    c2 = sample_concepts[1]
    ontology_graph.add_concept(c2)
    with pytest.raises(ValueError, match="Source concept ID 'non_existent' not found in ontology."):
        ontology_graph.add_relationship("non_existent", c2.id, "IS_A")

def test_add_relationship_non_existent_target(ontology_graph, sample_concepts):
    c1 = sample_concepts[0]
    ontology_graph.add_concept(c1)
    with pytest.raises(ValueError, match="Target concept ID 'non_existent' not found in ontology."):
        ontology_graph.add_relationship(c1.id, "non_existent", "IS_A")

def test_find_structural_analogies_empty_graph(ontology_graph):
    dummy_graph: Graph = {"nodes": ["x", "y"], "edges": []}
    analogies = ontology_graph.find_structural_analogies(dummy_graph)
    assert analogies == []

def test_find_structural_analogies_returns_sample(ontology_graph, sample_concepts):
    for c in sample_concepts:
        ontology_graph.add_concept(c)
    dummy_graph: Graph = {"nodes": ["x", "y"], "edges": []}
    analogies = ontology_graph.find_structural_analogies(dummy_graph, top_k=2)
    assert len(analogies) == 2
    assert all(isinstance(a, Concept) for a in analogies)
    
    # Ensure they are from the graph's concepts
    graph_concept_ids = {c.id for c in sample_concepts}
    sampled_ids = {c.id for c in analogies}
    assert sampled_ids.issubset(graph_concept_ids)

def test_strengthen_edges_placeholder(ontology_graph, sample_concepts, capsys):
    concept = sample_concepts[0]
    ontology_graph.add_concept(concept)
    ontology_graph.strengthen_edges(concept.id, 0.1)
    captured = capsys.readouterr()
    assert f"OntologyGraph: Strengthening edges for concept '{concept.id}' with strength 0.1 (placeholder)" in captured.out
    # Assert that no actual change occurred (for now)
    assert len(ontology_graph.nodes) == 1
