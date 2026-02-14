import json
import math
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.lobes.native_cortex import NativeCortex
from hnsds.brain.lobes.native_embedding import NativeEmbedding

def inspect_brain(stimulus):
    print(f"\n=== BRAIN INSPECTION: '{stimulus}' ===")
    
    # 1. Load the Brain Components
    embedding = NativeEmbedding(vocab_size=200)
    cortex = NativeCortex(input_size=200, hidden_size=20, output_size=3)
    
    # 2. Vectorize Input (The "Sensory Signal")
    input_vector = embedding.embed(stimulus)
    print(f"\n[1] SENSORY INPUT (Vectorized):")
    # Show non-zero active neurons in the input layer
    active_inputs = [i for i, x in enumerate(input_vector) if x > 0]
    print(f"    Active Input Neurons: {active_inputs}")
    
    # 3. Forward Pass Layer 1 (Hidden Layer Analysis)
    # Replicating the logic from NativeCortex.forward to inspect intermediate states
    # Z1 = Sigmoid(Input @ W1 + B1)
    
    hidden_activations = []
    w1 = cortex.W1
    b1 = cortex.B1
    
    for j in range(cortex.hidden_size):
        activation = 0
        for k in range(cortex.input_size):
            activation += input_vector[k] * w1[k][j]
        activation += b1[0][j]
        
        # Apply Sigmoid
        sigmoid_val = 1.0 / (1.0 + math.exp(-activation))
        hidden_activations.append(sigmoid_val)
        
    print(f"\n[2] HIDDEN LAYER ACTIVITY (The 'Subconscious'):")
    print("    (Neurons firing above 0.5 are 'active')")
    
    fired_neurons = []
    for i, val in enumerate(hidden_activations):
        bar = "#" * int(val * 10)
        if val > 0.5:
            fired_neurons.append(i)
            print(f"    Neuron {i:02d}: [{bar:<10}] {val:.4f} <--- FIRING")
        else:
            print(f"    Neuron {i:02d}: [{bar:<10}] {val:.4f}")
            
    if not fired_neurons:
        print("    (No strong reaction in hidden layer - Brain is unsure or input is novel)")

    # 4. Forward Pass Layer 2 (Output Layer Analysis)
    # Z2 = Sigmoid(Hidden @ W2 + B2)
    output_activations = []
    w2 = cortex.W2
    b2 = cortex.B2
    
    intents = ["MATH", "CODING", "CONVERSATIONAL"]
    
    print(f"\n[3] OUTPUT SIGNAL (The 'Conscious Decision'):")
    for j in range(cortex.output_size):
        activation = 0
        for k in range(cortex.hidden_size):
            activation += hidden_activations[k] * w2[k][j]
        activation += b2[0][j]
        
        sigmoid_val = 1.0 / (1.0 + math.exp(-activation))
        output_activations.append(sigmoid_val)
        
        intent = intents[j]
        bar = "#" * int(sigmoid_val * 20)
        print(f"    {intent:<15}: [{bar:<20}] {sigmoid_val:.4f}")

    # Decision
    best_idx = output_activations.index(max(output_activations))
    print(f"\n>>> FINAL DECISION: {intents[best_idx]}")
    print("    (This decision directs the Planner to the correct memory bank)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_brain(sys.argv[1])
    else:
        inspect_brain("calculate the sum")