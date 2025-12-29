import os
import logging
import json
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class GenerativeSynthesizer:
    """
    The 'Neural' Lobe of the brain.
    Now connected to Real Intelligence via Google Gemini API.
    """
    def __init__(self, model_name="gemini-1.5-flash"):
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.logger = logging.getLogger("HNSDS")
        
        if self.api_key and HAS_GENAI:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
            self.logger.info(f"Connected to Real Intelligence: {model_name}")
        else:
            self.model = None
            if not HAS_GENAI:
                self.logger.warning("Library 'google-generativeai' not found.")
            if not self.api_key:
                self.logger.warning("No GEMINI_API_KEY found in environment.")

    def propose(self, goal, examples):
        """
        Generates a candidate solution using the Real AI Model.
        """
        # 1. Check for Real Intelligence
        if not self.model:
            return self._fallback_response(goal)

        # 2. Construct the Prompt
        prompt = self._construct_prompt(goal, examples)
        
        # 3. Call the Real Model
        try:
            response = self.model.generate_content(prompt)
            candidate = self._clean_response(response.text)
            return candidate
        except Exception as e:
            self.logger.error(f"AI Model Error: {e}")
            return "def solve(): return 'Error: AI Connection Failed'"

    def _construct_prompt(self, goal, examples):
        # Specific instructions to ensure the model acts as a Symbolic Generator
        base_instruction = """
        You are the 'Synthesizer Lobe' of a Neuro-Symbolic AI. 
        Your job is to generate a SINGLE, PRECISE candidate solution for a formal verifier.
        
        RULES:
        1. Return ONLY the code or logic. NO markdown, NO explanations.
        2. If the request is for Python code, write a complete function `def solve(...)`.
        3. If the request is for a Proof, write a Z3 (Python `z3-solver`) script that sets up the variables and constraints.
        4. If the request is for Analysis, provide a structured summary.
        """

        goal_desc = goal.get('description') or goal.get('equation') or str(goal)
        goal_type = goal.get('type')

        prompt = f"{base_instruction}\n\nCURRENT GOAL ({goal_type}): {goal_desc}\n"
        
        if goal_type == "proof":
            prompt += "\nOUTPUT FORMAT: A python script using 'z3'. Assume 'from z3 import *' is already done. Use 's = Solver()'. To prove a theorem, add the NEGATION of the theorem to the solver (Proof by Contradiction).\n"
        elif goal_type == "coding":
            prompt += "\nOUTPUT FORMAT: Valid Python function named 'solve'.\n"

        if examples:
            prompt += "\nAVOID THESE PREVIOUSLY FAILED CANDIDATES (Counterexamples):\n"
            for ex in examples:
                prompt += f"- {ex}\n"
        
        return prompt

    def _clean_response(self, text):
        # Remove markdown code blocks if the model adds them
        text = text.replace("```python", "").replace("```", "").strip()
        return text

    def _fallback_response(self, goal):
        """
        Deterministic Mock for Demo (Simulates Neural Extraction)
        """
        desc = str(goal).lower()
        
        # Simulate Formalization (JSON Output)
        if "formalization" in desc or "extract" in desc:
            if "velocity" in desc or "meters" in desc:
                return json.dumps({
                    "type": "math",
                    "equations": ["v == 100 / 5"],
                    "variables": ["v"]
                })
            if "fibonacci" in desc:
                return json.dumps({
                    "type": "coding",
                    "description": "fibonacci function"
                })
            return json.dumps({"type": "conversational", "response": "I understand your request."})

        # Simulate Classification
        if "classify" in desc:
            if any(w in desc for w in ["velocity", "solve", "math", "find"]):
                return "ANALYTICAL"
            if "fibonacci" in desc or "code" in desc:
                return "ANALYTICAL"
            return "CONVERSATIONAL"

        # Simulate Code/Solution Generation
        if isinstance(goal, dict):
            if goal.get("type") == "math":
                # Extract equation and solve simply
                return "v=20.0"
            if goal.get("type") == "coding":
                return "def solve(n):\n    if n <= 1: return n\n    return solve(n-1) + solve(n-2)"

        return """
# SYSTEM OFFLINE
# Real AI Model connection failed.
"""


    def compose(self, solutions):
        return "\n".join(str(s) for s in solutions)