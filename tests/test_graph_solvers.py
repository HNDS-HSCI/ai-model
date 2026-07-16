import unittest
from hnsds.verifier.graph_solver import GraphSolver
from hnsds.verifier.dependency_solver import DependencySolver

class TestGraphSolver(unittest.TestCase):
    
    def setUp(self):
        self.graph = GraphSolver()

    def test_topological_sort_valid(self):
        self.graph.add_edge("A", "B")
        self.graph.add_edge("B", "C")
        self.assertTrue(self.graph.is_dag())
        # C should be evaluated first, then B, then A
        sort = self.graph.topological_sort()
        self.assertEqual(sort, ["C", "B", "A"])

    def test_cycle_detection(self):
        self.graph.add_edge("S1", "S2")
        self.graph.add_edge("S2", "S3")
        self.graph.add_edge("S3", "S1") # Cycle!
        self.assertFalse(self.graph.is_dag())
        self.assertIsNotNone(self.graph.detect_cycles())

    def test_regional_compliance(self):
        self.graph.add_node("S1", {"region": "eu-central"})
        self.graph.add_node("S2", {"region": "us-east"})
        self.graph.add_edge("S1", "S2")
        
        # Rule: eu-central cannot depend on us-east
        rules = [("eu-central", "us-east")]
        self.assertFalse(self.graph.verify_regional_compliance(rules))

        # Different edge, should be fine
        self.graph.add_node("S3", {"region": "ap-south"})
        self.graph.add_edge("S3", "S2")
        self.assertFalse(self.graph.verify_regional_compliance(rules)) # Still false because S1->S2 exists
        
        graph2 = GraphSolver()
        graph2.add_node("S1", {"region": "us-east"})
        graph2.add_node("S2", {"region": "eu-central"})
        graph2.add_edge("S1", "S2") # us-east depends on eu-central, which is allowed
        self.assertTrue(graph2.verify_regional_compliance(rules))


class TestDependencySolver(unittest.TestCase):
    
    def setUp(self):
        self.solver = DependencySolver()

    def test_valid_resolution(self):
        self.solver.register_package("lib-1", "1.0.0")
        self.solver.register_package("lib-2", "2.0.0")
        self.solver.add_dependency("lib-1", "lib-2")
        self.assertEqual(self.solver.resolve(), "VALID_ORDER")

    def test_cyclic_dependency(self):
        self.solver.register_package("A", "1.0.0")
        self.solver.register_package("B", "1.0.0")
        self.solver.add_dependency("A", "B")
        self.solver.add_dependency("B", "A")
        self.assertEqual(self.solver.resolve(), "CYCLIC_DEPENDENCY")

    def test_missing_version(self):
        self.solver.register_package("A", "1.0.0")
        self.solver.register_package("B", "2.0.0")
        # Requires B version 3.0.0 (Invalid)
        self.solver.add_dependency("A", "B", "3.0.0")
        self.assertEqual(self.solver.resolve(), "INVALID_ORDER")

    def test_unregistered_package(self):
        self.solver.register_package("A", "1.0.0")
        # B is never registered
        self.solver.add_dependency("A", "B")
        self.assertEqual(self.solver.resolve(), "INVALID_ORDER")

if __name__ == "__main__":
    unittest.main()
