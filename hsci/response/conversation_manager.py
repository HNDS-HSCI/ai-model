from typing import List, Dict, Any, Optional
from hsci.core.data_types import StructuredInput, EntityValue

class ConversationManager:
    """
    Manages session history and context resolution for follow-up questions.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def resolve_followup(self, raw_input: str, current_structured_dict: Dict[str, Any]) -> StructuredInput:
        """
        Merges current structured input with context from previous turns if necessary.
        """
        # Simple resolution: if current has no entities but history does, copy them
        if not current_structured_dict.get('entities') and self.history:
            last_turn = self.history[-1]
            current_structured_dict['entities'] = last_turn.get('entities', {}).copy()
            current_structured_dict['is_followup'] = True
        
        # Convert dict back to StructuredInput (simplified)
        # Note: rir_loop.py handles the actual class conversion for now
        return current_structured_dict

    def add_turn(self, structured: StructuredInput, output: Any, response: str):
        """Adds a turn to the conversation history."""
        self.history.append({
            "entities": structured.entities,
            "domain": structured.domain,
            "response": response,
            "output": output
        })
        if len(self.history) > 10:
            self.history.pop(0)
