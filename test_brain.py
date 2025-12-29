import logging
import sys
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def main():
    # 1. Build the Brain
    brain = HyperSymbolicBrain()

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # CASE 1: A problem the brain 'knows' (Intuition Test)
    problem_1 = "Solve x + 2 = 5"
    print(f"\n--- TEST 1: INTUITION (Known Problem) ---")
    brain.process(problem_1)
    print(brain.get_mind_state())

    # CASE 2: A new complex problem (Deliberation Test)
    problem_2 = "Solve x + y = 30, x - y = 10"
    print(f"\n--- TEST 2: DELIBERATION (New Problem) ---")
    brain.process(problem_2)
    print(brain.get_mind_state())

    # CASE 3: Growth Test (Learning and Mastery)
    problem_3 = "Solve x + 10 = 50"
    print(f"\n--- TEST 3: GROWTH (Phase 1: Learning) ---")
    brain.process(problem_3)
    print("Brain just solved a new problem and stored it in long-term memory.")
    
    print(f"\n--- TEST 3: GROWTH (Phase 2: Mastery) ---")
    print("Providing the same stimulus again...")
    brain.process(problem_3)
    print(brain.get_mind_state())

if __name__ == "__main__":
    main()
