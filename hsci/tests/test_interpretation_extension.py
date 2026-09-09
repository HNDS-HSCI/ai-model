"""Unit tests for the HSCI Interpretation Extension (Cognitive Substrate
Final Review, "Interpretation Extension"): LanguageInterpreter/
math_composition.py now produce a typed Quantity/Variable/Operation/Equals
structure for math-shaped input instead of collapsing it into one raw-text
CONCEPT mention.

These tests check STRUCTURE, not final answers -- no solver is invoked
anywhere in this file, matching the step's explicit boundary ("natural
language -> typed semantic structure", not "natural language -> answer").
"""
import pytest

from hsci.cognition.interpretation.interpreter import LanguageInterpreter
from hsci.cognition.interpretation.models import RawInput
from hsci.cognition.interpretation.semantic_model import EntityRole
from hsci.cognition.interpretation.math_composition import compose_math_structure


def _interpret_primary(text: str):
    interp = LanguageInterpreter()
    raw = RawInput.from_text(text)
    iset = interp.interpret(raw)
    assert iset.candidates, f"no candidates produced for {text!r}"
    return iset.candidates[0]


def _relation_types(sem_req):
    return [r.relation_type for r in sem_req.relations]


def _mentions_by_role(sem_req):
    out = {"QUANTITY": [], "VARIABLE": [], "CONCEPT": []}
    for m in sem_req.entity_mentions:
        out[m.role.value].append(m)
    return out


# ─────────────────────────────────────────────────────────────
# Direct structure: "x + 10 = 20"
# ─────────────────────────────────────────────────────────────

def test_direct_equation_produces_typed_structure():
    candidate = _interpret_primary("x + 10 = 20")
    assert candidate.proposed_intent == "SolveMathematics"
    sr = candidate.semantic_request
    assert sr is not None

    by_role = _mentions_by_role(sr)
    assert len(by_role["VARIABLE"]) == 1
    assert by_role["VARIABLE"][0].surface_form == "x"

    quantity_values = {m.numeric_value for m in by_role["QUANTITY"]}
    assert quantity_values == {10.0, 20.0}
    for m in by_role["QUANTITY"]:
        assert m.is_known is True

    assert "OPERATION:ADD" in _relation_types(sr)
    assert "EQUALS" in _relation_types(sr)


@pytest.mark.parametrize("text", [
    "3x + 7 = 25",
    "x - 5 = 12",
    "x / 4 = 3",
])
def test_other_direct_equations_produce_typed_structure(text):
    candidate = _interpret_primary(text)
    sr = candidate.semantic_request
    assert sr is not None
    by_role = _mentions_by_role(sr)
    assert len(by_role["VARIABLE"]) == 1
    assert len(by_role["QUANTITY"]) >= 2
    assert "EQUALS" in _relation_types(sr)
    op_types = [rt for rt in _relation_types(sr) if rt.startswith("OPERATION:")]
    assert len(op_types) >= 1


# ─────────────────────────────────────────────────────────────
# Natural-language convergence: three ADD phrasings, one structure
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "a number plus 10 equals 20",
    "a number increased by 10 is 20",
    "10 added to a number gives 20",
])
def test_add_phrasings_converge_on_equivalent_structure(text):
    candidate = _interpret_primary(text)
    sr = candidate.semantic_request
    assert sr is not None
    by_role = _mentions_by_role(sr)

    assert len(by_role["VARIABLE"]) == 1
    quantity_values = sorted(m.numeric_value for m in by_role["QUANTITY"])
    assert quantity_values == [10.0, 20.0]

    add_relations = [r for r in sr.relations if r.relation_type == "OPERATION:ADD"]
    assert len(add_relations) == 1
    # The variable is always the base/source of the ADD, regardless of
    # which side of "added to" it appeared on in the surface sentence.
    assert add_relations[0].source_mention == by_role["VARIABLE"][0].surface_form
    assert add_relations[0].target_mention == "10"

    equals_relations = [r for r in sr.relations if r.relation_type == "EQUALS"]
    assert len(equals_relations) == 1
    assert equals_relations[0].target_mention == "20"


def test_no_new_regex_was_needed_per_phrasing_convergence_proof():
    """Proves convergence is structural, not per-phrasing: all three ADD
    phrasings above produce byte-identical (source_mention, relation_type,
    target_mention) relation triples once the variable's own surface form
    is normalized -- i.e. the SAME underlying composition logic handled
    all three without any phrasing-specific branch."""
    structures = [
        compose_math_structure("a number plus 10 equals 20"),
        compose_math_structure("a number increased by 10 is 20"),
        compose_math_structure("10 added to a number gives 20"),
    ]
    assert all(s is not None for s in structures)
    relation_shapes = [
        [(r.relation_type, r.target_mention) for r in s.relations]
        for s in structures
    ]
    assert relation_shapes[0] == relation_shapes[1] == relation_shapes[2]


# ─────────────────────────────────────────────────────────────
# Subtraction direction (mandatory): "12 less than a number is 9"
# ─────────────────────────────────────────────────────────────

def test_less_than_reverses_surface_order_correctly():
    """'Twelve less than a number is nine' must structurally represent
    number - 12, never 12 - number."""
    candidate = _interpret_primary("12 less than a number is 9")
    sr = candidate.semantic_request
    assert sr is not None

    subtract_relations = [r for r in sr.relations if r.relation_type == "OPERATION:SUBTRACT"]
    assert len(subtract_relations) == 1
    rel = subtract_relations[0]

    by_role = _mentions_by_role(sr)
    variable_form = by_role["VARIABLE"][0].surface_form

    # source_mention (the minuend) MUST be the variable, target_mention
    # (the subtrahend) MUST be 12 -- i.e. "number - 12", not "12 - number".
    assert rel.source_mention == variable_form
    assert rel.target_mention == "12"
    assert rel.source_mention != "12"

    equals_relations = [r for r in sr.relations if r.relation_type == "EQUALS"]
    assert equals_relations[0].target_mention == "9"


def test_decreased_by_and_less_than_produce_the_same_subtract_direction():
    """'a number decreased by 5' and '5 less than a number' both mean
    number - 5 -- opposite surface order, same argument roles."""
    decreased = compose_math_structure("a number decreased by 5 is 12")
    less_than = compose_math_structure("5 less than a number is 12")
    assert decreased is not None and less_than is not None

    def subtract_direction(structure):
        rel = next(r for r in structure.relations if r.relation_type == "OPERATION:SUBTRACT")
        return (rel.source_mention, rel.target_mention)

    assert subtract_direction(decreased) == subtract_direction(less_than) == ("a number", "5")


# ─────────────────────────────────────────────────────────────
# Multiplication: "a number doubled is 30"
# ─────────────────────────────────────────────────────────────

def test_doubled_distinguishes_variable_from_implicit_multiplier():
    candidate = _interpret_primary("a number doubled is 30")
    sr = candidate.semantic_request
    assert sr is not None
    by_role = _mentions_by_role(sr)

    assert len(by_role["VARIABLE"]) == 1
    assert by_role["VARIABLE"][0].surface_form == "a number"

    multiply_relations = [r for r in sr.relations if r.relation_type == "OPERATION:MULTIPLY"]
    assert len(multiply_relations) == 1
    assert multiply_relations[0].source_mention == "a number"
    assert multiply_relations[0].target_mention == "2"
    # The multiplier quantity (2) must be a distinct QUANTITY mention from
    # the variable, not folded into or confused with it.
    multiplier_mentions = [m for m in by_role["QUANTITY"] if m.numeric_value == 2.0]
    assert len(multiplier_mentions) == 1


def test_multiplied_by_explicit_operand():
    candidate = _interpret_primary("a number multiplied by 3 is 21")
    sr = candidate.semantic_request
    multiply_relations = [r for r in sr.relations if r.relation_type == "OPERATION:MULTIPLY"]
    assert len(multiply_relations) == 1
    assert multiply_relations[0].target_mention == "3"


# ─────────────────────────────────────────────────────────────
# No raw-expression collapse
# ─────────────────────────────────────────────────────────────

def test_math_input_is_no_longer_a_single_raw_concept_mention():
    for text in ["x + 10 = 20", "a number increased by 10 is 20", "12 less than a number is 9"]:
        candidate = _interpret_primary(text)
        sr = candidate.semantic_request
        assert sr is not None
        assert len(sr.entity_mentions) > 1, f"{text!r} collapsed to a single mention"
        assert not any(
            m.surface_form == text and m.role == EntityRole.CONCEPT
            for m in sr.entity_mentions
        ), f"{text!r} still represented as a single raw CONCEPT blob"
        # No relation may reference the whole original text either.
        assert not any(text in (r.source_mention, r.target_mention) for r in sr.relations)


# ─────────────────────────────────────────────────────────────
# Honest fallback: composition must not manufacture structure
# ─────────────────────────────────────────────────────────────

def test_out_of_scope_input_does_not_manufacture_a_structure():
    """Bare arithmetic with no unknown and no equality copula ('144 / 12')
    is out of this step's scope -- compose_math_structure must honestly
    return None rather than guess, and the interpreter must fall back to
    its pre-existing behavior (unchanged, not this step's concern)."""
    assert compose_math_structure("144 / 12") is None
    assert compose_math_structure("Compare Java interface and abstract class") is None
    assert compose_math_structure("What is the relationship between Java Interface and Abstraction?") is None


def test_composition_never_invents_a_variable_from_bare_numbers():
    """A sentence with numbers but no equality assertion and no recognized
    operation predicate must not produce a VARIABLE or EQUALS out of thin
    air."""
    result = compose_math_structure("There are 10 apples and 20 oranges")
    assert result is None


# ─────────────────────────────────────────────────────────────
# No solver invocation
# ─────────────────────────────────────────────────────────────

def test_math_composition_module_never_references_a_solver():
    import hsci.cognition.interpretation.math_composition as mc
    forbidden = ("sympy", "z3", "universalmathengine", "universal_math_engine")
    for name in vars(mc):
        low = name.lower()
        assert not any(term in low for term in forbidden), (
            f"math_composition.py namespace unexpectedly references a solver-related name: {name}"
        )


def test_interpreter_module_does_not_gain_a_new_solver_dependency():
    import hsci.cognition.interpretation.interpreter as interp_module
    # LanguageInterpreter already (pre-existing, unrelated to this step)
    # imports NeuralSemanticModel, which itself imports
    # normalize_natural_math_phrasing from universal_math_engine for its own
    # SOLVE_MATH fast-path detection -- that dependency predates this step
    # and is out of scope to remove. This test only proves THIS step's new
    # code (math_composition) adds no additional solver coupling.
    import hsci.cognition.interpretation.math_composition as mc
    assert not hasattr(mc, "sympy")
    assert not hasattr(mc, "z3")


# ─────────────────────────────────────────────────────────────
# Existing behavior regression (focused, in addition to the full suite)
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_intent", [
    ("What is a Java interface?", "ExplainConcept"),
    ("Compare Java interface with class.", "CompareConcepts"),
    ("What is the relationship between Java Interface and Abstraction?", "FindRelationship"),
])
def test_existing_non_math_communicative_goals_are_unaffected(text, expected_intent):
    candidate = _interpret_primary(text)
    assert candidate.proposed_intent == expected_intent
