import os
import sys
import time

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain


def main():
    print("\n" + "=" * 60)
    print("   HSCI: Hyper-Symbolic Cognitive Invention (Native V2)   ")
    print("   \"Disrupting AI with True Symbolic Reasoning\"         ")
    print("=" * 60)
    print("Ready to solve Logic Puzzles, Math, and Code.")
    print(
        "Try: 'The Brit lives in the red house. The Swede lives in the green house. The Brit is next to the Swede.'"
    )
    print("Type 'exit' to quit.\n")

    brain = HyperSymbolicBrain()

    while True:
        try:
            user_input = input("\n[USER] > ")
            if user_input.lower() in ["exit", "quit"]:
                break

            start = time.time()
            response = brain.process(user_input)
            end = time.time()

            print(f"[HSCI] > {response}")
            print(f"       (Time: {end-start:.4f}s)")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
