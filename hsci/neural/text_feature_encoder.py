"""
NativeTextEncoder — Phase 1 of HSCI Activation
Converts raw text entities into real feature vectors for the GNN.
No external NLP library (no spaCy, no BERT, no transformers).
Uses character-level features + numeric normalization.
Input dim: 256 (matches PerceiverConfig.input_dim)
"""
import torch
from typing import Dict, Any, Optional
from hsci.core.data_types import EntityValue

# ─── Character vocabulary for feature extraction ───────────────────────────
CHAR_VOCAB = "abcdefghijklmnopqrstuvwxyz0123456789+-*/=._, "
CHAR_TO_IDX = {c: i + 1 for i, c in enumerate(CHAR_VOCAB)}  # 0 = padding
VOCAB_SIZE = len(CHAR_VOCAB) + 1

# Domain vocabulary for one-hot domain encoding
DOMAINS = ["arithmetic", "physics", "finance", "geometry", "algebra", "logic", "general", "unknown"]
DOMAIN_TO_IDX = {d: i for i, d in enumerate(DOMAINS)}

# Known operation keyword embeddings
OP_KEYWORDS = {
    "add": 0, "plus": 0, "sum": 0,
    "subtract": 1, "minus": 1, "less": 1,
    "multiply": 2, "times": 2, "product": 2,
    "divide": 3, "division": 3, "ratio": 3,
    "percent": 4, "rate": 4, "tax": 4, "discount": 4,
    "distance": 5, "velocity": 5, "speed": 5,
    "force": 6, "mass": 6, "accel": 6,
    "area": 7, "length": 7, "width": 7,
}


class NativeTextEncoder:
    """
    Converts entity dictionaries and domain hints into real PyTorch tensors.
    Used by NeuralPerceiver to feed real (non-random) data into the GNN.

    Feature vector layout (256 dims total):
      [0:45]   — character-level name hash (45 chars max)
      [45]     — is_known flag (1.0 = known, 0.0 = unknown)
      [46:48]  — numeric value (normalized + log-scale)
      [48:58]  — unit/domain hash (10 chars)
      [58:68]  — operation keyword presence (10 op categories)
      [68:76]  — domain one-hot (8 domains)
      [76:256] — zero padding
    """

    def encode_entities(
        self,
        entities: Dict[str, Any],
        input_dim: int = 256,
        domain: str = "general"
    ) -> torch.Tensor:
        """
        Encode a dict of EntityValue objects into a (N, input_dim) tensor.
        Each row corresponds to one entity.
        """
        rows = []
        for name, ev in entities.items():
            if not isinstance(ev, EntityValue):
                # Wrap raw values
                ev = EntityValue(value=ev, unit=None, known=(ev is not None), raw_text=str(ev))

            vec = torch.zeros(input_dim)

            # ── [0:45] Character-level name encoding ──────────────────────
            name_lower = name.lower()[:45]
            for i, ch in enumerate(name_lower):
                idx = CHAR_TO_IDX.get(ch, 0)
                vec[i] = idx / VOCAB_SIZE

            # ── [45] Known/Unknown flag ────────────────────────────────────
            vec[45] = 1.0 if ev.known else 0.0

            # ── [46:48] Numeric value features ────────────────────────────
            if ev.value is not None:
                try:
                    raw_val = float(ev.value)
                    # Linear normalized (clipped to [-1e6, 1e6])
                    vec[46] = max(-1.0, min(1.0, raw_val / 1e6))
                    # Log-scale for large values
                    import math
                    if raw_val > 0:
                        vec[47] = min(1.0, math.log10(raw_val + 1) / 10)
                    elif raw_val < 0:
                        vec[47] = max(-1.0, -math.log10(-raw_val + 1) / 10)
                except (TypeError, ValueError):
                    # String value — hash first 2 chars
                    sv = str(ev.value).lower()
                    vec[46] = CHAR_TO_IDX.get(sv[0], 0) / VOCAB_SIZE if sv else 0.0
                    vec[47] = CHAR_TO_IDX.get(sv[1], 0) / VOCAB_SIZE if len(sv) > 1 else 0.0

            # ── [48:58] Unit encoding ──────────────────────────────────────
            unit_str = (ev.unit or "").lower()[:10]
            for i, ch in enumerate(unit_str):
                vec[48 + i] = CHAR_TO_IDX.get(ch, 0) / VOCAB_SIZE

            # ── [58:68] Operation keyword presence ────────────────────────
            # Check if entity name matches known operation categories
            name_and_unit = (name.lower() + " " + unit_str)
            for kw, op_idx in OP_KEYWORDS.items():
                if kw in name_and_unit:
                    vec[58 + op_idx] = 1.0

            # ── [68:76] Domain one-hot ─────────────────────────────────────
            domain_idx = DOMAIN_TO_IDX.get(domain.lower(), DOMAIN_TO_IDX["unknown"])
            if 68 + domain_idx < input_dim:
                vec[68 + domain_idx] = 1.0

            rows.append(vec)

        if not rows:
            return torch.zeros(1, input_dim)

        return torch.stack(rows)

    def build_edge_index(self, num_entities: int) -> torch.Tensor:
        """
        Builds a fully-connected directed edge index for the entity graph.
        Every entity node connects to every other entity node.
        Returns shape (2, E) where E = num_entities * (num_entities - 1).
        """
        if num_entities <= 1:
            return torch.zeros((2, 0), dtype=torch.long)

        src, dst = [], []
        for i in range(num_entities):
            for j in range(num_entities):
                if i != j:
                    src.append(i)
                    dst.append(j)

        return torch.tensor([src, dst], dtype=torch.long)

    def encode_text_bag(self, text: str, input_dim: int = 256) -> torch.Tensor:
        """
        Encodes raw text as a single bag-of-characters feature vector.
        Used as a fallback when entities dict is empty.
        """
        vec = torch.zeros(input_dim)
        text_lower = text.lower()[:input_dim]
        for i, ch in enumerate(text_lower):
            idx = CHAR_TO_IDX.get(ch, 0)
            vec[i] = idx / VOCAB_SIZE
        return vec.unsqueeze(0)  # shape (1, input_dim)
