import logging
import sys
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def main():
    brain = HyperSymbolicBrain()
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Stimulus: Plain human language
    stimulus = "Find x where x plus 5 is 15"
    print(f"\nStimulus: {stimulus}")

    # Brain Processing
    solution = brain.process(stimulus)
    
    print(f"\nFinal Solution: {solution}")
    print("\n--- DELIBERATION REPORT ---")
    print(brain.get_mind_state())

if __name__ == "__main__":
    main()

