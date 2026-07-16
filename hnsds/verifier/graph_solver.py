from typing import List, Dict, Set, Tuple, Optional
from collections import deque

class GraphSolver:
    """
    Core Directed Acyclic Graph (DAG) operations for HSCI.
    Provides cycle detection, topological sorting, BFS/DFS traversal,
    and regional compliance validation for Architecture Planning tasks.
    """
    def __init__(self):
        self.adjacency_list: Dict[str, List[str]] = {}
        self.node_properties: Dict[str, Dict] = {}

    def add_node(self, node_id: str, properties: Optional[Dict] = None) -> None:
        if properties is None:
            properties = {}
        if node_id not in self.adjacency_list:
            self.adjacency_list[node_id] = []
            self.node_properties[node_id] = properties
        else:
            self.node_properties[node_id].update(properties)

    def add_edge(self, source: str, target: str) -> None:
        """Adds a directed edge from source to target. (source depends on target)"""
        if source not in self.adjacency_list:
            self.add_node(source)
        if target not in self.adjacency_list:
            self.add_node(target)
        self.adjacency_list[source].append(target)

    def detect_cycles(self) -> Optional[List[str]]:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.adjacency_list.get(node, []):
                if neighbor not in visited:
                    res = dfs(neighbor, path + [neighbor])
                    if res: return res
                elif neighbor in rec_stack:
                    return path + [neighbor]
            rec_stack.remove(node)
            return None

        for n in self.adjacency_list:
            if n not in visited:
                cycle = dfs(n, [n])
                if cycle: return cycle
        return None

    def topological_sort(self) -> Optional[List[str]]:
        """Returns topological sort. If cycle exists, returns None."""
        if self.detect_cycles():
            return None

        visited: Set[str] = set()
        stack: List[str] = []

        def dfs(node: str):
            visited.add(node)
            for neighbor in self.adjacency_list.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
            stack.append(node)

        for n in self.adjacency_list:
            if n not in visited:
                dfs(n)

        return stack # Dependencies are correctly ordered for execution

    def bfs_traverse(self, start_node: str) -> List[str]:
        if start_node not in self.adjacency_list:
            return []
        visited = set([start_node])
        queue = deque([start_node])
        order = []
        while queue:
            curr = queue.popleft()
            order.append(curr)
            for neighbor in self.adjacency_list.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return order

    def is_dag(self) -> bool:
        return self.detect_cycles() is None

    def verify_regional_compliance(self, rules: List[Tuple[str, str]]) -> bool:
        """
        Validates regional cross-dependencies.
        rules format: [('eu-central', 'us-east')] -> 'eu-central' cannot depend on 'us-east'.
        """
        for source, neighbors in self.adjacency_list.items():
            src_reg = self.node_properties.get(source, {}).get('region')
            if not src_reg: continue
            
            for target in neighbors:
                tgt_reg = self.node_properties.get(target, {}).get('region')
                if not tgt_reg: continue
                
                if (src_reg, tgt_reg) in rules:
                    return False
        return True
