import pytest
from hsci.neural.entity_extractor import EntityExtractor

@pytest.fixture
def entity_extractor():
    return EntityExtractor()

def test_extract_known_integer_entity(entity_extractor):
    text = "salary=5000"
    entities = entity_extractor.extract(text)
    assert entities == {"salary": 5000}

def test_extract_known_float_entity(entity_extractor):
    text = "tax_rate=0.20"
    entities = entity_extractor.extract(text)
    assert entities == {"tax_rate": 0.20}

def test_extract_known_string_entity(entity_extractor):
    text = "currency=USD"
    entities = entity_extractor.extract(text)
    assert entities == {"currency": "USD"}

def test_extract_unknown_entity_find(entity_extractor):
    text = "find take-home"
    entities = entity_extractor.extract(text)
    assert entities == {"take_home": None}

def test_extract_unknown_entity_calculate(entity_extractor):
    text = "calculate x"
    entities = entity_extractor.extract(text)
    assert entities == {"x": None}

def test_extract_unknown_entity_solve_for(entity_extractor):
    text = "solve for distance"
    entities = entity_extractor.extract(text)
    assert entities == {"distance": None}

def test_extract_combination_of_known_and_unknown(entity_extractor):
    text = "salary=5000, tax_rate=0.20, find net_salary"
    entities = entity_extractor.extract(text)
    assert entities == {"salary": 5000, "tax_rate": 0.20, "net_salary": None}

def test_extract_unknown_entity_with_hyphen(entity_extractor):
    text = "find annual-income"
    entities = entity_extractor.extract(text)
    assert entities == {"annual_income": None}

def test_extract_known_entity_overrides_unknown(entity_extractor):
    text = "find salary, salary=1000"
    entities = entity_extractor.extract(text)
    assert entities == {"salary": 1000}

def test_extract_no_entities(entity_extractor):
    text = "This is a plain sentence."
    entities = entity_extractor.extract(text)
    assert entities == {}

def test_extract_multiple_known_entities(entity_extractor):
    text = "length=10 width=5 area=50"
    entities = entity_extractor.extract(text)
    assert entities == {"length": 10, "width": 5, "area": 50}
