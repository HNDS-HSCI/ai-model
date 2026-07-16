import pytest
import threading
import time
from typing import Tuple, List, Dict, Any
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.knowledge.concept_activation import (
    ConceptActivationEngine, ActivatedConcept, GraphSpreadingActivationStrategy
)

# Helper to initialize store and engine in memory
def setup_test_engine(db_path: str = ":memory:") -> Tuple[ConceptActivationEngine, KnowledgeManager, SQLiteProvider, EventBus]:
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
    
    # Custom CAE configuration
    config = {
        "maximum_hops": 2,
        "activation_decay": 0.2,
        "activation_threshold": 0.1,
        "maximum_active_concepts": 5,
        "competition_factor": 0.05
    }
    engine = ConceptActivationEngine(manager, event_bus, config)
    return engine, manager, provider, event_bus

def test_concept_spreading_activation_and_decay():
    """Verifies that seed concepts correctly spread activation to namespace and generalization neighbors."""
    engine, manager, provider, _ = setup_test_engine()
    
    # Populate a small graph
    c1 = Concept(id="c1", name="AddOne", namespace="math.arithmetic", generalizes_to=["c2"])
    c2 = Concept(id="c2", name="AddGeneral", namespace="math.arithmetic")
    
    manager.create_concept(c1)
    manager.create_concept(c2)
    
    # Create cognitive context
    ctx = CognitiveContext(request_id="req1", session_id="s1", stimulus="test")
    
    # Run Activation starting from c1 seed
    result_set = engine.activate_concepts(["AddOne"], ctx)
    
    # Verify c1 (seed) has score 1.0
    ac_c1 = result_set.get("c1")
    assert ac_c1 is not None
    assert ac_c1.score == 1.0
    
    # Verify c2 (neighbor) has score = 1.0 * (1 - decay) - competition
    # c2 score is: 1.0 * 0.8 - (1.0 * 0.05) = 0.75
    ac_c2 = result_set.get("c2")
    assert ac_c2 is not None
    assert ac_c2.score == 0.75
    assert ac_c2.source == "AddOne"
    assert "c1" in ac_c2.path
    assert ac_c2.path[-1] == "c2"
    
    # Verify WorkingMemory got updated
    assert ctx.working_memory.activation_field.activation_strengths["c1"] == 1.0
    assert ctx.working_memory.activation_field.activation_strengths["c2"] == 0.75
    
    provider.close()

def test_threshold_and_competition():
    """Asserts that concepts with score below threshold are pruned and competition lowers scores."""
    engine, manager, provider, _ = setup_test_engine()
    
    # Set high threshold and competition in config
    engine.config["activation_threshold"] = 0.8
    engine.config["competition_factor"] = 0.3
    
    c1 = Concept(id="c1", name="Seed")
    c2 = Concept(id="c2", name="Neighbor", generalizes_to=["c3"])
    c3 = Concept(id="c3", name="Leaf")
    
    # Establish connection
    c1.generalizes_to = ["c2"]
    
    manager.create_concept(c1)
    manager.create_concept(c2)
    manager.create_concept(c3)
    
    ctx = CognitiveContext(request_id="req", session_id="s", stimulus="t")
    result_set = engine.activate_concepts(["Seed"], ctx)
    
    # c1 is seed -> score 1.0
    # c2 score before competition: 1.0 * 0.8 = 0.8
    # c2 score after competition: 0.8 - (1.0 * 0.3) = 0.5
    # threshold is 0.8 -> c2 should be pruned!
    assert result_set.get("c1") is not None
    assert result_set.get("c2") is None
    assert result_set.get("c3") is None
    
    provider.close()

def test_explainability():
    """Asserts explainability paths and reasoning strings are fully populated."""
    engine, manager, provider, _ = setup_test_engine()
    
    c1 = Concept(id="c1", name="Addition", generalizes_to=["c2"])
    c2 = Concept(id="c2", name="GeneralMath")
    
    manager.create_concept(c1)
    manager.create_concept(c2)
    
    ctx = CognitiveContext(request_id="req", session_id="s", stimulus="t")
    result_set = engine.activate_concepts(["Addition"], ctx)
    
    ac_c2 = result_set.get("c2")
    assert ac_c2 is not None
    assert len(ac_c2.path) == 2
    assert ac_c2.path == ["c1", "c2"]
    assert "Generalization target" in ac_c2.reason
    
    provider.close()

def test_cache_hits_and_eventbus_invalidations():
    """Verifies that identical seed query hits local cache and database mutations clear cache."""
    engine, manager, provider, event_bus = setup_test_engine()
    
    c = Concept(id="c1", name="Add")
    manager.create_concept(c)
    
    ctx = CognitiveContext(request_id="r", session_id="s", stimulus="t")
    
    # Trigger first run to load cache
    engine.activate_concepts(["Add"], ctx)
    assert len(engine._activation_cache) == 1
    
    # Run again - should hit cache
    res = engine.activate_concepts(["Add"], ctx)
    assert res is not None
    
    # Mutate concept -> event should flush CAE cache
    c.strength = 0.99
    manager.update_concept(c)
    
    # Verify cache cleared
    assert len(engine._activation_cache) == 0
    
    provider.close()

def test_concurrency():
    """Concurrent lookup verification to assert cache thread safety."""
    import os
    db_file = "test_cae_concurrency.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    engine, manager, provider, _ = setup_test_engine(db_path=db_file)
    
    try:
        c1 = Concept(id="c1", name="ConcurrentAdd")
        manager.create_concept(c1)
        
        errors = []
        def worker(thread_id: int):
            try:
                for _ in range(10):
                    ctx = CognitiveContext(request_id=f"r-{thread_id}", session_id="s", stimulus="t")
                    res = engine.activate_concepts(["ConcurrentAdd"], ctx)
                    assert res.get("c1") is not None
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

def test_concept_activation_performance_benchmarks():
    """Measures latency of concept activation cycles under various node loads."""
    engine, manager, provider, _ = setup_test_engine()
    
    sizes = [10, 100, 1000, 10000]
    durations = {}
    
    ctx = CognitiveContext(request_id="b", session_id="s", stimulus="t")
    
    for size in sizes:
        concepts = [Concept(id=f"c_{size}_{i}", name=f"Concept_{size}_{i}", namespace=f"ns_{size}") for i in range(size)]
        for i in range(min(size - 1, 10)):  # Link a few hops to limit execution depth
            concepts[i].generalizes_to = [concepts[i+1].id]
            
        provider.begin_transaction()
        try:
            for concept in concepts:
                manager.concept_store.repository.create_concept(concept)
        finally:
            provider.commit_transaction()
            
        start = time.perf_counter()
        engine.activate_concepts([f"Concept_{size}_0"], ctx)
        durations[size] = (time.perf_counter() - start) * 1000.0
        
    print(f"\n--- ConceptActivationEngine Performance Benchmarks ---")
    for size in sizes:
        print(f"{size:<5} Concepts Spreading Latency: {durations[size]:.2f}ms")
    print(f"------------------------------------------------------")
    
    assert durations[10] < 50.0
    provider.close()
