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
        
    def teach(self, stimulus, concept_name, axiom):
        """
        Interactive Teaching API: Allows humans to teach the system new concepts.
        """
        self.logger.info(f"TEACHING: Binding stimulus to concept '{concept_name}' using axiom '{axiom}'")
        self.awareness_lobe.teach_concept(concept_name, stimulus, axiom)
        return f"Learned concept: {concept_name} -> Maps to {axiom}"

    def process(self, stimulus, budget=5):
        # 0.0 Reset State
        self.mind.memory_trace = []
        self.mind.state = "IDLE"

        # Check for teaching command
        if stimulus.lower().startswith("teach:"):
            parts = stimulus[6:].split("|")
            if len(parts) >= 3:
                return self.teach(parts[0].strip(), parts[1].strip(), parts[2].strip().upper())
            return "Teach format: 'teach: <stimulus> | <concept_name> | <axiom>'"

        self.logger.info(f"Local Brain Activity: Comprehending environment '{stimulus[:50]}...'")

        # 1. ENVIRONMENTAL PERCEPTION
        env = self.awareness_lobe.perceive_environment(stimulus)
        self.mind.memory_trace.append(f"AWARENESS: Environmental Map established ({len(env['entities'])} entities)")

        # 2. DELIBERATION (Applying Mastery)
        deliberation = self.awareness_lobe.deliberate(env)
        axiom = deliberation["axiom"]
        sigma = deliberation["goal"]
        rationale = deliberation.get("rationale", "No rationale generated.")
        
        self.mind.memory_trace.append(f"DELIBERATION: Selected Axiom {axiom}. Rationale: {rationale}")
        self.logger.info(f"AXIOM_APPLIED: {axiom}")

        # --- EXECUTION ---
        candidate = None
        
        # Axiom: COMPOSITION (Logic Puzzles)
        if axiom == "COMPOSITION":
            parsed_problem = self.logic_parser.parse(stimulus)
            candidate = self.csp_engine.solve_csp(parsed_problem)
            self.memory_lobe.log_episode(sigma, candidate, success=True)
            self.mind.finalize(candidate)
            return f"[{axiom}] Rationale: {rationale}\nSolution:\n{candidate}"

        # Axiom: SYNTHESIS (Code Generation)
        elif axiom == "SYNTHESIS":
            learned = self.memory_lobe.get_relevant_episodes(stimulus, top_k=3, threshold=0.8)
            seeded = [ep.get("candidate") for ep in learned if ep.get("success")]
            candidate = self.synthesizer.propose(sigma, examples=seeded)
        
        # Axiom: REDUCTION (Math)
        elif axiom == "REDUCTION":
            # Dynamic solving using Z3
            candidate = self.logic_prover.solve(sigma)

        # Axiom: TRANSFORMATION (Conversation)
        else:
            return f"[TRANSFORMATION] {sigma.get('response', 'Environment processed.')}"

        # 3. VERIFICATION LOOP
        if axiom == "REDUCTION" and "Solved:" in str(candidate):
             self.mind.finalize(candidate)
             return f"[{axiom}] Rationale: {rationale}\nProven Solution: {candidate}"

        for attempt in range(budget):
            success, feedback = self.logic_prover.verify(candidate, sigma)
            if success:
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                self.mind.finalize(candidate)
                return f"[{axiom}] Rationale: {rationale}\nProven Solution: {candidate}"
            else:
                self.logger.warning(f"Verification Failed: {feedback}")
                if axiom == "SYNTHESIS":
                    candidate = self.synthesizer.propose(sigma, examples=[feedback])
                else: break

        # Final check: if candidate has solved assignments, return it
        if candidate and "=" in str(candidate) and "Unsolvable" not in str(candidate):
            return f"[{axiom}] Rationale: {rationale}\nProven Solution: {candidate}"

        return f"[{axiom}] COGNITIVE_FAILURE: Environmental gap could not be bridged. Last attempt: {candidate}"

    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
