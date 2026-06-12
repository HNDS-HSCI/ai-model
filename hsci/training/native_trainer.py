"""
NativeTrainer — Phase 4 of HSCI Activation
Self-improving training loop using the existing concept corpus.
NO human labels. NO external models. 
The system learns from its own Z3-verified proofs.

How it works:
  1. Generate a problem from the concept corpus
  2. Feed it through the full RIR loop
  3. Z3 either proves or disproves the solution
  4. The proof result triggers a real gradient update (Phase 3)
  5. Repeat → the neural classifier gets smarter each iteration
"""
import random
import time
from typing import List, Tuple, Optional
from hsci.core.rir_loop import RIRLoop


# ─── Self-Play Training Corpus ─────────────────────────────────────────────
# Derived entirely from existing Z3 templates — no external data needed.
# Format: (input_text, expected_domain, expected_intent)
TRAINING_CORPUS: List[Tuple[str, str, str]] = [
    # ─── Arithmetic (REDUCTION) ───
    ("calculate 5 + 3", "arithmetic", "REDUCTION"),
    ("what is 100 - 45", "arithmetic", "REDUCTION"),
    ("compute 12 * 8", "arithmetic", "REDUCTION"),
    ("find result if a = 10 and b = 20", "arithmetic", "REDUCTION"),
    ("calculate 144 / 12", "arithmetic", "REDUCTION"),
    ("what is 7 plus 8", "arithmetic", "REDUCTION"),
    ("solve 250 minus 75", "arithmetic", "REDUCTION"),

    # ─── Finance (REDUCTION) ───
    ("find tax amount if salary = 50000 and rate = 0.3", "finance", "REDUCTION"),
    ("calculate profit if revenue = 1000 and cost = 700", "finance", "REDUCTION"),
    ("what is 20 percent of 500", "finance", "REDUCTION"),
    ("find discount amount if price = 200 and rate = 15", "finance", "REDUCTION"),
    ("calculate interest if principal = 10000 and rate = 0.05 and time = 3", "finance", "REDUCTION"),

    # ─── Physics (REDUCTION) ───
    ("what is velocity if distance = 100 and time = 5", "physics", "REDUCTION"),
    ("compute force given mass = 10 and acceleration = 9.8", "physics", "REDUCTION"),
    ("find distance if velocity = 60 and time = 2", "physics", "REDUCTION"),
    ("calculate acceleration if force = 50 and mass = 5", "physics", "REDUCTION"),

    # ─── Geometry (REDUCTION) ───
    ("what is the area if length = 5 and width = 3", "geometry", "REDUCTION"),
    ("calculate area of rectangle if l = 8 and w = 4", "geometry", "REDUCTION"),
    ("find area if base = 10 and h = 6", "geometry", "REDUCTION"),

    # ─── Algebra (COMPOSITION) ───
    ("if a = 5 and b = 3, find sum", "algebra", "COMPOSITION"),
    ("given x = 10 and y = 4, find the difference", "algebra", "COMPOSITION"),

    # ─── Social / Conversational (TRANSFORMATION) ───
    ("hello", "general", "TRANSFORMATION"),
    ("hi there", "general", "TRANSFORMATION"),
    ("help me", "general", "TRANSFORMATION"),
    ("who are you", "general", "TRANSFORMATION"),
    ("explain what you can do", "general", "TRANSFORMATION"),

    # ─── Code synthesis (SYNTHESIS) ───
    ("write code to add two numbers", "software_engineering", "SYNTHESIS"),
    ("implement a function to calculate area", "software_engineering", "SYNTHESIS"),
    ("create algorithm for sorting", "software_engineering", "SYNTHESIS"),
]


class NativeTrainer:
    """
    HSCI Self-Supervised Trainer.
    Runs the full RIR pipeline on synthetic examples.
    Z3 proof outcomes drive gradient updates in the neural classifier.

    This is the training loop that makes HSCI learn — entirely from
    its own symbolic verification, no human labels needed.
    """

    def __init__(self, rir: RIRLoop):
        self.rir = rir
        self.epoch_results: List[float] = []
        self.total_proofs = 0
        self.total_verified = 0

    def run_epoch(self, n_samples: int = 20, verbose: bool = False) -> float:
        """
        Run one self-play training epoch.

        For each sample:
          - Process through the full RIR loop
          - Z3 automatically triggers proof-guided weight update (Phase 3)
          - Track accuracy

        Returns: epoch accuracy (fraction of verified solutions)
        """
        samples = random.choices(TRAINING_CORPUS, k=n_samples)
        verified_count = 0

        for text, domain, expected_intent in samples:
            try:
                final_out, structured = self.rir.process_internal(text)
                self.total_proofs += 1

                if final_out.is_verified:
                    verified_count += 1
                    self.total_verified += 1

                if verbose:
                    status = "✅ VERIFIED" if final_out.is_verified else "❌ FAILED"
                    print(f"  {status} | '{text[:50]}' | concepts={final_out.concepts_used}")

            except Exception as e:
                if verbose:
                    print(f"  ⚠️  ERROR | '{text[:50]}' | {e}")

        accuracy = verified_count / n_samples
        self.epoch_results.append(accuracy)
        return accuracy

    def train(
        self,
        epochs: int = 50,
        samples_per_epoch: int = 20,
        verbose_every: int = 10,
        save_weights: bool = True
    ):
        """
        Full self-improving training loop.

        Args:
            epochs: Number of training epochs
            samples_per_epoch: How many problems to process per epoch
            verbose_every: Print detail every N epochs
            save_weights: Whether to persist weights after training
        """
        print(f"\n{'='*60}")
        print(f"🧠 HSCI Native Self-Training Loop")
        print(f"   Epochs: {epochs} | Samples/epoch: {samples_per_epoch}")
        print(f"   No LLMs. No labels. Pure proof-guided learning.")
        print(f"{'='*60}\n")

        start_time = time.time()

        for epoch in range(1, epochs + 1):
            verbose = (epoch % verbose_every == 0 or epoch == 1)
            acc = self.run_epoch(n_samples=samples_per_epoch, verbose=False)

            if epoch % verbose_every == 0 or epoch == 1:
                trend = ""
                if len(self.epoch_results) > 1:
                    delta = self.epoch_results[-1] - self.epoch_results[-2]
                    trend = f"↑ +{delta:.1%}" if delta > 0 else (f"↓ {delta:.1%}" if delta < 0 else "→")

                classifier_stats = self.rir.perceiver.intent_classifier.stats()
                print(
                    f"  Epoch {epoch:03d}/{epochs} | "
                    f"Accuracy: {acc:.1%} {trend} | "
                    f"Proofs: {self.total_proofs} | "
                    f"Neural updates: {classifier_stats['proof_count']} | "
                    f"Avg loss: {classifier_stats['avg_loss']:.4f}"
                )

        elapsed = time.time() - start_time
        final_acc = self.epoch_results[-1] if self.epoch_results else 0.0

        print(f"\n{'='*60}")
        print(f"✅ Training Complete!")
        print(f"   Total epochs:   {epochs}")
        print(f"   Total proofs:   {self.total_proofs}")
        print(f"   Verified:       {self.total_verified} ({self.total_verified/max(1,self.total_proofs):.1%})")
        print(f"   Final accuracy: {final_acc:.1%}")
        print(f"   Time elapsed:   {elapsed:.1f}s")
        print(f"{'='*60}\n")

        if save_weights:
            self._save_weights()

        return self.epoch_results

    def _save_weights(self):
        """Save trained neural weights to disk."""
        try:
            from hsci.training.weight_persistence import WeightPersistence
            wp = WeightPersistence()
            wp.save(self.rir.perceiver)
        except Exception as e:
            print(f"[NativeTrainer] Could not save weights: {e}")

    def benchmark(self) -> dict:
        """Run a quick accuracy benchmark without training."""
        acc = self.run_epoch(n_samples=len(TRAINING_CORPUS), verbose=True)
        return {
            "accuracy": acc,
            "total": len(TRAINING_CORPUS),
            "verified": int(acc * len(TRAINING_CORPUS))
        }
