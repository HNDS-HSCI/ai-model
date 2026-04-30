import logging
from hsci.core.data_types import SubGoal, Expression

class ProgramSynthesizer:
    """
    HSCI v3.1: Neurosymbolic Program Synthesizer.
    Constructs procedural logic from abstract sub-goals.
    """

    def __init__(self):
        self.logger = logging.getLogger("ProgramSynthesizer")
        self.primitives = {
            "ADDITION": "a + b",
            "SUBTRACTION": "a - b",
            "MULTIPLICATION": "a * b",
            "DIVISION": "a / b",
            "PERCENTAGE": "base * (rate / 100)",
            "PERCENTAGE_DECIMAL": "base * rate"
        }

    def synthesize(self, sub_goals, concept_assignments, entities) -> str:
        """
        Synthesizes a Python function from sub-goals and concepts.
        """
        if not sub_goals:
            return "# No sub-goals provided for synthesis."

        code_lines = ["def solution_algorithm(input_data):", "    # Autonomous Synthesis via HSCI RIR Loop"]
        
        # Extract variables from entities
        for name, ev in entities.items():
            if ev.known and ev.value is not None:
                code_lines.append(f"    {name} = {ev.value}")
            else:
                code_lines.append(f"    {name} = None # To be solved")

        code_lines.append("")

        for goal in sub_goals:
            concept = concept_assignments.get(goal.id)
            if concept and concept.name in self.primitives:
                logic = self.primitives[concept.name]
                target = goal.target_entity if goal.target_entity else "result"
                code_lines.append(f"    {target} = {logic}")
            else:
                code_lines.append(f"    # Step: {goal.description}")

        code_lines.append("")
        result_key = next((k for k, v in entities.items() if not v.known), "result")
        code_lines.append(f"    return {result_key}")

        return "\n".join(code_lines)
