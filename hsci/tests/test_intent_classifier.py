import pytest
from hsci.neural.intent_classifier import IntentClassifier
from hsci.core.data_types import AxiomType, PerceptionMap

@pytest.fixture
def intent_classifier():
    # input_dim and num_classes are placeholders for the neural network
    return IntentClassifier(input_dim=128, num_classes=4)

def test_classify_reduction_intent(intent_classifier):
    text = "solve for x"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.REDUCTION
    assert perception.confidence == 0.6

def test_classify_reduction_intent_compute(intent_classifier):
    text = "compute the total"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.REDUCTION
    assert perception.confidence == 0.6

def test_classify_composition_intent_given_find(intent_classifier):
    text = "given salary is 5000, find tax"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.COMPOSITION
    assert perception.confidence == 0.8 # Higher confidence for 'given...find' pattern

def test_classify_composition_intent_relationship(intent_classifier):
    text = "what is the relationship between force and acceleration?"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.COMPOSITION
    assert perception.confidence == 0.7

def test_classify_synthesis_intent(intent_classifier):
    text = "write code to sort an array"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.SYNTHESIS
    assert perception.confidence == 0.9

def test_classify_synthesis_intent_implement(intent_classifier):
    text = "implement a new algorithm"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.SYNTHESIS
    assert perception.confidence == 0.9

def test_classify_transformation_intent(intent_classifier):
    text = "convert this document to markdown"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.TRANSFORMATION
    assert perception.confidence == 0.85

def test_classify_transformation_intent_summarize(intent_classifier):
    text = "summarize the text"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.TRANSFORMATION
    assert perception.confidence == 0.85

def test_default_reduction_low_confidence(intent_classifier):
    text = "what is the capital of France?" # No strong keywords
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.REDUCTION
    assert perception.confidence == 0.1

def test_priority_synthesis_over_reduction(intent_classifier):
    text = "calculate the sum and write code for it"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.SYNTHESIS # Synthesis should take priority
    assert perception.confidence == 0.9

def test_priority_composition_over_reduction(intent_classifier):
    text = "find x, given y=5"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.COMPOSITION # Composition should take priority
    assert perception.confidence == 0.8 # Due to 'given...find' pattern

def test_priority_transformation_over_reduction(intent_classifier):
    text = "summarize the findings and calculate the total"
    perception = intent_classifier(text)
    assert perception.intent == AxiomType.TRANSFORMATION # Transformation should take priority
    assert perception.confidence == 0.85

