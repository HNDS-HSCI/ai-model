from typing import Any, List, Dict, Optional
from hsci.core.data_types import PerceptionMap, ProofTrace, WeightUpdate

class ProofGuidedWeightUpdater:
    """
    Computes neural weight updates from Z3 proof traces.

    Key insight: A proof trace tells us WHICH features of the
    perception were structurally relevant to the correct solution.
    The direction_hint carries the correct AxiomType to the NeuralPerceiver
    so it can run a real gradient update on the NativeNeuralClassifier.
    """

    def compute_update(
        self,
        perception: PerceptionMap,
        proof_trace: Any,
        direction: str,
        learning_rate: float,
        intent_hint: str = ""      # Phase 3: pass correct AxiomType.value
    ) -> WeightUpdate:

        deltas = {}

        if hasattr(proof_trace, 'concepts_applied'):
            # Strengthen concepts that appeared in proof
            for concept_name in proof_trace.concepts_applied:
                param_name = f"concept_weight_{concept_name}"
                deltas[param_name] = learning_rate

        # Features that did NOT contribute get slight weakening
        all_features = set(perception.entities.keys())
        contributing = set()
        if hasattr(proof_trace, 'variable_assignments'):
             contributing = set(proof_trace.variable_assignments.keys())

        non_contributing = all_features - contributing
        for feature in non_contributing:
            deltas[f"entity_weight_{feature}"] = -0.001

        return WeightUpdate(
            deltas=deltas,
            direction=direction,
            learning_rate=learning_rate,
            proof_version=getattr(proof_trace, 'version', 0) if hasattr(proof_trace, 'version') else 0,
            source="proof" if direction == "strengthen" else "counterexample",
            direction_hint=intent_hint,   # Phase 3: carry intent to perceiver
        )
