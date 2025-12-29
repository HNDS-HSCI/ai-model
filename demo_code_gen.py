import logging
import sys
print("Debug: Starting imports...", flush=True)
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger

# Configure logging to show the "Thought Process"
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

def main():
    # 1. Initialize the Brain's Lobes
    perception = Parser()
    formalizer = SpecBuilder()
    planner = HTNPlanner()
    # We use the Native Engine (simulated via Z3 interface wrapper for now or standard verifier)
    # The Code Gen path in Verifier needs to be robust. 
    # Let's check Z3Verifier implementation first.
    verifier = Z3Verifier() 
    learner = EpisodeLogger()
    synthesizer = EnumerativeSynthesizer(learner=learner)

    orchestrator = HNSDSOrchestrator(perception, formalizer, planner, synthesizer, verifier, learner)

    # 2. The User's Request
    user_input = "write code for addition of 2 numbers"
    print(f"User Input: '{user_input}'\n")

    # 3. Run the "Thinking" Loop
    print("--- STARTING COGNITIVE PROCESS ---")
    result = orchestrator.run(user_input)
    print("--- PROCESS FINISHED ---\
")

    if result:
        print(">>> GENERATED SOLUTION:")
        print(result)
    else:
        print(">>> FAILED to generate solution.")

if __name__ == "__main__":
    main()
