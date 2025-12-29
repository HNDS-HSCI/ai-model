from hnsds.brain.cognitive_core import HyperSymbolicBrain

brain = HyperSymbolicBrain()

print("--- Test 1: Math (Should Pass) ---")
res = brain.process("find x where x + 5 = 10")
print(f"Result: {res}")

print("\n--- Test 2: Code Gen (Should Fail or be Unknown) ---")
res_code = brain.process("write a function that adds two numbers")
print(f"Result: {res_code}")
