from hsci.core.data_types import StructuredInput
from hsci.language.spacy_parser import SpacyParser
from hsci.language.llm_parser import LLMParser

class LanguageBridge:
    """
    LAYER 0: Language Bridge
    Only entry point for raw human language into HSCI.
    Converts ANY natural language to StructuredInput.
    NEVER answers questions. Only extracts structure.
    """

    CONFIDENCE_THRESHOLD = 0.70

    def __init__(self, use_llm: bool = True):
        self.spacy_parser = SpacyParser()
        self.llm_parser = LLMParser("phi3:mini") if use_llm else None

    def parse(self, raw_input: str) -> StructuredInput:
        """
        Main entry point for parsing natural language.
        """
        # Try spaCy first (fast, rule-based)
        result = self.spacy_parser.parse(raw_input)

        # Escalate to LLM if confidence is low
        if result.confidence < self.CONFIDENCE_THRESHOLD:
            if self.llm_parser and self.llm_parser.available:
                llm_result = self.llm_parser.parse(raw_input)
                if llm_result.confidence > result.confidence:
                    return llm_result

        return result
