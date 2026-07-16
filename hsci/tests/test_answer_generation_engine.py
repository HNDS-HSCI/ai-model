import pytest
import threading
from typing import Tuple
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.reasoning.reasoning_engine import ReasoningResult, Conclusion, ReasoningTrace, ReasoningStep
from hsci.response.answer_generation_engine import AnswerGenerationEngine

# Helper setup
def setup_test_generation() -> Tuple[AnswerGenerationEngine, KnowledgeManager, SQLiteProvider]:
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
    engine = AnswerGenerationEngine(event_bus)
    return engine, manager, provider

def create_mock_reasoning_result(conclusions=None, contradictions=None) -> ReasoningResult:
    trace = ReasoningTrace()
    trace.add_step(
        ReasoningStep(
            step_number=1,
            action="Inferred concept links",
            concepts_used=["Java", "Inheritance"],
            conclusions=["Inheritance generalizes to Class"],
            confidence=0.90
        )
    )
    actual_conclusions = conclusions if conclusions is not None else [Conclusion("Inheritance generalizes to Class", ["link"], 0.90)]
    actual_contradictions = contradictions if contradictions is not None else []
    
    return ReasoningResult(
        conclusions=actual_conclusions,
        supporting_evidence=["link"],
        assumptions=[],
        confidence=0.90,
        reasoning_trace=trace,
        intermediate_results=["Inheritance generalizes to Class"],
        remaining_unknowns=[],
        contradictions=actual_contradictions
    )

def test_generation_formatting_styles():
    """Verifies Standard, Step-by-Step, and Technical formatting outputs."""
    engine, manager, provider = setup_test_generation()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    res = create_mock_reasoning_result()
    
    # Style: Standard
    ans_std = engine.generate(res, ctx, style="Standard")
    assert "verified the following connections" in ans_std.direct_answer
    assert ans_std.sections[0].title == "Verified Connections"
    
    # Style: Step-by-Step
    ans_sbs = engine.generate(res, ctx, style="Step-by-Step")
    assert "sequential steps" in ans_sbs.direct_answer
    assert "Step 1" in ans_sbs.sections[0].content
    
    # Style: Technical
    ans_tech = engine.generate(res, ctx, style="Technical")
    assert "Technical logic trace" in ans_tech.direct_answer
    assert "Evidence" in ans_tech.sections[0].content
    
    provider.close()

def test_generation_error_handling_empty_and_contradictory():
    """Asserts that empty reasoning sets and contradiction logs flag formatted error blocks."""
    engine, manager, provider = setup_test_understanding_mock()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    # Empty conclusions
    res_empty = create_mock_reasoning_result(conclusions=[])
    ans_empty = engine.generate(res_empty, ctx)
    assert ans_empty.confidence.score == 0.0
    assert "Error Details" in ans_empty.sections[0].title
    
    # Contradictory
    res_contra = create_mock_reasoning_result(contradictions=["Statement contradicts existing"])
    ans_contra = engine.generate(res_contra, ctx)
    assert ans_contra.confidence.score == 0.0
    assert "Contradictory findings" in ans_contra.sections[0].content
    
    provider.close()

def test_generation_concurrency():
    """Asserts request-scoped parallel execution thread safety."""
    engine, manager, provider = setup_test_understanding_mock()
    res = create_mock_reasoning_result()
    
    errors = []
    def worker(thread_id: int):
        try:
            for _ in range(5):
                ctx = CognitiveContext(request_id=f"r-{thread_id}", session_id="s", stimulus="t")
                ans = engine.generate(res, ctx)
                assert ans is not None
                assert len(ans.sections) > 0
        except Exception as e:
            errors.append(e)
            
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0
    provider.close()

def setup_test_understanding_mock():
    # Helper to resolve circular setup import mocks
    return setup_test_generation()
