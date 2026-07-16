import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hsci.reasoning.universal_physics_engine import UniversalPhysicsEngine
from hsci.reasoning.universal_math_engine import UniversalMathEngine
from hsci.core.data_types import EntityValue

# Test Physics
phys = UniversalPhysicsEngine()
entities = {
    "mass": EntityValue(12, None, True, "12"),
    "acceleration": EntityValue(9.8, None, True, "9.8"),
    "force": EntityValue(None, None, False, "unknown")
}
text = "what is the force if mass = 12 and acceleration = 9.8"
res = phys.solve_from_text(text, entities)
print("--- Physics Test ---")
print(f"Solved: {res.solved}")
print(f"Answer: {res.answer}")
print(f"Error : {res.error}")
print(f"Steps : {res.steps}")

# Test Math
math_eng = UniversalMathEngine()
text_math = "solve x**2 + 5*x + 6 = 0"
res_math = math_eng.solve_from_text(text_math, {})
print("\n--- Math Test ---")
print(f"Solved: {res_math.solved}")
print(f"Answer: {res_math.answer}")
print(f"Error : {res_math.error}")
print(f"Steps : {res_math.steps}")
