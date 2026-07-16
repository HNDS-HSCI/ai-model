import os
import time
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import SQLiteProvider, SchemaMigration
from hsci.core.kernel import EventBus
from hsci.knowledge.concept_repository import ConceptRepository
from hsci.knowledge.concept_store import ConceptStore
from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
from hsci.knowledge.knowledge_manager import KnowledgeManager

def run_demo():
    print("======================================================================")
    print("   HSCI V4 - KnowledgeManager Vertical Slice Demonstration")
    print("======================================================================")
    
    db_file = "demo_hsci_v4.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    # 1. Initialize SQLite Database Provider
    print("1. Initializing physical storage provider...")
    provider = SQLiteProvider(db_path=db_file)
    provider.initialize()

    # 2. Run sequential migrations discovered from files
    print("2. Running database migrations...")
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "migrations")
    migration = SchemaMigration(provider)
    migration.run_directory_migrations(migrations_dir)

    # 3. Assemble Logical Stores
    print("3. Assembling ConceptRepository and ConceptStore...")
    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)

    # 4. Initialize KnowledgeManager with replaceble cache
    print("4. Initializing KnowledgeManager with InMemoryKnowledgeCache...")
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)

    # 5. Populate concept record
    print("5. Populating concept data through KnowledgeManager...")
    concept = Concept(
        id="ground_addition",
        name="AdditionConcept",
        namespace="ground.arithmetic",
        axiom_type=AxiomType.REDUCTION,
        abstract_rule="x + y",
        z3_template="res == x + y",
        domain="arithmetic"
    )
    concept_id = manager.create_concept(concept, {
        "source_type": "USER_DEMONSTRATION",
        "acquisition_method": "MANUAL",
        "notes": "Addition concept vertical slice foundation test"
    })
    print(f"   -> Concept created successfully. Registered ID: {concept_id}")

    # 6. Simulate Cognitive Retrieval Query
    print("\n6. Simulating User/Engine Query Flow:")
    print("   User Query -> BrainKernel -> KnowledgeManager -> ConceptStore")
    
    start_time = time.perf_counter()
    retrieved = manager.get_concept_by_name("AdditionConcept")
    dur_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"   -> Query completed in {dur_ms:.4f}ms.")
    if retrieved:
        print("   -> Retrieved Concept Details:")
        print(f"      - ID:            {retrieved.id}")
        print(f"      - Name:          {retrieved.name}")
        print(f"      - Namespace:     {retrieved.namespace}")
        print(f"      - Abstract Rule: {retrieved.abstract_rule}")
        print(f"      - Z3 Template:   {retrieved.z3_template}")
        print(f"      - Status:        {retrieved.status}")
    else:
        print("   -> ERROR: Failed to retrieve concept.")

    # 7. Cleanup
    print("\n7. Cleaning up demonstration resources...")
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
