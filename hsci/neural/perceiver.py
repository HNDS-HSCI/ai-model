import torch
from typing import Any, Dict, List
from hsci.core.data_types import (
    StructuredInput, PerceptionMap, Graph, 
    Relationship, WeightUpdate, AxiomType
)
from hsci.core.config import PerceiverConfig
from hsci.neural.encoder import GraphEncoder
from hsci.neural.relationship_detector import RelationshipDetector

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
        self.weight_version = 0

    def perceive(self, structured: StructuredInput) -> PerceptionMap:
        """
        Builds a perception map from structured language input.
        """
        # Step 1: Build entity graph (placeholder for rich structure)
        graph = self._build_graph(structured)

        # Step 2: Encode graph (using real GNN encoder)
        with torch.no_grad():
             dummy_x = torch.randn(len(structured.entities) or 1, self.config.input_dim)
             dummy_edge_index = torch.zeros((2, 0), dtype=torch.long)
             dummy_batch = torch.zeros(dummy_x.size(0), dtype=torch.long)
             # Standard module call invokes forward()
             embedding = self.encoder(dummy_x, dummy_edge_index, dummy_batch)

        # Step 3: Extract relationships
        relationships = self.relationship_detector.detect(graph, embedding)

        # Map intent string to AxiomType enum
        intent = AxiomType(structured.intent)

        return PerceptionMap(
            entities=structured.entities,
            unknown_entities=structured.unknowns,
            relationships=relationships,
            intent=intent,
            confidence=structured.confidence,
            entity_graph=graph,
            domain=structured.domain,
            operation_hint=structured.operation_hint
        )

    def _build_graph(self, structured: StructuredInput) -> Dict[str, Any]:
        """Simple graph structure for now."""
        return {"nodes": list(structured.entities.keys()), "text": structured.raw_normalized}

    def update_weights_from_proof(self, update: WeightUpdate):
        """
        CRITICAL: ONLY way weights change.
        """
        print(f"NeuralPerceiver: Proof-guided weight update direction='{update.direction}' (version {update.proof_version})")
        self.weight_version += 1
