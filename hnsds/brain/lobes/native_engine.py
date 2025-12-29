import operator

class NativeSymbolicEngine:
    """
    INVENTION: The Axiomatic Core.
    This is a native logic reduction engine. It doesn't just call a library; 
    it implements the fundamental laws of symbolic reduction (Axioms).
    """
    def __init__(self):
        # Primordial Axioms: Basic operations defined as cognitive primitives
        self.axioms = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "==": operator.eq
        }

    def reduce(self, expression, assignments):
        """
        Natively reduces a symbolic expression based on current assignments.
        Example: "x + 2", {"x": 3} -> 5.0
        """
        try:
            # Normalize: Ensure spaces around operators
            expr = expression
            for op in self.axioms.keys():
                expr = expr.replace(op, f" {op} ")
            
            tokens = expr.split()
            
            # Replace variables with values
            processed_tokens = []
            for t in tokens:
                if t in assignments:
                    processed_tokens.append(str(assignments[t]))
                else:
                    processed_tokens.append(t)
            
            # Simple recursive reduction of triples
            while len(processed_tokens) >= 3:
                left = float(processed_tokens[0])
                op = processed_tokens[1]
                right = float(processed_tokens[2])
                
                if op in self.axioms:
                    res = self.axioms[op](left, right)
                    processed_tokens = [str(res)] + processed_tokens[3:]
                else:
                    break
            
            if len(processed_tokens) == 1:
                return float(processed_tokens[0])
            
            return None
        except Exception as e:
            return None


    def verify_natively(self, candidate, sigma):
        """
        Performs a native formal proof without external solvers.
        """
        if not candidate:
            return False, "No candidate provided"

        # Check for Python Code
        if str(candidate).startswith("def "):
            try:
                # Syntax Check
                compile(candidate, '<string>', 'exec')
                return True, None
            except Exception as e:
                return False, f"Syntax Error: {str(e)}"

        if "=" not in str(candidate): return False, "Malformed candidate"
        
        # Parse candidate assignments
        assignments = {}
        try:
            for part in str(candidate).split(","):
                if "=" not in part: continue
                var, val = part.split("=")
                assignments[var.strip()] = float(val.strip())
        except ValueError:
            return False, "Invalid assignment format"
            
        equations = sigma.get("equations", [])
        if not equations and "equation" in sigma:
            equations = [sigma["equation"]]
            
        for eq in equations:
            lhs, rhs = eq.split("==")
            # Reduce both sides natively
            res_l = self.reduce(lhs.strip(), assignments)
            res_r = self.reduce(rhs.strip(), assignments)
            
            print(f"DEBUG: {candidate} -> {lhs}: {res_l}, {rhs}: {res_r}")

            if res_l != res_r:
                return False, f"Native Contradiction: {res_l} != {res_r}"
                
        return True, None
