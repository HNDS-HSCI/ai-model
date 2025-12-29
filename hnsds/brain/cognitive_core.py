import logging
import json
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger
from hnsds.mental_model import MentalModel

from hnsds.brain.lobes.native_engine import NativeSymbolicEngine

from hnsds.brain.lobes.native_neural_lobe import NativeNeuralLobe

class HyperSymbolicBrain:
    """
    INVENTION: The Autonomous Hyper-Symbolic Brain.
    A self-contained system that uses Native Neural Perception 
    and Symbolic Verification to grow its own intelligence.
    NO THIRD PARTY DEPENDENCIES.
    """
    def __init__(self):
        self.logger = logging.getLogger("CognitiveCore")
        
        # Native Lobe Initialization
        self.neural_lobe = NativeNeuralLobe() # The Statistical/Neural component
        self.logic_prover = NativeSymbolicEngine() # The Deterministic/Symbolic component
        self.memory_lobe = EpisodeLogger()
        
        # The Active Mind
        self.mind = MentalModel(learner=self.memory_lobe)

    def process(self, stimulus, budget=5):
        self.logger.info("Local Brain Activity: Deliberating natively...")
        
        # 1. Native Neural Perception (Statistically derive intent/spec)
        sigma = self.neural_lobe.classify_and_formalize(stimulus)
        self.mind.set_specification(sigma)
        
        if sigma.get("type") == "conversational":
            return sigma.get("response")

        # 2. Native Reasoning & Synthesis
        # We search for a candidate that the Symbolic Prover accepts
        examples = []
        for attempt in range(budget):
            # The neural lobe proposes based on templates
            candidate = self.neural_lobe.propose_solution(sigma)
            
            # The Logic Prover verifies natively
            success, feedback = self.logic_prover.verify_natively(candidate, sigma)

            if success:
                # 3. SELF-GROWTH (The Learning Step)
                # If the solution is PROVEN, the brain reinforces the neural links
                # that led to this successful symbolic formalization.
                self.neural_lobe.grow(stimulus, sigma, sigma["type"])
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                
                self.mind.finalize(candidate)
                return f"PROVEN SOLUTION: {candidate}"
            else:
                examples.append(feedback)
        
        return "COGNITIVE_FAILURE: Native proof not found."



    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.synaptic_state.get_deliberation_report()
