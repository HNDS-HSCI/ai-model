import unittest
from hnsds.brain.cognitive_core import HyperSymbolicBrain
from hnsds.perception.logic_parser import LogicParser

class TestParserBridge(unittest.TestCase):
    
    def setUp(self):
        self.parser = LogicParser()
        self.brain = HyperSymbolicBrain()

    def test_logic_parser_architecture_extraction(self):
        prompt = '''ENTERPRISE DEPLOYMENT TOPOLOGY:
Service S0 must deploy in region us-east.
Service S1 must deploy in region eu-central.
S1 requires S0 to be healthy before booting.
Rule 1: Services in eu-central CANNOT depend on services in us-east due to GDPR isolation.
'''
        parsed = self.parser.parse_graph(prompt)
        
        self.assertEqual(len(parsed["nodes"]), 2)
        self.assertEqual(parsed["nodes"][0]["id"], "S0")
        self.assertEqual(parsed["nodes"][0]["properties"]["region"], "us-east")
        
        self.assertEqual(len(parsed["edges"]), 1)
        self.assertEqual(parsed["edges"][0]["source"], "S1")
        self.assertEqual(parsed["edges"][0]["target"], "S0")
        
        self.assertEqual(len(parsed["regional_rules"]), 1)
        self.assertEqual(parsed["regional_rules"][0]["src_region"], "eu-central")
        self.assertEqual(parsed["regional_rules"][0]["tgt_region"], "us-east")

    def test_logic_parser_dependency_extraction(self):
        prompt = '''PACKAGE MANAGER RESOLUTION GRAPH:
Package lib-0 v1.0.0 is available.
Package lib-1 v2.0.0 is available.
lib-1 strictly requires lib-0.
FATAL: lib-1 requires lib-5 v9.9.9, which does not exist.
'''
        parsed = self.parser.parse_graph(prompt)
        self.assertEqual(len(parsed["packages"]), 2)
        self.assertEqual(len(parsed["edges"]), 2)
        self.assertEqual(parsed["edges"][1]["expected_version"], "9.9.9")

    def test_cognitive_core_integration(self):
        prompt = '''ENTERPRISE DEPLOYMENT TOPOLOGY:
Service S0 must deploy in region us-east.
Service S1 must deploy in region eu-central.
S1 requires S0 to be healthy before booting.
Rule 1: Services in eu-central CANNOT depend on services in us-east due to GDPR isolation.
'''
        response = self.brain.process(prompt)
        self.assertIn("INVALID_ORDER", response)
        
    def test_cognitive_core_cycle(self):
        prompt = '''PACKAGE MANAGER RESOLUTION GRAPH:
Package lib-0 v1.0.0 is available.
Package lib-1 v1.0.0 is available.
lib-1 strictly requires lib-0.
lib-0 strictly requires lib-1.
'''
        response = self.brain.process(prompt)
        self.assertIn("CYCLIC_DEPENDENCY", response)

if __name__ == "__main__":
    unittest.main()
