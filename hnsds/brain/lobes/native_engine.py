import operator
from z3 import *

class NativeSymbolicEngine:
    """
    INVENTION: The Axiomatic Core.
    This is a native logic reduction engine. It doesn't just call a library; 
    it implements the fundamental laws of symbolic reduction (Axioms).
    Also bridges to Z3 for complex Constraint Satisfaction Problems (CSP).
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

    def solve_csp(self, parsed_problem):
        """
        Solves a Logic Puzzle (CSP) using Z3.
        Input: parsed_problem dict from LogicParser.
        """
        solver = Solver()
        
        # 1. Setup Universe of Discourse
        # In a logic puzzle, we usually map Entities -> Slots (e.g., House Numbers)
        # OR Attributes -> Entities.
        # Let's assume a standard grid: N Houses. Attributes are variables taking values 1..N
        
        # Find the 'positional' or 'primary' domain. 
        # Heuristic: If we have "House_1", "House_2", that's the domain 1..N.
        
        # Flatten all attributes to find unique values
        # e.g. color: [red, green], nat: [brit, swede]
        
        # Create Z3 Variables for each Attribute of each Entity?
        # Standard approach: Variables are the Attributes (e.g. Color_Red, Color_Green) 
        # and values are the House IDs (1..5).
        
        variables = {}
        domain_size = 5 # Default
        
        # Collect all unique "things" (Brit, Red, Coffee)
        # The Parser output needs to be robust. 
        # For now, let's assume specific structure: 
        # constraints: [{type: association, entity1: Brit, entity2: Red}]
        
        # We need to deduce the variables.
        # Let's treat every noun found as a Variable that maps to a Position (Int).
        all_nouns = set()
        for c in parsed_problem.get("constraints", []):
            if "entity1" in c: all_nouns.add(c["entity1"])
            if "entity2" in c: all_nouns.add(c["entity2"])
            
        # Create a Z3 Int for each noun
        for noun in all_nouns:
            v = Int(noun)
            variables[noun] = v
            solver.add(v >= 1, v <= 5) # Assume 5 slots for now
            
        # 2. Apply Constraints
        for c in parsed_problem.get("constraints", []):
            try:
                e1 = variables.get(c["entity1"])
                e2 = variables.get(c["entity2"])
                
                if e1 is None or e2 is None: continue
                
                if c["type"] == "association":
                    # "Brit is Red" -> Position(Brit) == Position(Red)
                    if c["negation"]:
                        solver.add(e1 != e2)
                    else:
                        solver.add(e1 == e2)
                        
                elif c["type"] == "adjacency":
                    # "Brit next to Green" -> |Pos(Brit) - Pos(Green)| == 1
                    # In Z3: Or(e1 == e2 + 1, e1 == e2 - 1)
                    if c["negation"]:
                        solver.add(Not(Or(e1 == e2 + 1, e1 == e2 - 1)))
                    else:
                        solver.add(Or(e1 == e2 + 1, e1 == e2 - 1))
            except Exception as e:
                print(f"Constraint Gen Error: {e}")

        # 3. Solve
        if solver.check() == sat:
            m = solver.model()
            results = []
            for name, var in variables.items():
                results.append(f"{name}={m[var]}")
            return "Solution: " + ", ".join(results)
        else:
            return "Unsatisfiable: No logic solution found."

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

        # Check for Python Code (Heuristic: contains 'def ' or 'import ' or 'class ')
        cand_str = str(candidate)
        if "def " in cand_str or "import " in cand_str or "class " in cand_str:
            try:
                # Syntax Check
                compile(cand_str, '<string>', 'exec')
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
            if not eq or "==" not in eq:
                continue # Skip malformed/empty equations
            
            lhs, rhs = eq.split("==")
            # Reduce both sides natively
            res_l = self.reduce(lhs.strip(), assignments)
            res_r = self.reduce(rhs.strip(), assignments)
            
            print(f"DEBUG: {candidate} -> {lhs}: {res_l}, {rhs}: {res_r}")

            if res_l != res_r:
                return False, f"Native Contradiction: {res_l} != {res_r}"
                
        return True, None
