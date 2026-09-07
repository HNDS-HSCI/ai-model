from typing import Dict

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

    Parsing order:
      1. SemanticCompiler -- deterministic rule-based lexicon (NSG-1).
      2. SpacyParser -- regex/heuristic parser (entity extraction, incl.
         synthesis-target naming the tagger below doesn't attempt).
      3. TrainableSemanticParser -- real trained model (spaCy features + a
         BiLSTM tagger, trained from scratch, no external API/LLM). Only
         used when SpacyParser's own confidence is too low -- it fills the
         gap where the deterministic paths fail, it doesn't preempt them.
      4. LLMParser -- optional local-model escalation (opt-in, off by default).
    """

    CONFIDENCE_THRESHOLD = 0.70
    TRAINABLE_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self, use_llm: bool = False, use_trainable: bool = True):
        self.spacy_parser = SpacyParser()
        self.semantic_compiler = SemanticCompiler()
        self.llm_parser = LLMParser("phi3:mini") if use_llm else None

        self.trainable_parser = None
        if use_trainable:
            self.trainable_parser = self._try_load_trainable_parser()

    @staticmethod
    def _try_load_trainable_parser():
        try:
            from hsci.language.semantic_tagger import TrainableSemanticParser

            candidate = TrainableSemanticParser()
            if candidate.load():
                return candidate
        except Exception:
            pass
        return None

    def parse(self, raw_input: str) -> StructuredInput:
        """
        Main entry point for parsing natural language.

        The deterministic SemanticCompiler stays authoritative for anything it
        already covers (exact field names like initial_quantity/change_quantity
        and full AST constraints feed the Z3 verifier's contradiction checks --
        regressing those would be a real correctness loss, not just a style
        change). The trained tagger only fills the gap: phrasing the rule-based
        lexicon doesn't recognize at all.
        """
        # 1. Deterministic path first (NSG-1) -- precise, fully verified, tested.
        sem_res = self.semantic_compiler.compile(raw_input)
        if isinstance(sem_res, SemanticIR):
            return self._structured_input_from_semantic_ir(sem_res, "semantic_compiler")

        # 2. Regex/heuristic parser -- still authoritative when it's confident
        # (e.g. it extracts synthesis-target names the tagger below never sees).
        result = self.spacy_parser.parse(raw_input)
        if result.confidence >= self.CONFIDENCE_THRESHOLD:
            return result

        # 3. Trained tagger fills the gap when the deterministic paths aren't
        # confident -- only takes over if it genuinely does better.
        if self.trainable_parser is not None:
            try:
                tagger_res = self.trainable_parser.compile(raw_input)
                if tagger_res.confidence >= self.TRAINABLE_CONFIDENCE_THRESHOLD and tagger_res.confidence > result.confidence:
                    return self._structured_input_from_semantic_ir(tagger_res, "trainable_semantic_tagger")
            except Exception:
                pass

        # 4. Escalate to LLM if still low confidence
        if self.llm_parser and self.llm_parser.available:
            llm_result = self.llm_parser.parse(raw_input)
            if llm_result.confidence > result.confidence:
                return llm_result

        return result

    def _structured_input_from_semantic_ir(self, sem_res: SemanticIR, parse_method: str) -> StructuredInput:
        typed_entities: Dict[str, EntityValue] = {}
        for k, v in sem_res.entities.items():
            if isinstance(v, EntityValue):
                typed_entities[k] = v
            else:
                typed_entities[k] = EntityValue(value=v, unit=None, known=v is not None, raw_text=str(v))
        if not any(not e.known for e in typed_entities.values()):
            typed_entities.setdefault("result", EntityValue(value=None, unit=None, known=False, raw_text="result"))

        # Map op_1 and op_2 if present for SolutionBuilder compatibility
        if "initial_quantity" in sem_res.entities and "change_quantity" in sem_res.entities:
            typed_entities["op_1"] = EntityValue(value=sem_res.entities["initial_quantity"], unit=None, known=True, raw_text=str(sem_res.entities["initial_quantity"]))
            typed_entities["op_2"] = EntityValue(value=sem_res.entities["change_quantity"], unit=None, known=True, raw_text=str(sem_res.entities["change_quantity"]))

        unknowns = [k for k, v in typed_entities.items() if not v.known] or ["result"]

        return StructuredInput(
            entities=typed_entities,
            intent=sem_res.intent or "REDUCTION",
            axiom=sem_res.intent or "REDUCTION",
            unknowns=unknowns,
            domain=sem_res.domain,
            operation_hint=parse_method,
            confidence=sem_res.confidence,
            raw_normalized=sem_res.raw_text,
            parse_method=parse_method,
            semantic_ir=sem_res
        )
