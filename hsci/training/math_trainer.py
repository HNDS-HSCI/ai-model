from datetime import datetime
from typing import List, Tuple, Dict, Any
from hsci.core.rir_loop import RIRLoop

MATH_TRAINING_EXAMPLES: List[Tuple[str, Any]] = [
    # Basic arithmetic
    ("2 + 3", 5),
    ("10 + 7", 17),
    ("100 + 50", 150),
    ("15 - 8", 7),
    ("100 - 37", 63),
    ("4 * 6", 24),
    ("12 * 11", 132),
    ("20 / 4", 5),
    ("100 / 8", 12.5),

    # Percentage
    ("20% of 500", 100),
    ("15% of 200", 30),
    ("tax is 18%, amount is 1000, find tax amount", 180),

    # Equations
    ("x + 5 = 10, find x", {"x": 5}),
    ("2x = 14, find x", {"x": 7}),
    ("x - 3 = 7, find x", {"x": 10}),

    # Multi-step
    ("salary is 5000, tax rate is 20%, find take-home pay", {"take_home": 4000}),
    ("base price 1000, discount 15%, find final price", {"final_price": 850}),
    ("rectangle length 8, width 5, find area", {"area": 40}),
]

class MathTrainer:
    """
    Orchestrates Phase 1: Math Training.
    Trains the HSCI system on basic arithmetic and algebra.
    """

    def __init__(self):
        self.loop = RIRLoop()

    def train(self):
        print(f"Starting Math Training Phase at {datetime.now()}")
        success_count = 0
        total = len(MATH_TRAINING_EXAMPLES)

        for i, (problem, expected) in enumerate(MATH_TRAINING_EXAMPLES):
            print(f"[{i+1}/{total}] Training on: {problem}")
            try:
                output = self.loop.process(problem)
                if output.is_verified:
                    print(f"  Success! Answer: {output.answer}")
                    success_count += 1
                else:
                    print(f"  Verification failed.")
            except Exception as e:
                print(f"  Error during processing: {e}")

        print(f"\nMath Training Complete.")
        print(f"Success Rate: {success_count}/{total} ({success_count/total:.1%})")

if __name__ == "__main__":
    trainer = MathTrainer()
    trainer.train()
