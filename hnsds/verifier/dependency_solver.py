from typing import List, Dict, Optional
from hnsds.verifier.graph_solver import GraphSolver

class DependencySolver:
    """
    Wraps the GraphSolver to solve transitive multi-level package dependencies,
    versioning requirements, and conflict resolution.
    """
    def __init__(self):
        self.graph = GraphSolver()
        self.registry: Dict[str, str] = {} 

    def register_package(self, pkg_name: str, version: str) -> None:
        self.registry[pkg_name] = version
        self.graph.add_node(pkg_name, {"version": version})

    def add_dependency(self, pkg_name: str, required_pkg: str, required_version: Optional[str] = None) -> None:
        self.graph.add_node(pkg_name)
        if required_pkg not in self.graph.adjacency_list:
            self.graph.add_node(required_pkg, {"expected_version": required_version} if required_version else {})
        elif required_version:
            self.graph.node_properties[required_pkg]["expected_version"] = required_version
            
        self.graph.add_edge(pkg_name, required_pkg)

    def resolve(self) -> str:
        # 1. Check for Missing Packages or Version Conflicts
        for node in self.graph.adjacency_list:
            props = self.graph.node_properties.get(node, {})
            
            # If the node was completely unregistered
            if node not in self.registry:
                return "INVALID_ORDER"
                
            # If a strict version constraint was placed but not met
            if "expected_version" in props and props["expected_version"]:
                if self.registry[node] != props["expected_version"]:
                    return "INVALID_ORDER"

        # 2. Cycle Detection
        cycle = self.graph.detect_cycles()
        if cycle:
            return "CYCLIC_DEPENDENCY"
            
        return "VALID_ORDER"
