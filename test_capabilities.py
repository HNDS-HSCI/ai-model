import logging
import sys
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.generative import GenerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger

# Quiet logging for clearer demo output
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

def main():
    # Setup System
    orchestrator = HNSDSOrchestrator(
        Parser(), SpecBuilder(), HTNPlanner(), 
        GenerativeSynthesizer(model_name="gemini-ultra"), 
        Z3Verifier(), EpisodeLogger()
    )

    print("\n=== SYSTEM CAPABILITY TEST ===")
    print("Demonstrating how the system handles different types of 'Correctness'.\n")

    # TEST 1: Math (Must be 100% Proven)
    q1 = "Prove that sum of two even numbers is even"
    print(f"INPUT 1: '{q1}'")
    print("EXPECTATION: Deterministic Proof")
    res1 = orchestrator.run(q1)
    if res1: print(f"OUTPUT: Theorem Holds. (Proven)\n")

    # TEST 2: General Knowledge (Cannot be Proven, only Answered)
    q2 = "Why is the sky blue?"
    print(f"INPUT 2: '{q2}'")
    print("EXPECTATION: Best-Effort Explanation")
    # This will trigger the fallback in our mock model
    res2 = orchestrator.run(q2)
    if res2: print(f"OUTPUT: {res2}\n")

if __name__ == "__main__":
    main()
