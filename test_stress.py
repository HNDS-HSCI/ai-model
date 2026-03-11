
import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain

def run_stress_test():
    logging.basicConfig(level=logging.INFO)
    brain = HyperSymbolicBrain()

    print("\n" + "="*60)
    print("   HSCI STRESS TEST: Instructional Priming & Generalization   ")
    print("="*60)

    # 1. THE TEACHING PHASE (Instructional Priming)
    # We teach it a base concept once.
    print("\n--- TEACHING PHASE ---")
    lesson = "teach: find the total if base is x and bonus is y | SALARY_SUMMATION | REDUCTION"
    print(f"[TEACH] > {lesson}")
    result = brain.process(lesson)
    print(f"[RESULT] > {result}")

    # 2. THE APPLICATION PHASE (Testing its Intelligence)
    # We ask a NEW question using DIFFERENT words (Calculate instead of Find, 1000 instead of x).
    print("\n--- APPLICATION PHASE (Zero-Shot) ---")
    stimulus = "Calculate the total result if the base is 1000 and the bonus is 500."
    
    print(f"[STIMULUS] > {stimulus}")
    
    response = brain.process(stimulus)
    
    print("\n" + "-"*60)
    print(f"[AI RESPONSE]\n{response}")
    print("-"*60)

    # Check the Mind Trace for understanding
    trace = brain.get_mind_state()
    print("\n[INTERNAL MENTAL TRACE]")
    for step in trace:
        # Trace is a string currently, split it for readability
        print(f"  {step}")

if __name__ == "__main__":
    run_stress_test()
