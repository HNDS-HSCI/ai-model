"""Compatibility adapter for the retired HNSDS neural-lobe interface."""

from hsci.neural.native_neural_classifier import _keyword_fallback


class NativeNeuralLobe:
    """Maps the legacy API onto the maintained HSCI intent classifier."""

    _TRAJECTORIES = {
        "REDUCTION": "MATH_REDUCTION",
        "COMPOSITION": "LOGIC_COMPOSITION",
        "SYNTHESIS": "CODE_SYNTHESIS",
        "TRANSFORMATION": "CONVERSATIONAL_FLOW",
    }

    _TYPES = {
        "REDUCTION": "mathematical",
        "COMPOSITION": "logical",
        "SYNTHESIS": "coding",
        "TRANSFORMATION": "conversational",
    }

    def classify_and_formalize(self, text: str) -> dict:
        result = _keyword_fallback(text)
        intent = result.intent.value
        return {
            "type": self._TYPES[intent],
            "intent": intent,
            "confidence": result.confidence,
            "domain": result.domain,
            "raw": text,
        }

    def simulate_trajectory(self, text: str) -> dict:
        specification = self.classify_and_formalize(text)
        specification.update(
            {
                "trajectory": self._TRAJECTORIES[specification["intent"]],
                "path": ["PERCEPTION", specification["intent"], "RESPONSE"],
                "desc": text,
            }
        )
        return specification
