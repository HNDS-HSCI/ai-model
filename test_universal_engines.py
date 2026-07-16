import sys
import os

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hsci.core.rir_loop import RIRLoop
from hsci.core.data_types import EntityValue

def test_universal_engines():
    print("Initializing HSCI Brain...")
    brain = RIRLoop(use_llm=False)
    
    print("\n--- TEST 1: Universal Math Engine (Algebra Solving) ---")
    eq_query = "solve x**2 + 5*x + 6 = 0"
    out, structured = brain.process_internal(eq_query)
    print(f"Query: {eq_query}")
    print(f"Verified: {out.is_verified}")
    print(f"Answer: {out.answer}")
    print(f"Reasoning Trace: {out.reasoning_trace}")
    
    print("\n--- TEST 2: Universal Math Engine (Arithmetic Evaluation) ---")
    arith_query = "calculate (50 - 10) * 3 / 2"
    out, structured = brain.process_internal(arith_query)
    print(f"Query: {arith_query}")
    print(f"Verified: {out.is_verified}")
    print(f"Answer: {out.answer}")
    print(f"Reasoning Trace: {out.reasoning_trace}")

    print("\n--- TEST 3: Universal Physics Engine (F = m * a) ---")
    physics_query = "what is the force if mass = 12 and acceleration = 9.8"
    out, structured = brain.process_internal(physics_query)
    print(f"Query: {physics_query}")
    print(f"Verified: {out.is_verified}")
    print(f"Answer: {out.answer}")
    print(f"Reasoning Trace: {out.reasoning_trace}")

    print("\n--- TEST 4: Universal Concept Engine (Autonomous Meta-Learning) ---")
    # Define a custom concept
    define_query = "define concept density as mass / volume"
    out, structured = brain.process_internal(define_query)
    print(f"Define Query: {define_query}")
    print(f"Verified: {out.is_verified}")
    print(f"Answer: {out.answer}")
    
    # Check if we can solve using the newly learned concept!
    solve_query = "what is the density if mass = 150 and volume = 3"
    out, structured = brain.process_internal(solve_query)
    print(f"\nSolve Query: {solve_query}")
    print(f"Verified: {out.is_verified}")
    print(f"Answer: {out.answer}")
    print(f"Reasoning Trace: {out.reasoning_trace}")

if __name__ == "__main__":
    test_universal_engines()
