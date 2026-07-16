import os
import json
import time
from typing import List, Dict, Any
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

def run_evaluation():
    print("======================================================================")
    print("   HSCI V4 - Evaluation Framework & Pipeline Benchmarking Runner")
    print("======================================================================")

    # 1. Setup UKM
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    
    migrations_dir = os.path.join(os.path.dirname(__file__), "hsci", "core", "migrations")
    migration = SchemaMigration(provider)
    migration.run_directory_migrations(migrations_dir)

    repo = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repo, event_bus)
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)

    # Pre-populate required evaluation concepts
    concepts = [
        Concept(id="c_java", name="Java", namespace="lang.oop"),
        Concept(id="c_inh", name="Inheritance", namespace="concept.oop", generalizes_to=["c_class"]),
        Concept(id="c_class", name="Class", namespace="concept.oop"),
        Concept(id="c_obj", name="Object", namespace="concept.oop"),
        Concept(id="c_eq", name="Equation", namespace="math"),
        Concept(id="c_ax", name="Axiom", namespace="logic")
    ]
    provider.begin_transaction()
    try:
        for c in concepts:
            manager.create_concept(c)
    finally:
        provider.commit_transaction()

    # Initialize subsystems
    understanding_engine = UnderstandingEngine(manager)
    activation_engine = ConceptActivationEngine(manager, event_bus)
    reasoning_engine = CognitiveReasoningEngine(manager, event_bus)
    answer_engine = AnswerGenerationEngine(event_bus)

    evaluation_files = [
        "evaluation/Java_OOP.json",
        "evaluation/Basic_Math.json",
        "evaluation/Logic.json"
    ]

    results = []
    total_latency_ms = 0.0
    total_cases = 0
    passed_cases = 0

    for file_path in evaluation_files:
        if not os.path.exists(file_path):
            print(f"Warning: Evaluation file '{file_path}' not found, skipping.")
            continue
            
        with open(file_path, "r") as f:
            cases = json.load(f)
            
        for case in cases:
            total_cases += 1
            question = case["question"]
            expected_concepts = case["expected_concepts"]
            success_criteria = case["success_criteria"]

            ctx = CognitiveContext(
                request_id=f"eval-{total_cases}",
                session_id="eval-agent",
                stimulus=question
            )

            # Execution Pipeline
            start_time = time.perf_counter()
            
            # Step 1: Understanding
            understanding_res = understanding_engine.understand(question, ctx)
            
            # Step 2: Concept Activation
            active_set = activation_engine.activate_concepts(understanding_res.seed_concepts, ctx)
            
            # Resolve concepts
            workspace_concepts = []
            for ac in active_set.concepts:
                concept_obj = manager.get_concept(ac.concept.id)
                if concept_obj:
                    workspace_concepts.append(concept_obj)

            # Step 3: Reasoning
            reasoning_ctx = ReasoningContext(goal="Evaluate correctness")
            reasoning_result = reasoning_engine.reason(workspace_concepts, ctx, reasoning_ctx)
            
            # Step 4: Answer Generation
            answer = answer_engine.generate(reasoning_result, ctx)
            
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            total_latency_ms += latency_ms

            # Accuracy check evaluation (success criteria string evaluation)
            # Local namespace variables for eval checking
            intent = understanding_res.intent
            seed_concepts = understanding_res.seed_concepts
            
            is_success = False
            try:
                is_success = eval(success_criteria, {}, {"intent": intent, "seed_concepts": seed_concepts})
            except Exception:
                is_success = False

            if is_success:
                passed_cases += 1

            results.append({
                "question": question,
                "latency_ms": latency_ms,
                "success": is_success,
                "intent": intent,
                "resolved_concepts": seed_concepts
            })

    avg_latency = total_latency_ms / total_cases if total_cases > 0 else 0.0
    accuracy = (passed_cases / total_cases) * 100.0 if total_cases > 0 else 0.0

    print(f"Evaluation Completed: {passed_cases}/{total_cases} cases passed ({accuracy:.2f}%)")
    print(f"Average Pipeline Latency: {avg_latency:.2f}ms")

    # Generate evaluation_report.md
    generate_report(results, avg_latency, accuracy)
    provider.close()

def generate_report(results: List[Dict[str, Any]], avg_latency: float, accuracy: float):
    report_content = f"""# HSCI V4 — Evaluation Framework Report (evaluation_report.md)

This report summarizes the pipeline execution accuracy and processing latency benchmarks calculated by the evaluation runner framework.

---

## 1. Global Benchmark Metrics

*   **Total Evaluation Cases**: {len(results)}
*   **Passed Cases**: {sum(1 for r in results if r["success"])}
*   **Concept Activation & Parsing Accuracy**: {accuracy:.2f}%
*   **Average Pipeline Latency**: {avg_latency:.2f}ms

---

## 2. Detailed Test Cases Output

| Case Question | Intent Classified | Resolved Concepts | Latency (ms) | Success |
|---|---|---|---|---|
"""
    for r in results:
        report_content += f"| {r['question']} | {r['intent']} | {r['resolved_concepts']} | {r['latency_ms']:.2f}ms | {'Passed' if r['success'] else 'Failed'} |\n"

    report_content += "\n---\n*Report generated automatically by the evaluation framework runner.*"
    
    with open("evaluation_report.md", "w") as f:
        f.write(report_content)
    print("Report written successfully to 'evaluation_report.md'.")

if __name__ == "__main__":
    run_evaluation()
