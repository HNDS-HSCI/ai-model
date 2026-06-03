import re
from typing import Any, Dict, List, Optional

class EntityExtractor:
    """
    Extracts entities, their values, and their types (known/known) from raw text.
    Handles numbers, variables, operators, units, unknowns.
    """

    def __init__(self):
        # Improved known pattern: support '=' for strings/numbers, and 'is' strictly for numbers
        self.known_entity_pattern = re.compile(r'\b([a-zA-Z_]\w*)\s*=\s*([\w\d\.]+)\b|\b([a-zA-Z_]\w*)\s+(?:is)\s+([\d\.]+)\b')
        
        # Improved unknown pattern to capture multi-word entities like "tax amount" and support hyphens
        # Fixed terminator to prevent matching 'in' inside words like 'income'
        self.unknown_patterns = [
            re.compile(r'(?:find|calculate|compute|solve for|what is)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+(?:in|if|given)|[\?\.,]|$)'),
            re.compile(r'([a-zA-Z0-9_\-\s]+?)\s+(?:is\s+unknown|is\s+to\s+be\s+found|is\s+what)'),
        ]
        self.stop_words = ["the", "a", "an", "for", "is", "of", "to", "what", "find", "calculate", "compute", "solve", "in", "it"]

    def extract(self, text: str) -> Dict[str, Any]:
        entities = {}
        
        # 1. Extract knowns
        knowns = self.known_entity_pattern.findall(text)
        for match in knowns:
            # findall with OR returns tuples of groups
            # group 0,1 for '=', group 2,3 for 'is'
            if match[0]:
                key, val = match[0], match[1]
            else:
                key, val = match[2], match[3]
            entities[key.strip()] = self._parse_val(val.strip())

        # 2. Extract unknowns
        unknown_found = False
        for pattern in self.unknown_patterns:
            matches = pattern.findall(text.lower())
            for match in matches:
                # Clean the match
                clean_match = match.strip().replace('-', '_') # Replace hyphen with underscore for variable naming
                # Remove stop words from the start/end
                words = clean_match.split()
                filtered_words = [w for w in words if w not in self.stop_words]
                if filtered_words:
                    entity_name = "_".join(filtered_words)
                    # Prioritize known over unknown
                    if entity_name not in entities:
                        entities[entity_name] = None
                        unknown_found = True

        # 3. Handle direct numbers without labels (e.g., "5 + 5")
        # Let's only do it if no labeled entities were found
        if not entities:
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
            for i, num in enumerate(numbers):
                entities[f"op_{i+1}"] = self._parse_val(num)

        # 4. Final Result marker
        if not unknown_found and len(entities) >= 2:
             # Only add 'result' automatically if all we found were generic operands
             if all(k.startswith("op_") for k in entities.keys()):
                 if "result" not in entities:
                     entities["result"] = None

        return entities

    def _parse_val(self, num_str: str) -> Any:
        try:
            if '.' in num_str:
                return float(num_str)
            return int(num_str)
        except ValueError:
            return num_str
