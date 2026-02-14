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
        """
        # 1. Vectorize the Goal
        goal_vector = self.embedding.embed(goal_desc)
        
        best_skill = None
        best_score = -1.0
        
        # 2. Semantic Search in Skill Memory
        for skill in self.skills:
            # We create a 'concept vector' for the skill from its tags
            # In a real system, these would be pre-calculated
            skill_text = " ".join(skill.get("tags", []))
            skill_vector = self.embedding.embed(skill_text)
            
            # Cosine Similarity
            # Dot Product (since vectors are normalized)
            score = 0
            for i in range(len(goal_vector)):
                score += goal_vector[i] * skill_vector[i]
                
            if score > best_score:
                best_score = score
                best_skill = skill
        
        # 3. Adapt
        # print(f"DEBUG: Best Skill: {best_skill.get('tags') if best_skill else 'None'} Score: {best_score}")
        if best_skill and best_score > 0.2: # Confidence threshold
            return best_skill["template"] + best_skill.get("test_wrapper", "")
            
        # Fallback: Construct empty function
        return f"def solve():\n    # TODO: Implement {goal_desc}\n    return None"

    def plan_conversational_task(self, stimulus):
        """
        Retrieves a natural response from memory based on similarity.
        """
        # (Keeping the simple logic here for now, but could be vectorized too)
        return "I am analyzing your request using my new Semantic Core."

    def _shingle(self, text, n=2):
        # Legacy helper
        return []
