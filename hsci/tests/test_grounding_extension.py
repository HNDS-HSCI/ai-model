"""Unit tests for the HSCI Grounding Extension (Cognitive Substrate Final
Review, §16 "Grounding Extension"): real QUANTITY/VARIABLE grounding,
removal of the SolveMathematics rubber-stamp, and the new PARTIALLY_GROUNDED
situation status.

These tests exercise GroundingEngine directly (with a real, seeded UKM via
bootstrap_cognitive_pipeline). No LanguageInterpreter change is required or
exercised for the QUANTITY/VARIABLE tests -- CandidateInterpretation objects
carrying role-typed EntityMentions are constructed by hand, exactly as a
future Interpret extension would eventually produce them. Two tests
(partial-grounding, existing-concept-regression) go through the real,
unmodified LanguageInterpreter to confirm end-to-end behavior for concept
mentions is unaffected.
"""
from types import SimpleNamespace

import pytest

from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline
from hsci.cognition.interpretation.grounding import GroundingEngine
from hsci.cognition.interpretation.models import (
    RawInput,
    InterpretationSet,
    CandidateInterpretation,
    GroundingStatus,
    SituationStatus,
)
from hsci.cognition.interpretation.semantic_model import (
    SemanticRequest,
    CommunicativeGoal,
    EntityMention,
    EntityRole,
)


def _quantity_candidate(surface_forms_and_values, proposed_intent="SolveMathematics"):
    """Builds a CandidateInterpretation carrying QUANTITY-role EntityMentions
    for each (surface_form, numeric_value) pair -- the shape a future
    Interpret extension would produce, constructed by hand here since
    LanguageInterpreter is out of scope for this step."""
    mentions = [
        EntityMention(
            surface_form=sf,
            normalized_form=sf,
            role=EntityRole.QUANTITY,
            numeric_value=None,  # force Ground to parse the surface form itself
        )
        for sf, _ in surface_forms_and_values
    ]
    return CandidateInterpretation(
        proposed_intent=proposed_intent,
        candidate_entity_mentions=[sf for sf, _ in surface_forms_and_values],
        confidence=0.9,
        semantic_request=SemanticRequest(goal=CommunicativeGoal.SOLVE_MATH, entity_mentions=mentions),
    )


class _ForceAmbiguousManager:
    """Minimal IKnowledgeManager wrapper forcing one specific mention to
    resolve as AMBIGUOUS (multiple alias matches), delegating everything
    else to a real manager. Used only to prove ambiguity still takes
    priority over the new PARTIALLY_GROUNDED status."""

    def __init__(self, real_manager, ambiguous_word: str, matches):
        self._real = real_manager
        self._ambiguous_word = ambiguous_word.lower()
        self._matches = matches
        self.concept_store = SimpleNamespace(repository=self)

    def get_concept_by_name(self, name):
        if name.strip().lower() == self._ambiguous_word:
            return None
        return self._real.get_concept_by_name(name)

    def resolve_alias(self, name):
        if name.strip().lower() == self._ambiguous_word:
            return self._matches
        return self._real.concept_store.repository.resolve_alias(name)


# ─────────────────────────────────────────────────────────────
# Test 1 — Quantity grounding
# ─────────────────────────────────────────────────────────────

def test_quantity_mention_grounds_to_resolved_numeric_value():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        candidate = _quantity_candidate([("10", 10.0)])
        raw = RawInput.from_text("10")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.GROUNDED
        assert len(situation.grounded_entities) == 1
        ge = situation.grounded_entities[0]
        assert ge.role == "QUANTITY"
        assert ge.numeric_value == 10.0
        assert ge.is_known is True
        assert ge.status == GroundingStatus.RESOLVED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 2 — Multiple quantities
# ─────────────────────────────────────────────────────────────

def test_multiple_quantity_mentions_all_ground_correctly():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        candidate = _quantity_candidate([("10", 10.0), ("20", 20.0)])
        raw = RawInput.from_text("10 20")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.GROUNDED
        assert len(situation.grounded_entities) == 2
        values = sorted(ge.numeric_value for ge in situation.grounded_entities)
        assert values == [10.0, 20.0]
        assert all(ge.role == "QUANTITY" and ge.is_known is True for ge in situation.grounded_entities)

        # "1,000" (thousands separator) must also parse correctly.
        candidate2 = _quantity_candidate([("1,000", 1000.0)])
        situation2 = pipeline.grounding_engine.ground(
            InterpretationSet(raw_input=RawInput.from_text("1,000"), candidates=[candidate2])
        )
        assert situation2.status == SituationStatus.GROUNDED
        assert situation2.grounded_entities[0].numeric_value == 1000.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 3 — Variable grounding
# ─────────────────────────────────────────────────────────────

def test_variable_mention_grounds_to_unresolved_unknown_value():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        mention = EntityMention(surface_form="x", normalized_form="x", role=EntityRole.VARIABLE)
        candidate = CandidateInterpretation(
            proposed_intent="SolveMathematics",
            candidate_entity_mentions=["x"],
            confidence=0.9,
            semantic_request=SemanticRequest(goal=CommunicativeGoal.SOLVE_MATH, entity_mentions=[mention]),
        )
        raw = RawInput.from_text("x")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.GROUNDED
        assert len(situation.grounded_entities) == 1
        ge = situation.grounded_entities[0]
        assert ge.role == "VARIABLE"
        assert ge.is_known is False
        assert ge.numeric_value is None
        assert ge.status == GroundingStatus.RESOLVED
        # Grounding a VARIABLE must never assign or infer an answer.
        assert ge.numeric_value != 0  # sanity: not silently defaulted to 0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 4 — No fake mathematics grounding (the rubber stamp is gone)
# ─────────────────────────────────────────────────────────────

def test_math_candidate_with_no_typed_mentions_is_not_fabricated_as_grounded():
    """Reproduces today's actual LanguageInterpreter output shape for a math
    query (a single CONCEPT-role mention whose surface form is the raw
    expression string, since Interpret has not been extended yet) and
    confirms Grounding no longer fabricates a resolved 'c_mathematics'
    entity for it. This is the direct removal of the audited rubber stamp."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        mention = EntityMention(surface_form="x + 10 = 20", normalized_form="x + 10 = 20")  # role defaults to CONCEPT
        candidate = CandidateInterpretation(
            proposed_intent="SolveMathematics",
            candidate_entity_mentions=["x + 10 = 20"],
            confidence=0.99,
            semantic_request=SemanticRequest(goal=CommunicativeGoal.SOLVE_MATH, entity_mentions=[mention]),
        )
        raw = RawInput.from_text("x + 10 = 20")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert not any(ge.concept_id == "c_mathematics" for ge in situation.grounded_entities)
        assert not any(ge.canonical_name == "Mathematics" for ge in situation.grounded_entities)
        # Honest outcome: the raw expression string does not resolve as a
        # UKM concept, so the situation is UNRESOLVED, not GROUNDED.
        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES
    finally:
        pipeline.provider.close()


def test_live_interpreter_math_query_now_grounds_via_real_typed_structure():
    """Same finding as the previous test, but through the real, unmodified
    LanguageInterpreter. When this test was first written (Grounding
    Extension step), it asserted UNRESOLVED_ENTITIES here and documented
    that as an accepted, temporary regression "until a future Interpret
    extension produces typed QUANTITY/VARIABLE mentions for Grounding to
    consume." That extension has since landed (Interpretation Extension
    step, math_composition.py) -- LanguageInterpreter now proposes real
    typed mentions for "x + 10 = 20", so Grounding legitimately resolves
    them. This is not the old fabricated 'c_mathematics' rubber stamp
    (still asserted absent below): every grounded entity here is a real,
    individually-resolved QUANTITY/VARIABLE, verified by role and value."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("x + 10 = 20")
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.GROUNDED
        assert not any(ge.concept_id == "c_mathematics" for ge in situation.grounded_entities)
        roles = sorted(ge.role for ge in situation.grounded_entities)
        assert roles == ["QUANTITY", "QUANTITY", "VARIABLE"]
        assert all(ge.status == GroundingStatus.RESOLVED for ge in situation.grounded_entities)
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 5 — Partial grounding
# ─────────────────────────────────────────────────────────────

def test_compare_with_one_unseeded_concept_is_partially_grounded():
    """'Compare Java interfaces with abstract classes.' -- Java Interface is
    seeded, Abstract Class is not. Grounding the real COMPARE candidate
    LanguageInterpreter produces for this query must yield PARTIALLY_GROUNDED,
    not a blanket UNRESOLVED_ENTITIES refusal (Cognitive Substrate Final
    Review §6/§8).

    Note: LanguageInterpreter also proposes a secondary "explain just the
    primary entity" alternative for this compound query (unrelated,
    pre-existing behavior, unmodified by this step). That smaller candidate
    grounds *more completely* (1/1 vs. 1/2) than the COMPARE candidate, so
    the outer ground()'s highest-grounding-score candidate selection picks it
    instead -- a correct, separate concern (candidate selection, not
    per-candidate grounding) that this step does not touch. This test
    isolates the COMPARE candidate itself to test grounding's status
    computation directly, exactly as LanguageInterpreter produced it.
    """
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("Compare Java interface and abstract class.")
        interp_set = pipeline.interpreter.interpret(raw)
        compare_candidate = next(c for c in interp_set.candidates if c.proposed_intent == "CompareConcepts")
        assert compare_candidate.candidate_entity_mentions == ["Java interface", "abstract class"]

        situation = pipeline.grounding_engine.ground(
            InterpretationSet(raw_input=raw, candidates=[compare_candidate])
        )

        assert situation.status == SituationStatus.PARTIALLY_GROUNDED
        statuses = {ge.mention: ge.status for ge in situation.grounded_entities}
        resolved = [m for m, s in statuses.items() if s == GroundingStatus.RESOLVED]
        unknown = [m for m, s in statuses.items() if s == GroundingStatus.UNKNOWN]
        assert any("interface" in m.lower() for m in resolved)
        assert any("abstract" in m.lower() for m in unknown)
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 6 — Existing concept grounding regression
# ─────────────────────────────────────────────────────────────

def test_existing_known_concept_grounding_is_unchanged():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("Explain Java interfaces.")
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.GROUNDED
        assert len(situation.grounded_entities) >= 1
        ge = situation.grounded_entities[0]
        assert ge.status == GroundingStatus.RESOLVED
        assert ge.role == "CONCEPT"
        assert ge.canonical_name is not None
        assert ge.concept_id is not None
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 7 — Existing unknown behavior
# ─────────────────────────────────────────────────────────────

def test_existing_unknown_concept_refusal_is_unchanged():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("What is quantum entanglement?")
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES
        assert any("quantum" in u.lower() for u in situation.unresolved_entities)
        assert situation.grounding_confidence == 0.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 8 — Ambiguous behavior unchanged, and still takes priority
# ─────────────────────────────────────────────────────────────

def test_ambiguous_status_still_takes_priority_over_partial_grounding():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        fake_matches = [
            SimpleNamespace(id="c_widget_a", name="Widget A"),
            SimpleNamespace(id="c_widget_b", name="Widget B"),
        ]
        mock_manager = _ForceAmbiguousManager(pipeline.manager, "widget", fake_matches)
        engine = GroundingEngine(mock_manager)

        # "Java Interface" resolves, "widget" is forced ambiguous, and
        # "totally_unknown_thing" is unknown -- ambiguity must still win.
        candidate = CandidateInterpretation(
            proposed_intent="CompareConcepts",
            candidate_entity_mentions=["Java Interface", "widget", "totally_unknown_thing"],
            confidence=0.9,
        )
        raw = RawInput.from_text("compare java interface, widget, and totally_unknown_thing")
        situation = engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.AMBIGUOUS
        assert any(a for a in situation.ambiguities if "widget" in a.lower())
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 9 — Grounding does not solve
# ─────────────────────────────────────────────────────────────

def test_grounding_module_never_references_a_solver():
    """Static boundary check: grounding.py must not import SymPy, Z3, or
    UniversalMathEngine at all -- if it isn't imported, it categorically
    cannot be invoked from this module."""
    import hsci.cognition.interpretation.grounding as grounding_module

    forbidden = ("sympy", "z3", "UniversalMathEngine", "universal_math_engine")
    for name in vars(grounding_module):
        for term in forbidden:
            assert term.lower() not in name.lower(), (
                f"grounding.py namespace unexpectedly references a solver-related name: {name}"
            )


def test_grounding_an_unparseable_quantity_does_not_raise_or_fabricate():
    """A QUANTITY-role mention whose surface form is not a bare numeral (an
    expression, not a single value) must ground honestly as UNKNOWN -- never
    silently attempt to evaluate/solve it, and never raise."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        mention = EntityMention(surface_form="10 + 20", normalized_form="10 + 20", role=EntityRole.QUANTITY)
        candidate = CandidateInterpretation(
            proposed_intent="SolveMathematics",
            candidate_entity_mentions=["10 + 20"],
            confidence=0.9,
            semantic_request=SemanticRequest(goal=CommunicativeGoal.SOLVE_MATH, entity_mentions=[mention]),
        )
        raw = RawInput.from_text("10 + 20")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES
        ge = situation.grounded_entities[0]
        assert ge.status == GroundingStatus.UNKNOWN
        assert ge.role == "QUANTITY"
        assert ge.numeric_value is None
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# Test 10 — Provenance
# ─────────────────────────────────────────────────────────────

def test_quantity_and_variable_grounding_preserve_provenance():
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        quantity_mention = EntityMention(surface_form="20", normalized_form="20", role=EntityRole.QUANTITY)
        variable_mention = EntityMention(surface_form="x", normalized_form="x", role=EntityRole.VARIABLE)
        candidate = CandidateInterpretation(
            proposed_intent="SolveMathematics",
            candidate_entity_mentions=["20", "x"],
            confidence=0.9,
            semantic_request=SemanticRequest(
                goal=CommunicativeGoal.SOLVE_MATH,
                entity_mentions=[quantity_mention, variable_mention],
            ),
        )
        raw = RawInput.from_text("20 x")
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[candidate]))

        assert situation.status == SituationStatus.GROUNDED
        by_role = {ge.role: ge for ge in situation.grounded_entities}
        assert by_role["QUANTITY"].provenance.get("match_type") == "numeric_literal"
        assert by_role["VARIABLE"].provenance.get("match_type") == "variable"

        # The situation-level evidence trail (same mechanism used for
        # concept grounding) must also carry a role-aware entry for each.
        evidence_types = {e.evidence_type for e in situation.evidence}
        assert "quantity_grounding" in evidence_types
        assert "variable_grounding" in evidence_types
    finally:
        pipeline.provider.close()
