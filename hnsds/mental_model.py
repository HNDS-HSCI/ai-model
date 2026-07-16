import re
import json
import os
import math
from collections import defaultdict
from .brain.lobes.native_planner import NativePlanner

class MentalModel:
    """
    The 'Mind' of the HNS-DS.
    A Self-Modifying Cognitive Architecture.
    
    Shift from Hardcoded Rules -> Learned Synaptic Weights + Neural Intuition.
    """
    def __init__(self, learner=None, synthesizer=None, cognitive_lobe=None, neural_lobe=None):
        self.state = "IDLE"
        self.memory_trace = []
        self.current_goal = None
        self.derived_solution = None
        self.learner = learner 
        self.synthesizer = synthesizer
        self.cognitive_lobe = cognitive_lobe or neural_lobe # The Native "Cognitive Frame" Lobe
        self.planner = NativePlanner() # The Native "Reasoning" Lobe
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
        Step 1: Perception via "Cognitive Framing" (Native Cognitive Lobe + Memory).
        """
        self.memory_trace.append(f"STIMULUS: {raw_input}")
        
        # 1. MEMORY CHECK (Episodic Recall)
        if self.learner:
            relevant = self.learner.get_relevant_episodes(raw_input, top_k=1, threshold=0.8)
            if relevant and relevant[0].get('success'):
                self.state = "RECALLING"
                self.recalled_episode = relevant[0]
                self.memory_trace.append(f"MEMORY_TRIGGERED: Recall Episode regarding '{self.recalled_episode['goal_str']}'")
                return self.state

        # 2. NATIVE COGNITIVE FRAMING (Predictive Trajectory)
        if self.cognitive_lobe and hasattr(self.cognitive_lobe, "simulate_trajectory"):
            # The Cognitive Lobe predicts the process trajectory based on Concept Graph
            sigma = self.cognitive_lobe.simulate_trajectory(raw_input)
            self.symbolic_spec = sigma
            
            # Determine mode from the predicted trajectory
            trajectory_type = sigma.get("trajectory", "CONVERSATIONAL_FLOW")
            path = " -> ".join(sigma.get("path", []))
            print(f"DEBUG_MENTAL_MODEL: predicted_trajectory='{trajectory_type}' path='{path}'")
            
            if trajectory_type in ["MATH_REDUCTION", "CODE_SYNTHESIS", "LOGIC_COMPOSITION"]:
                self.state = "ANALYTICAL"
            else:
                self.state = "CONVERSATIONAL"
                
            self.memory_trace.append(f"PREDICTED_TRAJECTORY: {trajectory_type} ({path})")
            return self.state

        # 3. FALLBACK (Legacy Weight Check)
        words = self._tokenize(raw_input)
        mode_scores = {m: 0.0 for m in self.available_modes}
        for w in words:
            if w in self.synaptic_weights:
                for mode, weight in self.synaptic_weights[w].items():
                    mode_scores[mode] += weight
        
        best_mode = max(mode_scores, key=mode_scores.get)
        if mode_scores[best_mode] > 0.1:
            self.state = best_mode
        else:
            self.state = "ANALYTICAL"
            
        self.memory_trace.append(f"COGNITIVE_MODE (Fallback): {self.state}")
        return self.state

    def deliberate(self, raw_input):
        """
        Step 2: Deliberation. 
        """
        self.memory_trace.append(f"DELIBERATING: Mode={self.state}")
        
        if self.state == "RECALLING":
            return self._deliberate_memory(raw_input)

        # If Neural Lobe already did the work in perceive(), return that spec
        if self.symbolic_spec:
            spec_type = self.symbolic_spec.get('type')
            self.memory_trace.append(f"USING_INTUITION_SPEC: {spec_type}")
            
            # Use Planner for Coding Tasks
            if spec_type == 'coding':
                desc = self.symbolic_spec.get('desc', raw_input)
                plan = self.planner.plan_coding_task(desc)
                self.memory_trace.append("PLAN_GENERATED: Analogical Reasoning applied.")
                self.symbolic_spec['candidate'] = plan
            
            # Use Planner for Conversational Tasks
            if spec_type == 'conversational':
                response = self.planner.plan_conversational_task(raw_input)
                self.memory_trace.append("CONVERSATION_PLANNED: Memory retrieval applied.")
                self.symbolic_spec['response'] = response
            
            return self.symbolic_spec
        
        # Fallback to simple structure
        return {"type": "coding", "raw": raw_input}


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
        candidate = self.recalled_episode.get('candidate')
        
        if not candidate:
            self.memory_trace.append("MEMORY_INCOMPLETE: No candidate found in episode. Re-deliberating.")
            self.state = "ANALYTICAL"
            return self.symbolic_spec # Fallback to spec derived in perceive
            
        self.memory_trace.append(f"MEMORY_RETRIEVED: Using past solution as template.")
        return {
            "type": goal_obj.get('type', 'coding'),
            "concept": goal_obj.get('concept', 'recalled'),
            "candidate": candidate
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

