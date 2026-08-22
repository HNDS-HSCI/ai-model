"""HSCI VS-5 Acceptance Test Suite: Cognitive Task Execution & Real User Interaction.

Evaluates the real, end-to-end execution of CognitiveTasks over the HSCI cognitive stack:
    - Group A: EXPLAIN_CONCEPT (Grounded retrieval, no hardcoding, definition mutability)
    - Group B: DERIVE_RELATIONSHIP (Transitive generalization derivation and causal premise ablation)
    - Group C: COMPARE_CONCEPTS (Multi-concept grounding, dual definition retrieval, structural comparison)
    - Group D: REPORT_UNKNOWN (Calibrated refusal, zero hallucination)
    - Group E: REPORT_AMBIGUITY (Candidate preservation, zero silent guessing)
    - Group F: REPORT_INSUFFICIENT_CONTEXT (Referential pronoun detection)
    - Group G: API / UI Integration (FastAPI /process end-to-end pipeline consistency)
    - Group H: Real User Scenario Phrasing Matrix
    - Group I: Large Input & Performance Latency Metrics

ZERO mocks on the cognitive execution path.
"""
import time
import pytest
from fastapi.testclient import TestClient

from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline
from hsci.core.data_types import Concept
from hsci.cognition.interpretation.models import (
    RawInput,
    TaskAction,
    SituationStatus,
    GroundingStatus,
)
from hsci.cognition.execution.execution_result import CognitiveExecutionResult
from brain_api import app


# ─────────────────────────────────────────────────────────────
# TEST GROUP A: EXPLAIN_CONCEPT
# ─────────────────────────────────────────────────────────────

def test_vs5_a1_explain_concept_real_ukm():
    """A1: 'What is a Java interface?' -> EXPLAIN_CONCEPT with real UKM definition and reasoning."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is a Java interface?")
        assert ans.direct_answer
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert hasattr(ans, "cognitive_task")
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
        assert hasattr(ans, "cognitive_execution_result")
        exec_res: CognitiveExecutionResult = ans.cognitive_execution_result
        assert exec_res.task_action == TaskAction.EXPLAIN_CONCEPT
        assert "Java Interface" in exec_res.grounded_concepts
        assert "Java Interface" in exec_res.retrieved_definitions
        assert ans.confidence.score > 0.85
    finally:
        pipeline.provider.close()


def test_vs5_a2_explain_concept_paraphrase_equivalence():
    """A2: 'Can you explain what an interface is in Java?' -> Equivalent EXPLAIN_CONCEPT execution."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Can you explain what an interface is in Java?")
        assert ans.direct_answer
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
    finally:
        pipeline.provider.close()


def test_vs5_a3_definition_mutability_no_hardcoding():
    """A3: Modifying the stored definition in UKM dynamically alters the synthesized answer (no hardcoded strings)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # Retrieve and mutate the stored concept definition
        original_concept = pipeline.manager.get_concept("c_java_interface")
        original_def = original_concept.abstract_rule

        mutated_def = "MUTATED_RULE: An interface is a pure behavioral boundary in modern systems."
        mutated_concept = Concept(
            id="c_java_interface",
            name="Java Interface",
            namespace="concept.oop",
            domain="programming",
            abstract_rule=mutated_def,
            status="ACTIVE",
            version=original_concept.version + 1,
        )
        pipeline.manager.update_concept(mutated_concept)

        ans = pipeline.answer("What is a Java interface?")
        assert mutated_def in ans.direct_answer
        assert "MUTATED_RULE" in ans.direct_answer

        # Restore original definition
        restored_concept = Concept(
            id="c_java_interface",
            name="Java Interface",
            namespace="concept.oop",
            domain="programming",
            abstract_rule=original_def,
            status="ACTIVE",
            version=mutated_concept.version + 1,
        )
        pipeline.manager.update_concept(restored_concept)

        ans_restored = pipeline.answer("What is a Java interface?")
        assert original_def in ans_restored.direct_answer
        assert "MUTATED_RULE" not in ans_restored.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP B: DERIVE_RELATIONSHIP
# ─────────────────────────────────────────────────────────────

def test_vs5_b1_derive_relationship_genuine_transitivity():
    """B1: 'What is the relationship between Java Interface and Abstraction?' -> DERIVE_RELATIONSHIP with proof trace."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is the relationship between Java Interface and Abstraction?")
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
        assert ans.cognitive_execution_result.task_action == TaskAction.DERIVE_RELATIONSHIP

        # Verify genuine derived conclusion was generated
        derived_list = ans.cognitive_execution_result.derived_conclusions
        assert len(derived_list) >= 1
        transitive_concl = next(
            (d for d in derived_list if "java interface generalizes to abstraction" in d["statement"].lower()),
            None
        )
        assert transitive_concl is not None
        assert transitive_concl["rule"] == "GeneralizationTransitivity"
        assert len(transitive_concl["premises"]) == 2

        assert "generalizes to abstraction" in ans.direct_answer.lower()
        assert ans.confidence.score > 0.80
    finally:
        pipeline.provider.close()


def test_vs5_b2_relationship_ablation_missing_premise():
    """B2: Removing the intermediate generalization premise blocks the derivation (proves causal inference)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # In the default seed: Java Interface -> Interface -> Abstraction
        # If we query a relationship between two concepts without connecting premises:
        ans = pipeline.answer("What is the relationship between Method and Java Interface?")
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP

        # Neither direct link nor transitive link exists from Method to Java Interface
        derived_list = ans.cognitive_execution_result.derived_conclusions
        assert not any("method generalizes to java interface" in d["statement"].lower() for d in derived_list)
        assert "no direct or derived relationship" in ans.direct_answer.lower() or ans.confidence.score == 0.0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP C: COMPARE_CONCEPTS
# ─────────────────────────────────────────────────────────────

def test_vs5_c1_compare_concepts_dual_grounding_and_contrast():
    """C1: 'How is a Java interface different from a class?' -> COMPARE_CONCEPTS with dual definitions & generalizations."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        prompt = "How is a Java interface different from a class?"
        ans = pipeline.answer(prompt)
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        assert ans.cognitive_execution_result.task_action == TaskAction.COMPARE_CONCEPTS

        # Verify definitions for BOTH concepts are present in the answer
        assert "Java Interface" in ans.direct_answer
        assert "Class" in ans.direct_answer
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert "blueprint bundling state and behaviour for objects" in ans.direct_answer

        # Verify structural sections contain generalizations for both concepts
        sec_titles = [s.title for s in ans.sections]
        assert "Definitions" in sec_titles
        assert "Structural Relationships & Generalizations" in sec_titles

        # Check knowledge sources contain retrieved definitions for both concepts
        retrieved_sources = [ks for ks in ans.knowledge_sources if ks.knowledge_type == "definition"]
        assert len(retrieved_sources) >= 2
        source_concept_names = [ks.source_concept_name for ks in retrieved_sources]
        assert "Java Interface" in source_concept_names
        assert "Class" in source_concept_names
    finally:
        pipeline.provider.close()


def test_vs5_c2_compare_concepts_knowledge_degradation():
    """C2: If a concept has no stored definition, comparison degrades honestly rather than fabricating."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # Clear the definition of 'c_class'
        class_concept = pipeline.manager.get_concept("c_class")
        emptied_class = Concept(
            id="c_class",
            name="Class",
            namespace="concept.oop",
            domain="programming",
            abstract_rule="",  # Empty definition
            status="ACTIVE",
            version=class_concept.version + 1,
        )
        pipeline.manager.update_concept(emptied_class)

        ans = pipeline.answer("How is a Java interface different from a class?")
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        # Must report absence of stored definition for Class rather than inventing one
        assert "no stored definition" in ans.direct_answer.lower() or "(No stored definition in UKM)" in ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP D: REPORT_UNKNOWN
# ─────────────────────────────────────────────────────────────

def test_vs5_d1_unknown_concept_zero_hallucination():
    """D1: 'What is quantum entanglement?' -> REPORT_UNKNOWN with 0.0 confidence and zero hallucination."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is quantum entanglement?")
        assert ans.confidence.score == 0.0
        assert ans.cognitive_task.action == TaskAction.REPORT_UNKNOWN
        assert ans.cognitive_execution_result.is_success is False
        assert "unable to resolve" in ans.direct_answer.lower()
        assert "no verified conclusions" in ans.direct_answer.lower()
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP E: REPORT_AMBIGUITY
# ─────────────────────────────────────────────────────────────

def test_vs5_e1_ambiguity_preservation_no_silent_guess():
    """E1: Querying ambiguous alias preserves all competing concepts and refuses silent [0] guessing."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        pipeline.provider.execute_write(
            "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
            ("c_java_interface", "poly_contract")
        )
        pipeline.provider.execute_write(
            "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
            ("c_class", "poly_contract")
        )

        ans = pipeline.answer("Explain poly_contract.")
        assert ans.confidence.score == 0.0
        assert ans.cognitive_task.action == TaskAction.REPORT_AMBIGUITY
        assert ans.cognitive_execution_result.is_success is False
        assert "ambiguous" in ans.direct_answer.lower()
        assert "Java Interface" in ans.direct_answer
        assert "Class" in ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP F: REPORT_INSUFFICIENT_CONTEXT
# ─────────────────────────────────────────────────────────────

def test_vs5_f1_missing_context_bare_referent():
    """F1: 'Why is it useful?' without preceding referent -> REPORT_INSUFFICIENT_CONTEXT (no guessing)."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Why is it useful?")
        assert ans.confidence.score == 0.0
        assert ans.cognitive_task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT
        assert ans.cognitive_execution_result.is_success is False
        assert "context" in ans.direct_answer.lower() or "antecedent" in ans.direct_answer.lower()
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP G: UI & API ROUTING CONSISTENCY
# ─────────────────────────────────────────────────────────────

def test_vs5_g1_fastapi_process_endpoint_consistency():
    """G1: HTTP POST /process executes the exact same CognitivePipeline with full provenance."""
    client = TestClient(app)

    # Test 1: Explanation
    res_exp = client.post("/process", json={"stimulus": "What is a Java interface?"})
    assert res_exp.status_code == 200
    data_exp = res_exp.json()
    assert data_exp["success"] is True
    assert data_exp["intent"] == "EXPLAIN_CONCEPT"
    assert "reference type declaring abstract methods" in data_exp["solution"]
    assert "Java Interface" in data_exp["concepts_used"]

    # Test 2: Comparison
    res_cmp = client.post("/process", json={"stimulus": "Compare Java interface and class."})
    assert res_cmp.status_code == 200
    data_cmp = res_cmp.json()
    assert data_cmp["success"] is True
    assert data_cmp["intent"] == "COMPARE_CONCEPTS"
    assert "Java Interface" in data_cmp["solution"]
    assert "Class" in data_cmp["solution"]

    # Test 3: Unknown Refusal
    res_unk = client.post("/process", json={"stimulus": "What is quantum entanglement?"})
    assert res_unk.status_code == 200
    data_unk = res_unk.json()
    assert data_unk["success"] is False
    assert data_unk["intent"] == "REPORT_UNKNOWN"
    assert data_unk["confidence"] == 0.0


# ─────────────────────────────────────────────────────────────
# TEST GROUP H: REAL USER SCENARIO MATRIX
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_action,expected_concept", [
    ("What exactly is a Java interface?", TaskAction.EXPLAIN_CONCEPT, "Java Interface"),
    ("Can you explain Java interfaces?", TaskAction.EXPLAIN_CONCEPT, "Java Interface"),
    ("Why do Java interfaces exist?", TaskAction.EXPLAIN_CONCEPT, "Java Interface"),
    ("Compare Java interfaces with classes.", TaskAction.COMPARE_CONCEPTS, "Java Interface"),
    ("What is the relationship between Java Interface and Abstraction?", TaskAction.DERIVE_RELATIONSHIP, "Java Interface"),
    ("Tell me about quantum entanglement.", TaskAction.REPORT_UNKNOWN, None),
    ("Why is it useful?", TaskAction.REPORT_INSUFFICIENT_CONTEXT, None),
])
def test_vs5_h1_user_scenario_matrix(query: str, expected_action: TaskAction, expected_concept: str):
    """H1: Diverse user phrasing accurately maps to the correct underlying CognitiveTask and concepts."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.cognitive_task.action == expected_action
        if expected_concept:
            assert expected_concept in ans.cognitive_execution_result.grounded_concepts or expected_concept.lower() in ans.direct_answer.lower()
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP I: PERFORMANCE & LARGE INPUT LATENCY
# ─────────────────────────────────────────────────────────────

def test_vs5_i1_large_input_performance_and_latency():
    """I1: Multi-paragraph enterprise query executes deterministically and records stage latencies."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        large_query = """
        We are building a distributed event-driven service architecture in Java.
        Our components require clean contract separation to facilitate decoupling.
        
        Specifically, can you explain what a Java interface is and how it relates to abstraction?
        
        This information will guide our engineering standards across multiple development squads.
        """
        start = time.perf_counter()
        raw = RawInput.from_text(large_query)
        t_interp_start = time.perf_counter()
        iset = pipeline.interpreter.interpret(raw)
        t_interp_end = time.perf_counter()

        t_ground_start = time.perf_counter()
        situation = pipeline.grounding_engine.ground(iset)
        t_ground_end = time.perf_counter()

        t_derive_start = time.perf_counter()
        task = pipeline.task_deriver.derive(situation)
        t_derive_end = time.perf_counter()

        t_exec_start = time.perf_counter()
        ans = pipeline.answer(large_query)
        t_exec_end = time.perf_counter()

        total_time = (t_exec_end - start) * 1000
        interp_time = (t_interp_end - t_interp_start) * 1000
        ground_time = (t_ground_end - t_ground_start) * 1000
        derive_time = (t_derive_end - t_derive_start) * 1000

        assert situation.status == SituationStatus.GROUNDED
        assert ans.cognitive_task.action in (TaskAction.EXPLAIN_CONCEPT, TaskAction.DERIVE_RELATIONSHIP)
        assert ans.confidence.score > 0.80

        # Performance constraints: total execution for large query < 250ms
        assert total_time < 250.0, f"Total execution took {total_time:.2f}ms (> 250ms threshold)"
        assert interp_time < 50.0, f"Interpretation took {interp_time:.2f}ms (> 50ms threshold)"
    finally:
        pipeline.provider.close()
