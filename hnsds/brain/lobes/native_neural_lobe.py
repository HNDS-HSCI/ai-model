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
        self.logger.info(f"CLASSIFYING: '{stim_low}'")

        # 0. Heuristic: Logic Puzzle Detection
        # ... (logic puzzle keywords)
        
        # 0.1 Heuristic: Coding Detection
        coding_keywords = ["function", "program", "write a script", "python script", "code for"]
        if any(kw in stim_low for kw in coding_keywords):
            return {
                "type": "coding",
                "goal": "synthesize",
                "desc": stimulus,
                "confidence": 0.95,
            }

        # 0.2 Heuristic: Multi-Equation (System) Detection
        # Count '=' more robustly
        total_equals = stim_low.count("=")
        if total_equals >= 2:
            equations = self._extract_equations(stim_low)
            self.logger.info(f"MULTI_EQ_HEURISTIC: found {len(equations)} equations from {total_equals} '=' marks")
            if len(equations) >= 2:
                spec = {
                    "type": "system",
                    "goal": "solve",
                    "equations": equations,
                    "variables": self._extract_variables(equations),
                    "raw": stimulus,
                    "confidence": 0.99
                }
                self.logger.info(f"SYSTEM_DETECTED: {spec}")
                return spec

        # 0.3 Heuristic: Simple Arithmetic (No variables)
        if re.match(r"^[\d\s\+\-\*\/\(\)\.]+$", stim_low):
            try:
                res_eval = eval(stim_low) if all(c in '0123456789+-*/(). ' for c in stim_low) else 0
                self.logger.info(f"ARITHMETIC_DETECTED: {stim_low} == {res_eval}")
                return {
                    "type": "math",
                    "goal": "solve",
                    "equation": f"{stim_low} == {res_eval}",
                    "variables": [],
                    "confidence": 0.99
                }
            except:
                pass

        # 0.4 Heuristic: Single Equation with Variables
        if "=" in stim_low and stim_low.count("=") == 1:
            equations = self._extract_equations(stim_low)
            if equations:
                spec = {
                    "type": "math",
                    "goal": "solve",
                    "equation": equations[0],
                    "variables": self._extract_variables(equations),
                    "raw": stimulus,
                    "confidence": 0.99
                }
                self.logger.info(f"SINGLE_EQ_DETECTED: {spec}")
                return spec

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
        ).strip()

        # Split into tokens first to avoid greedy regex issues
        # Standardize = 
        clean_text = re.sub(r"\s*=\s*", "=", clean_text)
        # Tokenize by space
        tokens = clean_text.split()
        
        final_equations = []
        for t in tokens:
            if "=" in t:
                # Basic equation token found like "x+y=10"
                eq = t.replace("=", " == ")
                if "==" in eq:
                    final_equations.append(eq)
            else:
                # If token doesn't have =, it might be part of an equation split by spaces
                # e.g. "x + y = 10" -> ["x", "+", "y", "=", "10"]
                # For now, let's assume equations are unified tokens or comma-separated
                pass
        
        # Fallback for space-separated like "x + y = 10"
        if not final_equations:
             # Look for pattern: something = something
             matches = re.findall(r"([a-z0-9\+\-\*\/\s\(\)\.]+\s*={1,2}\s*[\-a-z0-9\s\(\)\.]+)", text)
             for m in matches:
                 m = m.strip()
                 # If match has multiple =, split it non-greedily
                 if m.count("=") > 1 and "==" not in m:
                      # Split where a number is followed by a variable start
                      parts = re.split(r"(?<=\d)\s+(?=[a-z])", m)
                      for p in parts:
                          eq = p.strip().replace("=", " == ").replace(" ==  == ", " == ")
                          if "==" in eq: final_equations.append(eq)
                 else:
                      eq = m.strip().replace("=", " == ").replace(" ==  == ", " == ")
                      if "==" in eq: final_equations.append(eq)

        return final_equations

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
        self.logger.info(f"PROPOSE_SOLUTION: sigma={sigma}")
        if sigma.get("type") in ["math", "system"]:
            if sigma.get("type") == "system":
                # For systems, we can't use the simple _solve_native_math.
                # Use a simple Z3-based proposal for the verifier to check.
                return self._solve_system_candidate(sigma)

            eq = sigma.get("equation", "")
            if "==" in eq and not sigma.get("variables"):
                # Constant math like "1+1 == 2.0" -> candidate "result=2.0"
                lhs, rhs = eq.split("==")
                res = f"result={rhs.strip()}"
                self.logger.info(f"PROPOSED_CONSTANT_MATH: {res}")
                return res
            
            res = self._solve_native_math(eq)
            self.logger.info(f"PROPOSED_VARIABLE_MATH: {res}")
            return res

        # Fallback for coding if the Planner didn't generate one in MentalModel
        if sigma.get("type") == "coding":
            return "def solve(): pass"

        return "x=0"

    def _solve_native_math(self, eq_str):
        # ... (existing code)
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

    def _solve_system_candidate(self, goal):
        """
        Uses Symbolic Reasoning (Z3) to find a candidate solution for multi-variable systems.
        """
        from z3 import Solver, Int, sat

        try:
            s = Solver()
            var_names = goal.get("variables", ["x", "y"])
            z3_vars = {name: Int(name) for name in var_names}
            
            equations = goal.get("equations", [])
            for eq_str in equations:
                if not eq_str: continue
                try:
                    # Parse "x + y == 10" into Z3 constraint
                    z3_eq = eval(eq_str, {"__builtins__": None}, z3_vars)
                    s.add(z3_eq)
                except Exception as e:
                    self.logger.warning(f"Failed to parse equation '{eq_str}': {e}")
                    
            if s.check() == sat:
                m = s.model()
                solution_parts = []
                for name in var_names:
                    val = m[z3_vars[name]]
                    solution_parts.append(f"{name}={val}")
                return ", ".join(solution_parts)
            else:
                return "x=0, y=0"
        except Exception as e:
            return f"x=0, y=0 # ERROR: {e}"
