import z3

class ConstraintMatrixSolver:
    """
    Deterministic Constraint Matrix Solver using Z3.
    Validates mathematical constraints across massive resource allocation graphs.
    """
    def __init__(self):
        self.solver = z3.Solver()
        self.capacities = {} # resource -> int
        self.draws = {} # (node, resource) -> z3.Int
        self.max_draw_pct = {} # resource -> float
        self.node_resource_counts = {} # node -> int
        self.max_resources_per_node = None
        self.explicit_contradiction = False
        
    def add_capacity(self, resource: str, cap: int):
        self.capacities[resource] = cap
        
    def add_draw_link(self, node: str, resource: str):
        if node not in self.node_resource_counts:
            self.node_resource_counts[node] = 0
        self.node_resource_counts[node] += 1
        
        var_name = f"draw_{node}_{resource}"
        if (node, resource) not in self.draws:
            self.draws[(node, resource)] = z3.Int(var_name)
            # Default draw is >= 0
            self.solver.add(self.draws[(node, resource)] >= 0)
            
    def add_capacity_constraint(self, resource: str, pct: int):
        self.max_draw_pct[resource] = pct / 100.0
        
    def add_node_resource_limit(self, limit: int):
        self.max_resources_per_node = limit
        
    def add_proposed_state_draw(self, node: str, amount: int, resource: str):
        if (node, resource) not in self.draws:
            self.add_draw_link(node, resource)
        self.solver.add(self.draws[(node, resource)] == amount)
        
    def add_proposed_state_contradiction(self):
        self.explicit_contradiction = True
        self.solver.add(z3.BoolVal(False))
        
    def add_proposed_state_percent_draw(self, node: str, pct: int, resource: str):
        if (node, resource) not in self.draws:
            self.add_draw_link(node, resource)
        cap = self.capacities.get(resource, 0)
        amount = int(cap * (pct / 100.0))
        self.solver.add(self.draws[(node, resource)] == amount)

    def verify(self) -> str:
        """
        Runs the Z3 mathematical solver to verify if all constraints are Satisfiable.
        Returns: VALID, INVALID, or CONTRADICTION
        """
        # Build sum constraints
        resource_draws = {}
        for (n, r), var in self.draws.items():
            if r not in resource_draws:
                resource_draws[r] = []
            resource_draws[r].append(var)
            
        for r, vars_list in resource_draws.items():
            if r in self.max_draw_pct and r in self.capacities:
                limit = int(self.capacities[r] * self.max_draw_pct[r])
                self.solver.add(z3.Sum(vars_list) <= limit)
                
        # Static check for node limits
        if self.max_resources_per_node is not None:
            for n, count in self.node_resource_counts.items():
                if count > self.max_resources_per_node:
                    return "INVALID"
                    
        result = self.solver.check()
        if result == z3.sat:
            return "VALID"
        else:
            if self.explicit_contradiction:
                return "CONTRADICTION"
            return "INVALID"
