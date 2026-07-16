import unittest
from hnsds.verifier.constraint_matrix_solver import ConstraintMatrixSolver

class TestConstraintMatrixSolver(unittest.TestCase):
    def setUp(self):
        self.solver = ConstraintMatrixSolver()
        self.solver.add_capacity("R0", 1000)
        self.solver.add_capacity("R1", 2000)
        self.solver.add_capacity_constraint("R0", 80) # max 80% = 800
        self.solver.add_capacity_constraint("R1", 50) # max 50% = 1000
        self.solver.add_node_resource_limit(3)
        
    def test_valid_allocation(self):
        # Node N0 draws from R0
        self.solver.add_draw_link("N0", "R0")
        self.solver.add_proposed_state_draw("N0", 500, "R0")
        
        # 500 <= 800 -> VALID
        self.assertEqual(self.solver.verify(), "VALID")
        
    def test_invalid_allocation(self):
        # Node N0 draws from R0
        self.solver.add_draw_link("N0", "R0")
        self.solver.add_proposed_state_draw("N0", 900, "R0")
        
        # 900 > 800 -> INVALID
        self.assertEqual(self.solver.verify(), "INVALID")
        
    def test_multiple_nodes_invalid(self):
        # N0 draws 400 from R0
        # N1 draws 500 from R0
        self.solver.add_proposed_state_draw("N0", 400, "R0")
        self.solver.add_proposed_state_draw("N1", 500, "R0")
        
        # 400 + 500 = 900 > 800 -> INVALID
        self.assertEqual(self.solver.verify(), "INVALID")
        
    def test_node_resource_limit_violation(self):
        # Node N0 draws from R0, R1, R2, R3 (limit is 3)
        self.solver.add_proposed_state_draw("N0", 100, "R0")
        self.solver.add_proposed_state_draw("N0", 100, "R1")
        self.solver.add_proposed_state_draw("N0", 100, "R2")
        self.solver.add_proposed_state_draw("N0", 100, "R3")
        
        # Violates static limit
        self.assertEqual(self.solver.verify(), "INVALID")
        
    def test_explicit_contradiction(self):
        self.solver.add_proposed_state_contradiction()
        self.assertEqual(self.solver.verify(), "CONTRADICTION")
        
    def test_proposed_pct_draw_valid(self):
        # N0 draws 50% of R0 (500)
        self.solver.add_proposed_state_percent_draw("N0", 50, "R0")
        self.assertEqual(self.solver.verify(), "VALID")
        
    def test_proposed_pct_draw_invalid(self):
        # N0 draws 90% of R0 (900)
        self.solver.add_proposed_state_percent_draw("N0", 90, "R0")
        self.assertEqual(self.solver.verify(), "INVALID")

if __name__ == "__main__":
    unittest.main()
