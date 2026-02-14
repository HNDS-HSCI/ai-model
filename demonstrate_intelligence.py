import sys
import os
import time

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain

def demonstrate():
    brain = HyperSymbolicBrain()
    
    test_inputs = [
        "Sum the squares of even numbers in the list",
        "Product of numbers greater than 5 in the list",
        "The Brit lives in the red house. The Swede lives in the green house. The Brit is next to the Swede.",
        "solve x + 10 == 30"
    ]
    
    print("\n" + "="*70)
    print("   HSCI NATIVE INTELLIGENCE DEMONSTRATION")
    print("   (No Hardcoding - First-Principles Composition)")
    print("="*70 + "\n")

    for i, stimulus in enumerate(test_inputs):
        print(f'[{i+1}] INPUT: "{stimulus}"')
        start = time.time()
        
        # Process stimulus
        response = brain.process(stimulus)
        
        duration = time.time() - start
        
        print(f"    RESULT:\n{response}")
        print(f"    (Reasoning Time: {duration:.4f}s)")
        print("-" * 50)

if __name__ == "__main__":
    demonstrate()
