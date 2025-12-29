import logging
import sys
import os
import shutil
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("TestParadigm")

def setup_fresh_environment():
    """Clears past memories to start fresh."""
    if os.path.exists("episodes.jsonl"):
        os.remove("episodes.jsonl")
    if os.path.exists("hnsds/learner/primordial_knowledge.jsonl"):
        # We keep primordial knowledge if it exists, but for this test we want a clean slate
        # effectively simulating a 'newborn' brain for this specific test case.
        # But let's just clear the runtime episodes.
        pass

def test_learning_loop():
    setup_fresh_environment()
    
    # Initialize components
    p = Parser()
    f = SpecBuilder()
    pl = HTNPlanner()
    v = Z3Verifier()
    l = EpisodeLogger() # Learner
    sy = EnumerativeSynthesizer(learner=l)

    # Initialize orchestrator with Learner
    orchestrator = HNSDSOrchestrator(p, f, pl, sy, v, l)

    print("\n\n=== PHASE 1: FIRST ENCOUNTER (Learning) ===")
    prompt_1 = "calculate sum of 5 and 3"
    print(f"User: {prompt_1}")
    
    # Run the system
    result_1 = orchestrator.run(prompt_1, budget=100)
    print(f"System: {result_1}")
    
    # Verify it solved it
    if not result_1:
        print("❌ Phase 1 Failed: System could not solve the initial problem.")
        return

    # Check the Mental Model Trace
    trace_1 = orchestrator.write_solution()
    if "COGNITIVE_MODE: RECALLING" in trace_1:
        print("⚠️ Warning: System recalled something in Phase 1 (unexpected for fresh run).")
    else:
        print("✅ System used 'Instinct' (Analytical/Creative Mode) as expected.")

    print("\n\n=== PHASE 2: SECOND ENCOUNTER (Recalling) ===")
    prompt_2 = "calculate sum of 10 and 20" # Different words, same concept
    print(f"User: {prompt_2}")
    
    # Run the system again
    result_2 = orchestrator.run(prompt_2, budget=100)
    print(f"System: {result_2}")

    # Verify it solved it
    if not result_2:
        print("❌ Phase 2 Failed: System could not solve the second problem.")
        return

    # CRITICAL CHECK: Did it use memory?
    trace_2 = orchestrator.write_solution()
    print("\n--- Phase 2 Mental Trace ---")
    print(trace_2)
    
    if "COGNITIVE_MODE: RECALLING" in trace_2:
        print("\n✅ SUCCESS: The Mental Model successfully entered 'RECALLING' mode.")
        print("The system identified the similarity to the previous episode and adapted its strategy.")
    else:
        print("\n❌ FAILURE: The Mental Model did NOT enter 'RECALLING' mode.")
        print("It likely treated this as a brand new problem, ignoring its past experience.")

if __name__ == "__main__":
    test_learning_loop()
