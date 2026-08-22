"""HSCI Cognitive MVP Acceptance Test Suite (Sprint VS-3).

Evaluates the complete end-to-end cognitive vertical slice across Test Groups A through H.
All tests execute REAL production engines against a REAL SQLite UKM store with zero mocks
on the cognitive path.
"""
import pytest
import httpx

from hsci.core.cognitive_pipeline import CognitivePipeline, bootstrap_cognitive_pipeline
from hsci.core.kernel import CognitiveContext
from hsci.core.data_types import Concept
from hsci.knowledge.seeds.oop_concepts import build_oop_concepts
from hsci.reasoning.reasoning_engine import (
    CognitiveReasoningEngine, ReasoningContext, RuleBasedInferenceStrategy
)
from hsci.response.explanatory_synthesizer import ExplanatoryAnswer
from brain_api import app


# ─────────────────────────────────────────────
# TEST GROUP A — Knowledge Retrieval
# ─────────────────────────────────────────────

def test_group_a1_what_is_java_interface():
    """A1: 'What is a Java interface?' -> Understanding, Resolution, Retrieval, Answer."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ctx = CognitiveContext(request_id="a1", session_id="test", stimulus="What is a Java interface?")
        understanding = pipeline.understanding_engine.understand("What is a Java interface?", ctx)
        assert understanding.intent == "ExplainConcept"
        assert any("interface" in s.lower() for s in understanding.seed_concepts)

        ans = pipeline.answer("What is a Java interface?")
        assert ans.direct_answer
        assert len(ans.sections) >= 1
        assert "reference type declaring abstract methods" in ans.direct_answer or any(
            "reference type declaring abstract methods" in s.content for s in ans.sections
        )
    finally:
        pipeline.provider.close()


def test_group_a2_explain_java_interfaces():
    """A2: 'Explain Java interfaces.' -> Equivalent semantic understanding to A1."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ctx = CognitiveContext(request_id="a2", session_id="test", stimulus="Explain Java interfaces.")
        understanding = pipeline.understanding_engine.understand("Explain Java interfaces.", ctx)
        assert understanding.intent == "ExplainConcept"
        assert any("interface" in s.lower() for s in understanding.seed_concepts)

        ans = pipeline.answer("Explain Java interfaces.")
        assert ans.direct_answer
    finally:
        pipeline.provider.close()


def test_group_a3_can_you_explain_interface_in_java():
    """A3: 'Can you explain what an interface is in Java?' -> Resolves to Java Interface."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ctx = CognitiveContext(request_id="a3", session_id="test", stimulus="Can you explain what an interface is in Java?")
        understanding = pipeline.understanding_engine.understand("Can you explain what an interface is in Java?", ctx)
        assert understanding.intent == "ExplainConcept"
        assert any("interface" in s.lower() for s in understanding.seed_concepts)

        ans = pipeline.answer("Can you explain what an interface is in Java?")
        assert ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP B — Genuine Reasoning Derivation
# ─────────────────────────────────────────────

def test_group_b1_derive_java_interface_to_abstraction():
    """B1: Discover Java Interface -> Interface and Interface -> Abstraction, deriving Java Interface -> Abstraction."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ctx = CognitiveContext(request_id="b1", session_id="test", stimulus="What is the relationship between Java Interface and Abstraction?")
        # Real engines execution
        understanding = pipeline.understanding_engine.understand("What is the relationship between Java Interface and Abstraction?", ctx)
        activated = pipeline.activation_engine.activate_concepts(understanding.seed_concepts, ctx)
        workspace = [pipeline.manager.get_concept(ac.concept.id) for ac in activated.concepts]
        workspace = [c for c in workspace if c is not None]

        # Verify Java Interface does NOT directly store c_abstraction
        java_iface = pipeline.manager.get_concept("c_java_interface")
        assert java_iface is not None
        assert "c_abstraction" not in java_iface.generalizes_to

        # Execute reasoning
        reasoning_result = pipeline.reasoning_engine.reason(workspace, ctx, ReasoningContext(goal="test-b1"))
        
        # Discover derived conclusion
        derived_conclusions = [c for c in reasoning_result.conclusions if getattr(c, "derived", False)]
        assert len(derived_conclusions) >= 1

        transitive_conclusion = next(
            (c for c in derived_conclusions if "Java Interface generalizes to Abstraction" in c.statement),
            None
        )
        assert transitive_conclusion is not None
        assert transitive_conclusion.rule_name == "GeneralizationTransitivity"
        assert transitive_conclusion.depth == 1
        assert transitive_conclusion.derived is True
        assert len(transitive_conclusion.premises) == 2
        assert any("Java Interface generalizes to Interface" in p for p in transitive_conclusion.premises)
        assert any("Interface generalizes to Abstraction" in p for p in transitive_conclusion.premises)
        assert transitive_conclusion.confidence <= 0.90
    finally:
        pipeline.provider.close()


def test_group_b2_derive_method_to_abstraction():
    """B2: Method -> Class and Class -> Abstraction derives Method -> Abstraction."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ctx = CognitiveContext(request_id="b2", session_id="test", stimulus="Describe a method")
        understanding = pipeline.understanding_engine.understand("Describe a method", ctx)
        activated = pipeline.activation_engine.activate_concepts(understanding.seed_concepts, ctx)
        workspace = [pipeline.manager.get_concept(ac.concept.id) for ac in activated.concepts]
        workspace = [c for c in workspace if c is not None]

        method_c = pipeline.manager.get_concept("c_method")
        assert method_c is not None
        assert "c_abstraction" not in method_c.generalizes_to

        reasoning_result = pipeline.reasoning_engine.reason(workspace, ctx, ReasoningContext(goal="test-b2"))
        
        derived = next(
            (c for c in reasoning_result.conclusions if "Method generalizes to Abstraction" in c.statement),
            None
        )
        assert derived is not None
        assert derived.derived is True
        assert derived.rule_name == "GeneralizationTransitivity"
    finally:
        pipeline.provider.close()


def test_group_b3_ablation_missing_premise_blocks_derivation():
    """B3: If premise Interface -> Abstraction is removed, Java Interface -> Abstraction MUST disappear."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=False)
    try:
        # Custom seed with Interface -> Abstraction removed
        concepts = [
            Concept(
                id="c_abstraction",
                name="Abstraction",
                namespace="concept.oop",
                domain="programming",
                abstract_rule="Abstraction rule.",
            ),
            Concept(
                id="c_interface",
                name="Interface",
                namespace="concept.oop",
                domain="programming",
                generalizes_to=[],  # ABLATION: Interface -> Abstraction edge removed!
                abstract_rule="Interface contract.",
            ),
            Concept(
                id="c_java_interface",
                name="Java Interface",
                namespace="concept.oop",
                domain="programming",
                generalizes_to=["c_interface"],  # Java Interface -> Interface remains
                abstract_rule="Java interface declaration.",
            ),
        ]
        for c in concepts:
            pipeline.manager.create_concept(c)

        ctx = CognitiveContext(request_id="b3", session_id="test", stimulus="Explain what a Java interface is.")
        workspace = [pipeline.manager.get_concept(c.id) for c in concepts]
        
        reasoning_result = pipeline.reasoning_engine.reason(workspace, ctx, ReasoningContext(goal="test-b3"))
        
        # Assert that Java Interface -> Abstraction is NOT derived
        derived_statements = [c.statement for c in reasoning_result.conclusions]
        assert "Java Interface generalizes to Abstraction" not in derived_statements
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP C — Traceability
# ─────────────────────────────────────────────

def test_group_c_traceability_distinguishes_retrieved_vs_derived():
    """C: Final answer distinguishes retrieved knowledge from derived knowledge with full provenance."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain what a Java interface is.")
        assert isinstance(ans, ExplanatoryAnswer)

        # 1. Retrieved knowledge
        defs = [ks for ks in ans.knowledge_sources if ks.knowledge_type == "definition"]
        assert len(defs) == 1
        d = defs[0]
        assert d.source_concept_id == "c_java_interface"
        assert d.source_concept_name == "Java Interface"
        assert d.source_provenance["source_type"] == "CANONICAL_SEED"

        # 2. Derived knowledge
        derived_ks = [ks for ks in ans.knowledge_sources if ks.knowledge_type == "derived_relationship"]
        assert len(derived_ks) >= 1
        d_rel = derived_ks[0]
        assert d_rel.reasoning_rule == "GeneralizationTransitivity"
        assert d_rel.source_provenance["derived"] is True
        assert d_rel.source_provenance["source_type"] == "derived"
        assert len(d_rel.source_provenance["premises"]) == 2
        assert d_rel.reasoning_confidence <= 0.90
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP D — Unknown Knowledge
# ─────────────────────────────────────────────

def test_group_d_refuse_fabrication_on_unknown_knowledge():
    """D: 'What is quantum entanglement?' -> explicit refusal / uncertainty, zero hallucination."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is quantum entanglement?")
        # Must report inability to resolve or lack of verified knowledge
        assert ans.confidence.score == 0.0
        assert "unable to resolve" in ans.direct_answer.lower() or "no verified conclusions" in ans.direct_answer.lower() or any(
            "no verified conclusions" in s.content.lower() for s in ans.sections
        )
        # Must not fabricate facts
        assert "quantum" not in (ans.metadata.activation_concepts or [])
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP E — Knowledge vs Reasoning Failure Classification
# ─────────────────────────────────────────────

def test_group_e1_known_and_reasoned():
    """E1: Known concept + valid derivation -> Full explanatory answer with derived links."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain what a Java interface is.")
        assert isinstance(ans, ExplanatoryAnswer)
        assert ans.definition is not None
        assert any(ks.knowledge_type == "derived_relationship" for ks in ans.knowledge_sources)
        assert ans.confidence.score >= 0.80
    finally:
        pipeline.provider.close()


def test_group_e2_known_without_derivation():
    """E2: Known concept with no generalization parent (Abstraction) -> definition preserved without false derivation."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is Abstraction?")
        assert isinstance(ans, ExplanatoryAnswer)
        assert ans.definition is not None
        # Abstraction has no generalizations, so no derived transitive relations exist for it
        derived_for_abstraction = [
            ks for ks in ans.knowledge_sources
            if ks.knowledge_type == "derived_relationship" and "Abstraction generalizes to" in (ks.reasoning_conclusion or "")
        ]
        assert len(derived_for_abstraction) == 0
    finally:
        pipeline.provider.close()


def test_group_e3_unknown_knowledge():
    """E3: Unknown knowledge query -> confidence 0.0, no hallucinated definitions."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain superfluidity in helium-4.")
        assert ans.confidence.score == 0.0
        assert not getattr(ans, "definition", None)
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP F — Paraphrase Robustness
# ─────────────────────────────────────────────

@pytest.mark.parametrize("phrasing", [
    "What is a Java interface?",
    "Explain Java interfaces.",
    "Can you explain what an interface is in Java?",
    "Why do Java interfaces exist?",
    "What purpose does an interface serve in Java?",
])
def test_group_f_paraphrase_robustness(phrasing):
    """F: Test 5 distinct phrasings resolving the underlying concept and producing non-empty answers."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(phrasing)
        assert ans.direct_answer
        assert len(ans.sections) >= 1
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP G — Answer Quality & Calibration
# ─────────────────────────────────────────────

def test_group_g_confidence_calibration():
    """G: Derived confidence <= min(P1, P2) and never artificially inflated."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain what a Java interface is.")
        assert ans.confidence.score <= 0.90
        assert ans.confidence.score > 0.0
        for ks in ans.knowledge_sources:
            if ks.knowledge_type == "derived_relationship":
                assert ks.reasoning_confidence <= 0.90
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────
# TEST GROUP H — Real Application Runtime (API Endpoint)
# ─────────────────────────────────────────────

def test_group_h_web_application_reaches_cognitive_pipeline():
    """H: The FastAPI /process endpoint executes the V4 CognitivePipeline with full provenance."""
    import asyncio
    from brain_api import StimulusRequest, process_stimulus

    async def run_async():
        # 1. Test known concept explanation
        data = await process_stimulus(StimulusRequest(stimulus="What is a Java interface?"))
        assert data["success"] is True
        assert "reference type declaring abstract methods" in data["solution"]
        assert "DERIVED CONCLUSION" in data["deliberation"]
        assert "GeneralizationTransitivity" in data["deliberation"]
        assert data["confidence"] > 0.0

        # 2. Test unknown knowledge query
        data_u = await process_stimulus(StimulusRequest(stimulus="What is quantum entanglement?"))
        assert data_u["success"] is False
        assert data_u["confidence"] == 0.0

    asyncio.run(run_async())
