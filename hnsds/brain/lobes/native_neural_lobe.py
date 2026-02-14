import json
import os
import re
import math
from .native_cortex import NativeCortex
from .native_embedding import NativeEmbedding

class NativeNeuralLobe:
    """
    INVENTION: Native Neural Perception & Synthesis.
    
    This module implements the 'Intuition' of the HSCI brain WITHOUT
    external LLMs. It uses a True Neural Network (NativeCortex) to
    classify intent via learned Synaptic Weights.
    """
    def __init__(self, weight_path="synaptic_core.json"):
        self.weight_path = weight_path
        
        # 1. The Semantic Layer (Text -> Numbers)
        self.embedding = NativeEmbedding(vocab_size=200) # Input Size
        
        # 2. The Synaptic Core (The Neural Network)
        # Input: 200 dim vector, Hidden: 20 neurons, Output: 3 classes (MATH, CODING, CONV)
        self.cortex = NativeCortex(input_size=200, hidden_size=20, output_size=3)
        
        self.intents = ["MATH", "CODING", "CONVERSATIONAL"]

    def classify_and_formalize(self, stimulus):
        """
        Transduction: Maps natural language features to a Symbolic Goal.
        Mechanism: Neural Forward Pass + Logic Heuristics.
        """
        stim_low = stimulus.lower().strip()
        
        # 0. Heuristic: Logic Puzzle Detection
        # (This bypasses the small neural net for specific complex tasks)
        logic_keywords = ["lives in", "next to", "brit", "swede", "house", "puzzle", "neighbor"]
        if any(kw in stim_low for kw in logic_keywords) and len(stim_low.split()) > 5:
            return {
                "type": "logic",
                "goal": "solve_csp",
                "raw": stimulus,
                "confidence": 0.99
            }
        
        # 1. Vectorize
        input_vector = self.embedding.embed(stim_low)
        
        # 2. Neural Thinking (Forward Pass)
        output_signal = self.cortex.forward(input_vector)
        
        # 3. Interpret Signal (Argmax)
        best_idx = output_signal.index(max(output_signal))
        best_intent = self.intents[best_idx]
        confidence = output_signal[best_idx]
        
        # 4. Extract Specification based on best intent
        if best_intent == "MATH":
            return {
                "type": "math", 
                "goal": "solve", 
                "raw": stim_low,
                "equation": self._extract_equation(stim_low),
                "confidence": confidence
            }
        
        if best_intent == "CODING":
            return {
                "type": "coding", 
                "goal": "synthesize", 
                "desc": stimulus,
                "confidence": confidence
            }

        return {
            "type": "conversational", 
            "response": f"I received: '{stimulus}'. My Neural Net classifies this as {best_intent} (Signal: {confidence:.4f}).",
            "confidence": confidence
        }

    def grow(self, stimulus, successful_spec, intent):
        """
        Backpropagation: The Brain physically rewires itself based on success.
        """
        if not intent: return
        
        # 1. Vectorize Input
        input_vector = self.embedding.embed(stimulus)
        
        # 2. Create Target Signal (One-Hot Encoding)
        # e.g., if intent is CODING (idx 1) -> [0.0, 1.0, 0.0]
        target_vector = [0.0] * len(self.intents)
        try:
            target_idx = self.intents.index(intent.upper())
            target_vector[target_idx] = 1.0
        except ValueError:
            return # Unknown intent

        # 3. Train (Backprop)
        loss = self.cortex.train(input_vector, target_vector)
        self.cortex.save_weights()
        # print(f"DEBUG: Brain Learned. Loss: {loss:.6f}")

    def _extract_equation(self, text):
        # Heuristic: Find something that looks like an equation
        # Remove command words first
        clean_text = text.replace("solve", "").replace("calculate", "").replace("equals", "=")
        
        # Extract potential equation part
        # Look for pattern: LHS = RHS or LHS == RHS
        match = re.search(r'([a-z0-9\+\-\*\/\s]+={1,2}[a-z0-9\+\-\*\/\s]+)', clean_text)
        if match:
            eq = match.group(1).replace(" ", "")
            if "=" in eq and "==" not in eq:
                eq = eq.replace("=", "==")
            return eq
        return ""
    
    # Primitives map remains for the symbolic engine usage if needed, 
    # though usually handled by Prover.
    def propose_solution(self, sigma):
        """
        Synthesis: Deterministic search for a candidate solution.
        Acts as the 'Intuition' proposing a candidate for the Verifier.
        """
        if sigma.get("type") == "math":
            eq = sigma.get("equation", "")
            return self._solve_native_math(eq)
        
        # Fallback for coding if the Planner didn't generate one in MentalModel
        if sigma.get("type") == "coding":
            return "def solve(): pass"

        return "x=0"

    def _solve_native_math(self, eq_str):
        # Very simple solver for x + A == B types
        # This acts as the 'Neural Intuition' proposing a candidate for the Verifier
        try:
            if "==" not in eq_str: return "x=0"
            lhs, rhs = eq_str.split("==")
            
            # Simple heuristic solver
            # Assume form: x [op] A == B
            # Find the number in LHS
            nums = re.findall(r'\d+', lhs)
            if not nums: return "x=0"
            
            A = float(nums[0])
            B = float(rhs)
            
            # Inverse operations
            if "+" in lhs: val = B - A
            elif "-" in lhs: val = B + A
            elif "*" in lhs: val = B / A
            elif "/" in lhs: val = B * A
            else: val = 0
            
            return f"x={val}" 
        except:
            return "x=0"





