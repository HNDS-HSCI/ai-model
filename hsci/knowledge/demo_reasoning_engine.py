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

def run_demo():
    print("======================================================================")
    print("   HSCI V4 - End-to-End Cognitive Reasoning Engine Demonstration")
    print("======================================================================")

    db_file = "demo_cre.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    # 1. Setup UKM
    print("1. Initializing storage provider and running schema migrations...")
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

    # 4. Initialize Subsystem Engines
    print("4. Initializing Understanding, Activation, and Reasoning Engines...")
    understanding_engine = UnderstandingEngine(manager)
    activation_engine = ConceptActivationEngine(manager, event_bus)
    reasoning_engine = CognitiveReasoningEngine(manager, event_bus)

    # 5. Run user query through Pipeline
    user_query = "What is inheritance in Java?"
    print(f"\n5. [Pipeline Start] User Query: '{user_query}'")
    ctx = CognitiveContext(
        request_id="cre-demo-session",
        session_id="ground-agent",
        stimulus=user_query
    )
    
    # Stage 5.1: Understanding Engine
    start_time = time.perf_counter()
    understanding_res = understanding_engine.understand(user_query, ctx)
    parsing_dur_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"   -> [Understanding Result] intent: {understanding_res.intent}, seeds: {understanding_res.seed_concepts} (dur: {parsing_dur_ms:.2f}ms)")

    # Stage 5.2: Concept Activation Engine
    start_time = time.perf_counter()
    active_set = activation_engine.activate_concepts(understanding_res.seed_concepts, ctx)
    activation_dur_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"   -> [Concept Activation] Active workspace populated (dur: {activation_dur_ms:.2f}ms)")
    print(f"      Active Concepts: {[ac.concept.name for ac in active_set.concepts]}")

    # Resolve active Concept objects from KnowledgeManager for the Reasoning Engine
    workspace_concepts = []
    for ac in active_set.concepts:
        concept_obj = manager.get_concept(ac.concept.id)
        if concept_obj:
            workspace_concepts.append(concept_obj)

    # Stage 5.3: Cognitive Reasoning Engine (CRE)
    print("\n6. [Reasoning Engine Execution] Running CRE Loop over Active Workspace...")
    reasoning_ctx = ReasoningContext(goal="Explain user query intent")
    
    start_time = time.perf_counter()
    reasoning_result = reasoning_engine.reason(workspace_concepts, ctx, reasoning_ctx)
    reasoning_dur_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"   -> [Reasoning Complete] Proved logical facts in {reasoning_dur_ms:.2f}ms")

    # 7. Print verified findings, rules, and traces
    print("\n7. Reasoning Output Summary:")
    print(f"   - Final Reasoning Confidence: {reasoning_result.confidence:.2f}")
    print(f"   - Verified Conclusions:")
    for idx, c in enumerate(reasoning_result.conclusions):
        print(f"     [{idx + 1}] Conclusion:  {c.statement}")
        print(f"         Supporting Evidence: {c.evidence}")
        print()

    print("   - Reasoning Steps & Traces:")
    for step in reasoning_result.reasoning_trace.steps:
        print(f"     * Step {step.step_number}: {step.action}")
        print(f"       Concepts Used: {step.concepts_used}")
        print(f"       Inferred conclusions: {step.conclusions}")

    # 8. Cleanup
    print("\n8. Cleaning up resources...")
    provider.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    print("======================================================================")
    print("   Cognitive Reasoning Engine Demonstration Completed Successfully!")
    print("======================================================================")

if __name__ == "__main__":
    run_demo()
