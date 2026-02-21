import json
import os
import re
import math
import logging
from .native_cortex import NativeCortex
from .native_embedding import NativeEmbedding

logging.basicConfig(level=logging.DEBUG)


class NativeNeuralLobe:
    """
    INVENTION: Native Neural Perception & Synthesis.

    This module implements the 'Intuition' of the HSCI brain WITHOUT
    external LLMs. It uses a True Neural Network (NativeCortex) to
    classify intent via learned Synaptic Weights.
    """

    def __init__(self, weight_path="synaptic_core.json"):
        self.weight_path = weight_path
        self.logger = logging.getLogger("NativeNeuralLobe")

        # 1. The Semantic Layer (Text -> Numbers)
        self.embedding = NativeEmbedding(vocab_size=200)  # Input Size

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
        logic_keywords = [
            "lives in",
            "next to",
            "brit",
            "swede",
            "house",
            "puzzle",
            "neighbor",
        ]
        if any(kw in stim_low for kw in logic_keywords) and len(stim_low.split()) > 5:
            return {
                "type": "logic",
                "goal": "solve_csp",
                "raw": stimulus,
                "confidence": 0.99,
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
            equations = self._extract_equations(stim_low)
            spec = {
                "type": "math",
                "goal": "solve",
                "raw": stim_low,
                "confidence": confidence,
            }
            if len(equations) > 1:
                spec["type"] = "system"
                spec["equations"] = equations
                spec["variables"] = self._extract_variables(equations)
            elif len(equations) == 1:
                spec["equation"] = equations[0]
                spec["variables"] = self._extract_variables(equations)
            return spec

        if best_intent == "CODING":
            return {
                "type": "coding",
                "goal": "synthesize",
                "desc": stimulus,
                "confidence": confidence,
            }

        return {
            "type": "conversational",
            "response": f"I received: '{stimulus}'. My Neural Net classifies this as {best_intent} (Signal: {confidence:.4f}).",
            "confidence": confidence,
        }

    def grow(self, stimulus, successful_spec, intent):
        """
        Backpropagation: The Brain physically rewires itself based on success.
        """
        if not intent:
            return

        # 1. Vectorize Input
        input_vector = self.embedding.embed(stimulus)

        # 2. Create Target Signal (One-Hot Encoding)
        # e.g., if intent is CODING (idx 1) -> [0.0, 1.0, 0.0]
        target_vector = [0.0] * len(self.intents)
        try:
            target_idx = self.intents.index(intent.upper())
            target_vector[target_idx] = 1.0
        except ValueError:
            return  # Unknown intent

        # 3. Train (Backprop)
        loss = self.cortex.train(input_vector, target_vector)
        self.cortex.save_weights()

        # 4. Update synaptic weights JSON (PRINCIPLE 1 FIX)
        self._update_synaptic_json(stimulus, intent)
        self.logger.info(
            f"BRAIN_GREW: Updated weights for '{intent}' (Loss: {loss:.6f})"
        )

    def _update_synaptic_json(self, stimulus, intent):
        """
        Update the lightweight synaptic_core.json weights file.
        This is the 'intuition map' for quick pattern matching.
        PRINCIPLE 1 FIX: Persist Hebbian updates to enable future learning.
        """
        try:
            # Load current weights
            weights = {}
            if os.path.exists(self.weight_path):
                with open(self.weight_path, "r") as f:
                    weights = json.load(f)

            # Tokenize stimulus into n-grams and words
            words = stimulus.lower().split()
            bigrams = (
                [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
                if len(words) > 1
                else words
            )

            # Hebbian update: strengthen association with successful intent
            for token in bigrams + words:
                if token not in weights:
                    weights[token] = {}
                if intent not in weights[token]:
                    weights[token][intent] = 0.0

                # Successful path gets +0.1
                weights[token][intent] += 0.1

                # Decay competing intents
                for other_intent in self.intents:
                    if other_intent != intent and other_intent in weights[token]:
                        weights[token][other_intent] = max(
                            0, weights[token][other_intent] - 0.02
                        )

            # Save back
            with open(self.weight_path, "w") as f:
                json.dump(weights, f, indent=2)

            self.logger.debug(f"Synaptic weights persisted")

        except Exception as e:
            self.logger.error(f"Failed to update synaptic weights: {e}")

    def _extract_equations(self, text):
        # Heuristic: Find something that looks like an equation
        # Remove command words first
        clean_text = (
            text.replace("solve", "").replace("calculate", "").replace("equals", "=")
        )

        # Split by comma if present, else just look for patterns
        parts = clean_text.split(",") if "," in clean_text else [clean_text]
        equations = []

        for part in parts:
            # Look for pattern: LHS = RHS or LHS == RHS
            match = re.search(r"([a-z0-9\+\-\*\/\s]+={1,2}[\-a-z0-9\+\-\*\/\s]+)", part)
            if match:
                eq = match.group(1).strip()
                if "=" in eq and "==" not in eq:
                    eq = eq.replace("=", "==")
                equations.append(eq)
        return equations

    def _extract_variables(self, equations):
        vars_set = set()
        for eq in equations:
            # Find single letters that are likely variables
            found = re.findall(r"\b[a-z]\b", eq)
            vars_set.update(found)
        return list(vars_set)

    def _extract_equation(self, text):
        # Legacy single extractor wrapper
        eqs = self._extract_equations(text)
        return eqs[0] if eqs else ""

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
            if "==" not in eq_str:
                return "x=0"
            lhs, rhs = eq_str.split("==")

            # Simple heuristic solver
            # Assume form: x [op] A == B
            # Find the number in LHS
            nums = re.findall(r"\d+", lhs)
            if not nums:
                return "x=0"

            A = float(nums[0])
            B = float(rhs)

            # Inverse operations
            if "+" in lhs:
                val = B - A
            elif "-" in lhs:
                val = B + A
            elif "*" in lhs:
                val = B / A
            elif "/" in lhs:
                val = B * A
            else:
                val = 0

            return f"x={val}"
        except:
            return "x=0"
