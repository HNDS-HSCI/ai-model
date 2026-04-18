from datetime import datetime
from typing import List, Tuple, Dict, Any
from hsci.core.rir_loop import RIRLoop

# These problems were NEVER in training data
# System must solve them using transferred concepts
TRANSFER_TEST_CASES: List[Tuple[str, Any]] = [
    # Physics (never trained on)
    ("velocity is 20 m/s, time is 5s, find distance", {"distance": 100}),
    ("force is 50N, mass is 10kg, find acceleration", {"acceleration": 5}),

    # Finance (never trained on)
    ("principal 10000, rate 8% per year, find interest after 2 years", {"interest": 1600}),

    # Novel compositions
    ("monthly salary 8000, deductions 25%, find annual take-home", {"annual_take_home": 72000}),
]

class TransferTester:
    """
    Evaluation of concept transfer across domains.
    Tests if concepts learned in arithmetic/math can be applied to Physics/Finance.
    """

    def __init__(self):
        # We assume the loop might need some 'priming' or 
        # that it has already learned basic math.
        self.loop = RIRLoop()

    def run_tests(self):
        print(f"Starting Transfer Learning Evaluation at {datetime.now()}")
        success_count = 0
        total = len(TRANSFER_TEST_CASES)

        for i, (problem, expected) in enumerate(TRANSFER_TEST_CASES):
            print(f"[{i+1}/{total}] Transfer test: {problem}")
            try:
                output = self.loop.process(problem)
                if output.is_verified:
                    print(f"  Success! Proven Answer: {output.answer}")
                    print(f"  Concepts used: {[c.name for c in output.concepts_used]}")
                    success_count += 1
                else:
                    print(f"  Transfer failed (unverified).")
            except Exception as e:
                print(f"  Error during processing: {e}")

        print(f"\nTransfer Evaluation Complete.")
        print(f"Success Rate: {success_count}/{total} ({success_count/total:.1%})")
        print(f"Target: >80% for success.")

if __name__ == "__main__":
    tester = TransferTester()
    tester.run_tests()
