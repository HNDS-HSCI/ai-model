import pytest
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import SQLiteProvider, SchemaMigration, HSCIStorageError
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore

# Helper to initialize store in memory
def setup_test_store(db_path: str = ":memory:") -> Tuple[ConceptStore, SQLiteProvider, EventBus]:
    provider = SQLiteProvider(db_path=db_path)
    provider.initialize()
    
    # Run migrations
    migration = SchemaMigration(provider)
    import os
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "migrations")
    migration.run_directory_migrations(migrations_dir)
    
    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)
    return store, provider, event_bus

def test_concept_crud():
    """Validates basic CRUD logic for Concepts, including required attribute mappings."""
    store, provider, _ = setup_test_store()
    
    concept = Concept(
        id="c1",
        name="Addition",
        namespace="hsci.math.arithmetic",
        axiom_type=AxiomType.REDUCTION,
        abstract_rule="a + b",
        z3_template="result == a + b",
        domain="math",
        learned_from_domains=["math_sub"],
        strength=0.8,
        proof_count=10,
        z3_verified=True,
        aliases=["add", "sum"]
    )
    
    # Create
    store.create_concept(concept, {"source_type": "TEST", "notes": "initial creation"})
    
    # Get and Verify
    retrieved = store.get_concept("c1")
    assert retrieved is not None
    assert retrieved.name == "Addition"
    assert retrieved.namespace == "hsci.math.arithmetic"
    assert retrieved.axiom_type == AxiomType.REDUCTION
    assert retrieved.abstract_rule == "a + b"
    assert retrieved.strength == 0.8
    assert retrieved.z3_verified is True
    assert "add" in retrieved.aliases
    assert "sum" in retrieved.aliases
    assert "math_sub" in retrieved.learned_from_domains
    
    # Exists check
    assert store.exists("c1") is True
    assert store.exists("unknown") is False
    
    # Update
    concept.strength = 0.9
    concept.aliases.append("plus")
    store.update_concept(concept)
    
    updated = store.get_concept("c1")
    assert updated.strength == 0.9
    assert "plus" in updated.aliases
    
    provider.close()

def test_concept_alias_resolution():
    """Validates concept resolution by aliases."""
    store, provider, _ = setup_test_store()
    
    c1 = Concept(id="c1", name="Add", aliases=["plus", "sum"])
    c2 = Concept(id="c2", name="Subtract", aliases=["minus", "difference"])
    
    store.create_concept(c1)
    store.create_concept(c2)
    
    resolved = store.repository.resolve_alias("sum")
    assert len(resolved) == 1
    assert resolved[0].id == "c1"
    
    resolved_minus = store.repository.resolve_alias("minus")
    assert len(resolved_minus) == 1
    assert resolved_minus[0].id == "c2"
    
    provider.close()

def test_concept_namespace_and_search():
    """Validates namespace search and standard searches."""
    store, provider, _ = setup_test_store()
    
    c1 = Concept(id="c1", name="Add", namespace="math.arithmetic")
    c2 = Concept(id="c2", name="Diff", namespace="math.arithmetic.advanced")
    c3 = Concept(id="c3", name="PhysicsEngine", namespace="science.physics")
    
    store.create_concept(c1)
    store.create_concept(c2)
    store.create_concept(c3)
    
    # Namespace matches
    math_concepts = store.get_concepts_by_namespace("math.arithmetic")
    assert len(math_concepts) == 2
    assert any(c.id == "c1" for c in math_concepts)
    assert any(c.id == "c2" for c in math_concepts)
    
    # Global search matching name
    search_results = store.search("Physics")
    assert len(search_results) == 1
    assert search_results[0].id == "c3"
    
    provider.close()

def test_metadata_attachment():
    """Validates dynamic metadata attachments."""
    store, provider, _ = setup_test_store()
    
    c1 = Concept(id="c1", name="Add")
    store.create_concept(c1)
    
    store.attach_metadata("c1", "priority", "high")
    store.attach_metadata("c1", "cache_ttl", 3600)
    
    # Search by metadata
    results = store.search_by_metadata("priority", "high")
    assert len(results) == 1
    assert results[0].id == "c1"
    
    # Detach
    store.detach_metadata("c1", "priority")
    assert len(store.search_by_metadata("priority", "high")) == 0
    
    provider.close()

def test_concept_version_and_history():
    """Validates version list, promotions, and history trackers."""
    store, provider, _ = setup_test_store()
    
    c1_v1 = Concept(id="c1", name="Add", version=1, status="ACTIVE", abstract_rule="x + y")
    store.create_concept(c1_v1, {"notes": "v1 initial"})
    
    # Create another concept record with the same name but version 2 to test version history
    c1_v2_new = Concept(id="c2", name="Add", version=2, status="ACTIVE", abstract_rule="x + y + z")
    store.create_concept(c1_v2_new, {"notes": "v2 release"})
    
    versions = store.list_versions("Add")
    assert len(versions) == 2
    assert versions[0].version == 1
    assert versions[1].version == 2
    
    # Restore version 1
    restored = store.restore_version("c2", 1)
    assert restored.version == 3  # Increment version on restore
    assert restored.abstract_rule == "x + y"
    
    # Check history
    history = store.get_history("c1")
    assert len(history) >= 1
    assert history[0]["notes"] == "v1 initial"
    
    provider.close()

def test_concept_event_publishing():
    """Validates EventBus integrations on concept transitions."""
    store, provider, event_bus = setup_test_store()
    
    events_logged = []
    def on_concept_created(context: CognitiveContext) -> None:
        concept = context.working_memory.concept
        events_logged.append(("created", concept.id))
        
    def on_concept_archived(context: CognitiveContext) -> None:
        concept = context.working_memory.concept
        events_logged.append(("archived", concept.id))
        
    event_bus.subscribe("ConceptCreated", on_concept_created)
    event_bus.subscribe("ConceptArchived", on_concept_archived)
    
    c1 = Concept(id="c1", name="EventConcept")
    store.create_concept(c1)
    
    store.archive_concept("c1")
    
    assert ("created", "c1") in events_logged
    assert ("archived", "c1") in events_logged
    
    provider.close()

def test_merge_and_split_savepoints():
    """Validates nested savepoint transactions, splits, merges, and rollbacks."""
    store, provider, _ = setup_test_store()
    
    c1 = Concept(id="c1", name="AddOne", strength=0.5)
    c2 = Concept(id="c2", name="AddTwo", strength=0.6)
    
    store.create_concept(c1)
    store.create_concept(c2)
    
    # Merge
    merged = Concept(id="c_merged", name="AddMerged", strength=0.7)
    merged_id = store.merge_concepts("c1", "c2", merged)
    
    assert merged_id == "c_merged"
    assert store.get_concept("c1").status == "DEPRECATED"
    assert store.get_concept("c2").status == "DEPRECATED"
    assert store.get_concept("c_merged").status == "ACTIVE"
    
    # Split merged concept
    split1 = Concept(id="c_split1", name="SplitOne", strength=0.8)
    split2 = Concept(id="c_split2", name="SplitTwo", strength=0.8)
    
    s1, s2 = store.split_concept("c_merged", split1, split2)
    assert s1 == "c_split1"
    assert s2 == "c_split2"
    assert store.get_concept("c_merged").status == "DEPRECATED"
    assert store.get_concept("c_split1").status == "ACTIVE"
    
    # Rollback split check by inserting split with constraint failure (duplicate ID)
    fail_split1 = Concept(id="c_split1", name="SplitOneFail")  # Already exists!
    fail_split2 = Concept(id="c_split2_new", name="SplitTwoNew")
    
    # Parent status should be restored back if transaction rolls back
    original_status = store.get_concept("c_split1").status  # ACTIVE
    
    with pytest.raises(HSCIStorageError):
        store.split_concept("c_split1", fail_split1, fail_split2)
        
    # Check parent status remains ACTIVE (did not stay DEPRECATED during transaction rollback)
    assert store.get_concept("c_split1").status == original_status
    
    provider.close()

def test_concurrency_and_thread_safety():
    """Concurrency verification executing concurrent store lifecycle updates."""
    import os
    db_file = "test_concurrency.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    store, provider, _ = setup_test_store(db_path=db_file)
    
    try:
        c1 = Concept(id="c1", name="SharedConcept", strength=0.5)
        store.create_concept(c1)
        
        errors = []
        def worker(thread_id: int):
            try:
                for i in range(10):
                    # Multiple threads mutating strength/metadata simultaneously
                    concept = store.get_concept("c1")
                    concept.strength = float(thread_id * 10 + i) / 100.0
                    store.update_concept(concept)
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

def test_concept_store_performance_benchmarks():
    """Measures the latency metrics of ConceptStore CRUD, merge, and split cycles."""
    store, provider, _ = setup_test_store()
    
    # 1. Creation Latency
    c1 = Concept(id="c1", name="AddOne")
    c2 = Concept(id="c2", name="AddTwo")
    
    start = time.perf_counter()
    store.create_concept(c1)
    create_dur_ms = (time.perf_counter() - start) * 1000.0
    
    store.create_concept(c2)
    
    # 2. Read Latency
    start = time.perf_counter()
    store.get_concept("c1")
    read_dur_ms = (time.perf_counter() - start) * 1000.0
    
    # 3. Search Latency
    start = time.perf_counter()
    store.search("Add")
    search_dur_ms = (time.perf_counter() - start) * 1000.0
    
    # 4. Merge Latency
    merged = Concept(id="c_merged", name="AddMerged")
    start = time.perf_counter()
    store.merge_concepts("c1", "c2", merged)
    merge_dur_ms = (time.perf_counter() - start) * 1000.0
    
    # 5. Split Latency
    split1 = Concept(id="c_split1", name="SplitOne")
    split2 = Concept(id="c_split2", name="SplitTwo")
    start = time.perf_counter()
    store.split_concept("c_merged", split1, split2)
    split_dur_ms = (time.perf_counter() - start) * 1000.0
    
    print(f"\n--- ConceptStore Performance Benchmarks ---")
    print(f"Concept Creation Latency: {create_dur_ms:.2f}ms")
    print(f"Read Latency:             {read_dur_ms:.2f}ms")
    print(f"Search Latency:           {search_dur_ms:.2f}ms")
    print(f"Merge Latency:            {merge_dur_ms:.2f}ms")
    print(f"Split Latency:            {split_dur_ms:.2f}ms")
    print(f"-------------------------------------------")
    
    assert create_dur_ms < 50.0
    assert read_dur_ms < 20.0
    
    provider.close()
