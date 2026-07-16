import torch
from typing import Any, Dict, List, Union, Optional
from hsci.core.data_types import (
    StructuredInput, PerceptionMap, Graph,
    Relationship, WeightUpdate, AxiomType, InputSignal, EntityValue
)
from hsci.core.config import PerceiverConfig
from hsci.neural.encoder import GraphEncoder
from hsci.neural.relationship_detector import RelationshipDetector
from hsci.neural.entity_extractor import EntityExtractor
from hsci.neural.text_feature_encoder import NativeTextEncoder   # Phase 1
from hsci.neural.native_neural_classifier import NativeNeuralClassifier  # Phase 2

class NeuralPerceiver:
    """
    LAYER 1: Neural Perceiver
    Converts StructuredInput to PerceptionMap.
    Weights updated ONLY by ProofGuidedWeightUpdater.
    """

    def __init__(self, config: PerceiverConfig):
        self.config = config
        self.encoder = GraphEncoder(
            input_dim=config.input_dim,
            hidden_dim=config.hidden_dim,
            output_dim=config.output_dim,
            num_layers=config.num_layers
        )
        self.relationship_detector = RelationshipDetector()
        # Phase 2: Real neural classifier (replaces keyword IntentClassifier)
        self.intent_classifier = NativeNeuralClassifier(
            input_dim=config.output_dim,  # GNN output dim (128)
            num_classes=4
        )
        self.entity_extractor = EntityExtractor()
        # Phase 1: Real text-to-tensor encoder
        self.text_encoder = NativeTextEncoder()
        self.weight_version = 0
        # Phase 3: Store last embedding for proof-guided backprop
        self.last_embedding: Optional[torch.Tensor] = None
        self.last_raw_text: str = ""

    def perceive(self, structured: Union[StructuredInput, InputSignal]) -> PerceptionMap:
        """
        Builds a perception map from structured language input or raw input signal.
        """
        if isinstance(structured, InputSignal):
            # Backward compatibility for tests
            entities_dict = self.entity_extractor.extract(structured.raw_text)
            entities = {
                k: EntityValue(value=v, unit=None, known=(v is not None), raw_text=str(v))
                for k, v in entities_dict.items()
            }
            unknowns = [k for k, v in entities_dict.items() if v is None]
            intent_perception = self.intent_classifier(structured.raw_text)

            structured = StructuredInput(
                entities=entities,
                intent=intent_perception.intent.value,
                axiom=intent_perception.intent.value,
                unknowns=unknowns,
                domain=intent_perception.domain,
                operation_hint="perceived_from_signal",
                confidence=intent_perception.confidence,
                raw_normalized=structured.raw_text,
                parse_method="neural_fallback"
            )

        # Step 1: Build entity graph
        graph = self._build_graph(structured)

        # Step 2: Encode graph using REAL entity features (Phase 1)
        with torch.no_grad():
            x = self.text_encoder.encode_entities(
                structured.entities,
                self.config.input_dim,
                domain=structured.domain
            )
            edge_index = self.text_encoder.build_edge_index(x.size(0))
            batch = torch.zeros(x.size(0), dtype=torch.long)
            embedding = self.encoder(x, edge_index, batch)

        # Step 3: Extract relationships
        relationships = self.relationship_detector.detect(graph, embedding)

        # Step 4: Store embedding for proof-guided learning (Phase 3)
        self.last_embedding = embedding.detach().clone()
        self.last_raw_text = structured.raw_normalized

        # Step 5: Neural intent classification (Phase 2)
        neural_intent, neural_conf = self.intent_classifier.classify_with_fallback(
            embedding, raw_text=structured.raw_normalized
        )

        # Blend: trust language bridge if it has high confidence (e.g. clear keywords),
        # otherwise use neural classification
        if structured.confidence >= 0.90:
            # Language bridge is very confident (e.g. social greeting) — trust it
            try:
                final_intent = AxiomType(structured.intent)
                final_confidence = structured.confidence
            except ValueError:
                final_intent = neural_intent
                final_confidence = neural_conf
        else:
            final_intent = neural_intent
            final_confidence = neural_conf

        perception = PerceptionMap(
            entities=structured.entities,
            unknown_entities=structured.unknowns,
            relationships=relationships,
            intent=final_intent,
            confidence=final_confidence,
            entity_graph=graph,
            domain=structured.domain,
            operation_hint=structured.operation_hint
        )
        # Keep the training sample on the perception that produced the proof.
        # A shared "last embedding" can be replaced by another request.
        perception._neural_embedding = embedding.detach().clone()
        return perception

    def _build_graph(self, structured: StructuredInput) -> Dict[str, Any]:
        """Simple graph structure for now."""
        return {"nodes": list(structured.entities.keys()), "text": structured.raw_normalized}

    def update_weights_from_proof(self, update: WeightUpdate, embedding: Optional[torch.Tensor] = None):
        """
        Phase 3: REAL gradient-based weight update.
        Uses the stored embedding + proof direction to train the neural classifier.
        """
        training_embedding = embedding
        if training_embedding is None:
            print("[NeuralPerceiver] No matching embedding, skipping weight update.")
            return

        strengthen = (update.direction == "strengthen")

        # Resolve intent from direction_hint (set by LearningEngine)
        intent_hint = getattr(update, 'direction_hint', '')
        try:
            correct_intent = AxiomType(intent_hint) if intent_hint else None
        except ValueError:
            correct_intent = None

        if correct_intent is not None:
            loss = self.intent_classifier.update_from_proof(
                training_embedding,
                correct_intent,
                strengthen=strengthen,
                learning_rate=update.learning_rate
            )
            self.weight_version += 1
            print(
                f"[NeuralPerceiver] Proof-guided update | "
                f"intent={correct_intent.value} | strengthen={strengthen} | "
                f"loss={loss:.4f} | version={self.weight_version}"
            )
        else:
            print(f"[NeuralPerceiver] Proof update skipped (no intent hint). direction='{update.direction}'")
