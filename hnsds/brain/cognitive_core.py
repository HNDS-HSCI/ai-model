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
        self.awareness_lobe = CognitiveAwareness()
        self.logic_prover = Z3Verifier()      
        self.csp_engine = NativeSymbolicEngine() 
        self.memory_lobe = EpisodeLogger()
        self.logic_parser = LogicParser()
        self.synthesizer = EnumerativeSynthesizer(learner=self.memory_lobe)
        self.planner = HTNPlanner()

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
        self.mind.memory_trace = []
        self.mind.state = "IDLE"

        # 0.0 Check for Interactive Teaching
        if stimulus.lower().startswith("teach:"):
            parts = stimulus[6:].split("|")
            if len(parts) >= 3:
                return self.teach(parts[0].strip(), parts[1].strip(), parts[2].strip().upper())
            return "Teach format: 'teach: <stimulus> | <concept_name> | <axiom>'"

        self.logger.info(f"Local Brain Activity: Comprehending environment '{stimulus[:50]}...'")

        # 1. PERCEPTION: Map the Environment and State Gap
        env = self.awareness_lobe.perceive_environment(stimulus)
        self.mind.memory_trace.append(f"AWARENESS: Environmental Map established ({len(env['entities'])} entities)")

        # 2. DELIBERATION: Generate the Universal Sigma (Σ) Contract
        deliberation = self.awareness_lobe.deliberate(env)
        master_sigma = deliberation["goal"]
        rationale = deliberation.get("rationale", "No rationale generated.")
        
        self.mind.memory_trace.append(f"DELIBERATION: State Gap identified. Rationale: {rationale}")
        
        if deliberation["axiom"] == "TRANSFORMATION":
            return f"[TRANSFORMATION] {master_sigma.get('response', 'Environment processed.')}"

        # 3. RECURSIVE PLANNING: Decompose Goal into Logical Steps
        subgoals = self.planner.decompose(master_sigma)
        final_results = []

        # 4. UNIFIED REASONING MESH: Solve the constraints
        for i, sigma in enumerate(subgoals):
            step_name = sigma.get("step", f"Task {i+1}")
            self.logger.info(f"REASONING_ON_SUBGOAL: {step_name}")
            
            # The brain now cycles through its lobes to find the best fit for the constraint
            # It doesn't care if it's 'math' or 'code', it only cares if it's PROVEN.
            solution_found = False
            candidate = None
            
            # Priority 1: Mathematical/Logical Reduction (Highest Certainty)
            if not solution_found:
                candidate = self.logic_prover.solve(sigma)
                if candidate and "Solved:" in str(candidate) or "=" in str(candidate):
                    if "Unsolvable" not in str(candidate):
                        solution_found = True
                        method = "REDUCTION"

            # Priority 2: Constraint Satisfaction (Logical Composition)
            if not solution_found:
                parsed_problem = self.logic_parser.parse(sigma.get("problem", str(sigma)))
                candidate = self.csp_engine.solve_csp(parsed_problem)
                if candidate and "FAILED" not in str(candidate):
                    solution_found = True
                    method = "COMPOSITION"

            # Priority 3: Procedural Synthesis (Constructing new logic)
            if not solution_found:
                learned = self.memory_lobe.get_relevant_episodes(str(sigma), top_k=3, threshold=0.7)
                seeded = [ep.get("candidate") for ep in learned if ep.get("success")]
                candidate = self.synthesizer.propose(sigma, examples=seeded)
                method = "SYNTHESIS"

            # 5. VERIFICATION & SELF-CORRECTION LOOP
            for attempt in range(budget):
                self.mind.memory_trace.append(f"VERIFYING: {step_name} (via {method})")
                success, feedback = self.logic_prover.verify(candidate, sigma)
                
                if success:
                    solution_found = True
                    break
                else:
                    self.mind.memory_trace.append(f"REPAIR: Verifier rejected {method} hypothesis. Feedback: {feedback}")
                    if method == "SYNTHESIS":
                        candidate = self.synthesizer.propose(sigma, examples=[f"FIX ERROR: {feedback}"])
                    else: break

            if solution_found:
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                final_results.append(f"[{step_name}] Proven: {candidate}")
            else:
                final_results.append(f"[{step_name}] FAILED to bridge gap.")

        # 6. FINAL STATE SYNTHESIS
        proven_output = "\n".join(final_results)
        self.mind.finalize(proven_output)
        return f"[HSCI] Rationale: {rationale}\n\n" + proven_output
    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
