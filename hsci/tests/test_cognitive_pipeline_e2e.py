"""Sprint VS-1 — Vertical Cognitive Slice tests.

Covers the four required VS-1 tests:

1. End-to-End over a REAL UKM (no mocked reasoning result).
2. Canonical seed idempotency.
3. Pipeline failure handling for malformed/empty input.
4. Facade orchestration ordering (engines mocked ONLY for this ordering test).

The E2E test (Test 1) exercises the real UnderstandingEngine, ConceptActivationEngine,
CognitiveReasoningEngine and AnswerGenerationEngine against a real SQLiteProvider /
UKM / ConceptStore / KnowledgeManager. It never substitutes a mock ReasoningResult.
"""
from types import SimpleNamespace
from unittest import mock

import pytest

from hsci.core.cognitive_pipeline import CognitivePipeline, bootstrap_cognitive_pipeline
from hsci.core.kernel import CognitiveContext, EventBus, ValidationError
from hsci.reasoning.reasoning_engine import ReasoningContext
from hsci.knowledge.seeds.oop_concepts import seed_oop_concepts, build_oop_concepts

QUESTION = "Explain what a Java interface is."


# ─────────────────────────────────────────────
# Test 1 — End-to-End Real UKM
# ─────────────────────────────────────────────

def test_e2e_explain_java_interface_real_ukm():
    """Full slice over real engines — asserts AC1..AC7 with no mocked reasoning."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # Drive the REAL engines stage-by-stage to assert the intermediate
        # acceptance criteria, using the pipeline's own wired engine instances.
        ctx = CognitiveContext(request_id="e2e", session_id="test", stimulus=QUESTION)

        understanding = pipeline.understanding_engine.understand(QUESTION, ctx)
        # AC2: intent classified as ExplainConcept.
        assert understanding.intent == "ExplainConcept"
        # AC3 (seed): a non-empty Interface-related seed concept resolved.
        assert understanding.seed_concepts, "seed concepts must not be empty"
        assert any("interface" in s.lower() for s in understanding.seed_concepts)

        activated = pipeline.activation_engine.activate_concepts(
            understanding.seed_concepts, ctx
        )
        # AC4: activation returns a non-empty activated set.
        assert activated.concepts, "activated concept set must not be empty"
        # AC3 (activation): the Interface concept is activated.
        activated_ids = {ac.concept.id for ac in activated.concepts}
        assert "c_interface" in activated_ids

        workspace = [
            pipeline.manager.get_concept(ac.concept.id) for ac in activated.concepts
        ]
        workspace = [c for c in workspace if c is not None]
        assert workspace, "workspace must contain resolved concepts"

        reasoning_result = pipeline.reasoning_engine.reason(
            workspace, ctx, ReasoningContext(goal=f"Explain: {QUESTION}")
        )
        # AC5: at least one real reasoning conclusion.
        assert len(reasoning_result.conclusions) >= 1

        # AC1 + AC6 + AC7: integrated call returns an Answer generated from the
        # real reasoning result, with a non-empty direct answer.
        answer = pipeline.answer(QUESTION)
        assert answer.direct_answer, "direct_answer must not be empty"
        assert answer.sections, "answer must contain at least one section"
        # The answer references the activated Interface knowledge.
        assert "c_interface" in answer.metadata.activation_concepts
    finally:
        pipeline.provider.close()


def test_e2e_answer_styles_render():
    """The assembled path supports the existing answer styles without mocks."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        for style in ("Standard", "Step-by-Step", "Technical"):
            answer = pipeline.answer(QUESTION, style=style)
            assert answer.direct_answer
            assert answer.sections
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# Test 2 — Canonical Seed Idempotency
# ─────────────────────────────────────────────

def test_seed_idempotency_no_duplicates():
    """Running the seed twice creates nothing new and never duplicates (AC8)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    manager = pipeline.manager
    try:
        expected_count = len(build_oop_concepts())

        first_namespace = manager.search_by_namespace("concept.oop")
        assert len(first_namespace) == expected_count

        # Second application must be a no-op.
        result = seed_oop_concepts(manager)
        assert result["created"] == []
        assert len(result["skipped"]) == expected_count

        second_namespace = manager.search_by_namespace("concept.oop")
        assert len(second_namespace) == expected_count

        # Provenance remains canonical and singular (no duplicate provenance rows).
        history = manager.concept_store.get_history("c_java_interface")
        assert len(history) == 1
        assert history[0]["source_type"] == "CANONICAL_SEED"
    finally:
        pipeline.provider.close()


def test_seed_marks_canonical_provenance():
    """Seeded concepts carry CANONICAL_SEED provenance (canonical/learned split)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        for concept in build_oop_concepts():
            history = pipeline.manager.concept_store.get_history(concept.id)
            assert history, f"no provenance recorded for {concept.id}"
            assert history[0]["source_type"] == "CANONICAL_SEED"
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# Test 3 — Pipeline Failure Handling
# ─────────────────────────────────────────────

@pytest.mark.parametrize("bad_question", ["", "   ", "\n\t", None])
def test_empty_question_raises_validation_error(bad_question):
    """Malformed/empty input fails cleanly via the existing ValidationError (AC-fail)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=False)
    try:
        with pytest.raises(ValidationError):
            pipeline.answer(bad_question)  # type: ignore[arg-type]
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# Test 4 — Pipeline Ordering (engines mocked ONLY here)
# ─────────────────────────────────────────────

def test_pipeline_orchestration_order():
    """Facade calls the engines in the exact required order.

    Mocks are acceptable ONLY for this orchestration unit test.
    """
    call_order = []

    from hsci.core.data_types import Concept
    mock_concept = Concept(id="c_something", name="something", abstract_rule="something definition", namespace="test")
    manager = mock.MagicMock()
    manager.get_concept.return_value = mock_concept
    manager.get_all_concepts.return_value = [mock_concept]
    manager.get_concept_by_name.return_value = mock_concept
    event_bus = mock.MagicMock(spec=EventBus)

    pipeline = CognitivePipeline(manager, event_bus)

    def understand(text, context):
        call_order.append("understanding")
        return SimpleNamespace(intent="ExplainConcept", seed_concepts=["Seed"])

    def activate(seeds, context):
        call_order.append("activation")
        return SimpleNamespace(concepts=[])

    def reason(concepts, context, reasoning_context):
        call_order.append("reasoning")
        return SimpleNamespace(conclusions=[])

    def generate(reasoning_result, context, style="Standard"):
        call_order.append("answer")
        return SimpleNamespace(direct_answer="ok", sections=[])

    pipeline.understanding_engine = mock.MagicMock()
    pipeline.understanding_engine.understand.side_effect = understand
    pipeline.activation_engine = mock.MagicMock()
    pipeline.activation_engine.activate_concepts.side_effect = activate
    pipeline.reasoning_engine = mock.MagicMock()
    pipeline.reasoning_engine.reason.side_effect = reason
    pipeline.answer_engine = mock.MagicMock()
    pipeline.answer_engine.generate.side_effect = generate

    result = pipeline.answer("Explain something.")

    assert call_order == ["understanding", "activation", "reasoning", "answer"]
    assert result.direct_answer == "ok"
