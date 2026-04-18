import re
from typing import Any, Dict, List, Optional

class EntityExtractor:
    """
    Extracts entities, their values, and their types (known/unknown) from raw text.
    Handles numbers, variables, operators, units, unknowns.
    """

    def __init__(self):
        # Key must start with letter to avoid matching "5 = 10" in "x + 5 = 10"
        self.known_entity_pattern = re.compile(r'([a-zA-Z_]\w*)\s*(?:is|=)\s*(\d+(?:\.\d+)?)(?:\s*\w+)?')
        # Improved unknown pattern to capture multi-word entities like "tax amount"
        self.unknown_entity_pattern = re.compile(r'(?:find|calculate|solve for|what is)\s+([\w\s-]+)(?=\W|$)')
        self.number_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\b')
        # Coefficient pattern for things like "2x" or "10y"
        self.coef_pattern = re.compile(r'\b(\d+)([a-zA-Z_])\b')

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extracts entities from the given text.
        """
        entities: Dict[str, Any] = {}

        # 1. Extract coefficients (e.g., "2x")
        for match in self.coef_pattern.finditer(text):
            coef = int(match.group(1))
            var = match.group(2)
            entities[f"{var}_coef"] = coef
            if var not in entities:
                entities[var] = None

        # 2. Extract known entities (e.g., "salary is 5000", "x = 10")
        for match in self.known_entity_pattern.finditer(text):
            key = match.group(1)
            value_str = match.group(2)
            try:
                entities[key] = float(value_str) if '.' in value_str else int(value_str)
            except ValueError:
                entities[key] = value_str

        # 3. Extract unknown entities (e.g., "find distance")
        unknown_found = False
        for match in self.unknown_entity_pattern.finditer(text):
            key = match.group(1).strip().lower().replace(' ', '_').replace('-', '_')
            if key not in entities:
                entities[key] = None
                unknown_found = True

        # 4. Handle standalone numbers
        nums = [m.group(1) for m in self.number_pattern.finditer(text)]
        
        extracted_values = [str(v) for v in entities.values() if v is not None]
        unassigned_nums = [n for n in nums if n not in extracted_values]

        if unassigned_nums:
            for i, num_str in enumerate(unassigned_nums):
                key = f"op_{len(entities) + 1}"
                entities[key] = float(num_str) if '.' in num_str else int(num_str)

        # 5. Final Result marker
        if not unknown_found and len(entities) >= 2:
             if "result" not in entities:
                 entities["result"] = None

        return entities
