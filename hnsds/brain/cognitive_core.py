import logging
import json
from hnsds.perception.logic_parser import LogicParser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.generative import NativeProgramSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger
from hnsds.mental_model import MentalModel
from hnsds.brain.lobes.native_engine import NativeSymbolicEngine
from hnsds.brain.lobes.native_neural_lobe import NativeNeuralLobe

logging.basicConfig(level=logging.DEBUG)


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
        self.neural_lobe = NativeNeuralLobe()  # The Statistical/Neural component
        self.logic_prover = (
            NativeSymbolicEngine()
        )  # The Deterministic/Symbolic component
        self.memory_lobe = EpisodeLogger()
        self.logic_parser = LogicParser()
        self.synthesizer = NativeProgramSynthesizer()

        # The Active Mind
        self.mind = MentalModel(learner=self.memory_lobe, neural_lobe=self.neural_lobe)

    def process(self, stimulus, budget=5):
        # 0.0 Reset Mind State for New Request
        self.mind.memory_trace = []
        self.mind.symbolic_spec = None
        self.mind.recalled_episode = None
        self.mind.derived_solution = None
        self.mind.state = "IDLE"

        self.logger.info(f"Local Brain Activity: Deliberating natively for '{stimulus}'...")

        # 0. EARLY MEMORY CHECK (Before anything else) - PRINCIPLE 2 FIX
        # If exact match found in episodes, skip synthesis entirely
        recalled = self.memory_lobe.get_relevant_episodes(
            stimulus, top_k=1, threshold=0.95
        )
        if recalled and recalled[0].get("success"):
            solution = recalled[0].get("candidate")
            self.logger.info(f"MEMORY_RECALL_CANDIDATE: {solution}")
            success, _ = self.logic_prover.verify_natively(solution, {"type": "cached"})
            if success:
                self.logger.info("MEMORY_HIT: Using cached verified solution")
                return f"VERIFIED (from memory):\n{solution}"
            self.logger.warning("MEMORY_STALE: Recalled candidate failed verification.")

        # 1. PERCEPTION (Through the Mind)
        cognitive_state = self.mind.perceive(stimulus)
        self.logger.info(f"COGNITIVE_STATE: {cognitive_state}")

        # 2. DELIBERATION (Planning & Reasoning)
        # Fetch the symbolic spec generated during perception
        sigma = self.mind.symbolic_spec if self.mind.symbolic_spec else self.mind.deliberate(stimulus)
        self.logger.info(f"SIGMA: {sigma}")

        # --- ACTIVE CLARIFICATION (The Interrogator) ---
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
            self.neural_lobe.grow(stimulus, sigma, "logic")  # PRINCIPLE 1 FIX
            self.memory_lobe.log_episode(sigma, solution, success=True)
            self.mind.finalize(solution)
            return f"LOGICALLY PROVEN: {solution}"

        # RETRIEVE LEARNED EPISODES (Seed synthesis with past solutions) - PRINCIPLE 5 FIX
        learned_episodes = self.memory_lobe.get_relevant_episodes(
            stimulus, top_k=3, threshold=0.8
        )
        seeded_candidates = [
            ep.get("candidate") for ep in learned_episodes if ep.get("success")
        ]

        # SYNTHESIS (The Builder)
        if sigma.get("type") == "coding":
            if sigma.get("candidate") and "Hierarchical" in str(sigma.get("candidate")):
                candidate = sigma.get("candidate")
            else:
                candidate = self.synthesizer.propose(sigma, examples=seeded_candidates)
        else:
            candidate = sigma.get("candidate")
            if not candidate:
                candidate = self.neural_lobe.propose_solution(sigma)

        # 3. VERIFICATION + ITERATIVE REPAIR (The Symbolic Check) - PRINCIPLE 3 FIX
        counterexamples = []
        for attempt in range(budget):
            success, feedback = self.logic_prover.verify_natively(candidate, sigma)

            if success:
                # 4. SELF-GROWTH (The Learning Step)
                self.neural_lobe.grow(stimulus, sigma, sigma.get("type"))
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                self.mind.finalize(candidate)
                return f"PROVEN SOLUTION:\n{candidate}"
            else:
                # ITERATIVE REPAIR: Counterexample refines next candidate
                counterexamples.append(feedback)
                self.logger.warning(
                    f"Verification Failed (Attempt {attempt+1}): {feedback}"
                )
                if sigma.get("type") == "coding":
                    candidate = self.synthesizer.propose(
                        sigma, examples=counterexamples + seeded_candidates
                    )
                else:
                    # For math/logic, we don't have an iterative repair synthesizer yet.
                    break 

        return "COGNITIVE_FAILURE: Native proof not found after all attempts."

    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
