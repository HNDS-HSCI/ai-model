from typing import List
from hsci.core.data_types import PerceptionMap, SubGoal, AxiomType

class HTNPlanner:
    """
    Hierarchical Task Network planner.
    Decomposes complex goals into solvable sub-goals.
    """

    DECOMPOSITION_RULES = {
        AxiomType.REDUCTION: [
            ("IDENTIFY_UNKNOWNS", "Identify variables to solve for."),
            ("BUILD_EQUATION", "Construct a mathematical equation."),
            ("SOLVE_EQUATION", "Solve the mathematical equation.")
        ],
        AxiomType.COMPOSITION: [
            ("EXTRACT_ENTITIES", "Extract all relevant entities."),
            ("IDENTIFY_RELATIONSHIPS", "Determine relationships between entities."),
            ("BUILD_CONSTRAINT_NETWORK", "Construct a network of constraints."),
            ("SOLVE_NETWORK", "Solve the network of constraints.")
        ],
        AxiomType.SYNTHESIS: [
            ("DEFINE_INPUTS_OUTPUTS", "Define inputs and expected outputs."),
            ("IDENTIFY_ALGORITHM_PATTERN", "Identify suitable algorithmic patterns."),
            ("BUILD_PROCEDURE", "Construct the procedural logic."),
            ("VERIFY_INVARIANTS", "Verify algorithmic invariants.")
        ],
        AxiomType.TRANSFORMATION: [
            ("PARSE_SOURCE_STRUCTURE", "Parse the source information structure."),
            ("IDENTIFY_TARGET_STRUCTURE", "Identify the target information structure."),
            ("MAP_TRANSFORMATION_RULES", "Map rules for transformation."),
            ("APPLY_TRANSFORMATION", "Apply transformation rules.")
        ],
    }

    def decompose(self, perception: PerceptionMap) -> List[SubGoal]:
        """
        Decomposes the intent in perception into a sequence of sub-goals.
        """
        steps = self.DECOMPOSITION_RULES.get(perception.intent, [("UNKNOWN_INTENT_HANDLING", "Handle unknown or unclassifiable intent.")])
        sub_goals = []
        for name, description in steps:
            sub_goal = SubGoal(
                name=name,
                description=description,
                required_entities=list(perception.entities.keys()),
                target_entity=perception.unknown_entities[0] if perception.unknown_entities else "result",
                axiom_type=perception.intent
            )
            sub_goals.append(sub_goal)
        return sub_goals
