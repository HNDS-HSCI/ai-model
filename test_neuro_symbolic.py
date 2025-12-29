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
logger = logging.getLogger("TestNeuroSymbolic")

def setup_fresh_brain():
    """Wipes the Brain's memory (Episodes and Synaptic Weights)."""
    if os.path.exists("episodes.jsonl"):
        os.remove("episodes.jsonl")
    if os.path.exists("cognitive_weights.json"):
        os.remove("cognitive_weights.json")

def test_neuro_symbolic_learning():
    setup_fresh_brain()
    
    # Initialize components
    p = Parser()
    f = SpecBuilder()
    pl = HTNPlanner()
    v = Z3Verifier()
    l = EpisodeLogger()
    sy = EnumerativeSynthesizer(learner=l)

    # Initialize orchestrator
    orchestrator = HNSDSOrchestrator(p, f, pl, sy, v, l)

    print("\n\n=== PHASE 1: TABULA RASA (The 'Dumb' Brain) ===")
    print("Goal: The Brain does NOT know what 'compute' means. It has NO hardcoded keywords.")
    
    prompt_1 = "compute result of 5 plus 5"
    print(f"User: {prompt_1}")
    
    # Run the system
    result_1 = orchestrator.run(prompt_1, budget=100)
    
    # Check Trace 1
    trace_1 = orchestrator.write_solution()
    print("\n--- Phase 1 Trace ---")
    print(trace_1)
    print(f"DEBUG: result_1 = {result_1}")
    
    if "COGNITIVE_MODE: CONFUSED" in trace_1:
        print("✅ SUCCESS: The Brain was initially CONFUSED (as expected).")
        print("It had to EXPLORE to find the solution.")
    else:
        print("⚠️ Warning: The Brain claimed to know what 'compute' means (unexpected).")

    if result_1:
         print("✅ SUCCESS: The Brain solved it despite being confused.")
    
    # CLEAR SHORT-TERM MEMORY (Trace) TO ISOLATE PHASE 2
    orchestrator.mind.memory_trace = []

    print("\n\n=== PHASE 2: SYNAPTIC PLASTICITY (The 'Learned' Brain) ===")
    print("Goal: The Brain should now intuitively know that 'compute' -> ANALYTICAL mode.")
    
    prompt_2 = "compute result of 10 minus 2" 
    # Note: 'minus' might be new, but 'compute' and 'result' are now weighted.
    print(f"User: {prompt_2}")
    
    # Run the system again
    result_2 = orchestrator.run(prompt_2, budget=100)
    
    # Check Trace 2
    trace_2 = orchestrator.write_solution()
    print("\n--- Phase 2 Trace ---")
    print(trace_2)
    
    if "COGNITIVE_MODE: ANALYTICAL" in trace_2 and "CONFUSED" not in trace_2:
        print("\n✅ SUCCESS: The Brain entered ANALYTICAL mode immediately!")
        print("It used its learned Synaptic Weights to route 'compute' -> Analytical Lobe.")
    elif "RECALLING" in trace_2:
        print("\n⚠️ Note: It used Episodic Memory (Recall) instead of Synaptic Weights.")
        print("This is also valid intelligence, but we wanted to test the Weight Classification.")
    else:
        print("\n❌ FAILURE: The Brain was still CONFUSED.")

if __name__ == "__main__":
    test_neuro_symbolic_learning()
