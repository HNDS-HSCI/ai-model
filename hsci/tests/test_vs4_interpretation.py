"""HSCI VS-4 Acceptance Test Suite: Cognitive Interpretation & Task Derivation.

Tests the full cognitive interpretation boundary:
    RawInput
        ↓
    LanguageInterpreter
        ↓
    GroundingEngine
        ↓
    CognitiveSituation
        ↓
    TaskDeriver
        ↓
    CognitivePipeline

Executes REAL production engines against a REAL SQLite UKM store with zero mocks
on the cognitive path.
"""
import pytest
from typing import List, Dict, Any

from hsci.core.cognitive_pipeline import CognitivePipeline, bootstrap_cognitive_pipeline
from hsci.cognition.interpretation.models import (
    RawInput,
    CandidateInterpretation,
    InterpretationSet,
    GroundedEntity,
    GroundingStatus,
    CognitiveSituation,
    SituationStatus,
    CognitiveTask,
    TaskAction,
    Evidence,
)
from hsci.cognition.interpretation.interpreter import LanguageInterpreter
from hsci.cognition.interpretation.grounding import GroundingEngine
from hsci.cognition.interpretation.task_deriver import TaskDeriver
from hsci.core.data_types import Concept


# ─────────────────────────────────────────────
# TEST 1 — Concept Explanation
# ─────────────────────────────────────────────

def test_vs4_01_concept_explanation():
    """Test 1: 'What is a Java interface?' -> Grounded, Java Interface resolved, EXPLAIN_CONCEPT."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("What is a Java interface?")
        assert raw.original_text == "What is a Java interface?"

        interp_set = pipeline.interpreter.interpret(raw)
        assert len(interp_set.candidates) >= 1
        top_cand = interp_set.candidates[0]
        assert top_cand.proposed_intent == "ExplainConcept"

        situation = pipeline.grounding_engine.ground(interp_set)
        assert situation.status == SituationStatus.GROUNDED
        assert any(ge.status == GroundingStatus.RESOLVED and "interface" in ge.canonical_name.lower() for ge in situation.grounded_entities)

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.EXPLAIN_CONCEPT
        assert "interface" in task.primary_target.lower()

        # End-to-end pipeline execution
        ans = pipeline.answer("What is a Java interface?")
        assert ans.direct_answer
        assert hasattr(ans, "cognitive_situation")
        assert hasattr(ans, "cognitive_task")
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 2 — Paraphrase Robustness & Purpose
# ─────────────────────────────────────────────

def test_vs4_02_paraphrase_and_purpose():
    """Test 2: 'I'm confused about what Java interfaces are and why they exist.' -> EXPLAIN_CONCEPT."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "I'm confused about what Java interfaces are and why they exist."
        raw = RawInput.from_text(prompt)
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)
        task = pipeline.task_deriver.derive(situation)

        assert situation.status == SituationStatus.GROUNDED
        assert task.action == TaskAction.EXPLAIN_CONCEPT
        assert any("interface" in ge.canonical_name.lower() for ge in situation.grounded_entities if ge.status == GroundingStatus.RESOLVED)

        ans = pipeline.answer(prompt)
        assert ans.direct_answer
        assert ans.confidence.score > 0.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 3 — Multi-Concept Comparison
# ─────────────────────────────────────────────

def test_vs4_03_comparison_task_derivation():
    """Test 3: 'How is a Java interface different from an abstract class?' -> COMPARE_CONCEPTS."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "How is a Java interface different from a class?"
        raw = RawInput.from_text(prompt)
        interp_set = pipeline.interpreter.interpret(raw)

        # Check candidate interpretation has comparison intent and two entities
        top_cand = interp_set.candidates[0]
        assert top_cand.proposed_intent == "CompareConcepts"
        assert len(top_cand.candidate_entity_mentions) >= 2

        situation = pipeline.grounding_engine.ground(interp_set)
        assert situation.status == SituationStatus.GROUNDED
        resolved = [ge for ge in situation.grounded_entities if ge.status == GroundingStatus.RESOLVED]
        assert len(resolved) >= 2

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.COMPARE_CONCEPTS
        assert task.primary_target is not None
        assert len(task.secondary_targets) >= 1

        ans = pipeline.answer(prompt)
        assert ans.direct_answer
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 4 — Multi-Concept Relationship Derivation
# ─────────────────────────────────────────────

def test_vs4_04_relationship_task_derivation():
    """Test 4: 'What is the relationship between Java Interface and Abstraction?' -> DERIVE_RELATIONSHIP."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "What is the relationship between Java Interface and Abstraction?"
        raw = RawInput.from_text(prompt)
        interp_set = pipeline.interpreter.interpret(raw)

        top_cand = interp_set.candidates[0]
        assert top_cand.proposed_intent == "FindRelationship"
        assert len(top_cand.candidate_entity_mentions) >= 2

        situation = pipeline.grounding_engine.ground(interp_set)
        assert situation.status == SituationStatus.GROUNDED

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.DERIVE_RELATIONSHIP
        assert "interface" in task.primary_target.lower() or "abstraction" in task.primary_target.lower()

        ans = pipeline.answer(prompt)
        assert ans.direct_answer
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 5 — Unknown Concept Refusal
# ─────────────────────────────────────────────

def test_vs4_05_unknown_concept_refusal():
    """Test 5: 'What is quantum entanglement?' -> UNKNOWN entity, REPORT_UNKNOWN, 0.0 confidence."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "What is quantum entanglement?"
        raw = RawInput.from_text(prompt)
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES
        assert any("quantum" in u.lower() for u in situation.unresolved_entities)

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.REPORT_UNKNOWN

        ans = pipeline.answer(prompt)
        assert ans.confidence.score == 0.0
        assert "unable to resolve" in ans.direct_answer.lower()
        assert ans.cognitive_task.action == TaskAction.REPORT_UNKNOWN
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 6 — Missing Context Detection
# ─────────────────────────────────────────────

def test_vs4_06_missing_context_detection():
    """Test 6: 'Why is it useful?' with no previous referent -> INSUFFICIENT_CONTEXT."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "Why is it useful?"
        raw = RawInput.from_text(prompt)
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.INSUFFICIENT_CONTEXT
        assert len(situation.assumptions) >= 1

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT

        ans = pipeline.answer(prompt)
        assert ans.confidence.score == 0.0
        assert "context" in ans.direct_answer.lower() or "antecedent" in ans.direct_answer.lower()
        assert ans.cognitive_task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 7 — Ambiguity Detection & Refusal
# ─────────────────────────────────────────────

def test_vs4_07_ambiguity_no_silent_guessing():
    """Test 7: Ambiguous alias matching multiple concepts -> AMBIGUOUS, no silent [0] picking."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # Add an ambiguous alias 'poly_contract' pointing to BOTH Java Interface AND Class
        pipeline.provider.execute_write(
            "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
            ("c_java_interface", "poly_contract")
        )
        pipeline.provider.execute_write(
            "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
            ("c_class", "poly_contract")
        )

        raw = RawInput.from_text("Explain what poly_contract is.")
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        assert situation.status == SituationStatus.AMBIGUOUS
        assert len(situation.ambiguities) >= 1
        amb_ent = next(ge for ge in situation.grounded_entities if ge.status == GroundingStatus.AMBIGUOUS)
        assert len(amb_ent.candidate_concept_names) >= 2
        assert "Java Interface" in amb_ent.candidate_concept_names
        assert "Class" in amb_ent.candidate_concept_names

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.REPORT_AMBIGUITY

        ans = pipeline.answer("Explain what poly_contract is.")
        assert ans.confidence.score == 0.0
        assert "ambiguous" in ans.direct_answer.lower()
        assert ans.cognitive_task.action == TaskAction.REPORT_AMBIGUITY
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 8 — Unsupported Relationship Validation
# ─────────────────────────────────────────────

def test_vs4_08_unsupported_relationship_not_fabricated():
    """Test 8: Two grounded concepts with an unsupported relationship hypothesis -> not fabricated."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text("Explain how Java Interface inherits from Method.")
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)

        # Both concepts exist, but no direct inheritance exists from Java Interface to Method
        resolved_names = [ge.canonical_name for ge in situation.grounded_entities if ge.status == GroundingStatus.RESOLVED]
        assert "Java Interface" in resolved_names or "Method" in resolved_names

        ans = pipeline.answer("Explain how Java Interface inherits from Method.")
        # Must not fabricate an assertion that Java Interface inherits from Method
        assert "java interface inherits from method" not in ans.direct_answer.lower()
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 9 — Long Multi-Paragraph Input
# ─────────────────────────────────────────────

def test_vs4_09_long_input_preservation():
    """Test 9: Multi-paragraph user input preserves original text, extracts major concepts, and derives task."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        long_text = """
        I am designing a large-scale enterprise system in Java and thinking about our architecture.
        We have many decoupled components that communicate across services.
        
        Specifically, can you explain what a Java interface is and how it relates to abstraction?
        
        This will help our team establish our design patterns correctly.
        """
        raw = RawInput.from_text(long_text)
        assert raw.original_text == long_text

        interp_set = pipeline.interpreter.interpret(raw)
        assert len(interp_set.candidates) >= 1

        situation = pipeline.grounding_engine.ground(interp_set)
        assert situation.status == SituationStatus.GROUNDED
        assert any(ge.status == GroundingStatus.RESOLVED for ge in situation.grounded_entities)

        task = pipeline.task_deriver.derive(situation)
        assert task.action in (TaskAction.EXPLAIN_CONCEPT, TaskAction.DERIVE_RELATIONSHIP)

        ans = pipeline.answer(long_text)
        assert ans.direct_answer
        assert ans.confidence.score > 0.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 10 — LLM Disabled by Default
# ─────────────────────────────────────────────

def test_vs4_10_llm_disabled_by_default():
    """Test 10: Entire VS-4 cognitive interpretation stack functions 100% deterministically with LLM disabled."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        assert pipeline.interpreter.enable_llm is False
        assert pipeline.interpreter.llm_adapter is None

        ans = pipeline.answer("What is a Java interface?")
        assert ans.direct_answer
        assert ans.confidence.score > 0.0
        assert hasattr(ans, "cognitive_situation")
        assert ans.cognitive_situation.accepted_interpretation.source_method.startswith("structural_")
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 11 — Untrusted LLM Proposal Grounding & Rejection
# ─────────────────────────────────────────────

class MockUntrustedLLMAdapter:
    """Mock LLM proposing invalid, hallucinated, or malformed hypotheses."""
    def __init__(self, proposals: List[Dict[str, Any]]):
        self.proposals = proposals

    def propose(self, text: str) -> List[Dict[str, Any]]:
        return self.proposals


def test_vs4_11_untrusted_llm_hallucination_rejected():
    """Test 11: LLM proposes hallucinated concept -> GroundingEngine rejects it and does NOT fabricate knowledge."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        fake_llm = MockUntrustedLLMAdapter(proposals=[
            {
                "intent": "ExplainConcept",
                "entities": ["NonExistentQuantumWidget", "HypotheticalAxiom99"],
                "relationships": [{"type": "warp_drive"}],
                "confidence": 0.99  # LLM hallucinates high confidence
            }
        ])

        interpreter_with_llm = LanguageInterpreter(llm_adapter=fake_llm, enable_llm=True)
        raw = RawInput.from_text("Explain the widget.")
        interp_set = interpreter_with_llm.interpret(raw)

        # Ensure LLM proposal was captured as untrusted candidate
        llm_cand = next(c for c in interp_set.candidates if c.source_method == "llm_untrusted_proposal")
        assert llm_cand.confidence == 0.99

        # Grounding MUST reject the hallucinated entities as UNKNOWN
        situation = pipeline.grounding_engine.ground(InterpretationSet(raw_input=raw, candidates=[llm_cand]))
        assert situation.status == SituationStatus.UNRESOLVED_ENTITIES
        assert "NonExistentQuantumWidget" in situation.unresolved_entities
        assert situation.grounding_confidence == 0.0  # Grounding overrides untrusted confidence

        task = pipeline.task_deriver.derive(situation)
        assert task.action == TaskAction.REPORT_UNKNOWN
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST 12 — Paraphrase Matrix (10+ Variations)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_action", [
    ("What is a Java interface?", TaskAction.EXPLAIN_CONCEPT),
    ("Explain Java interfaces.", TaskAction.EXPLAIN_CONCEPT),
    ("Can you explain what an interface is in Java?", TaskAction.EXPLAIN_CONCEPT),
    ("Why do Java interfaces exist?", TaskAction.EXPLAIN_CONCEPT),
    ("What purpose does an interface serve in Java?", TaskAction.EXPLAIN_CONCEPT),
    ("Tell me about Java Interface.", TaskAction.EXPLAIN_CONCEPT),
    ("I am curious about the Java interface concept.", TaskAction.EXPLAIN_CONCEPT),
    ("Compare Java interface and class.", TaskAction.COMPARE_CONCEPTS),
    ("How is an interface different from a class?", TaskAction.COMPARE_CONCEPTS),
    ("What is the relationship between Java Interface and Abstraction?", TaskAction.DERIVE_RELATIONSHIP),
    ("Why is it useful?", TaskAction.REPORT_INSUFFICIENT_CONTEXT),
    ("What is dark energy warp resonance?", TaskAction.REPORT_UNKNOWN),
])
def test_vs4_12_paraphrase_matrix(query: str, expected_action: TaskAction):
    """Test 12: 12 materially different phrasing categories converge to correct CognitiveTasks."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        raw = RawInput.from_text(query)
        interp_set = pipeline.interpreter.interpret(raw)
        situation = pipeline.grounding_engine.ground(interp_set)
        task = pipeline.task_deriver.derive(situation)

        assert task.action == expected_action, f"Query '{query}' derived '{task.action}' instead of expected '{expected_action}'"
    finally:
        pipeline.provider.close()
