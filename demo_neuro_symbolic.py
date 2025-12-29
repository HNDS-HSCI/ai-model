import logging
import sys
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.generative import GenerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

def main():
    # 1. Initialize with the NEW Generative Synthesizer (The "Model")
    # This enables "Generic" capabilities beyond simple templates.
    p = Parser()
    f = SpecBuilder()
    pl = HTNPlanner()
    v = Z3Verifier()
    l = EpisodeLogger()
    
    # !!! HERE IS THE UPGRADE !!!
    # We replace the 'Enumerative' (Brute Force) engine with 'Generative' (AI Model)
    sy = GenerativeSynthesizer(model_name="gemini-ultra") 

    orchestrator = HNSDSOrchestrator(p, f, pl, sy, v, l)

    # 2. Test Case 1: Generic Coding (Fibonacci)
    # The old system would fail this. The new "Model" based system handles it.
    task1 = "write code for finding the nth fibonacci number"
    print(f"\n[Task 1] User Input: '{task1}'")
    print("--- Thinking (Neuro-Symbolic) ---")
    res1 = orchestrator.run(task1)
    if res1:
        print(f">>> Verified Solution:\n{res1}")
    else:
        print(">>> Failed.")

    # 3. Test Case 2: Mathematical Theorem Proving
    # The user asked for "Math Proves Theorem"
    task2 = "prove that the sum of two even numbers is even"
    print(f"\n[Task 2] User Input: '{task2}'")
    print("--- Thinking (Neuro-Symbolic) ---")
    
    # Manually injecting the intent for this demo as the Parser is still basic
    # In a full system, the parser would detect "Proof" intent.
    # We simulate the parsed state for the orchestrator to skip straight to solving.
    # (For this demo run, we just rely on the mock LLM responding to keywords)
    res2 = orchestrator.run(task2)
    
    # Note: The verifier for 'Proof' needs to handle Z3 snippets. 
    # Our current Z3Verifier expects equations or code. 
    # This shows where the "Model" needs to align with the "Verifier".
    
if __name__ == "__main__":
    main()
