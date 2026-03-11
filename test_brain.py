import logging
import sys
import os
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def main():
    # Clear cache for a clean tutorial experience
    if os.path.exists("mental_intelligence.json"):
        os.remove("mental_intelligence.json")

    # 1. Build the Brain
    brain = HyperSymbolicBrain()

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    print("==================================================")
    print("   HSCI TUTORIAL: Axiomatic Reasoning Flow        ")
    print("==================================================\n")

    # CASE 1: Instructional Priming (Teaching)
    print("--- STEP 1: TEACHING THE BRAIN ---")
    lesson = "teach: find the total if base is x and bonus is y | SALARY_SUMMATION | REDUCTION"
    print(f"Input: {lesson}")
    res1 = brain.process(lesson)
    print(f"Brain Output: {res1}\n")

    # CASE 2: Generalization (Zero-Shot using learned logic)
    print("--- STEP 2: ANALOGICAL REASONING ---")
    problem = "Calculate the total result if the base is 5000 and the bonus is 200"
    print(f"Input: {problem}")
    res2 = brain.process(problem)
    print(f"Brain Output: {res2}\n")

    # CASE 3: View the Cognitive Trace
    print("--- STEP 3: COGNITIVE TRACE (The Mental Model) ---")
    trace = brain.get_mind_state()
    for i, step in enumerate(trace):
        print(f"[{i:02d}] {step}")

    print("\n✅ Tutorial Complete. The brain has mastered the concept and solved the problem.")

if __name__ == "__main__":
    main()
