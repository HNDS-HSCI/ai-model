import unittest
from hnsds.perception.logic_parser import LogicParser
from hnsds.brain.lobes.native_engine import NativeSymbolicEngine

class TestLogicReasoning(unittest.TestCase):
    def setUp(self):
        self.parser = LogicParser()
        self.engine = NativeSymbolicEngine()

    def test_simple_adjacency_puzzle(self):
        # The Problem
        text = "The Brit is in the red house. The Swede is in the green house. The Brit is next to the Swede."
        
        print(f"\n[TEST] Input Puzzle: {text}")
        
        # 1. Parse
        parsed = self.parser.parse(text)
        print(f"[TEST] Parsed Constraints: {parsed['constraints']}")
        
        # 2. Solve
        solution = self.engine.solve_csp(parsed)
        print(f"[TEST] Z3 Solution: {solution}")
        
        # 3. Assertions
        self.assertIn("brit=", solution.lower())
        self.assertIn("swede=", solution.lower())
        self.assertIn("red=", solution.lower())
        
        # Extract values to verify logic
        # e.g. "brit=1, red=1, swede=2, green=2"
        # We need to parse the solution string back
        parts = solution.replace("Solution: ", "").split(", ")
        val_map = {}
        for p in parts:
            k, v = p.split("=")
            val_map[k] = int(v)
            
        # Brit must be Red
        self.assertEqual(val_map["brit"], val_map["red"])
        # Swede must be Green
        self.assertEqual(val_map["swede"], val_map["green"])
        # Brit must be next to Swede
        diff = abs(val_map["brit"] - val_map["swede"])
        self.assertEqual(diff, 1)

if __name__ == "__main__":
    unittest.main()
