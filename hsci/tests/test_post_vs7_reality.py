"""HSCI Post-VS7 System Reality & Usability Test Suite.

Executes the full Real-User Test Matrix, Knowledge Mutability verification,
Arbitrary Concept Generalization, Cognitive Data Flow threading, and Real FastAPI /process runtime.

ZERO question-specific hardcoding. ZERO mocked cognitive execution paths.
"""
import time
import pytest
from fastapi.testclient import TestClient

from brain_api import app
from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline
from hsci.core.data_types import Concept
from hsci.cognition.interpretation.models import TaskAction, GroundingStatus
from hsci.cognition.workspace import WorkspaceStatus, CognitiveWorkspace


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


# ─────────────────────────────────────────────────────────────
# TEST GROUP A: BASIC EXPLANATION (REAL-USER QUERIES)
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_keyword", [
    ("What is a Java interface?", "reference type declaring abstract methods"),
    ("Explain Java Interface.", "reference type declaring abstract methods"),
    ("I don't understand interfaces in Java.", "reference type declaring abstract methods"),
    ("What does a class mean?", "blueprint"),
    ("What is abstraction?", "hides"),
])
def test_group_a_basic_explanation(query: str, expected_keyword: str):
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score > 0.80
        assert ans.cognitive_task.action == TaskAction.EXPLAIN_CONCEPT
        assert expected_keyword.lower() in ans.direct_answer.lower()
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP B: COMPARISON (REAL-USER QUERIES)
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "How is an interface different from a class?",
    "Compare Java interface and class.",
    "Are interface and class the same thing?",
    "What is the difference between interface and class?",
])
def test_group_b_comparison(query: str):
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score > 0.80
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        assert "contract" in ans.direct_answer.lower() or "reference type" in ans.direct_answer.lower()
        assert "blueprint" in ans.direct_answer.lower() or "class" in ans.direct_answer.lower()
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP C: RELATIONSHIP DERIVATION (REAL-USER QUERIES)
# ─────────────────────────────────────────────────────────────

def test_group_c1_derived_transitive_relationship():
    """Derives Java Interface -> Abstraction transitively from stored axioms."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("What is the relationship between Java Interface and Abstraction?")
        assert ans.confidence.score > 0.80
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
        assert "Java Interface generalizes to Abstraction" in ans.direct_answer
        assert "GeneralizationTransitivity" in ans.direct_answer
    finally:
        pipeline.provider.close()


def test_group_c2_stored_direct_relationship():
    """Identifies direct stored relationship Java Interface -> Interface."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("How is Java Interface related to Interface?")
        assert ans.confidence.score > 0.80
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
        assert "Java Interface generalizes to Interface" in ans.direct_answer
    finally:
        pipeline.provider.close()


def test_group_c3_stored_direct_class_abstraction():
    """Identifies direct stored relationship Class -> Abstraction."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("How are Class and Abstraction connected?")
        assert ans.confidence.score > 0.80
        assert ans.cognitive_task.action == TaskAction.DERIVE_RELATIONSHIP
        assert "Class generalizes to Abstraction" in ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP D: COMPOUND MULTI-TASK REQUESTS
# ─────────────────────────────────────────────────────────────

def test_group_d1_compound_explain_and_compare():
    """Explain Java Interface and compare it with Class."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain Java Interface and compare it with Class.")
        assert ans.confidence.score > 0.80
        assert "reference type" in ans.direct_answer.lower()
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


def test_group_d2_triple_compound_explain_compare_relate():
    """Explain Java Interface, compare it with Class, and relate to Abstraction."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain Java Interface, compare it with Class, and tell me how it relates to Abstraction.")
        assert ans.confidence.score > 0.80
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
        assert len(ans.workspace.task_graph.tasks) >= 3
        assert len(ans.workspace.results) >= 3
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP E: CONVERSATIONAL & NOISY INPUT
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Hey, I am confused about Java interfaces. Can you explain what they are?",
    "So basically what is an interface in Java?",
    "I've been reading about Java classes and interfaces and don't really get the difference.",
])
def test_group_e_conversational_input(query: str):
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score > 0.80
        assert ans.direct_answer
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP F: UNKNOWN CONCEPT REFUSAL
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "What is quantum entanglement?",
    "What is DarkMatterQuantumWarp?",
    "Explain something_that_does_not_exist.",
])
def test_group_f_unknown_concepts(query: str):
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score == 0.0
        assert ans.cognitive_task.action == TaskAction.REPORT_UNKNOWN
        assert ans.workspace.status == WorkspaceStatus.REFUSED
        assert "Unable to resolve concept" in ans.direct_answer or "No verified conclusions" in ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP G: AMBIGUOUS & MISSING CONTEXT REFUSAL
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "What is it?",
    "Explain this.",
    "How is it different?",
    "Why does it matter?",
])
def test_group_g_missing_context(query: str):
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score == 0.0
        assert ans.cognitive_task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT
        assert ans.workspace.status == WorkspaceStatus.REFUSED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP H: NEGATION & CONSTRAINTS
# ─────────────────────────────────────────────────────────────

def test_group_h1_negation_compound_override():
    """'Don't explain Java Interface; compare it with Class.' overrides to comparison."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Don't explain Java Interface; compare it with Class.")
        assert ans.cognitive_task.action == TaskAction.COMPARE_CONCEPTS
        assert ans.confidence.score > 0.80
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP I: KNOWLEDGE MUTABILITY VERIFICATION
# ─────────────────────────────────────────────────────────────

def test_group_i1_definition_mutability():
    """Mutating concept definition in UKM immediately changes the generated answer."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        # Baseline query
        ans1 = pipeline.answer("Explain Java Interface.")
        assert "reference type declaring abstract methods" in ans1.direct_answer

        # Mutate definition in UKM
        concept = pipeline.manager.get_concept("c_java_interface")
        original_def = concept.abstract_rule
        concept.abstract_rule = "A custom mutated definition for enterprise contracts."
        pipeline.manager.concept_store.repository.update_concept(concept)
        pipeline.manager.cache.invalidate_concept("c_java_interface")

        # Re-run same query
        ans2 = pipeline.answer("Explain Java Interface.")
        assert "A custom mutated definition for enterprise contracts." in ans2.direct_answer

        # Restore original definition
        concept.abstract_rule = original_def
        pipeline.manager.concept_store.repository.update_concept(concept)
        pipeline.manager.cache.invalidate_concept("c_java_interface")

        ans3 = pipeline.answer("Explain Java Interface.")
        assert "reference type declaring abstract methods" in ans3.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP J: ARBITRARY CONCEPT GENERALIZATION (BEYOND OOP)
# ─────────────────────────────────────────────────────────────

def test_group_j1_arbitrary_concept_generalization():
    """Verifies that completely new, non-OOP concepts operate through identical cognitive architecture."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=False)
    try:
        # Register new arbitrary domain concepts: Quantum Computing
        c_qbit = Concept(
            id="c_qbit",
            name="QuantumBit",
            aliases=["quantumbit", "qubit"],
            abstract_rule="A quantum bit is a two-state quantum-mechanical system.",
            namespace="physics.quantum",
            generalizes_to=["c_qstate"],
        )
        c_qstate = Concept(
            id="c_qstate",
            name="QubitState",
            aliases=["qubitstate"],
            abstract_rule="A qubit state is a normalized vector in a two-dimensional Hilbert space.",
            namespace="physics.quantum",
            generalizes_to=["c_superposition"],
        )
        c_super = Concept(
            id="c_superposition",
            name="SuperpositionState",
            aliases=["superpositionstate"],
            abstract_rule="A state where quantum systems exist across multiple basis states simultaneously.",
            namespace="physics.quantum",
            generalizes_to=[],
        )

        pipeline.manager.concept_store.repository.create_concept(c_qbit)
        pipeline.manager.concept_store.repository.create_concept(c_qstate)
        pipeline.manager.concept_store.repository.create_concept(c_super)

        # 1. Generic Explanation
        ans_exp = pipeline.answer("What is QuantumBit?")
        assert ans_exp.confidence.score > 0.80
        assert "two-state quantum-mechanical system" in ans_exp.direct_answer

        # 2. Generic Comparison
        ans_comp = pipeline.answer("Compare QuantumBit and QubitState.")
        assert ans_comp.confidence.score > 0.80
        assert "two-state quantum-mechanical system" in ans_comp.direct_answer
        assert "normalized vector" in ans_comp.direct_answer

        # 3. Generic Transitive Reasoning Derivation
        ans_rel = pipeline.answer("What is the relationship between QuantumBit and SuperpositionState?")
        assert ans_rel.confidence.score > 0.80
        assert "QuantumBit generalizes to SuperpositionState" in ans_rel.direct_answer
        assert "GeneralizationTransitivity" in ans_rel.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP K: TRUE COGNITIVE DATA FLOW THREADING
# ─────────────────────────────────────────────────────────────

def test_group_k1_cognitive_data_flow_threading():
    """Verifies that downstream tasks receive upstream TaskResult in parameters['upstream_results']."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Explain Java Interface, compare it with Class, and tell me how it relates to Abstraction.")
        ws: CognitiveWorkspace = ans.workspace

        # Find the dependent relate task
        relate_tasks = [t for t in ws.task_graph.tasks.values() if t.action == TaskAction.DERIVE_RELATIONSHIP]
        assert len(relate_tasks) == 1
        t_rel = relate_tasks[0]

        # Verify upstream dependencies exist and were passed in parameters['upstream_results']
        assert len(t_rel.dependencies) > 0
        assert "upstream_results" in t_rel.parameters
        assert len(t_rel.parameters["upstream_results"]) > 0
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP L: REAL FASTAPI HTTP /process RUNTIME
# ─────────────────────────────────────────────────────────────

def test_group_l1_fastapi_http_process_runtime(api_client):
    """Executes live HTTP POST /process requests against FastAPI application."""
    # 1. Explain
    resp = api_client.post("/process", json={"stimulus": "What is a Java interface?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["confidence"] > 0.80
    assert "reference type" in data["solution"].lower()
    assert "[RETRIEVED DEFINITION]" in data["deliberation"]

    # 2. Derive Relationship
    resp2 = api_client.post("/process", json={"stimulus": "What is the relationship between Java Interface and Abstraction?"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert "[DERIVED CONCLUSION]" in data2["deliberation"]

    # 3. Refusal on Unknown Concept
    resp3 = api_client.post("/process", json={"stimulus": "What is quantum entanglement?"})
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["success"] is False
    assert data3["confidence"] == 0.0
    assert "Unable to resolve concept" in data3["solution"] or "Missing Knowledge" in data3["solution"]

    # 4. Mathematical Equation Solving via /process
    resp4 = api_client.post("/process", json={"stimulus": "solve 3x + 12 = 0"})
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["success"] is True
    assert data4["confidence"] == 1.0
    assert "-4" in data4["solution"]


# ─────────────────────────────────────────────────────────────
# TEST GROUP M: MATHEMATICAL & GENERAL PROBLEM SOLVING
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_ans", [
    ("solve 3x + 12 = 0", "-4"),
    ("calculate 144 / 12", "12"),
    ("what is 25 * 4 + 50", "150"),
    ("solve x^2 - 5*x + 6 = 0", "2"),
])
def test_group_m1_mathematical_solving(query: str, expected_ans: str):
    """Solves mathematical equations and arithmetic using SymPy CAS."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer(query)
        assert ans.confidence.score == 1.0
        assert ans.cognitive_task.action == TaskAction.SOLVE_MATHEMATICS
        assert expected_ans in ans.direct_answer
        assert ans.workspace.status == WorkspaceStatus.COMPLETED
    finally:
        pipeline.provider.close()


def test_group_m2_general_greeting():
    """Handles general greetings and system overview conversationally."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("hello")
        assert ans.confidence.score == 1.0
        assert ans.cognitive_task.action == TaskAction.ANSWER_GENERAL
        assert "HSCI Neuro-Symbolic Cognitive Brain" in ans.direct_answer
    finally:
        pipeline.provider.close()
