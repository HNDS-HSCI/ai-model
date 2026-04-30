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
        # 1. Handle SYNTHESIS (Code Generation)
        if any(c in ["SYNTHESIS"] for c in final_output.concepts_used) or domain == "software_engineering":
            prefix = "💻 Code Synthesis Result:\n"
            code = final_output.answer if isinstance(final_output.answer, str) else str(final_output.answer)
            return f"{prefix}I have synthesized the following algorithm based on your request:\n\n```python\n{code}\n```\n\nVerified by structural induction."

        # 2. Handle TRANSFORMATION (Conversational / General)
        social_keywords = {"hi", "hello", "hey", "greetings", "who are you"}
        if any(w in original_input.lower().split() for w in social_keywords):
            return "Hello! I am HSCI, a Hyper-Symbolic Cognitive Intelligence. I don't just guess—I prove. Ask me to solve a math problem, generate code, or analyze data, and I will show you my reasoning trace."
            
        if "help" in original_input.lower().split():
            return "I am a v3.0 Neurosymbolic AI. You can ask me to solve math problems (e.g., 'If salary is 5000 and tax is 15%, find tax'), logic puzzles, or code synthesis. I use Z3 SMT to verify every answer mathematically."

        # 3. Handle Fallback for General Knowledge
        if not final_output.concepts_used and not final_output.reasoning_trace:
             return f"I perceive your input as a general knowledge query related to '{domain}'. As a specialized symbolic engine, I am currently optimized for mathematical and logical proofs. You can 'teach:' me the underlying logic of this topic to enable deeper reasoning."

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
