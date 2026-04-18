import re
from typing import Dict, List, Any, Optional
from hsci.core.data_types import StructuredInput, EntityValue, AxiomType

class SpacyParser:
    """
    Rule-based language parser using regex and heuristics.
    v3.1: Improved to avoid duplicate entity extraction.
    """

    def __init__(self):
        # Key must start with letter
        self.known_pattern = re.compile(r'([a-zA-Z_]\w*)\s*(?:is|=)\s*(\d+(?:\.\d+)?)(?:\s*(\w+|%))?')
        self.unknown_pattern = re.compile(r'(?:find|calculate|solve for|what is)\s+([\w\s-]+)(?=\W|$)')
        self.number_pattern = re.compile(r'\b(\d+(?:\.\d+)?)(?:\s*(\w+|%))?\b')

    def parse(self, text: str) -> StructuredInput:
        """
        Parses text into StructuredInput.
        """
        entities: Dict[str, EntityValue] = {}
        unknowns: List[str] = []

        # 1. Extract knowns (e.g., "salary is 5000")
        # We track character spans to avoid overlapping matches
        spans = []
        for match in self.known_pattern.finditer(text):
            name = match.group(1)
            val_str = match.group(2)
            unit = match.group(3)
            val = float(val_str) if '.' in val_str else int(val_str)
            
            # Normalize percentage
            if unit == '%':
                val = val / 100.0
                unit = 'percentage'
            
            entities[name] = EntityValue(
                value=val,
                unit=unit,
                known=True,
                raw_text=match.group(0)
            )
            spans.append(match.span())

        # 2. Extract unknowns
        for match in self.unknown_pattern.finditer(text):
            name = match.group(1).strip().lower().replace(' ', '_').replace('-', '_')
            if name not in entities:
                entities[name] = EntityValue(
                    value=None,
                    unit=None,
                    known=False,
                    raw_text=match.group(0)
                )
                unknowns.append(name)
            spans.append(match.span())

        # 3. Handle standalone numbers (only if not part of previous spans)
        unassigned_idx = 1
        for match in self.number_pattern.finditer(text):
            start, end = match.span()
            # Check if this number is already covered by a known_pattern span
            if any(s <= start and end <= e for s, e in spans):
                continue
                
            val_str = match.group(1)
            unit = match.group(2)
            val = float(val_str) if '.' in val_str else int(val_str)
            if unit == '%':
                val = val / 100.0
                unit = 'percentage'
            
            key = f"op_{unassigned_idx}"
            while key in entities:
                unassigned_idx += 1
                key = f"op_{unassigned_idx}"
            
            entities[key] = EntityValue(
                value=val,
                unit=unit,
                known=True,
                raw_text=match.group(0)
            )
            unassigned_idx += 1

        # Default unknowns
        if not unknowns:
            if "result" not in entities:
                entities["result"] = EntityValue(None, None, False, "inferred")
                unknowns.append("result")

        # Intent
        intent = AxiomType.REDUCTION.value
        if any(w in text.lower() for w in ["given", "if", "relationship"]):
            intent = AxiomType.COMPOSITION.value

        return StructuredInput(
            entities=entities,
            intent=intent,
            axiom=intent,
            unknowns=unknowns,
            domain="finance" if any(w in text.lower() for w in ["salary", "tax"]) else "arithmetic",
            operation_hint="basic_arithmetic",
            confidence=0.8,
            raw_normalized=text.strip(),
            parse_method="spacy"
        )
