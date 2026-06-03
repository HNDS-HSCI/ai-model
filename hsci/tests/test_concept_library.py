import pytest
from datetime import datetime
from hsci.core.data_types import Concept, AxiomType
from hsci.knowledge.concept_library import ConceptLibrary

@pytest.fixture
def concept_library():
    # Initialize WITHOUT seeding to ensure a clean state for testing
    return ConceptLibrary(seed=False)

@pytest.fixture
def sample_concepts():
    concept1 = Concept(
        id="addition_int", name="ADDITION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a + b", z3_template="result == a + b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.8, proof_count=10, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )
    concept2 = Concept(
        id="subtraction_int", name="SUBTRACTION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a - b", z3_template="result == a - b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.5, proof_count=5, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )
    concept3 = Concept(
        id="multiply_float", name="MULTIPLICATION", axiom_type=AxiomType.REDUCTION,
        abstract_rule="result = a * b", z3_template="result == a * b",
        domain="arithmetic", learned_from_domains=["arithmetic"],
        strength=0.9, proof_count=15, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["a", "b"],
        optional_entities=[], z3_verified=True
    )
    concept4 = Concept(
        id="synthesis_sort", name="SORTING_ALGORITHM", axiom_type=AxiomType.SYNTHESIS,
        abstract_rule="sort(list)", z3_template="",
        domain="programming", learned_from_domains=["programming"],
        strength=0.7, proof_count=7, created_at=datetime.now(),
        last_used=datetime.now(), generalizes_to=[], required_entities=["list"],
        optional_entities=[], z3_verified=False
    )
    return [concept1, concept2, concept3, concept4]

def test_add_concept(concept_library, sample_concepts):
    concept = sample_concepts[0]
    concept_library.add(concept)
    assert concept_library.contains(concept.id)
    assert len(concept_library._concepts) == 1

def test_add_duplicate_concept_warns_and_updates(concept_library, sample_concepts, capsys):
    concept = sample_concepts[0]
    concept_library.add(concept)
    concept_library.add(concept) # Add same concept again
    captured = capsys.readouterr()
    assert "Warning: Concept with ID 'addition_int' already exists. Updating." in captured.out
    assert len(concept_library._concepts) == 1 # Should not add as new entry

def test_find_by_intent(concept_library, sample_concepts):
    for c in sample_concepts:
        concept_library.add(c)
    
    reduction_concepts = concept_library.find_by_intent(AxiomType.REDUCTION, [])
    assert len(reduction_concepts) == 3
    assert all(c.axiom_type == AxiomType.REDUCTION for c in reduction_concepts)

    synthesis_concepts = concept_library.find_by_intent(AxiomType.SYNTHESIS, [])
    assert len(synthesis_concepts) == 1
    assert synthesis_concepts[0].name == "SORTING_ALGORITHM"

    composition_concepts = concept_library.find_by_intent(AxiomType.COMPOSITION, [])
    assert len(composition_concepts) == 0

def test_update_strength(concept_library, sample_concepts):
    concept = sample_concepts[0]
    concept_library.add(concept)
    
    initial_strength = concept.strength
    new_strength = 0.95
    concept_library.update_strength(concept.id, new_strength)
    assert concept_library._concepts[concept.id].strength == new_strength

def test_update_strength_non_existent_concept_warns(concept_library, capsys):
    concept_library.update_strength("non_existent_id", 0.7)
    captured = capsys.readouterr()
    assert "Warning: Concept with ID 'non_existent_id' not found for strength update." in captured.out

def test_contains_concept(concept_library, sample_concepts):
    concept = sample_concepts[0]
    concept_library.add(concept)
    assert concept_library.contains(concept.id)
    
    assert not concept_library.contains("non_existent")

def test_sample_concepts(concept_library, sample_concepts):
    for c in sample_concepts:
        concept_library.add(c)
    
    sampled = concept_library.sample(2)
    assert len(sampled) == 2
    # Ensure sampled concepts are from the original set
    sampled_ids = {c.id for c in sampled}
    original_ids = {c.id for c in sample_concepts}
    assert sampled_ids.issubset(original_ids)

def test_get_weakest_concepts(concept_library, sample_concepts):
    for c in sample_concepts:
        concept_library.add(c)
    
    # Expected order of IDs by strength: subtraction_int (0.5), synthesis_sort (0.7), addition_int (0.8), multiply_float (0.9)
    weakest_2 = concept_library.get_weakest(2)
    assert len(weakest_2) == 2
    assert weakest_2[0].id == "subtraction_int"
    assert weakest_2[1].id == "synthesis_sort"
