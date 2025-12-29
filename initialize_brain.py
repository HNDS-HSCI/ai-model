import json
import os

def initialize():
    # 1. Seed Cognitive Weights (Synaptic Intuition)
    weights = {
        # Analytical Triggers
        "calculate": {"ANALYTICAL": 1.0, "CREATIVE": 0.0, "CONVERSATIONAL": 0.0},
        "solve": {"ANALYTICAL": 1.0, "CREATIVE": 0.0, "CONVERSATIONAL": 0.0},
        "sum": {"ANALYTICAL": 0.8, "CREATIVE": 0.0, "CONVERSATIONAL": 0.0},
        "find": {"ANALYTICAL": 0.7, "CREATIVE": 0.2, "CONVERSATIONAL": 0.0},
        "equation": {"ANALYTICAL": 1.0, "CREATIVE": 0.0, "CONVERSATIONAL": 0.0},
        "code": {"ANALYTICAL": 1.0, "CREATIVE": 0.5, "CONVERSATIONAL": 0.0},
        "function": {"ANALYTICAL": 1.0, "CREATIVE": 0.3, "CONVERSATIONAL": 0.0},
        "python": {"ANALYTICAL": 0.9, "CREATIVE": 0.4, "CONVERSATIONAL": 0.0},
        
        # Creative/Exploratory Triggers
        "imagine": {"ANALYTICAL": 0.0, "CREATIVE": 1.0, "CONVERSATIONAL": 0.2},
        "create": {"ANALYTICAL": 0.2, "CREATIVE": 1.0, "CONVERSATIONAL": 0.0},
        "story": {"ANALYTICAL": 0.0, "CREATIVE": 1.0, "CONVERSATIONAL": 0.5},
        "build": {"ANALYTICAL": 0.5, "CREATIVE": 0.8, "CONVERSATIONAL": 0.0},
        
        # Conversational Triggers
        "hello": {"ANALYTICAL": 0.0, "CREATIVE": 0.0, "CONVERSATIONAL": 1.0},
        "hi": {"ANALYTICAL": 0.0, "CREATIVE": 0.0, "CONVERSATIONAL": 1.0},
        "who": {"ANALYTICAL": 0.0, "CREATIVE": 0.0, "CONVERSATIONAL": 0.8},
        "what": {"ANALYTICAL": 0.3, "CREATIVE": 0.0, "CONVERSATIONAL": 0.5},
        "explain": {"ANALYTICAL": 0.5, "CREATIVE": 0.0, "CONVERSATIONAL": 1.0},
        "why": {"ANALYTICAL": 0.4, "CREATIVE": 0.0, "CONVERSATIONAL": 1.0}
    }
    
    with open("cognitive_weights.json", "w") as f:
        json.dump(weights, f, indent=2)
    print("Synaptic weights initialized.")

    # 2. Seed Primordial Episodes (Experience)
    episodes = [
        {
            "goal_str": "solve x + 2 = 5",
            "goal_obj": {"type": "math", "equation": "x + 2 == 5", "variables": ["x"]},
            "candidate": "x=3",
            "success": True
        },
        {
            "goal_str": "write a function to add two numbers",
            "goal_obj": {"type": "coding", "description": "add two numbers"},
            "candidate": "def solve(a, b):\n    return a + b",
            "success": True
        }
    ]
    
    with open("episodes.jsonl", "w") as f:
        for ep in episodes:
            f.write(json.dumps(ep) + "\n")
    print("Primordial episodes initialized.")

if __name__ == "__main__":
    initialize()
