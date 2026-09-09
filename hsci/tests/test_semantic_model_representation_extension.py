"""Unit tests for the HSCI representation extension (Cognitive Substrate Final
Review, §17): EntityMention.role/numeric_value/is_known and the closed
OPERATION_RELATION_TYPES vocabulary on SemanticRelation.relation_type.

Pure data-model tests. No Interpret/Ground/Reason/Verify/Answer stage is
exercised or imported here — this file only tests that the new fields exist,
default correctly, and round-trip through to_dict().
"""
from hsci.cognition.interpretation.semantic_model import (
    EntityMention,
    EntityRole,
    SemanticRelation,
    OPERATION_RELATION_TYPES,
)


# ─────────────────────────────────────────────────────────────
# EntityRole / EntityMention
# ─────────────────────────────────────────────────────────────

def test_entity_role_has_exactly_the_three_sanctioned_values():
    assert {m.value for m in EntityRole} == {"CONCEPT", "QUANTITY", "VARIABLE"}


def test_existing_entity_mention_construction_is_backward_compatible():
    """A construction site that predates this change (no role/numeric_value/
    is_known kwargs) must default to CONCEPT/None/None and behave exactly as
    it did before the extension."""
    mention = EntityMention(
        surface_form="Java Interface",
        normalized_form="java interface",
        confidence=0.95,
    )
    assert mention.role == EntityRole.CONCEPT
    assert mention.numeric_value is None
    assert mention.is_known is None
    # Every pre-existing field is untouched.
    assert mention.surface_form == "Java Interface"
    assert mention.normalized_form == "java interface"
    assert mention.candidate_identity is None
    assert mention.span_start == 0
    assert mention.span_end == 0
    assert mention.confidence == 0.95
    assert mention.resolution_state == "UNRESOLVED"


def test_existing_entity_mention_to_dict_is_backward_compatible():
    mention = EntityMention(surface_form="Abstraction", normalized_form="abstraction")
    d = mention.to_dict()
    assert d["role"] == "CONCEPT"
    assert d["numeric_value"] is None
    assert d["is_known"] is None
    assert d["surface_form"] == "Abstraction"


def test_quantity_entity_mention_round_trips_through_to_dict():
    mention = EntityMention(
        surface_form="10",
        normalized_form="10",
        role=EntityRole.QUANTITY,
        numeric_value=10.0,
        is_known=True,
    )
    d = mention.to_dict()
    assert d["role"] == "QUANTITY"
    assert d["numeric_value"] == 10.0
    assert d["is_known"] is True
    # A str-Enum member survives equality against the plain string value too.
    assert d["role"] == EntityRole.QUANTITY


def test_variable_entity_mention_round_trips_through_to_dict():
    mention = EntityMention(
        surface_form="x",
        normalized_form="x",
        role=EntityRole.VARIABLE,
        is_known=False,
    )
    d = mention.to_dict()
    assert d["role"] == "VARIABLE"
    assert d["is_known"] is False
    assert d["numeric_value"] is None  # a VARIABLE need not carry a value


# ─────────────────────────────────────────────────────────────
# SemanticRelation / OPERATION_RELATION_TYPES
# ─────────────────────────────────────────────────────────────

def test_operation_relation_types_are_exactly_the_sanctioned_closed_set():
    assert OPERATION_RELATION_TYPES == {
        "OPERATION:ADD",
        "OPERATION:SUBTRACT",
        "OPERATION:MULTIPLY",
        "OPERATION:DIVIDE",
        "EQUALS",
    }


def test_operation_add_relation_round_trips_through_to_dict():
    rel = SemanticRelation(
        source_mention="x",
        relation_type="OPERATION:ADD",
        target_mention="10",
        confidence=0.9,
    )
    assert rel.relation_type in OPERATION_RELATION_TYPES
    d = rel.to_dict()
    assert d["relation_type"] == "OPERATION:ADD"
    assert d["source_mention"] == "x"
    assert d["target_mention"] == "10"


def test_equals_relation_is_accepted_and_serialized():
    rel = SemanticRelation(
        source_mention="result",
        relation_type="EQUALS",
        target_mention="20",
    )
    assert rel.relation_type in OPERATION_RELATION_TYPES
    d = rel.to_dict()
    assert d["relation_type"] == "EQUALS"


def test_existing_non_operation_relation_types_are_unaffected():
    """Pre-existing concept-relation values (never part of the operation
    vocabulary) must continue to construct and serialize exactly as before."""
    for existing_relation_type in ("COMPARISON", "RELATIONSHIP", "GENERALIZATION", "PURPOSE"):
        rel = SemanticRelation(
            source_mention="Java Interface",
            relation_type=existing_relation_type,
            target_mention="Class",
            confidence=0.95,
        )
        assert rel.relation_type == existing_relation_type
        assert rel.relation_type not in OPERATION_RELATION_TYPES
        d = rel.to_dict()
        assert d["relation_type"] == existing_relation_type


def test_operation_relation_preserves_source_target_ordering():
    """'x - 10' and '10 - x' must remain distinguishable: relation_type alone
    is symmetric-looking, so the distinction must live entirely in which
    mention is source_mention vs. target_mention, exactly as SemanticRelation
    already preserves for every other relation_type."""
    x_minus_10 = SemanticRelation(source_mention="x", relation_type="OPERATION:SUBTRACT", target_mention="10")
    ten_minus_x = SemanticRelation(source_mention="10", relation_type="OPERATION:SUBTRACT", target_mention="x")

    d1 = x_minus_10.to_dict()
    d2 = ten_minus_x.to_dict()

    assert d1["source_mention"] == "x" and d1["target_mention"] == "10"
    assert d2["source_mention"] == "10" and d2["target_mention"] == "x"
    assert d1 != d2

    # Same check for division, the other non-commutative operation named in
    # the review (x / 2 vs. 2 / x).
    x_div_2 = SemanticRelation(source_mention="x", relation_type="OPERATION:DIVIDE", target_mention="2")
    two_div_x = SemanticRelation(source_mention="2", relation_type="OPERATION:DIVIDE", target_mention="x")
    assert x_div_2.to_dict() != two_div_x.to_dict()
