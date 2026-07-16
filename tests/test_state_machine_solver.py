import unittest
from hnsds.verifier.state_machine_solver import StateMachineSolver

class TestStateMachineSolver(unittest.TestCase):
    def setUp(self):
        self.solver = StateMachineSolver()
        states = ["STATE_0", "STATE_1", "STATE_2", "STATE_10", "STATE_15", "STATE_24"]
        for s in states:
            self.solver.register_state(s)
            
        self.solver.add_transition("STATE_0", "STATE_1")
        self.solver.add_transition("STATE_1", "STATE_2")
        self.solver.add_transition("STATE_2", "STATE_10")
        self.solver.add_transition("STATE_10", "STATE_15")
        self.solver.add_transition("STATE_15", "STATE_24")
        self.solver.add_transition("STATE_0", "STATE_24")
        self.solver.add_transition("STATE_24", "STATE_0")
        self.solver.add_transition("STATE_1", "STATE_1") # Cycle
        
        # Rules
        self.solver.add_terminal_state("STATE_24")
        self.solver.add_recovery_rule("STATE_10", "STATE_2")
        self.solver.add_forbidden_direct("STATE_0", "STATE_24")
        self.solver.add_conditional_transition("STATE_10", "STATE_15")
        
    def test_valid_trace(self):
        trace = ["STATE_0", "STATE_1", "STATE_2"]
        self.assertTrue(self.solver.verify_trace(trace))
        
    def test_invalid_transition(self):
        trace = ["STATE_0", "STATE_15"]
        self.assertFalse(self.solver.verify_trace(trace))
        
    def test_terminal_violation(self):
        # STATE_24 is terminal, cannot transition out to STATE_0
        trace = ["STATE_24", "STATE_0"]
        self.assertFalse(self.solver.verify_trace(trace))
        
    def test_recovery_workflow_violation(self):
        # Enters STATE_10 without STATE_2
        self.solver.add_transition("STATE_1", "STATE_10")
        trace = ["STATE_0", "STATE_1", "STATE_10"]
        self.assertFalse(self.solver.verify_trace(trace))
        
    def test_forbidden_direct(self):
        # 0 -> 24 is forbidden
        trace = ["STATE_0", "STATE_24"]
        self.assertFalse(self.solver.verify_trace(trace))
        
    def test_conditional_transition(self):
        # 10 -> 15 is conditional (needs token, which is absent)
        trace = ["STATE_0", "STATE_1", "STATE_2", "STATE_10", "STATE_15"]
        self.assertFalse(self.solver.verify_trace(trace))
        
    def test_cyclic_transition(self):
        # Cyclic transition 1 -> 1 is valid natively if registered
        trace = ["STATE_0", "STATE_1", "STATE_1", "STATE_2"]
        self.assertTrue(self.solver.verify_trace(trace))

if __name__ == "__main__":
    unittest.main()
