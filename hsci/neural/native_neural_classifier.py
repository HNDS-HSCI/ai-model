"""
NativeNeuralClassifier — Phase 2 of HSCI Activation
Replaces keyword-matching with a real trained PyTorch MLP.
Input: 128-dim GNN embedding (output of GraphEncoder)
Output: One of 4 AxiomTypes (REDUCTION, COMPOSITION, SYNTHESIS, TRANSFORMATION)

Training: Proof-guided — Z3 proofs are used as the ground-truth signal.
No human labels required. The system teaches itself.
"""
import torch
import torch.nn as nn
from typing import Tuple, Optional
from hsci.core.data_types import AxiomType


# Fallback keyword rules — used ONLY as initialization hints, then overridden by neural
_KEYWORD_RULES = {
    AxiomType.SYNTHESIS: ["write code", "implement", "script", "function for", "algorithm", "create", "build"],
    AxiomType.TRANSFORMATION: ["convert", "translate", "explain", "summarize", "hi", "hello", "hey", "who are you", "help"],
    AxiomType.COMPOSITION: ["given", "relationship between", "if and only", "logic"],
    AxiomType.REDUCTION: ["solve", "calculate", "find", "compute", "what is", "distance", "velocity", "force"],
}

def _keyword_fallback(text: str) -> Tuple[AxiomType, float]:
    """Initial keyword-based hint — used only when neural confidence is very low."""
    text_lower = text.lower()
    for axiom_type, keywords in _KEYWORD_RULES.items():
        if any(kw in text_lower for kw in keywords):
            return axiom_type, 0.6
    return AxiomType.REDUCTION, 0.3


class NativeNeuralClassifier(nn.Module):
    """
    HSCI Native Intent Classifier.
    A 3-layer MLP trained via proof-guided gradient updates.

    Architecture:
      Linear(128 → 64) → ReLU → Dropout(0.15)
      Linear(64 → 32) → ReLU
      Linear(32 → 4) → Softmax

    No pre-training needed. Starts with keyword-guided bootstrapping,
    then learns from Z3 proofs over time.
    """

    CLASSES = [
        AxiomType.REDUCTION,
        AxiomType.COMPOSITION,
        AxiomType.SYNTHESIS,
        AxiomType.TRANSFORMATION,
    ]

    NEURAL_CONFIDENCE_THRESHOLD = 0.45  # below this, fall back to keywords

    def __init__(self, input_dim: int = 128, num_classes: int = 4):
        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_classes),
        )

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=0.001, weight_decay=1e-4)

        # Track training stats
        self.proof_count = 0
        self.total_loss = 0.0

        # Initialize weights with Xavier for stable start
        self._init_weights()

    def _init_weights(self):
        for layer in self.net:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, embedding: torch.Tensor) -> Tuple[AxiomType, float]:
        """
        Classify a GNN embedding into one of 4 intent types.
        Returns (AxiomType, confidence_score).
        """
        if embedding is None or embedding.numel() == 0:
            return AxiomType.REDUCTION, 0.1

        # Handle both (1, D) and (D,) shaped tensors
        if embedding.dim() == 1:
            embedding = embedding.unsqueeze(0)

        with torch.no_grad():
            logits = self.net(embedding)
            probs = torch.softmax(logits, dim=-1)
            confidence, pred_idx = torch.max(probs, dim=-1)

        conf_val = confidence.item()
        pred_class = self.CLASSES[pred_idx.item()]

        return pred_class, conf_val

    def classify_with_fallback(self, embedding: torch.Tensor, raw_text: str = "") -> Tuple[AxiomType, float]:
        """
        Classify using neural network. Fall back to keywords if confidence is too low.
        This ensures correct behavior even before the network has been trained.
        """
        neural_intent, neural_conf = self(embedding)

        if neural_conf >= self.NEURAL_CONFIDENCE_THRESHOLD:
            return neural_intent, neural_conf

        # Low confidence — blend neural with keyword hint
        kw_intent, kw_conf = _keyword_fallback(raw_text)

        # Trust keywords more early on, neural more after training
        if self.proof_count < 20:
            return kw_intent, kw_conf
        elif self.proof_count < 100:
            # Blend: 50/50
            if neural_intent == kw_intent:
                return neural_intent, max(neural_conf, kw_conf)
            else:
                return kw_intent, kw_conf  # keywords win until trained enough
        else:
            # Fully trust neural after 100 proofs
            return neural_intent, neural_conf

    def update_from_proof(
        self,
        embedding: torch.Tensor,
        correct_intent: AxiomType,
        strengthen: bool,
        learning_rate: Optional[float] = None
    ) -> float:
        """
        Proof-guided training step.
        Called by LearningEngine after Z3 verifies or disproves a solution.

        Args:
            embedding: The GNN embedding that produced this classification
            correct_intent: The AxiomType that was (or should have been) correct
            strengthen: True if proof succeeded, False if it failed
            learning_rate: Optional override

        Returns:
            Loss value for monitoring
        """
        if embedding is None or embedding.numel() == 0:
            return 0.0

        if embedding.dim() == 1:
            embedding = embedding.unsqueeze(0)

        if learning_rate is not None:
            for pg in self.optimizer.param_groups:
                pg['lr'] = learning_rate

        target_idx = self.CLASSES.index(correct_intent)
        target = torch.tensor([target_idx], dtype=torch.long)

        self.optimizer.zero_grad()
        logits = self.net(embedding)

        if strengthen:
            # Standard cross-entropy: push toward correct class
            loss = self.criterion(logits, target)
        else:
            # Contrastive: penalize wrong class (weaker signal)
            loss = -0.2 * self.criterion(logits, target)

        loss.backward()
        self.optimizer.step()

        loss_val = abs(loss.item())
        self.proof_count += 1
        self.total_loss += loss_val

        return loss_val

    def stats(self) -> dict:
        """Return training statistics."""
        avg_loss = self.total_loss / max(1, self.proof_count)
        return {
            "proof_count": self.proof_count,
            "avg_loss": round(avg_loss, 4),
            "confidence_threshold": self.NEURAL_CONFIDENCE_THRESHOLD,
        }
