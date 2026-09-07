import re
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
            text = context_text.lower()
            
            # 1. Prioritize concept if its name is mentioned in the query text
            for concept in ranked:
                c_name = concept.name.lower()
                if c_name in text or c_name.replace("_", " ") in text:
                    return concept

            # 2. Prioritize concept if its required entities match the query text entities.
            # Whole-word match only, and single-letter entity names ("a", "b" --
            # ADDITION/SUBTRACTION/MULTIPLICATION/DIVISION all declare identical
            # required_entities=["a","b"] in z3_templates.py) are excluded
            # entirely: a raw substring check let them match spuriously against
            # ANY text containing that letter ("tax", "salary", "rate" all
            # contain "a"), and even with word-boundaries, "a" is a common
            # standalone English word (e.g. a sub-goal description like
            # "Construct a mathematical equation" contains it as the article,
            # not as the variable). A single letter can never reliably signal
            # which concept is meant, so it silently forced every one of those
            # four concepts to tie and always resolve to whichever came first
            # in dict order (ADDITION), falsely reported as Z3-verified
            # regardless of what was actually asked.
            for concept in ranked:
                meaningful_entities = [e for e in concept.required_entities if len(e) >= 2]
                if meaningful_entities:
                    overlap = [
                        e for e in meaningful_entities
                        if re.search(rf"\b{re.escape(e.lower())}\b", text)
                    ]
                    if len(overlap) >= len(meaningful_entities) - 1 and len(meaningful_entities) >= 2:
                        return concept

            # 3. Prioritize concept if one of its registered aliases is mentioned.
            # This replaces two hardcoded Python word-lists (one for "distance/
            # velocity/force/..." -> MULTIPLICATION, one for "tax/discount/
            # percent" -> PERCENTAGE) with one generic mechanism: any concept
            # can declare its own trigger words as data (Concept.aliases) rather
            # than the composer hardcoding specific concept names in source.
            for concept in ranked:
                for alias in concept.aliases:
                    if alias.lower() in text:
                        return concept

            # No concept was distinguished by name, entities, or alias.
            # Strength (proof_count-driven reinforcement from the learning
            # loop) is still a real, earned signal when it actually
            # differs between candidates -- so a genuine leader is fine to
            # return. What's NOT fine is breaking a tie by dict/insertion
            # order alone, which is exactly how the bug above produced a
            # confident-but-wrong "verified" ADDITION answer for word
            # problems needing a different operation: every candidate had
            # the same seeded strength=1.0, so "highest strength" was
            # really just "first in Z3_METADATA". Only return ranked[0]
            # when it's a single candidate or a genuine leader; otherwise
            # admit the concept couldn't be determined rather than guess.
            if len(ranked) == 1 or ranked[0].strength > ranked[1].strength:
                return ranked[0]
            return None

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
        print(f"ConceptComposer: Composing analogies for sub-goal '{sub_goal.name}' (placeholder)")
        if analogical:
            return self.rank_by_strength(analogical)[0]
        return None

    def synthesize_from_primitives(self, sub_goal: SubGoal) -> Optional[Concept]:
        """
        Placeholder for synthesizing a concept from primitives.
        """
        print(f"ConceptComposer: Synthesizing from primitives for sub-goal '{sub_goal.name}' (placeholder)")
        return None
