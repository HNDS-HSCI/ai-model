import re
from typing import Dict, List, Any, Optional
from hsci.core.data_types import StructuredInput, EntityValue, AxiomType
from hsci.neural.entity_extractor import EntityExtractor

class SpacyParser:
    """
    Rule-based language parser using heuristics and EntityExtractor.
    v3.1: Improved to avoid duplicate entity extraction.
    """

    def __init__(self):
        self.entity_extractor = EntityExtractor()

    def parse(self, text: str) -> StructuredInput:
        """
        Parses text into StructuredInput.
        """
        # 1. Delegate entity extraction to the more robust EntityExtractor
        entities_raw = self.entity_extractor.extract(text)
        
        entities: Dict[str, EntityValue] = {}
        unknowns: List[str] = []
        
        # 2. Convert to EntityValue and track unknowns
        for k, v in entities_raw.items():
            if isinstance(v, EntityValue):
                 entities[k] = v
                 if not v.known:
                     unknowns.append(k)
            else:
                 is_known = v is not None
                 entities[k] = EntityValue(
                     value=v,
                     unit=None,
                     known=is_known,
                     raw_text=str(v)
                 )
                 if not is_known:
                     unknowns.append(k)

        # Default unknowns
        if not unknowns:
            if "result" not in entities:
                entities["result"] = EntityValue(None, None, False, "inferred")
                unknowns.append("result")

        # Intent Discovery (Axiomatic Mapping)
        intent = AxiomType.REDUCTION.value
        confidence = 0.8
        domain = "arithmetic"

        text_lower = text.lower()
        
        # 1. TRANSFORMATION (Conversational/Social)
        social_keywords = ["hi", "hello", "hey", "greetings", "help", "who are you"]
        if any(w in text_lower for w in social_keywords):
            intent = AxiomType.TRANSFORMATION.value
            confidence = 0.95
            domain = "general"
        
        # 2. SYNTHESIS (Coding/Creation)
        elif any(w in text_lower for w in ["write code", "implement", "script", "function for", "algorithm"]):
            intent = AxiomType.SYNTHESIS.value
            confidence = 0.85
            domain = "software_engineering"

        # 3. COMPOSITION (Logic Puzzles/Constraints)
        elif any(w in text_lower for w in ["given", "if", "relationship"]):
            intent = AxiomType.COMPOSITION.value
            confidence = 0.75
            domain = "logic"

        # 4. Domain Refinement for REDUCTION
        if intent == AxiomType.REDUCTION.value:
            if any(w in text_lower for w in ["salary", "tax", "price", "discount", "interest"]):
                domain = "finance"
            elif any(w in text_lower for w in ["velocity", "force", "mass", "acceleration", "distance", "gravity"]):
                domain = "physics"

        return StructuredInput(
            entities=entities,
            intent=intent,
            axiom=intent,
            unknowns=unknowns,
            domain=domain,
            operation_hint="llm_perceived_intent" if confidence > 0.9 else "rule_based_inference",
            confidence=confidence,
            raw_normalized=text.strip(),
            parse_method="spacy"
        )
