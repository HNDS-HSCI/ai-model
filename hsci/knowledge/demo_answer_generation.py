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
from hsci.reasoning.reasoning_engine import CognitiveReasoningEngine, ReasoningContext
from hsci.response.answer_generation_engine import AnswerGenerationEngine

def run_demo():
    print("======================================================================")
    print("   HSCI V4 - End-to-End Answer Generation Engine (AGE) Demonstration")
    print("======================================================================")

    db_file = "demo_age.db"
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

    # 3. Populate concepts representing Programming / OOP Domain
    print("3. Preloading OOP concepts database...")
    concepts = [
        Concept(id="c_inh", name="Inheritance", namespace="concept.oop", generalizes_to=["c_class"]),
        Concept(id="c_class", name="Class", namespace="concept.oop"),
        Concept(id="c_dup", name="Duplication", namespace="concept.oop")
    ]
    
    provider.begin_transaction()
    try:
        for c in concepts:
            manager.create_concept(c)
    finally:
        provider.commit_transaction()

    # 4. Initialize Subsystem Engines
    print("4. Initializing pipeline subsystems...")
    understanding_engine = UnderstandingEngine(manager)
    activation_engine = ConceptActivationEngine(manager, event_bus)
    reasoning_engine = CognitiveReasoningEngine(manager, event_bus)
    answer_engine = AnswerGenerationEngine(event_bus)

    # 5. Run user query through Pipeline
    user_query = "Why does inheritance reduce code duplication?"
    print(f"\n5. [Pipeline Start] User Question: '{user_query}'")
    ctx = CognitiveContext(
        request_id="age-demo-session",
        session_id="ground-agent",
        stimulus=user_query
    )
    
    # 5.1 Understanding
    start_time = time.perf_counter()
    understanding_res = understanding_engine.understand(user_query, ctx)
    print(f"   -> [Understanding] Intent: {understanding_res.intent}")

    # 5.2 Concept Activation
    active_set = activation_engine.activate_concepts(understanding_res.seed_concepts, ctx)
    print(f"   -> [Activation] Activated Concepts: {[ac.concept.name for ac in active_set.concepts]}")

    # Resolve active Concept objects
    workspace_concepts = []
    for ac in active_set.concepts:
        concept_obj = manager.get_concept(ac.concept.id)
        if concept_obj:
            workspace_concepts.append(concept_obj)

    # 5.3 Reasoning
    reasoning_ctx = ReasoningContext(goal="Explain duplication reduction")
    reasoning_result = reasoning_engine.reason(workspace_concepts, ctx, reasoning_ctx)
    print(f"   -> [Reasoning] Verified Conclusions count: {len(reasoning_result.conclusions)}")

    # 5.4 Answer Generation (AGE)
    print("\n6. [Answer Engine Execution] Generating explainable output (Standard Style)...")
    answer = answer_engine.generate(reasoning_result, ctx, style="Standard")
    print(f"   -> Direct Answer: {answer.direct_answer}")
    for section in answer.sections:
        print(f"   - Section '{section.title}':\n{section.content}")

    print(f"\n   -> Confidence: Score={answer.confidence.score:.2f} ({answer.confidence.description})")
    print(f"   -> Explanation Summary: {answer.explanation.reasoning_summary}")
    print(f"   -> References to Activated Concepts: {answer.metadata.activation_concepts}")

    # 8. Cleanup
    print("\n7. Cleaning up resources...")
    provider.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    print("======================================================================")
    print("   Answer Generation Demonstration Completed Successfully!")
    print("======================================================================")

if __name__ == "__main__":
    run_demo()
