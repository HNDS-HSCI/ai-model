import re
from typing import Any

from hsci.core.data_types import AxiomType, PerceiverConfig, PerceptionMap

class IntentClassifier:
    """
    Classifies the intent of the input into one of the AxiomType categories.
    Initially rule-based using keywords, later to be replaced by a neural component.
    """

    def __init__(self, input_dim: int, num_classes: int):
        # input_dim and num_classes are for the future neural network.
        # For now, they are ignored for the rule-based approach.
        self.input_dim = input_dim
        self.num_classes = num_classes

        # Rule-based keyword matching for intent classification
        self.reduction_keywords = ["solve", "calculate", "find", "compute", "what is", "distance", "velocity", "acceleration", "force"]
        self.composition_keywords = ["given", "if", "relationship between"]
        self.synthesis_keywords = ["write code", "build", "implement", "create algorithm"]
        self.transformation_keywords = ["convert", "translate", "explain", "summarize"]

    def __call__(self, text_or_embedding: Any) -> PerceptionMap:
        """
        Classifies the intent based on keywords in the input text.
        For neural integration, this would take an embedding. For now, it takes text.
        """
        # For rule-based, we expect raw text. In a full system,
        # the NeuralPerceiver would pass an embedding.
        if not isinstance(text_or_embedding, str):
            # This is a placeholder for when a neural embedding is actually used.
            # For now, we'll assume text is passed directly for rule-based classification.
            # A more robust system would handle this by inspecting the full input_signal
            # or by having a separate text processing step before this.
            return PerceptionMap(
                entities={},
                unknown_entities=[],
                relationships=[],
                intent=AxiomType.REDUCTION, # Default or error handling
                confidence=0.0,
                entity_graph=None
            )
        
        text = text_or_embedding.lower()
        
        # Check for SYNTHESIS intent
        for keyword in self.synthesis_keywords:
            if keyword in text:
                return PerceptionMap(
                    entities={},
                    unknown_entities=[],
                    relationships=[],
                    intent=AxiomType.SYNTHESIS,
                    confidence=0.9, # High confidence for direct keyword match
                    entity_graph=None
                )

        # Check for COMPOSITION intent
        # "given...find" and "if...then" imply two parts to the query
        if any(kw in text for kw in ["given", "if"]) and "find" in text:
            return PerceptionMap(
                entities={},
                unknown_entities=[],
                relationships=[],
                intent=AxiomType.COMPOSITION,
                confidence=0.8,
                entity_graph=None
            )
        for keyword in self.composition_keywords:
            if keyword in text:
                return PerceptionMap(
                    entities={},
                    unknown_entities=[],
                    relationships=[],
                    intent=AxiomType.COMPOSITION,
                    confidence=0.7,
                    entity_graph=None
                )

        # Check for TRANSFORMATION intent
        for keyword in self.transformation_keywords:
            if keyword in text:
                return PerceptionMap(
                    entities={},
                    unknown_entities=[],
                    relationships=[],
                    intent=AxiomType.TRANSFORMATION,
                    confidence=0.85,
                    entity_graph=None
                )

        # Default to REDUCTION if no other intent is strongly matched
        # Check for REDUCTION intent last, as it's the most general arithmetic/logic
        for keyword in self.reduction_keywords:
            if keyword in text:
                return PerceptionMap(
                    entities={},
                    unknown_entities=[],
                    relationships=[],
                    intent=AxiomType.REDUCTION,
                    confidence=0.6, # Lower confidence if it's a general keyword
                    entity_graph=None
                )

        # If no keywords are matched, default to REDUCTION with low confidence
        return PerceptionMap(
            entities={},
            unknown_entities=[],
            relationships=[],
            intent=AxiomType.REDUCTION,
            confidence=0.1,
            entity_graph=None
        )