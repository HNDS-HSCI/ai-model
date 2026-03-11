import logging
import json
from hnsds.perception.logic_parser import LogicParser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger
from hnsds.mental_model import MentalModel
from hnsds.brain.lobes.native_engine import NativeSymbolicEngine
from hnsds.brain.lobes.cognitive_lobe import CognitiveAwareness

logging.basicConfig(level=logging.DEBUG)


class HyperSymbolicBrain:
    """
    INVENTION: The Autonomous Hyper-Symbolic Brain.
    
    NEW ARCHITECTURE: System Awareness & Axiomatic Logic.
    Processes information by comprehending the whole context as an environment
    and applying mastered mental axioms to solve gaps.
    """

    def __init__(self):
        self.logger = logging.getLogger("CognitiveCore")

        # Native Lobe Initialization
        self.awareness_lobe = CognitiveAwareness()  # Environmental Awareness
        self.logic_prover = Z3Verifier()      
        self.csp_engine = NativeSymbolicEngine() 
        self.memory_lobe = EpisodeLogger()
        self.logic_parser = LogicParser()
        self.synthesizer = EnumerativeSynthesizer(learner=self.memory_lobe)

        # The Active Mind
        self.mind = MentalModel(learner=self.memory_lobe, cognitive_lobe=self.awareness_lobe)
        
        # INVENTION: Initial Mental Priming (Instructional Teaching)
        self._prime_mental_intelligence()

    def _prime_mental_intelligence(self):
        """
        Teaching Phase: The brain learns the basic concepts through environment perception.
        """
        teaching_data = [
            ("MATH_REDUCTION", "solve x + 5 = 10", "REDUCTION"),
            ("CODE_SYNTHESIS", "write a python function to sum three numbers", "SYNTHESIS"),
            ("LOGIC_COMPOSITION", "There are 3 houses. The Brit is in the red house", "COMPOSITION")
        ]
        
        self.logger.info("BRAIN_PRIMING: Establishing Mental Intelligence...")
        for concept, stimulus, axiom in teaching_data:
            self.awareness_lobe.teach_concept(concept, stimulus, axiom)
        self.logger.info("BRAIN_PRIMED: Mastery of Base Axioms established.")

    def process(self, stimulus, budget=5):
        # 0.0 Reset State
        self.mind.memory_trace = []
        self.mind.state = "IDLE"

        self.logger.info(f"Local Brain Activity: Comprehending environment '{stimulus[:50]}...'")

        # 1. ENVIRONMENTAL PERCEPTION
        # Absorbs the whole context block
        env = self.awareness_lobe.perceive_environment(stimulus)
        self.mind.memory_trace.append(f"AWARENESS: Environmental Map established ({len(env['entities'])} entities)")

        # 2. DELIBERATION (Applying Mastery)
        # Identifies the gap and the axiom required
        deliberation = self.awareness_lobe.deliberate(env)
        axiom = deliberation["axiom"]
        sigma = deliberation["goal"]
        
        self.mind.memory_trace.append(f"DELIBERATION: Selected Axiom {axiom}")
        self.logger.info(f"AXIOM_APPLIED: {axiom}")

        # --- EXECUTION ---
        
        # Axiom: COMPOSITION (Logic Puzzles)
        if axiom == "COMPOSITION":
            parsed_problem = self.logic_parser.parse(stimulus)
            solution = self.csp_engine.solve_csp(parsed_problem)
            self.memory_lobe.log_episode(sigma, solution, success=True)
            self.mind.finalize(solution)
            return f"LOGICALLY DERIVED (COMPOSITION):\n{solution}"

        # Axiom: SYNTHESIS (Code Generation)
        if axiom == "SYNTHESIS":
            # Retrieve past successes for this environment
            learned = self.memory_lobe.get_relevant_episodes(stimulus, top_k=3, threshold=0.8)
            seeded = [ep.get("candidate") for ep in learned if ep.get("success")]
            candidate = self.synthesizer.propose(sigma, examples=seeded)
        
        # Axiom: REDUCTION (Math)
        elif axiom == "REDUCTION":
            # Use Z3 for reduction
            from hnsds.brain.lobes.native_neural_lobe import NativeNeuralLobe
            temp_lobe = NativeNeuralLobe() # Legacy bridge for solve logic
            candidate = temp_lobe._solve_system_candidate(sigma)

        # Axiom: TRANSFORMATION (Conversation)
        else:
            return sigma.get("response", "Environment processed.")

        # 3. VERIFICATION LOOP
        for attempt in range(budget):
            success, feedback = self.logic_prover.verify(candidate, sigma)
            if success:
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                self.mind.finalize(candidate)
                return f"DERIVED SOLUTION (via {axiom}):\n{candidate}"
            else:
                self.logger.warning(f"Verification Failed: {feedback}")
                if axiom == "SYNTHESIS":
                    candidate = self.synthesizer.propose(sigma, examples=[feedback])
                else: break

        return "COGNITIVE_FAILURE: Environmental gap could not be bridged."

    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
