import logging
from hnsds.mental_model import MentalModel

class HNSDSOrchestrator:
    def __init__(self, perception, formalizer, planner, synthesizer, verifier, learner):
        self.perception = perception
        self.formalizer = formalizer
        self.planner = planner
        self.synthesizer = synthesizer
        self.verifier = verifier
        self.learner = learner
        self.logger = logging.getLogger("HNSDS")
        self.mind = MentalModel(learner=self.learner, synthesizer=self.synthesizer, neural_lobe=self.perception)

    def run(self, raw_input, budget=10):
        """
        Executes the Neuro-Symbolic Cognitive Loop.
        """
        self.logger.info("Starting Cognitive Process...")
        
        # 1. Perception
        self.mind.perceive(raw_input)
        
        # 2. Deliberation (Neural Extraction of Symbolic Spec)
        sigma = self.mind.deliberate(raw_input)
        
        if sigma.get("type") == "conversational" and "response" in sigma:
            return sigma["response"]

        # 3. Strategic Planning
        self.mind.set_specification(sigma)
        
        # 4. Synthesis & Verification Loop
        examples = []
        for attempt in range(budget):
            # Propose a solution based on the symbolic spec
            candidate = self.synthesizer.propose(sigma, examples)
            
            # Formally verify the candidate
            success, feedback = self.verifier.verify(candidate, sigma)
            
            if success:
                self.mind.finalize(candidate)
                if self.learner:
                    self.learner.log_episode(sigma, candidate, success=True)
                
                # REINFORCEMENT: Update synapses if successful
                # This mimics 'Hebbian Learning' - effective pathways are strengthened.
                self.mind.reinforce(raw_input, self.mind.state)
                
                return candidate
            else:
                self.logger.warning(f"Verification Failed (Attempt {attempt+1}): {feedback}")
                examples.append(feedback)
                if self.learner:
                    self.learner.log_episode(sigma, candidate, counterexample=feedback, success=False)
                
        return "COGNITIVE_FAILURE: Formal verification failed after multiple attempts."


    def write_solution(self):
        """
        Returns the human-readable deliberation report from the AI's mind.
        """
        return self.mind.write_solution()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("HNS-DS Orchestrator Initialized.")
