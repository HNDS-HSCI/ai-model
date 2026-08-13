from hsci.core.data_types import StructuredInput, SemanticIR, SemanticCompilationFailure, EntityValue
from hsci.language.spacy_parser import SpacyParser
from hsci.language.llm_parser import LLMParser
from hsci.language.semantic_compiler import SemanticCompiler


class LanguageBridge:
    """
    LAYER 0: Language Bridge
    Only entry point for raw human language into HSCI.
    Converts ANY natural language to StructuredInput or SemanticIR.
    NEVER answers questions. Only extracts structure.
    """

    CONFIDENCE_THRESHOLD = 0.70

    def __init__(self, use_llm: bool = False):
        self.spacy_parser = SpacyParser()
        self.semantic_compiler = SemanticCompiler()
        self.llm_parser = LLMParser("phi3:mini") if use_llm else None

    def parse(self, raw_input: str) -> StructuredInput:
        """
        Main entry point for parsing natural language.
        """
        # Try SemanticCompiler first (NSG-1 local, deterministic)
        sem_res = self.semantic_compiler.compile(raw_input)
        if isinstance(sem_res, SemanticIR):
            typed_entities: Dict[str, EntityValue] = {}
            for k, v in sem_res.entities.items():
                if isinstance(v, EntityValue):
                    typed_entities[k] = v
                else:
                    typed_entities[k] = EntityValue(value=v, unit=None, known=v is not None, raw_text=str(v))
            if "result" not in typed_entities:
                typed_entities["result"] = EntityValue(value=None, unit=None, known=False, raw_text="result")

            # Map op_1 and op_2 if present for SolutionBuilder compatibility
            if "initial_quantity" in sem_res.entities and "change_quantity" in sem_res.entities:
                typed_entities["op_1"] = EntityValue(value=sem_res.entities["initial_quantity"], unit=None, known=True, raw_text=str(sem_res.entities["initial_quantity"]))
                typed_entities["op_2"] = EntityValue(value=sem_res.entities["change_quantity"], unit=None, known=True, raw_text=str(sem_res.entities["change_quantity"]))

            return StructuredInput(
                entities=typed_entities,
                intent=sem_res.intent or "REDUCTION",
                axiom=sem_res.intent or "REDUCTION",
                unknowns=["result"],
                domain=sem_res.domain,
                operation_hint="nsg1_semantic_compiler",
                confidence=sem_res.confidence,
                raw_normalized=sem_res.raw_text,
                parse_method="semantic_compiler",
                semantic_ir=sem_res
            )



        # Fall back to spaCy parser
        result = self.spacy_parser.parse(raw_input)

        # Escalate to LLM if confidence is low
        if result.confidence < self.CONFIDENCE_THRESHOLD:
            if self.llm_parser and self.llm_parser.available:
                llm_result = self.llm_parser.parse(raw_input)
                if llm_result.confidence > result.confidence:
                    return llm_result

        return result

