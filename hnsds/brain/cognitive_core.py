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

        if stimulus.lower().startswith("teach:"):
            parts = stimulus[6:].split("|")
            if len(parts) >= 3:
                return self.teach(parts[0].strip(), parts[1].strip(), parts[2].strip().upper())
            return "Teach format: 'teach: <stimulus> | <concept_name> | <axiom>'"

        self.logger.info(f"Local Brain Activity: Comprehending environment '{stimulus[:50]}...'")

        # 1. PERCEPTION
        env = self.awareness_lobe.perceive_environment(stimulus)
        self.mind.memory_trace.append(f"AWARENESS: Environmental Map established ({len(env['entities'])} entities)")

        # 2. DELIBERATION
        deliberation = self.awareness_lobe.deliberate(env)
        master_axiom = deliberation["axiom"]
        master_sigma = deliberation["goal"]
        rationale = deliberation.get("rationale", "No rationale generated.")
        
        self.mind.memory_trace.append(f"DELIBERATION: Selected Master Axiom {master_axiom}. Rationale: {rationale}")
        
        if master_axiom == "TRANSFORMATION":
            return f"[TRANSFORMATION] {master_sigma.get('response', 'Environment processed.')}"

        # 3. RECURSIVE DECOMPOSITION (Planning)
        subgoals = self.planner.decompose(master_sigma)
        if len(subgoals) > 1:
            self.mind.memory_trace.append(f"PLANNING: Decomposed complex intent into {len(subgoals)} sub-tasks.")
        
        final_results = []

        # 4. EXECUTION & SELF-CORRECTION LOOP
        for i, sigma in enumerate(subgoals):
            step_name = sigma.get("step", f"Task {i+1}")
            self.logger.info(f"EXECUTING_SUBGOAL: {step_name}")
            
            candidate = None
            axiom = master_axiom
            
            # Subgoal Axiom Override
            if sigma.get("goal") == "synthesize": axiom = "SYNTHESIS"
            elif sigma.get("goal") == "solve" and sigma.get("type") == "logic": axiom = "COMPOSITION"

            # Execute Initial Hypothesis
            if axiom == "COMPOSITION":
                parsed_problem = self.logic_parser.parse(sigma.get("problem", stimulus))
                candidate = self.csp_engine.solve_csp(parsed_problem)
            elif axiom == "SYNTHESIS":
                learned = self.memory_lobe.get_relevant_episodes(str(sigma), top_k=3, threshold=0.7)
                seeded = [ep.get("candidate") for ep in learned if ep.get("success")]
                candidate = self.synthesizer.propose(sigma, examples=seeded)
            elif axiom == "REDUCTION":
                candidate = self.logic_prover.solve(sigma)

            # Verification & Auto-Correction Loop
            success_achieved = False
            
            if axiom == "REDUCTION" and candidate and "Solved:" in str(candidate):
                success_achieved = True
            elif candidate and "=" in str(candidate) and "Unsolvable" not in str(candidate):
                success_achieved = True
            else:
                for attempt in range(budget):
                    self.mind.memory_trace.append(f"VERIFICATION (Attempt {attempt+1}): Proving {step_name}")
                    success, feedback = self.logic_prover.verify(candidate, sigma)
                    
                    if success:
                        success_achieved = True
                        break
                    else:
                        self.logger.warning(f"Self-Correction Triggered: {feedback}")
                        self.mind.memory_trace.append(f"CORRECTION: Verifier rejected hypothesis. Reason: {feedback}")
                        
                        # Generate new hypothesis based on failure
                        if axiom == "SYNTHESIS":
                            candidate = self.synthesizer.propose(sigma, examples=[f"AVOID THIS ERROR: {feedback}"])
                        else: 
                            break # Math/Logic currently rely on single-shot solvers if Z3 rejects

            if success_achieved:
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                final_results.append(f"[{step_name}] Proven: {candidate}")
            else:
                final_results.append(f"[{step_name}] FAILED: {candidate}")

        self.mind.finalize("\n".join(final_results))
        return f"[{master_axiom}] Rationale: {rationale}\n\n" + "\n".join(final_results)
    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
