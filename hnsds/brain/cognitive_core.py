import logging
import json
from hnsds.perception.parser import Parser
from hnsds.perception.logic_parser import LogicParser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.generative import NativeProgramSynthesizer
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
        self.logic_parser = LogicParser()
        self.synthesizer = NativeProgramSynthesizer()
        
        # The Active Mind
        self.mind = MentalModel(learner=self.memory_lobe, neural_lobe=self.neural_lobe)

    def process(self, stimulus, budget=5):
        self.logger.info("Local Brain Activity: Deliberating natively...")
        
        # 1. PERCEPTION (Through the Mind)
        # The Mind's perceive() now returns the cognitive state (e.g. ANALYTICAL, CONVERSATIONAL)
        cognitive_state = self.mind.perceive(stimulus)
        
        # 2. DELIBERATION (Planning & Reasoning)
        # The Mind uses the Native Neural Lobe to get the Symbolic Spec (sigma)
        sigma = self.mind.deliberate(stimulus)
        
        # --- ACTIVE CLARIFICATION (The Interrogator) ---
        # If the Neural Lobe is unsure, ask the user instead of guessing.
        confidence = sigma.get("confidence", 1.0)
        if confidence < 0.4 and sigma.get("type") != "conversational":
            return f"CLARIFICATION NEEDED: I am only {confidence*100:.1f}% sure you want {sigma.get('type')}. Could you be more specific?"

        # If it's just chat, return the planned response
        if cognitive_state == "CONVERSATIONAL" and sigma.get("type") != "logic":
            return sigma.get("response", "I hear you.")
            
        # SPECIAL HANDLING: LOGIC PUZZLES (Disruptive Capability)
        if sigma.get("type") == "logic":
            parsed_problem = self.logic_parser.parse(sigma.get("raw", stimulus))
            solution = self.logic_prover.solve_csp(parsed_problem)
            self.mind.finalize(solution)
            return f"LOGICALLY PROVEN: {solution}"
        
        # SYNTHESIS (The Builder)
        # FORCE: Use the First-Principles Synthesizer for coding to avoid template recall errors.
        if sigma.get("type") == "coding":
             candidate = self.synthesizer.propose(sigma)
        else:
             candidate = sigma.get("candidate")
             if not candidate:
                 candidate = self.neural_lobe.propose_solution(sigma)

        # 3. VERIFICATION (The Symbolic Check)
        # We search for a candidate that the Symbolic Prover accepts
        for attempt in range(budget):
            
            # The Logic Prover verifies natively
            success, feedback = self.logic_prover.verify_natively(candidate, sigma)

            if success:
                # 4. SELF-GROWTH (The Learning Step)
                # If the solution is PROVEN, the brain reinforces the neural links
                # that led to this successful symbolic formalization.
                self.neural_lobe.grow(stimulus, sigma, sigma.get("type"))
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                
                self.mind.finalize(candidate)
                return f"PROVEN SOLUTION:\n{candidate}"
            else:
                # In a real loop, we would ask the planner to 're-plan' based on feedback
                pass
        
        return "COGNITIVE_FAILURE: Native proof not found."



    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
