import os
import time
from hsci.core.data_types import Concept
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.knowledge.concept_activation import ConceptActivationEngine
from hsci.knowledge.understanding_engine import UnderstandingEngine

def run_demo():
    print("======================================================================")
    print("   HSCI V4 - Understanding Engine & Activation Integration Demonstration")
    print("======================================================================")

    db_file = "demo_understanding.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    # 1. Setup UKM
    print("1. Initializing storage provider and running migrations...")
    provider = SQLiteProvider(db_path=db_file)
    provider.initialize()
    
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "migrations")
    migration = SchemaMigration(provider)
    migration.run_directory_migrations(migrations_dir)

    print("2. Assembling repositories and logical managers...")
    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)

    # 3. Populate math and programming domain concepts
    print("3. Preloading Java and Inheritance concepts...")
    concepts = [
        Concept(id="c_java", name="Java", namespace="lang.oop"),
        Concept(id="c_inh", name="Inheritance", namespace="concept.oop", generalizes_to=["c_class"]),
        Concept(id="c_class", name="Class", namespace="concept.oop"),
        Concept(id="c_obj", name="Object", namespace="concept.oop")
    ]
    
    provider.begin_transaction()
    try:
        for c in concepts:
            manager.create_concept(c)
    finally:
        provider.commit_transaction()

    # 4. Initialize Engines
    print("4. Initializing UnderstandingEngine and ConceptActivationEngine...")
    understanding_engine = UnderstandingEngine(manager)
    activation_engine = ConceptActivationEngine(manager, event_bus)

    # 5. Run user query through UnderstandingEngine
    user_query = "What is inheritance in Java?"
    print(f"\n5. Processing User Query: '{user_query}'")
    ctx = CognitiveContext(
        request_id="sprint-10-demo",
        session_id="ground-agent",
        stimulus=user_query
    )
    
    start_time = time.perf_counter()
    result = understanding_engine.understand(user_query, ctx)
    parsing_dur_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"   -> Parsed successfully in {parsing_dur_ms:.4f}ms.")
    print("   -> Understanding Result:")
    print(f"      - Intent:          {result.intent}")
    print(f"      - Seed Concepts:   {result.seed_concepts}")
    print(f"      - Entities:        {result.entities}")
    print(f"      - Confidence:      {result.confidence:.2f}")
    print(f"      - Normalized query: {result.normalized_query}")

    # 6. Pipe seeds directly to ConceptActivationEngine
    print("\n6. Piping resolved seed concepts directly to ConceptActivationEngine...")
    
    start_time = time.perf_counter()
    active_set = activation_engine.activate_concepts(result.seed_concepts, ctx)
    activation_dur_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"   -> Active concepts found: {len(active_set.concepts)} in {activation_dur_ms:.4f}ms.")
    for idx, ac in enumerate(active_set.concepts):
        print(f"   [{idx + 1}] Active Concept: {ac.concept.name:<12} (Score: {ac.score:.4f})")
        print(f"       - Propagation Path: {' -> '.join(ac.path)}")
        print(f"       - Reason:           {ac.reason}")
        print()

    # 7. Cleanup
    print("7. Cleaning up resources...")
    provider.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    print("======================================================================")
    print("   Demonstration Finished Successfully!")
    print("======================================================================")

if __name__ == "__main__":
    run_demo()
