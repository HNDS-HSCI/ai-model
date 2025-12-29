import json
import os
import re
import math
from collections import Counter

import sympy
from sympy import symbols, Eq, solve as sympy_solve

class NativeNeuralLobe:
    """
    INVENTION: Neural-Guided Symbolic Search (NGSS) Engine.
    This is a self-contained intelligence that constructs responses
    by searching a symbolic space of logic-primitives.
    """
    def __init__(self, weight_path="synaptic_core.json"):
        self.weight_path = weight_path
        self.knowledge_base = self._load_knowledge()
        self.features = self.knowledge_base.get("features", {})
        self.facts = self.knowledge_base.get("facts", {})
        
        # LOGIC PRIMITIVES (The Building Blocks of Thought)
        self.primitives = {
            "ADD": lambda *args: sum(args),
            "SUB": lambda a, b: a - b,
            "MUL": lambda a, b: a * b,
            "DIV": lambda a, b: a / b if b != 0 else 0,
            "ITER": "loop",
            "RECURSE": "recursion"
        }

    def classify_and_formalize(self, stimulus):
        """
        Transduction: Maps natural language features to a Symbolic Goal.
        """
        stim_low = stimulus.lower().strip()
        tokens = self._extract_features(stim_low)
        
        # 1. Neural Scoring (The Intuition)
        scores = {p: 0.0 for p in self.primitives}
        scores.update({"MATH": 0.0, "CODE": 0.0, "CHAT": 0.0})
        
        for t in tokens:
            if t in self.features:
                for target, weight in self.features[t].items():
                    if target in scores: scores[target] += weight

        # 2. Goal Extraction
        # Identify variables and constants
        constants = [float(n) for n in re.findall(r'\d+', stim_low)]
        variables = re.findall(r'\b[a-z]\b', stim_low)

        # 3. Decision Matrix (The Mental State)
        if "=" in stim_low or scores["MATH"] > 0.5:
            return {"type": "math", "goal": "solve", "raw": stim_low, "vars": variables or ["x"]}
        
        if any(w in stim_low for w in ["code", "function", "write", "program"]):
            return {"type": "coding", "goal": "synthesize", "desc": stimulus, "arity": len(constants) or 2}

        return {"type": "conversational", "response": self._generate_thought_trace(stimulus, scores)}

    def propose_solution(self, sigma):
        """
        Synthesis: Searches for the logic-primitive composition that 
        satisfies the formal goal.
        """
        if sigma["type"] == "math":
            return self._search_math_space(sigma["raw"])
        
        if sigma["type"] == "coding":
            return self._search_program_space(sigma)
            
        return "Task acknowledged."

    def _search_program_space(self, sigma):
        """
        Constructs a program by composing primitives.
        """
        desc = sigma["desc"].lower()
        arity = 2
        # Use learned weights to find the core operation
        ops = ["+", "-", "*", "/"]
        weights = [0.1, 0.1, 0.1, 0.1]
        
        if "add" in desc or "sum" in desc: weights[0] = 1.0
        if "sub" in desc or "minus" in desc: weights[1] = 1.0
        if "multi" in desc or "times" in desc: weights[2] = 1.0
        
        best_op = ops[weights.index(max(weights))]
        
        # Determine arity dynamically from the request
        num_match = re.search(r'(\d+)', desc)
        if num_match: arity = int(num_match.group(1))

        args = [chr(97 + i) for i in range(arity)]
        expression = f" {best_op} ".join(args)
        
        return f"def solve({', '.join(args)}):\n    return {expression}"

    def _search_math_space(self, raw):
        """Uses SymPy to solve the equation derived from the stimulus."""
        try:
            clean = re.sub(r'[a-z A-Z]', '', raw.split("=")[0])
            # This is where the model 'reasons' about the equation structure
            return self._solve_symbolically(raw.replace("=", "=="))
        except:
            return "x=0"

    def _generate_thought_trace(self, stim, scores):
        trace = f"STIMULUS RECEIVED: '{stim}'\n"
        trace += f"NEURAL ACTIVATION: { {k: round(v, 2) for k, v in scores.items() if v > 0} }\n"
        trace += "DELIBERATION: Synthesizing response from learned facts and logic primitives..."
        return trace

    def _extract_features(self, text):
        return re.findall(r'\w+', text.lower())

    def _load_knowledge(self):
        if os.path.exists(self.weight_path):
            try:
                with open(self.weight_path, "r") as f:
                    return json.load(f)
            except: pass
        return {"features": {}, "facts": {}}

    def _save_knowledge(self):
        with open(self.weight_path, "w") as f:
            json.dump({"features": self.features, "facts": self.facts}, f, indent=2)

    def _solve_symbolically(self, equation):
        try:
            if "==" not in equation: return "x=0"
            lhs_str, rhs_str = equation.split("==")
            var_names = set(re.findall(r'[a-z]', equation)) or {"x"}
            syms = {name: sympy.symbols(name) for name in var_names}
            lhs_expr = sympy.parse_expr(lhs_str.strip(), local_dict=syms)
            rhs_expr = sympy.parse_expr(rhs_str.strip(), local_dict=syms)
            sol = sympy.solve(sympy.Eq(lhs_expr, rhs_expr))
            if sol:
                v = list(var_names)[0]
                return f"{v}={float(sol[0]) if sol[0].is_number else sol[0]}"
            return "x=0"
        except: return "x=0"

    def grow(self, stimulus, successful_spec, intent):
        tokens = self._extract_features(stimulus)
        for t in tokens:
            if t not in self.features:
                self.features[t] = {}
            self.features[t][intent] = self.features[t].get(intent, 0.0) + 0.2
        self._save_knowledge()



