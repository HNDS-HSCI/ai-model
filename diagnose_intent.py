
import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain
from hnsds.brain.lobes.native_graph import NativeGraph

def diagnose():
    print("--- HSCI INTENT DIAGNOSTIC ---")
    
    # 1. Check Graph directly
    graph = NativeGraph()
    solve_relations = graph.get_related("solve", "MAPS_TO_AXIOM")
    print(f"Graph 'solve' -> MAPS_TO_AXIOM: {solve_relations}")
    
    # 2. Check Brain perception
    brain = HyperSymbolicBrain()
    stimulus = "can you solve x+y = 10 and x-y = 20"
    env = brain.awareness_lobe.perceive_environment(stimulus)
    
    print(f"Entities: {env['entities']}")
    print(f"Intent: {env['intent']}")
    
    # 3. Check Deliberation
    deliberation = brain.awareness_lobe.deliberate(env)
    print(f"Axiom: {deliberation['axiom']}")
    print(f"Rationale: {deliberation['rationale']}")
    
    if deliberation['axiom'] == "REDUCTION":
        print("✅ SUCCESS: Intent correctly mapped to REDUCTION.")
    else:
        print("❌ FAILURE: Intent mapped to TRANSFORMATION.")

if __name__ == "__main__":
    diagnose()
