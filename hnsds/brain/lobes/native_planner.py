import json
import os
from hnsds.brain.lobes.native_graph import NativeGraph

class NativePlanner:
    """
    INVENTION: Native Semantic Planner.
    
    Uses Cognitive Frame intersection to retrieve and adapt skills from memory.
    No hardcoded rules, no tokenization.
    """
    def __init__(self, memory_path="episodes.jsonl"):
        self.memory_path = memory_path
        self.skills_path = "hnsds/brain/knowledge/skills.json"
        self.ontology = NativeGraph()
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
        Generates code by finding the semantically closest skill based on concept intersection.
        """
        return self._find_best_skill(goal_desc)

    def _extract_concepts(self, text):
        concepts = set()
        text_lower = text.lower()
        for concept in self.ontology.nodes.keys():
            if concept in text_lower:
                canon = self.ontology.find_synonym(concept)
                concepts.add(canon)
        return concepts

    def _find_best_skill(self, goal_desc):
        goal_concepts = self._extract_concepts(goal_desc)
        best_skill = None
        best_score = -1.0
        
        for skill in self.skills:
            skill_text = " ".join(skill.get("tags", []))
            skill_concepts = self._extract_concepts(skill_text)
            
            # Jaccard Similarity of Concepts
            union = goal_concepts.union(skill_concepts)
            if union:
                score = len(goal_concepts.intersection(skill_concepts)) / len(union)
                if score > best_score:
                    best_score = score
                    best_skill = skill
        
        if best_skill and best_score > 0.0:
            return best_skill["template"] + best_skill.get("test_wrapper", "")
            
        return f"# TODO: Implement {goal_desc}"

    def plan_conversational_task(self, stimulus):
        return "I am analyzing your request using my Concept Frame logic."

    def _shingle(self, text, n=2):
        return []
