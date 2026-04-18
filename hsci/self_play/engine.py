import time
import logging
import z3
from threading import Thread
from typing import Any, List
from hsci.self_play.hypothesis_builder import HypothesisBuilder
from hsci.core.data_types import PerceptionMap

class SelfPlayEngine:
    """
    Autonomous knowledge discovery.
    Runs in background thread when system is idle.
    Ensures thread-safe Z3 usage via transactional contexts.
    """

    def __init__(self, knowledge_base, reasoning_engine, z3_verifier, learning_engine):
        self.knowledge = knowledge_base
        self.reasoning = reasoning_engine
        self.verifier = z3_verifier
        self.learning = learning_engine
        self.hypothesis_builder = HypothesisBuilder()
        self.running = False
        self.logger = logging.getLogger("SelfPlayEngine")
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
            self.logger.setLevel(logging.INFO)

    def start(self):
        if not self.running:
            self.running = True
            thread = Thread(target=self._run_loop, daemon=True)
            thread.start()
            self.logger.info("🧠 Self-play engine ACTIVATED.")

    def stop(self):
        self.running = False
        self.logger.info("💤 Self-play engine STOPPED.")

    def _run_loop(self):
        while self.running:
            try:
                hypothesis = self._generate_hypothesis()
                self.logger.info(f"💡 Generated hypothesis: {hypothesis.entity_graph.get('text', 'Unknown structure')}")

                self._solve_and_learn(hypothesis)

                weak_concepts = self.knowledge.concept_library.get_weakest(n=2)
                for concept in weak_concepts:
                    if not self.running:
                         break
                    self.logger.info(f"🎯 Target practice for weak concept: {concept.name}")
                    practice_hypothesis = self.hypothesis_builder.build_for_concept(
                        concept,
                        difficulty=concept.strength
                    )
                    self._solve_and_learn(practice_hypothesis)

                time.sleep(2.0) 

            except Exception as e:
                time.sleep(5.0) 
                continue

    def _generate_hypothesis(self) -> PerceptionMap:
        concepts = self.knowledge.concept_library.sample(n=2)
        return self.hypothesis_builder.build_from_concepts(concepts)

    def _solve_and_learn(self, hypothesis: PerceptionMap):
        # Fresh context for the self-play transaction
        ctx = z3.Context()
        
        knowledge_result = self.knowledge.query(hypothesis)
        
        plan = self.reasoning.reason(hypothesis, knowledge_result, ctx=ctx)
        
        primary_concept = None
        if plan.concept_assignments:
             primary_concept = list(plan.concept_assignments.values())[0]

        result = self.verifier.verify(
            plan.candidate_solution, 
            hypothesis, 
            primary_concept,
            ctx=ctx
        )

        self.learning.learn(hypothesis, plan, result)
        
        if result.valid:
            self.logger.info(f"✅ Self-play SUCCESS.")
        else:
            self.logger.info(f"❌ Self-play REFUTED.")
