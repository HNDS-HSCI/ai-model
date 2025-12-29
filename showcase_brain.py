import logging
import sys
import os
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def main():
    # Configure logging to see the "Mind" in action
    logging.basicConfig(
        level=logging.INFO, 
        format="%(name)s: %(message)s", 
        stream=sys.stdout
    )
    
    # Initialize the Brain
    # This automatically loads weights and episodes
    brain = HyperSymbolicBrain()
    
    print("\n" + "="*50)
    print("HYPER-SYMBOLIC COGNITIVE INVENTION SHOWCASE")
    print("="*50)

    # TEST 1: Neural-Symbolic Perception (Unknown Input)
    # The brain hasn't been hardcoded for "velocity"
    print("\n[STIMULUS 1] Physics Problem (Neural Perception)")
    query1 = "A car travels 100 meters in 5 seconds. What is its velocity v?"
    result1 = brain.process(query1)
    print(f"\nRESULT: {result1}")
    print("\nCOGNITIVE TRACE:")
    print(brain.mind.get_trace())

    # TEST 2: Learning & Reinforcement
    # We verify that it reinforced the "ANALYTICAL" mode for this type of query
    print("\n" + "-"*30)
    print("\n[STIMULUS 2] Similar Problem (Reinforced Intuition)")
    query2 = "Distance is 50, time is 10, find velocity v."
    result2 = brain.process(query2)
    print(f"\nRESULT: {result2}")
    
    # TEST 3: Complex Context / Coding
    print("\n" + "-"*30)
    print("\n[STIMULUS 3] Algorithmic Intent")
    query3 = "Implement a fibonacci function in python"
    result3 = brain.process(query3)
    print(f"\nRESULT: {result3}")

    print("\n" + "="*50)
    print("SHOWCASE COMPLETE")
    print("="*50)

if __name__ == "__main__":
    main()
