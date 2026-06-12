"""
WeightPersistence — Phase 5 of HSCI Activation
Saves and loads neural weights between sessions so HSCI's learning is permanent.
Saves: GNN encoder + intent classifier + training stats.
Auto-loads on RIRLoop startup.
"""
import torch
import json
from pathlib import Path
from typing import Optional


class WeightPersistence:
    """
    Persists HSCI neural weights between sessions.
    HSCI learns in session N → weights saved → loaded in session N+1.
    This makes learning permanent — the system gets smarter over time.
    """

    WEIGHTS_DIR = Path("weights")
    DEFAULT_FILENAME = "hsci_weights.pt"
    STATS_FILENAME = "hsci_training_stats.json"

    def save(self, perceiver, filename: Optional[str] = None):
        """
        Save GNN encoder + intent classifier weights to disk.
        Also saves training statistics as a JSON sidecar.
        """
        self.WEIGHTS_DIR.mkdir(exist_ok=True)
        path = self.WEIGHTS_DIR / (filename or self.DEFAULT_FILENAME)

        checkpoint = {
            "encoder_state_dict": perceiver.encoder.state_dict(),
            "intent_classifier_state_dict": perceiver.intent_classifier.state_dict(),
            "weight_version": perceiver.weight_version,
        }
        torch.save(checkpoint, path)

        # Save stats as JSON for easy inspection
        stats = perceiver.intent_classifier.stats()
        stats["weight_version"] = perceiver.weight_version
        stats_path = self.WEIGHTS_DIR / self.STATS_FILENAME
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        print(
            f"[WeightPersistence] ✅ Saved weights → {path} "
            f"(version={perceiver.weight_version}, "
            f"proof_count={stats['proof_count']})"
        )

    def load(self, perceiver, filename: Optional[str] = None) -> bool:
        """
        Load saved weights into the perceiver's encoder and classifier.
        Returns True if weights were loaded, False if starting fresh.
        """
        path = self.WEIGHTS_DIR / (filename or self.DEFAULT_FILENAME)

        if not path.exists():
            print("[WeightPersistence] No saved weights found — starting fresh.")
            return False

        try:
            checkpoint = torch.load(path, weights_only=True)
            perceiver.encoder.load_state_dict(checkpoint["encoder_state_dict"])
            perceiver.intent_classifier.load_state_dict(
                checkpoint["intent_classifier_state_dict"]
            )
            perceiver.weight_version = checkpoint.get("weight_version", 0)

            # Also restore proof_count so confidence thresholds adapt correctly
            stats_path = self.WEIGHTS_DIR / self.STATS_FILENAME
            if stats_path.exists():
                with open(stats_path) as f:
                    stats = json.load(f)
                perceiver.intent_classifier.proof_count = stats.get("proof_count", 0)

            print(
                f"[WeightPersistence] ✅ Loaded weights ← {path} "
                f"(version={perceiver.weight_version}, "
                f"proof_count={perceiver.intent_classifier.proof_count})"
            )
            return True

        except Exception as e:
            print(f"[WeightPersistence] ⚠️  Could not load weights: {e}. Starting fresh.")
            return False

    def inspect(self) -> dict:
        """Show saved weight stats without loading."""
        stats_path = self.WEIGHTS_DIR / self.STATS_FILENAME
        if stats_path.exists():
            with open(stats_path) as f:
                return json.load(f)
        return {}
