from typing import Any, List, Optional
from hsci.core.data_types import FinalOutput, ResponseContext, ResponseType
from hsci.response.conversation_manager import ConversationManager

class ResponseBridge:
    """
    LAYER 6: Response Bridge
    Explains the answer in natural human language.
    """

    def __init__(self):
        self.conversation_manager = ConversationManager()

    def generate(self, final_output: FinalOutput, original_input: str, domain: str) -> str:
        """
        Generates a natural language response with full explanation.
        """
        if not final_output.is_verified:
            return self._generate_unverified_response(final_output)

        # Extract numerical answer from z3_model
        answer_val = final_output.answer
        if final_output.proof and final_output.proof.variable_assignments:
             # Find the most likely 'result' key
             potential_keys = ['result', 'tax_amount', 'distance', 'acceleration', 'interest', 'area']
             for k in potential_keys:
                  if k in final_output.proof.variable_assignments:
                       answer_val = final_output.proof.variable_assignments[k]
                       break

        # Domain-aware formatting
        prefix = ""
        unit = ""
        if domain == "finance":
            prefix = "💰 Financial Calculation Result:\n"
            unit = "₹" # Default for India as per previous memories
        elif domain == "physics":
            prefix = "⚛️ Physics Calculation Result:\n"
        else:
            prefix = "✅ Calculation Result:\n"

        display_answer = f"{unit}{answer_val}" if unit else f"{answer_val}"
        answer_text = f"The answer is {display_answer}."
        
        trace_text = "\n\nReasoning steps:"
        for i, step in enumerate(final_output.reasoning_trace):
             trace_text += f"\n  {i+1}. {step}"
        
        verification_text = f"\n\n✓ Mathematically verified by Z3 SMT Solver."
        concepts_text = f"\nConcepts used: {', '.join(final_output.concepts_used)}"

        full_response = f"{prefix}{answer_text}{trace_text}{verification_text}{concepts_text}"
        
        return full_response

    def _generate_unverified_response(self, final_output: FinalOutput) -> str:
        msg = "⚠ I was unable to formally verify this answer."
        if final_output.correction_hint:
            msg += f"\nHint: {final_output.correction_hint}"
        
        msg += "\n\nYou can help me learn by using the 'teach:' command with a proven example."
        return msg
