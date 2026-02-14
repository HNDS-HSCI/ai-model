from hnsds.brain.lobes.native_neural_lobe import NativeNeuralLobe
import random

def train_brain():
    print("Initializing Native Neural Brain...")
    # Delete old weights to start fresh
    import os
    if os.path.exists("synaptic_core.json"):
        os.remove("synaptic_core.json")
        
    lobe = NativeNeuralLobe()
    
    # Enhanced Training Data
    # Repeating crucial patterns to force learning
    training_data = [
        # MATH (Goal: 1, 0, 0)
        ("solve x + 10 = 20", "MATH"),
        ("calculate the sum of 5 and 5", "MATH"),
        ("what is 100 divided by 10", "MATH"),
        ("solve y - 5 = 0", "MATH"),
        ("math problem", "MATH"),
        ("compute the result", "MATH"),
        ("add two numbers", "MATH"),
        ("multiply 5 by 5", "MATH"),
        
        # CODING (Goal: 0, 1, 0)
        ("write a python function to add numbers", "CODING"),
        ("code a fibonacci sequence", "CODING"),
        ("write a sort function", "CODING"),
        ("create a python script", "CODING"),
        ("implement a loop", "CODING"),
        ("program a solution", "CODING"),
        ("def function", "CODING"),
        ("generate code", "CODING"),
        
        # HR / Business Logic (CODING)
        ("calculate wages", "CODING"),
        ("payroll system", "CODING"),
        ("filter employees", "CODING"),
        ("staff management", "CODING"),
        ("salary computation", "CODING"),
        ("hiring process", "CODING"),
        
        # CONVERSATIONAL (Goal: 0, 0, 1)
        ("hello how are you", "CONVERSATIONAL"),
        ("who are you", "CONVERSATIONAL"),
        ("explain yourself", "CONVERSATIONAL"),
        ("good morning", "CONVERSATIONAL"),
        ("hi there", "CONVERSATIONAL"),
        ("what is your name", "CONVERSATIONAL"),
        ("tell me a joke", "CONVERSATIONAL")
    ]
    
    print(f"Training on {len(training_data)} samples...")
    
    # Train for more epochs
    lobe.cortex.learning_rate = 0.5 # Boost learning rate for faster convergence
    
    for epoch in range(200):
        total_loss = 0
        random.shuffle(training_data) # Shuffle to prevent pattern memorization
        for text, intent in training_data:
            # Manually train via grow/cortex
            # grow() embeds and calls train()
            lobe.grow(text, None, intent)
            
    print("Neural Weights Optimized and Saved.")

if __name__ == "__main__":
    train_brain()
