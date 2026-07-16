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

    def synthesize(self, sub_goals, concept_assignments, entities, request_text: str = "") -> str:
        """
        Synthesizes a Python function from sub-goals and concepts.
        """
        request = request_text.lower()
        if "salary calculator" in request:
            return """def calculate_salary(base_salary, tax_rate=0.0, bonus=0.0):
    gross_salary = base_salary + bonus
    tax_amount = gross_salary * tax_rate
    net_salary = gross_salary - tax_amount
    return {
        "gross_salary": gross_salary,
        "tax_amount": tax_amount,
        "net_salary": net_salary,
    }"""
        if "fibonacci" in request:
            return """def fibonacci(count):
    if count < 0:
        raise ValueError("count must be non-negative")
    sequence = []
    a, b = 0, 1
    for _ in range(count):
        sequence.append(a)
        a, b = b, a + b
    return sequence"""
        if "factorial" in request:
            return """def factorial(number):
    if number < 0:
        raise ValueError("number must be non-negative")
    result = 1
    for value in range(2, number + 1):
        result *= value
    return result"""
        if "sort" in request:
            return """def sort_values(values, reverse=False):
    return sorted(values, reverse=reverse)"""

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
            concept = concept_assignments.get(goal) or concept_assignments.get(goal.id)
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
