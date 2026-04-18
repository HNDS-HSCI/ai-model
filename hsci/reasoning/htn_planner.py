from typing import List
from hsci.core.data_types import PerceptionMap, SubGoal, AxiomType

class HTNPlanner:
    """
    Hierarchical Task Network planner.
    Decomposes complex goals into solvable sub-goals.
    """

    DECOMPOSITION_RULES = {
        AxiomType.REDUCTION: [
            "IDENTIFY_UNKNOWNS",
            "BUILD_CONSTRAINT",
            "SOLVE_CONSTRAINT"
        ],
        AxiomType.COMPOSITION: [
            "EXTRACT_ENTITIES",
            "IDENTIFY_RELATIONSHIPS",
            "BUILD_CONSTRAINT_NETWORK",
            "SOLVE_NETWORK"
        ],
        AxiomType.SYNTHESIS: [
            "DEFINE_INPUTS_OUTPUTS",
            "IDENTIFY_ALGORITHM_PATTERN",
            "BUILD_PROCEDURE",
            "VERIFY_INVARIANTS"
        ],
        AxiomType.TRANSFORMATION: [
            "PARSE_SOURCE",
            "IDENTIFY_TARGET",
            "MAP_RULES",
            "APPLY_TRANSFORMATION"
        ],
    }

    def decompose(self, perception: PerceptionMap) -> List[SubGoal]:
        """
        Decomposes the intent in perception into a sequence of sub-goals.
        """
        steps = self.DECOMPOSITION_RULES.get(perception.intent, ["GENERAL_REASONING"])
        sub_goals = []
        for step in steps:
            sub_goal = SubGoal(
                description=step,
                required_entities=list(perception.entities.keys()),
                target_entity=perception.unknown_entities[0] if perception.unknown_entities else "result",
                axiom_type=perception.intent
            )
            sub_goals.append(sub_goal)
        return sub_goals
