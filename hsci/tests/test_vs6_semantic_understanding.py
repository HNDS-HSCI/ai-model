"""HSCI VS-6 Acceptance Test Suite: General Cognitive Language Understanding.

Evaluates semantic intermediate representation, communicative goal convergence,
linguistic variation robustness, negation/modality preservation, context references,
and adversarial proposal grounding.

ZERO mocks on the cognitive execution path.
"""
import time
import pytest

from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline
from hsci.cognition.interpretation.models import (
    RawInput,
    TaskAction,
    SituationStatus,
    GroundingStatus,
)
from hsci.cognition.interpretation.semantic_model import (
    CommunicativeGoal,
    SemanticRequest,
    EntityMention,
    SemanticRelation,
    SemanticConstraint,
)
from hsci.cognition.interpretation.untrusted_proposer import UntrustedSemanticProposer


# ─────────────────────────────────────────────────────────────
# TEST GROUP 1: ADVERSARIAL PHRASING & COMMUNICATIVE GOAL
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "What is a Java interface?",
    "Can you explain Java interfaces?",
    "I don't understand interfaces in Java.",
    "Tell me about Java Interface.",
    "What exactly does a Java interface mean?",
    "Give me an explanation of Java interface.",
    "What purpose does an interface serve in Java?",
    "Why do Java interfaces exist?",
])
def test_vs6_01_explain_phrasing_convergence(query: str):
    """Paraphrases with EXPLAIN intent converge on CommunicativeGoal.EXPLAIN and TaskAction.EXPLAIN_CONCEPT."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text(query)
        iset = pipeline.interpreter.interpret(raw)
        assert len(iset.candidates) >= 1
        primary = iset.candidates[0]
        assert primary.semantic_request is not None
        assert primary.semantic_request.goal == CommunicativeGoal.EXPLAIN
        assert "java interface" in [em.normalized_form for em in primary.semantic_request.entity_mentions] or "interface" in [em.normalized_form for em in primary.semantic_request.entity_mentions]

        ans = pipeline.answer(query)
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert ans.confidence.score > 0.85
    finally:
        pipeline.provider.close()


@pytest.mark.parametrize("query", [
    "How is a Java interface different from a class?",
    "Compare Java interface with class.",
    "What's the difference between a Java interface and a class?",
    "Are Java interfaces and classes the same thing?",
    "Why would someone use a Java interface instead of a class?",
    "Java interface vs class.",
])
def test_vs6_02_compare_phrasing_convergence(query: str):
    """Paraphrases with COMPARE intent converge on CommunicativeGoal.COMPARE and TaskAction.COMPARE_CONCEPTS."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text(query)
        iset = pipeline.interpreter.interpret(raw)
        assert len(iset.candidates) >= 1
        primary = iset.candidates[0]
        assert primary.semantic_request is not None
        assert primary.semantic_request.goal == CommunicativeGoal.COMPARE
        assert len(primary.semantic_request.entity_mentions) >= 2

        ans = pipeline.answer(query)
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        assert "Java Interface" in ans.direct_answer
        assert "Class" in ans.direct_answer
    finally:
        pipeline.provider.close()


@pytest.mark.parametrize("query", [
    "What is the relationship between Java Interface and Abstraction?",
    "How are Java Interface and Abstraction connected?",
    "Does Java Interface have anything to do with Abstraction?",
    "How does Java Interface relate to Abstraction?",
    "What's the connection between Java Interface and Abstraction?",
])
def test_vs6_03_relate_phrasing_convergence(query: str):
    """Paraphrases with RELATE intent converge on CommunicativeGoal.RELATE and TaskAction.DERIVE_RELATIONSHIP."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text(query)
        iset = pipeline.interpreter.interpret(raw)
        assert len(iset.candidates) >= 1
        primary = iset.candidates[0]
        assert primary.semantic_request is not None
        assert primary.semantic_request.goal == CommunicativeGoal.RELATE

        ans = pipeline.answer(query)
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
        assert "generalizes to abstraction" in ans.direct_answer.lower()
        assert ans.confidence.score > 0.80
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 2: SEMANTIC STRUCTURE EQUIVALENCE & DISTINCTION
# ─────────────────────────────────────────────────────────────

def test_vs6_04_semantic_equivalence_across_forms():
    """Different phrasings produce equivalent SemanticRequest objects."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        q1 = "What is a Java interface?"
        q2 = "Give me an explanation of Java interface."

        req1 = pipeline.interpreter.interpret(RawInput.from_text(q1)).candidates[0].semantic_request
        req2 = pipeline.interpreter.interpret(RawInput.from_text(q2)).candidates[0].semantic_request

        assert req1.goal == req2.goal == CommunicativeGoal.EXPLAIN
        assert req1.output_requirements[0].output_type == req2.output_requirements[0].output_type
        assert [e.normalized_form for e in req1.entity_mentions] == [e.normalized_form for e in req2.entity_mentions]
    finally:
        pipeline.provider.close()


def test_vs6_05_semantic_distinguishability():
    """Different goals (Explain vs Compare vs Relate) produce distinct SemanticRequests."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        q_exp = "Explain Java interface."
        q_cmp = "Compare Java interface and class."
        q_rel = "What is the relationship between Java interface and abstraction?"

        req_exp = pipeline.interpreter.interpret(RawInput.from_text(q_exp)).candidates[0].semantic_request
        req_cmp = pipeline.interpreter.interpret(RawInput.from_text(q_cmp)).candidates[0].semantic_request
        req_rel = pipeline.interpreter.interpret(RawInput.from_text(q_rel)).candidates[0].semantic_request

        assert req_exp.goal == CommunicativeGoal.EXPLAIN
        assert req_cmp.goal == CommunicativeGoal.COMPARE
        assert req_rel.goal == CommunicativeGoal.RELATE

        assert req_exp.goal != req_cmp.goal
        assert req_cmp.goal != req_rel.goal
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 3: NEGATION, MODALITY & CONDITIONALS
# ─────────────────────────────────────────────────────────────

def test_vs6_06_negation_compound_constraint():
    """'Don't explain X; compare X and Y' extracts COMPARE goal and negative constraint without dropping intent."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        query = "Don't explain Java interface; compare Java interface and class."
        iset = pipeline.interpreter.interpret(RawInput.from_text(query))
        primary = iset.candidates[0]
        assert primary.semantic_request is not None
        assert primary.semantic_request.goal == CommunicativeGoal.COMPARE
        assert len(primary.semantic_request.constraints) >= 1
        assert primary.semantic_request.constraints[0].operator == "NOT"

        ans = pipeline.answer(query)
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        assert "Java Interface" in ans.direct_answer
        assert "Class" in ans.direct_answer
    finally:
        pipeline.provider.close()


def test_vs6_07_modality_detection():
    """'Can a Java interface be an abstraction?' flags hypothetical modality."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        query = "Can a Java interface relate to abstraction?"
        iset = pipeline.interpreter.interpret(RawInput.from_text(query))
        primary = iset.candidates[0]
        assert primary.semantic_request.modality == "HYPOTHETICAL"
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 4: CONTEXT REFERENCES & BARE REFERENTS
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("deictic_query", [
    "Why is it useful?",
    "What about this?",
    "How does that work?",
    "Explain the previous one.",
])
def test_vs6_08_context_reference_preservation(deictic_query: str):
    """Deictic queries preserve ContextReference and safely refuse without antecedents."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        iset = pipeline.interpreter.interpret(RawInput.from_text(deictic_query))
        primary = iset.candidates[0]
        assert primary.requires_context is True
        assert len(primary.semantic_request.context_references) >= 1

        ans = pipeline.answer(deictic_query)
        assert ans.cognitive_task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT
        assert ans.confidence.score == 0.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 5: NOISY CONVERSATIONAL STIMULI
# ─────────────────────────────────────────────────────────────

def test_vs6_09_noisy_conversational_input():
    """Isolates core entity and goal from surrounding conversational noise."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        noisy_query = "Hey, I am trying to understand this thing called Java Interface, and everyone keeps talking about it. What actually is Java Interface?"
        ans = pipeline.answer(noisy_query)
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert ans.confidence.score > 0.85
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 6: UNTRUSTED PROPOSER & HALLUCINATION REJECTION
# ─────────────────────────────────────────────────────────────

def test_vs6_10_untrusted_proposer_sanitization():
    """Untrusted external proposal is sanitized, stripped of fake IDs, and rejected if concept is absent."""
    fake_proposal = {
        "goal": "EXPLAIN",
        "entity_mentions": [{"mention": "DarkMatterQuantumWarp"}],
        "relationships": [],
        "confidence": 0.99,  # Inflated confidence from external model
    }
    cand = UntrustedSemanticProposer.parse_proposal(fake_proposal)
    assert cand is not None
    assert cand.source_method == "llm_untrusted_proposal"

    # Grounding against UKM MUST reject unknown entity
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        iset = pipeline.interpreter.interpret(RawInput.from_text("What is DarkMatterQuantumWarp?"))
        iset.candidates.append(cand)
        situation = pipeline.grounding_engine.ground(iset)
        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.REPORT_UNKNOWN
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 7: MULTI-PARAGRAPH INPUT & LATENCY
# ─────────────────────────────────────────────────────────────

def test_vs6_11_multi_paragraph_semantic_performance():
    """Multi-paragraph enterprise text parses semantic requests and maintains low latency."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        doc = """
        Architecture Context:
        Our engineering team is building a microservices platform in Java.
        We have strict guidelines regarding type hierarchy, contract interfaces, and polymorphic dispatch.
        
        Requirements Discussion:
        Some engineers argue for using concrete base classes, while others favor pure interfaces.
        To standardize our architecture guidelines, we need clarity on language fundamentals.
        
        Core Question:
        How is a Java interface different from a class?
        
        Additional Notes:
        Please ensure the distinction covers structural definitions and abstraction hierarchies.
        """
        start = time.perf_counter()
        raw = RawInput.from_text(doc)
        iset = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(iset)
        task = pipeline.task_deriver.derive(situation)
        ans = pipeline.answer(doc)
        total_ms = (time.perf_counter() - start) * 1000

        assert situation.status == SituationStatus.GROUNDED
        assert task.action == TaskAction.COMPARE_CONCEPTS
        assert "Java Interface" in ans.direct_answer
        assert "Class" in ans.direct_answer
        assert total_ms < 250.0, f"Latency {total_ms:.2f}ms exceeded 250ms"
    finally:
        pipeline.provider.close()
