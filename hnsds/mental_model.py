import re
import json
import os
import math
from collections import defaultdict

class MentalModel:
    """
    The 'Mind' of the HNS-DS.
    A Self-Modifying Cognitive Architecture.
    
    Shift from Hardcoded Rules -> Learned Synaptic Weights + Neural Intuition.
    """
    def __init__(self, learner=None, synthesizer=None):
        self.state = "IDLE"
        self.memory_trace = []
        self.current_goal = None
        self.derived_solution = None
        self.learner = learner 
        self.synthesizer = synthesizer
        self.recalled_episode = None
        self.final_proof = None
        self.symbolic_spec = None
        
        # --- SYNAPTIC WEIGHTS (The "Connectome") ---
        self.weights_path = "cognitive_weights.json"
        self.synaptic_weights = self._load_weights()
        
        # Cognitive Modes (The Lobes)
        self.available_modes = ["CREATIVE", "ANALYTICAL", "CONVERSATIONAL"]

    def _load_weights(self):
        if os.path.exists(self.weights_path):
            try:
                with open(self.weights_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_weights(self):
        with open(self.weights_path, 'w') as f:
            json.dump(self.synaptic_weights, f, indent=2)

    def perceive(self, raw_input):
        """
        Step 1: Perception via "Intuition" (Weighted Classification + Neural Confirmation).
        """
        self.memory_trace.append(f"STIMULUS: {raw_input}")
        
        # 1. MEMORY CHECK (Episodic Recall)
        if self.learner:
            relevant = self.learner.get_relevant_episodes(raw_input, top_k=1, threshold=0.8)
            if relevant:
                self.state = "RECALLING"
                self.recalled_episode = relevant[0]
                self.memory_trace.append(f"MEMORY_TRIGGERED: Recall Episode regarding '{self.recalled_episode['goal_str']}'")
                return self.state

        # 2. INTUITION CHECK (Synaptic Classification)
        words = self._tokenize(raw_input)
        mode_scores = {m: 0.0 for m in self.available_modes}
        for w in words:
            if w in self.synaptic_weights:
                for mode, weight in self.synaptic_weights[w].items():
                    mode_scores[mode] += weight
        
        best_mode = max(mode_scores, key=mode_scores.get)
        
        # 3. NEURAL PERCEPTION (If intuition is weak, use the Synthesizer to decide mode)
        if mode_scores[best_mode] < 0.2 and self.synthesizer:
            self.memory_trace.append("INTUITION_WEAK: Activating Neural Perception...")
            neural_mode = self._neural_classify(raw_input)
            if neural_mode in self.available_modes:
                self.state = neural_mode
                self.memory_trace.append(f"NEURAL_PERCEPTION_RESULT: {self.state}")
                return self.state

        if mode_scores[best_mode] > 0.1:
            self.state = best_mode
        else:
            self.state = "ANALYTICAL" # Default fallback
            
        self.memory_trace.append(f"COGNITIVE_MODE: {self.state}")
        return self.state

    def _neural_classify(self, raw_input):
        prompt = {
            "type": "classification",
            "description": f"Classify this input into one of {self.available_modes}: '{raw_input}'. Return ONLY the word."
        }
        return self.synthesizer.propose(prompt, []).strip().upper()

    def deliberate(self, raw_input):
        """
        Step 2: Deliberation. 
        Instead of hardcoded rules, use Neural-Symbolic Formalization.
        """
        self.memory_trace.append(f"DELIBERATING: Mode={self.state}")
        
        if self.state == "RECALLING":
            return self._deliberate_memory(raw_input)

        # Use Neural Lobe to extract the Formal Specification (Sigma)
        if self.synthesizer:
            self.memory_trace.append("NEURAL_FORMALIZATION: Extracting Symbolic Specification...")
            sigma = self._neural_formalize(raw_input)
            self.symbolic_spec = sigma
            return sigma
        
        # Fallback to simple structure if synthesizer is offline
        return {"type": "coding", "raw": raw_input}

    def _neural_formalize(self, raw_input):
        prompt = {
            "type": "formalization",
            "description": f"Extract the symbolic logic from: '{raw_input}'. Output ONLY valid JSON with 'type' (coding, math, proof, conversational) and details (equations, goals, or response). Example: {{'type': 'math', 'equations': ['x + 2 == 5'], 'variables': ['x']}}"
        }
        res = self.synthesizer.propose(prompt, [])
        try:
            # Robust JSON extraction from potential markdown
            res_clean = res.strip()
            if "```json" in res_clean:
                res_clean = res_clean.split("```json")[1].split("```")[0].strip()
            elif "```" in res_clean:
                res_clean = res_clean.split("```")[1].split("```")[0].strip()
            
            # Remove any trailing commas or common LLM JSON artifacts
            res_clean = re.sub(r',\s*}', '}', res_clean)
            res_clean = re.sub(r',\s*]', ']', res_clean)
            
            return json.loads(res_clean)
        except Exception as e:
            self.memory_trace.append(f"FORMALIZATION_ERROR: {str(e)}. Falling back to conversational.")
            return {"type": "conversational", "response": res}


    def reinforce(self, raw_input, success_mode):
        """
        Reinforcement Learning Step.
        Neurons that fire together, wire together.
        """
        words = self._tokenize(raw_input)
        for w in words:
            if w not in self.synaptic_weights:
                self.synaptic_weights[w] = {m: 0.0 for m in self.available_modes}
            self.synaptic_weights[w][success_mode] += 0.5
            for m in self.available_modes:
                if m != success_mode:
                    self.synaptic_weights[w][m] = max(0, self.synaptic_weights[w][m] - 0.1)

        self._save_weights()
        self.memory_trace.append(f"SYNAPSES_UPDATED: {success_mode}")

    def _tokenize(self, text):
        return [w.lower() for w in re.findall(r'\w+', text)]

    def _deliberate_memory(self, data):
        goal_obj = self.recalled_episode.get('goal_obj', {})
        self.memory_trace.append(f"MEMORY_RETRIEVED: Using past solution as template.")
        return {
            "type": goal_obj.get('type', 'coding'),
            "concept": goal_obj.get('concept', 'recalled'),
            "reference": self.recalled_episode.get('candidate')
        }

    def set_specification(self, sigma):
        self.symbolic_spec = sigma
        self.memory_trace.append(f"SIGMA_ESTABLISHED: {sigma.get('type')}")

    def finalize(self, solution):
        self.derived_solution = solution
        self.memory_trace.append("SOLUTION_FINALIZED")

    def get_trace(self):
        header = "=== COGNITIVE TRACE (HSCI) ===\n"
        return header + "\n".join(f"[{i:02d}] {trace}" for i, trace in enumerate(self.memory_trace))


    def write_solution(self):
        return self.get_trace()

