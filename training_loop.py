import logging
import sys
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def train():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    brain = HyperSymbolicBrain()
    
    print("--- STARTING NATIVE TRAINING LOOP ---")
    
    # Episode 1: Math Discovery
    # The brain sees 'calculate' which it doesn't know well yet
    print("\n[STIMULUS] 'calculate x + 2 = 5'")
    res1 = brain.process("calculate x + 2 = 5")
    print(f"Result: {res1}")
    
    # Episode 2: Reinforcement check
    # Now it should be more confident about 'calculate' being 'math'
    print("\n[STIMULUS] 'calculate y - 10 = 0'")
    # We simulate a slightly different wording
    res2 = brain.process("calculate y - 10 = 0")
    print(f"Result: {res2}")

    # Check the learned weights
    print("\n--- LEARNED SYNAPTIC WEIGHTS (GROWTH) ---")
    calc_weights = brain.neural_lobe.features.get("calculate", {})
    print(f"Weights for 'calculate': {calc_weights}")


    print("\n[STATUS] The system is now running entirely on its own weights and native logic.")

if __name__ == "__main__":
    train()
