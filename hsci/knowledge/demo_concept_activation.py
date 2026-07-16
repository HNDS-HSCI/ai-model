import os
import time
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager
from hsci.knowledge.concept_activation import ConceptActivationEngine

def run_demo():
    print("======================================================================")
    print("   HSCI V4 - Concept Activation Engine (CAE) Demonstration")
    print("======================================================================")

    db_file = "demo_cae.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    # 1. Setup UKM and KnowledgeManager façade
    print("1. Initializing storage provider and running schema migrations...")
    provider = SQLiteProvider(db_path=db_file)
    provider.initialize()
    
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "migrations")
    migration = SchemaMigration(provider)
    migration.run_directory_migrations(migrations_dir)

    print("2. Assembling repositories and logical manager...")
    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)

    # 3. Preload a structured concept network representing mathematical reasoning
    print("3. Preloading math concept network...")
    concepts = [
        Concept(id="c_add", name="Addition", namespace="math.arithmetic", generalizes_to=["c_op"]),
        Concept(id="c_sub", name="Subtraction", namespace="math.arithmetic", generalizes_to=["c_op"]),
        Concept(id="c_mul", name="Multiplication", namespace="math.arithmetic", generalizes_to=["c_op"]),
        Concept(id="c_op", name="ArithmeticOperator", namespace="math.basic"),
        Concept(id="c_int", name="Integer", namespace="math.types"),
        Concept(id="c_float", name="FloatingPoint", namespace="math.types")
    ]
    
    provider.begin_transaction()
    try:
        for c in concepts:
            manager.create_concept(c)
    finally:
        provider.commit_transaction()

    # 4. Initialize Concept Activation Engine
    print("4. Initializing ConceptActivationEngine...")
    engine = ConceptActivationEngine(manager, event_bus)

    # 5. Run activation cycle starting from seed concept 'Addition'
    print("\n5. Executing spreading activation pipeline from seed: 'Addition'")
    ctx = CognitiveContext(
        request_id="demo-session-9",
        session_id="ground-agent",
        stimulus="User asks to add two integers"
    )
    
    start_time = time.perf_counter()
    active_set = engine.activate_concepts(["Addition"], ctx)
    dur_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"   -> Spreading completed in {dur_ms:.4f}ms.")
    print(f"   -> Total activated nodes: {len(active_set.concepts)}")

    # 6. Print activations explainability metrics
    print("\n6. Activation List & Explainability:")
    for idx, ac in enumerate(active_set.concepts):
        print(f"   [{idx + 1}] Concept: {ac.concept.name:<18} (ID: {ac.concept.id})")
        print(f"       - Activation Score: {ac.score:.4f}")
        print(f"       - Seed Source:      {ac.source}")
        print(f"       - Propagation Path: {' -> '.join(ac.path)}")
        print(f"       - Reason:           {ac.reason}")
        print()

    # 7. Verify WorkingMemory got updated
    print("7. Verifying WorkingMemory workspace state:")
    wm = ctx.working_memory
    print(f"   -> ActivationField entries: {list(wm.activation_field.activation_strengths.keys())}")
    print(f"   -> AttentionBuffer salience: {wm.attention_buffer.salient_entities}")
    print(f"   -> Active skills assigned:   {wm.active_skills}")

    # 8. Cleanup
    print("\n8. Cleaning up resources...")
    provider.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    print("======================================================================")
    print("   Concept Activation Demonstration Completed Successfully!")
    print("======================================================================")

if __name__ == "__main__":
    run_demo()
