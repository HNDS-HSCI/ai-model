import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from hsci.core.data_types import Concept
from hsci.core.kernel import CognitiveContext
from hsci.core.working_memory import SemanticFrame
from hsci.knowledge.knowledge_manager import IKnowledgeManager

logger = logging.getLogger("HSCI.Knowledge.UnderstandingEngine")

# ─────────────────────────────────────────────
# UNDERSTANDING RESULT REPRESENTATION
# ─────────────────────────────────────────────

class UnderstandingResult:
    """Encapsulates structured cognitive representations parsed from raw text."""
    def __init__(self, intent: str, seed_concepts: List[str], entities: Dict[str, str],
                 keywords: List[str], constraints: List[str], confidence: float,
                 ambiguities: List[str], normalized_query: str, explanations: Dict[str, str]):
        self.intent: str = intent
        self.seed_concepts: List[str] = seed_concepts
        self.entities: Dict[str, str] = entities
        self.keywords: List[str] = keywords
        self.constraints: List[str] = constraints
        self.confidence: float = confidence
        self.ambiguities: List[str] = ambiguities
        self.normalized_query: str = normalized_query
        self.explanations: Dict[str, str] = explanations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "seed_concepts": self.seed_concepts,
            "entities": self.entities,
            "keywords": self.keywords,
            "constraints": self.constraints,
            "confidence": self.confidence,
            "ambiguities": self.ambiguities,
            "normalized_query": self.normalized_query,
            "explanations": self.explanations
        }


# ─────────────────────────────────────────────
# UNDERSTANDING ENGINE INTERFACE
# ─────────────────────────────────────────────

class IUnderstandingEngine(ABC):
    """Abstract interface defining user text translation to structured frames."""
    @abstractmethod
    def understand(self, text: str, context: CognitiveContext) -> UnderstandingResult:
        pass


# ─────────────────────────────────────────────
# DETERMINISTIC UNDERSTANDING ENGINE
# ─────────────────────────────────────────────

class UnderstandingEngine(IUnderstandingEngine):
    """
    Deterministic rule-based parser mapping human language query stems
    to registered semantic concepts via the IKnowledgeManager facade.
    """
    def __init__(self, manager: IKnowledgeManager):
        self.manager: IKnowledgeManager = manager

    def understand(self, text: str, context: CognitiveContext) -> UnderstandingResult:
        """Executes the 8-stage translation pipeline to structured result frames."""
        explanations: Dict[str, str] = {}

        # Stage 1: Input Normalization
        normalized = text.lower().strip()
        # Remove standard punctuation but keep periods inside alphanumeric contexts
        normalized = re.sub(r"[^\w\s\.]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        explanations["normalization"] = f"Cleaned raw input: '{text}' -> '{normalized}'"

        # Stage 2: Sentence Segmentation
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", normalized) if s.strip()]
        explanations["segmentation"] = f"Identified {len(sentences)} sentence boundary frames."

        # Stage 3: Tokenization
        tokens = []
        for s in sentences:
            tokens.extend([w for w in s.split(" ") if w])
        explanations["tokenization"] = f"Tokenized words: {tokens}"

        # Stage 4: Entity Extraction
        entities = {}
        # Simple entity matcher: Programming domains & math parameters
        entity_rules = {
            "java": "language",
            "python": "language",
            "cpp": "language",
            "c": "language",
            "integer": "data_type",
            "float": "data_type",
            "string": "data_type",
            "class": "construct",
            "object": "construct"
        }
        for token in tokens:
            if token in entity_rules:
                entities[token] = entity_rules[token]
        explanations["entity_extraction"] = f"Extracted semantic entities: {entities}"

        # Stage 5: Concept Resolution through KnowledgeManager
        seed_concepts = []
        ambiguities = []
        
        # Test N-Grams (up to trigrams) to resolve compound terms like "arithmetic operator"
        resolved_ids = set()
        resolved_names = set()
        
        n = len(tokens)
        i = 0
        while i < n:
            resolved_segment = False
            for length in [3, 2, 1]:
                if i + length <= n:
                    phrase = " ".join(tokens[i:i+length])
                    
                    # 1. Direct name lookup
                    concept = self.manager.get_concept_by_name(phrase)
                    if not concept:
                        # 2. Try alias lookup
                        resolved_aliases = self.manager.concept_store.repository.resolve_alias(phrase)
                        if len(resolved_aliases) == 1:
                            concept = resolved_aliases[0]
                        elif len(resolved_aliases) > 1:
                            # Flag ambiguity if name matches multiple concepts
                            concept = resolved_aliases[0]
                            ambiguities.append(f"Alias '{phrase}' matches multiple concepts: {[c.name for c in resolved_aliases]}")
                    
                    if concept and concept.id not in resolved_ids:
                        seed_concepts.append(concept.name)
                        resolved_ids.add(concept.id)
                        resolved_names.add(concept.name)
                        resolved_segment = True
                        i += length
                        break
            if not resolved_segment:
                i += 1

        explanations["concept_resolution"] = f"Resolved concept seeds: {seed_concepts}"

        # Stage 6: Intent Classification
        intent = "GeneralQuery"
        confidence = 0.50
        
        # Simple prefix syntax matching rules
        intent_rules = [
            (r"\b(what is|explain|describe|define)\b", "ExplainConcept", 0.95),
            (r"\b(solve|evaluate|calculate|compute)\b", "SolveEquation", 0.90),
            (r"\b(prove|verify|check)\b", "VerifyAxiom", 0.85)
        ]
        
        for pattern, classification, score in intent_rules:
            if re.search(pattern, normalized):
                intent = classification
                confidence = score
                break
                
        explanations["intent_classification"] = f"Classified intent as '{intent}' with {confidence} confidence."

        # Stage 7: Ambiguity Detection (add custom validation checks)
        if len(seed_concepts) == 0:
            ambiguities.append("No active UKM concepts resolved.")
            confidence = max(0.10, confidence - 0.20)
        explanations["ambiguity_detection"] = f"Detected {len(ambiguities)} ambiguity alerts: {ambiguities}"

        # Stage 8: Produce UnderstandingResult
        result = UnderstandingResult(
            intent=intent,
            seed_concepts=seed_concepts,
            entities=entities,
            keywords=tokens,
            constraints=[],
            confidence=confidence,
            ambiguities=ambiguities,
            normalized_query=normalized,
            explanations=explanations
        )

        # Populate WorkingMemory
        self._populate_working_memory(result, context)
        return result

    def _populate_working_memory(self, result: UnderstandingResult, context: CognitiveContext) -> None:
        """Synchronizes understanding frames into the request WorkingMemory."""
        wm = context.working_memory
        
        # Populate SemanticFrame
        wm.semantic_frame = SemanticFrame(
            intent=result.intent,
            entities=result.entities,
            raw_tokens=result.keywords
        )
        
        # Populate AttentionBuffer with seed concepts as top salient items
        for concept in result.seed_concepts:
            wm.attention_buffer.add_salience(concept, 1.0)
