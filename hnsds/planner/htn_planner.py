class HTNPlanner:
    """
    Hierarchical Task Network (HTN) Planner.
    Responsible for Recursive Decomposition of complex intents into manageable Axiomatic tasks.
    """
    def decompose(self, sigma):
        """
        Decomposes a complex specification Sigma into a list of sub-specifications.
        """
        if not isinstance(sigma, dict):
            return [sigma]
            
        # 1. Math/System Decomposition
        # In HSCI, mathematical systems are solved holistically to preserve
        # inter-variable constraints (e.g., total = base + bonus).
        if sigma.get("type") in ["math", "system", "logic"]:
            return [sigma] 

        # 2. Complex Feature Decomposition (Software Engineering)
        if sigma.get("complexity") == "high" and sigma.get("type") == "coding":
            # Break down a "feature" into Data, Logic, and Integration
            desc = sigma.get("desc", "")
            return [
                {
                    "type": "coding",
                    "goal": "synthesize",
                    "step": "DATA_STRUCTURE",
                    "desc": f"Define data structures for: {desc}"
                },
                {
                    "type": "coding",
                    "goal": "synthesize",
                    "step": "BUSINESS_LOGIC",
                    "desc": f"Write core functions for: {desc}"
                },
                {
                    "type": "logic",
                    "goal": "solve",
                    "step": "INTEGRATION",
                    "problem": f"Compose DATA and LOGIC for: {desc}"
                }
            ]
            
        return [sigma]
