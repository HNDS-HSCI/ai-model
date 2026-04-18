from typing import List, Any, Optional
from hsci.core.data_types import SubGoal, Concept

class ConceptComposer:
    """
    Composes relevant concepts to build a candidate solution.
    Handles cross-domain transfer by looking for analogical matches.
    """

    def __init__(self):
        pass

    def find_best(self, sub_goal: SubGoal, direct: List[Concept], analogical: List[Concept], context_text: str = "") -> Optional[Concept]:
        """
        Finds the best concept to apply for a given sub-goal.
        """
        # Improved selection logic: use context_text to bias concept choice
        if direct:
            ranked = self.rank_by_strength(direct)
            
            # Domain-specific heuristics
            text = context_text.lower()
            if any(w in text for w in ["distance", "velocity", "force", "mass", "acceleration", "interest"]):
                 # Prioritize MULTIPLICATION or LINEAR_EQUATION for these
                 mult_concepts = [c for c in ranked if c.name == "MULTIPLICATION"]
                 if mult_concepts:
                     return mult_concepts[0]
            
            if any(w in text for w in ["tax", "discount", "percent"]):
                 perc_concepts = [c for c in ranked if c.name == "PERCENTAGE"]
                 if perc_concepts:
                     return perc_concepts[0]

            return ranked[0]

        # Then try analogical transfer
        if analogical:
            return self.compose_analogies(sub_goal, analogical)

        # Last resort: attempt synthesis from primitives (placeholder)
        return self.synthesize_from_primitives(sub_goal)

    def rank_by_strength(self, concepts: List[Concept]) -> List[Concept]:
        """
        Ranks concepts by their strength (descending).
        """
        return sorted(concepts, key=lambda c: c.strength, reverse=True)

    def compose_analogies(self, sub_goal: SubGoal, analogical: List[Concept]) -> Optional[Concept]:
        """
        Placeholder for composing analogical concepts.
        """
        if analogical:
            return self.rank_by_strength(analogical)[0]
        return None

    def synthesize_from_primitives(self, sub_goal: SubGoal) -> Optional[Concept]:
        """
        Placeholder for synthesizing a concept from primitives.
        """
        return None
