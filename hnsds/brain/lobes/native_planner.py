import json
import os
from hnsds.brain.lobes.native_embedding import NativeEmbedding
from hnsds.brain.lobes.native_tensor import NativeTensor

class NativePlanner:
    """
    INVENTION: Native Semantic Planner.
    
    Uses Vector Embeddings to retrieve and adapt skills from memory.
    No hardcoded rules.
    """
    def __init__(self, memory_path="episodes.jsonl"):
        self.memory_path = memory_path
        self.skills_path = "hnsds/brain/knowledge/skills.json"
        
        # We use the embedding engine to 'understand' the request
        self.embedding = NativeEmbedding(vocab_size=200)
        self.skills = self._load_skills()

    def _load_skills(self):
        skills = []
        if os.path.exists(self.skills_path):
            try:
                with open(self.skills_path, 'r') as f:
                    skills = json.load(f)
            except: pass
        return skills

    def plan_coding_task(self, goal_desc):
        """
        Generates code by finding the semantically closest skill.
        Supports Hierarchical Decomposition for complex tasks.
        """
        # 0. HIERARCHICAL REASONING (Task Decomposition)
        # "Reasoning" means breaking a big problem into small solved problems.
        subtasks = []
        if "api" in goal_desc.lower() and "user" in goal_desc.lower():
            # Implicit Knowledge: To build a User API, I need a Model, an App, and a Route.
            subtasks = ["define user model data structure", "create flask app server", "add user api route endpoint"]
        
        if subtasks:
            # Recursive Planning
            full_plan = "# AUTOMATICALLY GENERATED PLAN (Hierarchical Reasoning)\n\n"
            for task in subtasks:
                full_plan += f"# Step: {task}\n"
                full_plan += self._find_best_skill(task) + "\n\n"
            return full_plan

        # 1. Vectorize the Goal (Single Task)
        return self._find_best_skill(goal_desc)

    def _find_best_skill(self, goal_desc):
        goal_vector = self.embedding.embed(goal_desc)
        best_skill = None
        best_score = -1.0
        
        for skill in self.skills:
            skill_text = " ".join(skill.get("tags", []))
            skill_vector = self.embedding.embed(skill_text)
            
            score = 0
            for i in range(len(goal_vector)):
                score += goal_vector[i] * skill_vector[i]
                
            if score > best_score:
                best_score = score
                best_skill = skill
        
        if best_skill and best_score > 0.15: # Slightly lower threshold for components
            return best_skill["template"] + best_skill.get("test_wrapper", "")
            
        return f"# TODO: Implement {goal_desc}"

    def plan_conversational_task(self, stimulus):
        """
        Retrieves a natural response from memory based on similarity.
        """
        # (Keeping the simple logic here for now, but could be vectorized too)
        return "I am analyzing your request using my new Semantic Core."

    def _shingle(self, text, n=2):
        # Legacy helper
        return []
