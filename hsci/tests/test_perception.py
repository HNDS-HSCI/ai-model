import pytest
from datetime import datetime
from hsci.core.data_types import InputSignal, AxiomType, PerceptionMap, Relationship
from hsci.core.config import PerceiverConfig
from hsci.neural.perceiver import NeuralPerceiver

@pytest.fixture
def neural_perceiver():
    config = PerceiverConfig()
    return NeuralPerceiver(config)

def test_perceive_reduction_intent_with_entities(neural_perceiver):
    raw_text = "salary=5000, tax_rate=0.20, find net_salary"
    input_signal = InputSignal(
        raw_text=raw_text,
        structured_data=None,
        timestamp=datetime.now(),
        session_id="test_session_1"
    )

    perception_map = neural_perceiver.perceive(input_signal)

    assert perception_map.intent == AxiomType.REDUCTION
    assert perception_map.confidence > 0.0 # Expecting some confidence for a matched intent
    assert perception_map.entities["salary"].value == 5000
    assert perception_map.entities["tax_rate"].value == 0.20
    assert perception_map.entities["net_salary"].value == None
    assert perception_map.entities["net_salary"].known == False
    assert perception_map.unknown_entities == ["net_salary"]
    assert isinstance(perception_map.entity_graph, dict) # Placeholder graph is a dict
    assert "nodes" in perception_map.entity_graph
    assert "salary" in perception_map.entity_graph["nodes"]
    assert "net_salary" in perception_map.entity_graph["nodes"]
    assert perception_map.relationships == [] # Currently a placeholder

def test_perceive_synthesis_intent_with_no_entities(neural_perceiver):
    raw_text = "write code to sort a list"
    input_signal = InputSignal(
        raw_text=raw_text,
        structured_data=None,
        timestamp=datetime.now(),
        session_id="test_session_2"
    )

    perception_map = neural_perceiver.perceive(input_signal)

    assert perception_map.intent == AxiomType.SYNTHESIS
    assert perception_map.confidence == 0.9 # High confidence for direct keyword match
    assert perception_map.entities == {}
    assert perception_map.unknown_entities == []
    assert isinstance(perception_map.entity_graph, dict)
    assert perception_map.relationships == []

def test_perceive_composition_intent(neural_perceiver):
    raw_text = "given force=10, mass=2, find acceleration"
    input_signal = InputSignal(
        raw_text=raw_text,
        structured_data=None,
        timestamp=datetime.now(),
        session_id="test_session_3"
    )

    perception_map = neural_perceiver.perceive(input_signal)

    assert perception_map.intent == AxiomType.COMPOSITION
    assert perception_map.confidence == 0.8 # Higher confidence for 'given...find' pattern
    assert perception_map.entities["force"].value == 10
    assert perception_map.entities["mass"].value == 2
    assert perception_map.entities["acceleration"].value == None
    assert perception_map.unknown_entities == ["acceleration"]
    assert isinstance(perception_map.entity_graph, dict)
    assert perception_map.relationships == []

def test_perceive_transformation_intent(neural_perceiver):
    raw_text = "summarize the following document"
    input_signal = InputSignal(
        raw_text=raw_text,
        structured_data=None,
        timestamp=datetime.now(),
        session_id="test_session_4"
    )

    perception_map = neural_perceiver.perceive(input_signal)

    assert perception_map.intent == AxiomType.TRANSFORMATION
    assert perception_map.confidence == 0.85
    assert perception_map.entities == {}
    assert perception_map.unknown_entities == []
    assert isinstance(perception_map.entity_graph, dict)
    assert perception_map.relationships == []

def test_perceive_input_signal_type_mismatch(neural_perceiver):
    # Test for when input to intent_classifier is not a string (e.g., future embedding)
    # The current rule-based classifier handles this by returning a default PerceptionMap
    
    # Simulate an embedding being passed instead of raw_text
    dummy_embedding = {"vector": [0.1, 0.2, 0.3]} 
    
    # We directly call the internal intent_classifier for this test
    # In a full run, this would come from the encoder
    intent_perception = neural_perceiver.intent_classifier(dummy_embedding)

    assert intent_perception.intent == AxiomType.REDUCTION
    assert intent_perception.confidence == 0.0 # Default confidence when input is not text
    assert intent_perception.entities == {}

