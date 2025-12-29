class HTNPlanner:
    def decompose(self, sigma):
        """
        Decomposes a complex specification Sigma into a list of sub-specifications.
        In HNS-DS, systems of equations are often solved holistically 
        if the variable space is small.
        """
        if not isinstance(sigma, dict):
            return [sigma]
            
        # For small systems (demo), solve holistically to ensure inter-variable constraints
        if sigma.get("type") == "system":
            if len(sigma.get("variables", [])) <= 3:
                return [sigma]
            
            subgoals = []
            for eq in sigma.get("equations", []):
                subgoals.append({
                    "type": "math",
                    "equation": eq,
                    "variables": sigma.get("variables")
                })
            return subgoals
            
        return [sigma]
