import pytest
import threading
import time
from unittest.mock import MagicMock, call
from datetime import datetime
import z3

from hsci.reasoning.reasoning_engine import (
    CognitiveReasoningEngine, ReasoningContext, RuleBasedInferenceStrategy, ReasoningStep,
    Inference, Assumption, Conclusion, ReasoningTrace, ReasoningResult, ReasoningEngine
)
from hsci.core.data_types import (
    PerceptionMap, KnowledgeResult, ReasoningPlan, SubGoal, Concept,
    AxiomType, Expression, ProofTrace, VerificationResult
)
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.reasoning.concept_composer import ConceptComposer
from hsci.reasoning.solution_builder import SolutionBuilder

# ─────────────────────────────────────────────
# LEGACY COMPATIBILITY TEST FIXTURES & TESTS
# ─────────────────────────────────────────────

@pytest.fixture
def mock_htn_planner():
    planner = MagicMock(spec=HTNPlanner)
    planner.decompose.return_value = [
        SubGoal(name="MOCK_SUBGOAL_1", description="desc1"),
        SubGoal(name="MOCK_SUBGOAL_2", description="desc2")
    ]
    return planner

@pytest.fixture
def mock_concept_composer():
    composer = MagicMock(spec=ConceptComposer)
    composer.find_best.return_value = Concept(
        id="mock_concept", name="MOCK_CONCEPT", axiom_type=AxiomType.REDUCTION,
        abstract_rule="", z3_template="", domain="", learned_from_domains=[],
        strength=0.0, proof_count=0, created_at=datetime.now(), last_used=datetime.now(),
        generalizes_to=[], required_entities=[], optional_entities=[], z3_verified=True
    )
    return composer

@pytest.fixture
def mock_solution_builder():
    builder = MagicMock(spec=SolutionBuilder)
    builder.build.return_value = Expression(value=z3.IntVal(1) + z3.IntVal(1) == z3.IntVal(2), concepts_used=["mock_concept"])
    return builder

@pytest.fixture
def legacy_reasoning_engine(mock_htn_planner, mock_concept_composer, mock_solution_builder):
    engine = ReasoningEngine()
    engine.htn_planner = mock_htn_planner
    engine.concept_composer = mock_concept_composer
    engine.solution_builder = mock_solution_builder
    return engine

@pytest.fixture
def mock_perception_map():
    return PerceptionMap(
        entities={"a": 1, "b": 1},
        unknown_entities=["result"],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=0.9,
        entity_graph={"nodes": ["a", "b", "result"]}
    )

@pytest.fixture
def mock_knowledge_result():
    return KnowledgeResult(
        direct_matches=[],
        analogical_matches=[],
        episodes=[],
        confidence=0.5
    )

def test_legacy_reasoning_engine_initialization(legacy_reasoning_engine):
    assert isinstance(legacy_reasoning_engine.htn_planner, MagicMock)
    assert isinstance(legacy_reasoning_engine.concept_composer, MagicMock)
    assert isinstance(legacy_reasoning_engine.solution_builder, MagicMock)

def test_legacy_reason_method_workflow(legacy_reasoning_engine, mock_perception_map, mock_knowledge_result,
                                     mock_htn_planner, mock_concept_composer, mock_solution_builder):
    reasoning_plan = legacy_reasoning_engine.reason(mock_perception_map, mock_knowledge_result)
    mock_htn_planner.decompose.assert_called_once_with(mock_perception_map)
    assert reasoning_plan.sub_goals == mock_htn_planner.decompose.return_value
    assert mock_concept_composer.find_best.call_count == len(reasoning_plan.sub_goals)
    expected_concept = mock_concept_composer.find_best.return_value
    assert all(concept == expected_concept for concept in reasoning_plan.concept_assignments.values())
    assert reasoning_plan.primary_concept == expected_concept
    mock_solution_builder.build.assert_called_once_with(
        reasoning_plan.sub_goals,
        reasoning_plan.concept_assignments,
        mock_perception_map.entities,
        ctx=None
    )
    assert reasoning_plan.candidate_solution == mock_solution_builder.build.return_value
    assert isinstance(reasoning_plan, ReasoningPlan)

def test_legacy_repair_method_placeholder(legacy_reasoning_engine, mock_perception_map, mock_knowledge_result):
    subgoals = [SubGoal(name="ORIGINAL", description="original")]
    original_plan = ReasoningPlan(
        sub_goals=subgoals,
        concept_assignments={subgoals[0]: None},
        composition_order=[],
        candidate_solution=Expression(value="original_solution", concepts_used=[]),
        concepts_used=[],
        primary_concept=None,
        perception=mock_perception_map,
        knowledge=mock_knowledge_result
    )
    counterexample = {"error": "test_failure"}
    correction_hint = "try something else"
    repaired_plan = legacy_reasoning_engine.repair(original_plan, counterexample, correction_hint)
    assert repaired_plan.perception == original_plan.perception
    assert repaired_plan.knowledge == original_plan.knowledge


# ─────────────────────────────────────────────
# NEW CRE COGNITIVE REASONING ENGINE TESTS
# ─────────────────────────────────────────────

def setup_cre_engine() -> tuple:
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    migration = SchemaMigration(provider)
    import os
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "migrations")
    migration.run_directory_migrations(migrations_dir)
    
    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)
    cre = CognitiveReasoningEngine(manager, event_bus)
    return cre, manager, provider, event_bus

def test_cre_rule_based_inference():
    """Verifies that the inference strategy derives namespace dependencies and generalizations."""
    cre, manager, provider, _ = setup_cre_engine()
    
    c1 = Concept(id="c_inh", name="Inheritance", namespace="concept.oop", generalizes_to=["c_class"])
    c2 = Concept(id="c_class", name="Class", namespace="concept.oop")
    
    reasoning_ctx = ReasoningContext(goal="Find programming structures")
    
    strategy = RuleBasedInferenceStrategy()
    inferences = strategy.infer([c1, c2], reasoning_ctx)
    
    statements = {inf.derived_statement for inf in inferences}
    assert any("Inheritance generalizes to Class" in s for s in statements)
    assert any("namespace 'concept.oop'" in s for s in statements)
    
    provider.close()

def test_cre_consistency_circular_and_contradictions():
    """Ensures circular proof reasoning and negation contradictions are flagged and rejected."""
    cre, manager, provider, _ = setup_cre_engine()
    
    c = Concept(id="c_java", name="Java")
    cog_ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    # Custom strategy yielding conflicting & duplicate statements
    class FlawedStrategy(RuleBasedInferenceStrategy):
        def infer(self, active_concepts, context):
            return [
                Inference("Rule1", "Java is compiled", [], 0.90, ["Java"]),
                # Duplicate / Circular
                Inference("Rule2", "Java is compiled", [], 0.90, ["Java"]),
                # Contradicting
                Inference("Rule3", "not Java is compiled", [], 0.90, ["Java"])
            ]
            
    cre.inference_strategy = FlawedStrategy()
    
    reasoning_ctx = ReasoningContext(goal="Verify properties", max_steps=2)
    res = cre.reason([c], cog_ctx, reasoning_ctx)
    
    # Exactly 1 verified conclusion ("Java is compiled")
    assert len(res.conclusions) == 1
    assert res.conclusions[0].statement == "Java is compiled"
    
    # Check contradictions list
    assert len(res.contradictions) == 1
    assert "conflicts with" in res.contradictions[0]
    
    # Check rejected trace
    rejections = res.reasoning_trace.rejected_conclusions
    assert len(rejections) == 2
    rejection_reasons = {rej.rejected_reason for rej in rejections}
    assert any("Circular reasoning" in r for r in rejection_reasons)
    
    provider.close()

def test_cre_concurrency():
    """Asserts thread safety of parallel reasoning request sessions."""
    cre, manager, provider, _ = setup_cre_engine()
    
    c = Concept(id="c_java", name="Java")
    
    errors = []
    def worker(thread_id: int):
        try:
            for _ in range(5):
                cog_ctx = CognitiveContext(request_id=f"r-{thread_id}", session_id="s", stimulus="t")
                reasoning_ctx = ReasoningContext(goal=f"Thread goal {thread_id}")
                res = cre.reason([c], cog_ctx, reasoning_ctx)
                assert res is not None
        except Exception as e:
            errors.append(e)
            
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0
    provider.close()

def test_cre_performance_benchmarks():
    """Benchmarks reasoning engine latency metrics under various active concept counts."""
    cre, manager, provider, _ = setup_cre_engine()
    
    sizes = [10, 100, 1000]
    cog_ctx = CognitiveContext(request_id="b", session_id="s", stimulus="t")
    
    print("\n--- CognitiveReasoningEngine Performance Benchmarks ---")
    for size in sizes:
        concepts = [Concept(id=f"c_{i}", name=f"C_{i}", namespace="math") for i in range(size)]
        
        start = time.perf_counter()
        reasoning_ctx = ReasoningContext(goal="Match namespaces", max_steps=1)
        res = cre.reason(concepts, cog_ctx, reasoning_ctx)
        dur_ms = (time.perf_counter() - start) * 1000.0
        
        print(f"{size:<5} Concepts Reasoning Latency: {dur_ms:.2f}ms (Inferences: {len(res.conclusions)})")
        assert dur_ms < 150.0  # Verification must run rapidly
        
    print("-------------------------------------------------------")
    provider.close()
