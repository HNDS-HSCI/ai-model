import logging
import sys
import os
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def test_cognitive_architecture():
    # Fresh state
    for f in ["episodes.jsonl", "cognitive_weights.json", "cognitive_frames.json", "synaptic_core.json"]:
        if os.path.exists(f): os.remove(f)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s - %(message)s", stream=sys.stdout
    )

    print("=== INITIALIZING NEW COGNITIVE ARCHITECTURE ===")
    brain = HyperSymbolicBrain()

    print("\n=== TEST 1: WHOLE PARAGRAPH PROCESSING ===")
    paragraph = "There are 3 houses. The Brit is in the red house. The Swede is in house 3. The red house is next to house 2."
    result = brain.process(paragraph)
    print(f"Result:\n{result}")
    
    print("\n=== TEST 2: WHOLE CODE BLOCK PROCESSING ===")
    code_block = '''
def calculate_area(length, width):
    area = length * width
    return area
    
# Can you write a python function to sum three numbers?
'''
    result = brain.process(code_block)
    print(f"Result:\n{result}")

    print("\n=== DELIBERATION TRACE (Mental Model) ===")
    print(brain.get_mind_state())

if __name__ == "__main__":
    test_cognitive_architecture()
