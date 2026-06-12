from datetime import datetime
from typing import Any, List, Optional
from hsci.core.data_types import (
    PerceptionMap, ReasoningPlan, VerificationResult, LearningResult, 
    Episode, WeightUpdate, Concept, ProofTrace
)
from hsci.learning.concept_extractor import ConceptExtractor
from hsci.learning.proof_guided_updater import ProofGuidedWeightUpdater

class LearningEngine:
    """
    LAYER 5: Learning Engine
    Updates knowledge and neural weights from proven interactions.
    """

    def __init__(self, neural_perceiver, knowledge_base):
        self.perceiver = neural_perceiver
        self.knowledge = knowledge_base
        self.concept_extractor = ConceptExtractor()
        self.proof_guided_updater = ProofGuidedWeightUpdater()
        self.learning_rate = 0.01

    def learn(
        self,
        perception: PerceptionMap,
        plan: ReasoningPlan,
        verification: VerificationResult
    ) -> LearningResult:

        if verification.valid and verification.proof_trace:
            return self._learn_from_proof(
                perception, plan, verification
            )
        else:
            return self._learn_from_failure(
                perception, plan, verification
            )

    def _learn_from_proof(self, perception: PerceptionMap, plan: ReasoningPlan, verification: VerificationResult) -> LearningResult:
        """
        Proof succeeded. Extract concept. Strengthen pathways.
        """

        # 1. Extract concept from proof trace
        # ConceptExtractor needs to handle EntityValue and ProofTrace
        new_concept = self.concept_extractor.extract(
            perception,
            plan.candidate_solution,
            verification.proof_trace,
            self.knowledge
        )

        # 2. Store or reinforce concept
        learned = None
        reinforced = None
        if self.knowledge.concept_library.contains(new_concept.name):
            self.knowledge.concept_library.update_strength(
                new_concept.name, self.learning_rate
            )
            reinforced = new_concept
        else:
            self.knowledge.concept_library.add(new_concept)
            self.knowledge.ontology.integrate(new_concept)
            learned = new_concept

        # 3. Update neural weights based on proof (Phase 3)
        weight_update = self.proof_guided_updater.compute_update(
            perception=perception,
            proof_trace=verification.proof_trace,
            direction="strengthen",
            learning_rate=self.learning_rate,
            intent_hint=perception.intent.value   # Phase 3: pass correct intent
        )
        self.perceiver.update_weights_from_proof(weight_update)

        # 4. Store episode
        episode = Episode(
            input_summary=perception.operation_hint,
            domain=perception.domain,
            solution=plan.candidate_solution,
            concepts_used=plan.concepts_used,
            was_verified=True,
            timestamp=datetime.now()
        )
        self.knowledge.episode_memory.store(episode)

        return LearningResult(
            new_concept=learned,
            reinforced_concept=reinforced,
            weight_updates=weight_update,
            episode_stored=episode
        )

    def _learn_from_failure(self, perception: PerceptionMap, plan: ReasoningPlan, verification: VerificationResult) -> LearningResult:
        """
        Proof failed. Weaken wrong neural pathways.
        """
        weight_update = self.proof_guided_updater.compute_update(
            perception=perception,
            proof_trace=verification.counterexample or {},
            direction="weaken",
            learning_rate=self.learning_rate * 0.5,
            intent_hint=perception.intent.value   # Phase 3: pass intent even on failure
        )
        self.perceiver.update_weights_from_proof(weight_update)

        return LearningResult(
            weight_updates=weight_update,
            failure_logged=verification.correction_hint
        )
