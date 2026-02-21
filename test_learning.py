from hnsds.brain.lobes.native_neural_lobe import NativeNeuralLobe

def verify_learning():
    lobe = NativeNeuralLobe()
    
    # Test sentences NOT in the training data
    test_cases = [
        "Construct a new algorithm for prime numbers", 
        "What is the total of fifty and twenty",       
        "Good evening to you"                          
    ]
    
    print("\n--- NEURAL INFERENCE TEST (After Training) ---")
    for test in test_cases:
        sigma = lobe.classify_and_formalize(test)
        # Handle the fact that sigma returns 'type' as lowercase string usually
        intent_type = str(sigma.get("type", "unknown")).upper()
        confidence = sigma.get("confidence", 0.0)
        print(f"Input: '{test}'")
        print(f"Classification: {intent_type} (Confidence: {confidence:.4f})")
        print("-" * 30)

if __name__ == "__main__":
    verify_learning()