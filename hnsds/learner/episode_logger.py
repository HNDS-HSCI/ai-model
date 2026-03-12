import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class EpisodeLogger:
    def __init__(
        self,
        storage_path="episodes.jsonl",
        primordial_path="hnsds/learner/primordial_knowledge.jsonl",
    ):
        self.storage_path = storage_path
        self.primordial_path = primordial_path
        self._ensure_storage()
        self.primordial_episodes = self._load_primordial()

    def _ensure_storage(self):
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                pass

    def _load_primordial(self):
        episodes = []
        if os.path.exists(self.primordial_path):
            with open(self.primordial_path, "r") as f:
                for line in f:
                    try:
                        episodes.append(json.loads(line))
                    except:
                        continue
        return episodes

    def log_episode(self, goal, candidate, counterexample=None, success=False):
        episode = {
            "goal_str": str(goal),
            "goal_obj": goal,
            "candidate": candidate,
            "counterexample": counterexample,
            "success": success,
        }
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(episode) + "\n")

    def get_relevant_episodes(self, current_goal, top_k=3, threshold=0.5):
        """
        Uses TF-IDF similarity to find past episodes relevant to the current goal.
        Includes both 'Learned' episodes and 'Primordial' knowledge.
        """
        learned_episodes = self._load_learned()

        # The Brain's total memory = Primordial (Training) + Learned (Experience)
        all_episodes = self.primordial_episodes + learned_episodes

        if not all_episodes:
            return []

        past_goals = [ep["goal_str"] for ep in all_episodes]
        current_goal_str = str(current_goal)

        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(past_goals + [current_goal_str])
            similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])[0]

            relevant_indices = np.where(similarities >= threshold)[0]
            sorted_indices = relevant_indices[
                np.argsort(similarities[relevant_indices])
            ][::-1]

            results = [all_episodes[i] for i in sorted_indices[:top_k]]
            return results
        except Exception:
            return [ep for ep in all_episodes if ep["goal_str"] == current_goal_str]

    def _load_learned(self):
        learned_episodes = []
        if os.path.exists(self.storage_path) and os.stat(self.storage_path).st_size > 0:
            with open(self.storage_path, "r") as f:
                for line in f:
                    try:
                        learned_episodes.append(json.loads(line))
                    except:
                        continue
        return learned_episodes

    def consolidate_experience(self, brain):
        """
        Refinement Loop: Periodically promotes frequent successful episodes 
        to permanent axioms in mental_intelligence.json.
        """
        learned = self._load_learned()
        successes = [ep for ep in learned if ep.get("success")]
        
        # Identify concepts that have high success rates
        # (In a real system, this would use a more complex clustering algorithm)
        # For the prototype, we simply promote any unique success that was verified.
        promoted_count = 0
        for ep in successes:
            goal_obj = ep.get("goal_obj")
            if not isinstance(goal_obj, dict): continue
            
            concept_name = f"AUTO_MASTERED_{goal_obj.get('type','GENERIC')}_{promoted_count}"
            stimulus = ep.get("goal_str")
            axiom = "REDUCTION" if goal_obj.get("type") == "math" else "SYNTHESIS"
            
            # Teach the brain this new consolidated concept
            brain.teach(stimulus, concept_name, axiom)
            promoted_count += 1
            
        return promoted_count
