import pytest
import threading
import time
from datetime import datetime
from typing import Tuple, List, Dict, Any
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import SQLiteProvider, SchemaMigration, HSCIStorageError
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import (
    KnowledgeManager, KnowledgeNotFoundError, KnowledgeConflictError,
    KnowledgeValidationError, KnowledgeStoreUnavailableError
)

# Helper to initialize manager and store in memory
def setup_test_manager(db_path: str = ":memory:") -> Tuple[KnowledgeManager, ConceptStore, SQLiteProvider, EventBus]:
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
    return manager, store, provider, event_bus

def test_knowledge_manager_routing_and_crud():
    """Verifies standard routing and CRUD delegation to the underlying store."""
    manager, store, provider, _ = setup_test_manager()
    
    c = Concept(id="c1", name="LogicAnd", namespace="math.logic", strength=0.7)
    
    # Create
    manager.create_concept(c, {"notes": "initial"})
    assert manager.exists("c1") is True
    
    # Read
    concept = manager.get_concept("c1")
    assert concept is not None
    assert concept.name == "LogicAnd"
    
    # Get by name
    by_name = manager.get_concept_by_name("LogicAnd")
    assert by_name is not None
    assert by_name.id == "c1"
    
    # Search & Namespace routing
    results = manager.search("Logic")
    assert len(results) == 1
    
    ns_results = manager.search_by_namespace("math.logic")
    assert len(ns_results) == 1
    
    provider.close()

def test_knowledge_manager_cache_hits_and_invalidations():
    """Asserts cache hit metrics and verifies EventBus invalidation triggers."""
    manager, store, provider, event_bus = setup_test_manager()
    
    c = Concept(id="c1", name="ArithmeticAdd", namespace="math.basic")
    manager.create_concept(c)
    
    # First access - loads from store into cache
    concept = manager.get_concept("c1")
    assert concept is not None
    
    # Modify directly in database, bypassing manager, to verify cache hit returns cached state
    store.repository.provider.execute_write(
        "UPDATE ukm_concepts SET strength = 0.99 WHERE id = 'c1';"
    )
    
    # Should get cached value (old strength=0.5)
    cached_val = manager.get_concept("c1")
    assert cached_val.strength == 0.5
    
    # Mutate through manager - triggers invalidation
    c.strength = 0.8
    manager.update_concept(c)
    
    # Cache should be cleared for c1, so it fetches the new strength from the database
    cleared_val = manager.get_concept("c1")
    assert cleared_val.strength == 0.8
    
    provider.close()

def test_exception_translation():
    """Verifies persistence layer exceptions are translated to logical domain exceptions."""
    manager, store, provider, _ = setup_test_manager()
    
    # 1. Create a validation error (out-of-bounds strength)
    invalid_concept = Concept(id="c1", name="Invalid", strength=-5.0)
    with pytest.raises(KnowledgeValidationError):
        manager.create_concept(invalid_concept)
        
    # 2. Create a duplicate conflict error
    c1 = Concept(id="c2", name="AddOne")
    c2 = Concept(id="c3", name="AddOne")  # Duplicate active name
    manager.create_concept(c1)
    
    with pytest.raises(KnowledgeConflictError):
        manager.create_concept(c2)
        
    provider.close()

def test_savepoint_transaction_routing():
    """Verifies merge and split routing within savepoints works."""
    manager, store, provider, _ = setup_test_manager()
    
    c1 = Concept(id="c1", name="AddOne")
    c2 = Concept(id="c2", name="AddTwo")
    manager.create_concept(c1)
    manager.create_concept(c2)
    
    merged = Concept(id="c_merged", name="AddMerged")
    merged_id = manager.merge_concepts("c1", "c2", merged)
    
    assert merged_id == "c_merged"
    assert manager.get_concept("c1").status == "DEPRECATED"
    assert manager.get_concept("c_merged").status == "ACTIVE"
    
    provider.close()

def test_concurrency_cache_lookups():
    """Concurrent lookup verification to assert cache thread safety."""
    import os
    db_file = "test_manager_concurrency.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    manager, store, provider, _ = setup_test_manager(db_path=db_file)
    
    try:
        c = Concept(id="c1", name="Concurrent", strength=0.5)
        manager.create_concept(c)
        
        errors = []
        def worker(thread_id: int):
            try:
                for _ in range(20):
                    concept = manager.get_concept("c1")
                    assert concept is not None
                    assert concept.name == "Concurrent"
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

def test_knowledge_manager_benchmarks():
    """Measures cache-hit vs cache-miss lookup performance benchmarks."""
    manager, store, provider, _ = setup_test_manager()
    
    c = Concept(id="c1", name="Speedy")
    manager.create_concept(c)
    
    # Cache Miss (first read)
    start = time.perf_counter()
    manager.get_concept("c1")
    miss_dur_ms = (time.perf_counter() - start) * 1000.0
    
    # Cache Hit (second read)
    start = time.perf_counter()
    manager.get_concept("c1")
    hit_dur_ms = (time.perf_counter() - start) * 1000.0
    
    print(f"\n--- KnowledgeManager Latency Benchmarks ---")
    print(f"Cache Miss Lookup Latency: {miss_dur_ms:.2f}ms")
    print(f"Cache Hit Lookup Latency:  {hit_dur_ms:.2f}ms")
    print(f"--------------------------------------------")
    
    assert hit_dur_ms < miss_dur_ms
    assert hit_dur_ms < 5.0  # Cache hit should be sub-5ms
    
    provider.close()

def test_demonstration_slice():
    """Vertical slice integration demonstration representing user queries."""
    manager, store, provider, _ = setup_test_manager()
    
    # Pre-populate knowledge model
    c = Concept(
        id="ground_addition",
        name="AdditionConcept",
        namespace="ground.arithmetic",
        abstract_rule="x + y",
        z3_template="res == x + y",
        domain="arithmetic"
    )
    manager.create_concept(c)
    
    # Simulated User Query Flow:
    # 1. Subsystem queries KnowledgeManager
    retrieved = manager.get_concept_by_name("AdditionConcept")
    
    # 2. Verify structure
    assert retrieved is not None
    assert retrieved.id == "ground_addition"
    assert retrieved.abstract_rule == "x + y"
    
    provider.close()
