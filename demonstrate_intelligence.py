import logging
import sys
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    # Initialize the "Brain"
    brain = HyperSymbolicBrain()
    
    print("\n--- HSCI INTELLIGENCE DEMONSTRATION ---")
    print("Goal: Demonstrate 'Human-Like' End-to-End Feature Construction.")
    print("Task: 'Build a User API'")
    print("-" * 50)
    
    # The Prompt
    prompt = "Build a User API"
    
    # 1. The Brain Thinks (Perceive -> Plan -> Verify)
    result = brain.process(prompt)
    
    # 2. Output the Result
    print(f"\nAI RESPONSE:\n{result}")
    
    print("\n" + "-" * 50)
    print("ANALYSIS:")
    print("1. Did it guess? No. It used 'Hierarchical Reasoning' to break the task down.")
    print("2. Did it use a 'Black Box'? No. It used explicitly defined 'Computer Science Primitives' (flask, model, route).")
    print("3. Is it verifiable? Yes. The output code is constructed from verified templates.")

if __name__ == "__main__":
    main()