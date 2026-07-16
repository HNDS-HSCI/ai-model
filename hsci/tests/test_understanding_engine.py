import pytest
import threading
from typing import Tuple
from hsci.core.data_types import Concept
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.knowledge.understanding_engine import UnderstandingEngine

# Helper setup
def setup_test_understanding(db_path: str = ":memory:") -> Tuple[UnderstandingEngine, KnowledgeManager, SQLiteProvider]:
    provider = SQLiteProvider(db_path=db_path)
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
    engine = UnderstandingEngine(manager)
    return engine, manager, provider

def test_normalization_and_tokenization():
    """Verifies that query normalization trims whitespace, cleans characters, and segments correctly."""
    engine, manager, provider = setup_test_understanding()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    res = engine.understand("  What is  inheritance, in Java?   ", ctx)
    assert res.normalized_query == "what is inheritance in java"
    assert "inheritance" in res.keywords
    assert "java" in res.keywords
    
    provider.close()

def test_entity_extraction():
    """Asserts that predefined domain construct tags are resolved successfully."""
    engine, manager, provider = setup_test_understanding()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    res = engine.understand("Java coding construct representing a class", ctx)
    assert res.entities["java"] == "language"
    assert res.entities["class"] == "construct"
    
    provider.close()

def test_concept_resolution():
    """Verifies concept naming matches query terms via the KnowledgeManager façade."""
    engine, manager, provider = setup_test_understanding()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    c1 = Concept(id="c_java", name="Java")
    c2 = Concept(id="c_inh", name="Inheritance")
    manager.create_concept(c1)
    manager.create_concept(c2)
    
    res = engine.understand("What is inheritance in Java?", ctx)
    assert "Java" in res.seed_concepts
    assert "Inheritance" in res.seed_concepts
    
    # Assert WorkingMemory gets synchronized
    assert ctx.working_memory.semantic_frame is not None
    assert ctx.working_memory.semantic_frame.intent == "ExplainConcept"
    assert "Java" in ctx.working_memory.attention_buffer.salient_entities
    
    provider.close()

def test_ambiguity_handling():
    """Verifies that queries resolving to zero active concepts flag ambiguity warnings."""
    engine, manager, provider = setup_test_understanding()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    res = engine.understand("What is unknown construct?", ctx)
    assert len(res.seed_concepts) == 0
    assert any("No active UKM concepts resolved" in a for a in res.ambiguities)
    
    provider.close()

def test_intent_classification():
    """Verifies grammar intent classification metrics."""
    engine, manager, provider = setup_test_understanding()
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    # Pre-populate concept entities to ensure zero ambiguity penalties
    manager.create_concept(Concept(id="c_inh", name="Inheritance"))
    manager.create_concept(Concept(id="c_eq", name="Equation"))
    manager.create_concept(Concept(id="c_ax", name="Axiom"))
    
    res1 = engine.understand("What is inheritance?", ctx)
    assert res1.intent == "ExplainConcept"
    assert res1.confidence == 0.95
    
    res2 = engine.understand("Solve equation 5+2", ctx)
    assert res2.intent == "SolveEquation"
    assert res2.confidence == 0.90
    
    res3 = engine.understand("Verify if axiom 5=5 is true", ctx)
    assert res3.intent == "VerifyAxiom"
    assert res3.confidence == 0.85
    
    provider.close()

def test_understanding_concurrency():
    """Verifies concurrent execution safety of text translation queries."""
    import os
    db_file = "test_understanding_concurrency.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    engine, manager, provider = setup_test_understanding(db_path=db_file)
    
    try:
        c = Concept(id="c_java", name="Java")
        manager.create_concept(c)
        
        errors = []
        def worker(thread_id: int):
            try:
                for _ in range(10):
                    ctx = CognitiveContext(request_id=f"r-{thread_id}", session_id="s", stimulus="t")
                    res = engine.understand("What is Java?", ctx)
                    assert res.intent == "ExplainConcept"
                    assert "Java" in res.seed_concepts
            except Exception as e:
                errors.append(e)
                
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        assert len(errors) == 0
    finally:
        provider.close()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass
