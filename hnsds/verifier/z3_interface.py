from z3 import *
import re

class Z3Verifier:
    """
    The Formal Verification & Logic engine of the HNS-DS.
    It takes the native symbolic output and uses SMT solving 
    to provide definitive proofs, solutions, or counterexamples.
    """
    
    def solve(self, formal_spec):
        """
        Uses Z3 to actually compute the solution for a set of constraints.
        """
        if not isinstance(formal_spec, dict):
            return "Error: Invalid spec"
            
        equations = formal_spec.get("equations", [])
        if not equations and formal_spec.get("equation"):
            equations = [formal_spec.get("equation")]
            
        if not equations:
            return "No constraints found to solve."

        s = Solver()
        var_names = formal_spec.get("variables", [])
        
        # If no vars specified, extract them
        if not var_names:
            for eq in equations:
                var_names.extend(re.findall(r'\b[a-zA-Z]\b', eq))
            var_names = list(set(var_names))
            
        z3_vars = {name: Real(name) for name in var_names}

        for eq_str in equations:
            if not eq_str: continue
            try:
                # Standardize == and parse expression
                clean_eq = eq_str.replace("=", "==").replace("====", "==").strip()
                z3_eq = eval(clean_eq, {"__builtins__": None}, z3_vars)
                s.add(z3_eq)
            except Exception as e:
                pass # Ignore malformed

        if s.check() == sat:
            model = s.model()
            results = []
            for d in model.decls():
                val = model[d]
                # Convert Z3 RatNumRef to standard string
                if is_rational_value(val):
                    results.append(f"{d.name()}={val.numerator_as_long()/val.denominator_as_long()}")
                else:
                    results.append(f"{d.name()}={val}")
            if results:
                return ", ".join(results)
            else:
                return "Solved: Constraints are valid (True)."
        else:
            return "Unsolvable: Constraints are contradictory."

    def verify(self, candidate_solution, formal_spec):
        try:
            # 0. Safety Check for Synthesizer Errors
            if isinstance(candidate_solution, str) and candidate_solution.startswith("# Error"):
                return False, f"Synthesizer Failure: {candidate_solution}"

            if not isinstance(formal_spec, dict):
                return False, "Invalid symbolic specification."
            
            spec_type = formal_spec.get("type")

            # 1. Generic Analysis & Conversational (No verification needed, relies on Model)
            if spec_type in ["analysis", "conversational"]:
                return True, None

            # 2. Code Generation (Syntax Verification)
            if spec_type == "coding":
                try:
                    compile(str(candidate_solution), '<string>', 'exec')
                    return True, None
                except Exception as e:
                    return False, f"Syntax Error: {str(e)}"

            # 3. Theorem Proving (Z3 Script Verification)
            if spec_type == "proof":
                 pass
            
            # 4. Standard Math (Equation Solving)
            else:
                pass

            # --- Verification Execution ---
            
            # Case A: Theorem Proving (Raw Z3 Script)
            if "s.add" in str(candidate_solution) and "Int(" in str(candidate_solution):
                loc = {'s': Solver(), 'Int': Int, 'Real': Real, 'sat': sat, 'unsat': unsat}
                try:
                    exec(str(candidate_solution), {}, loc)
                    if loc['s'].check() == unsat:
                        return True, None
                    else:
                        return False, "Counterexample found (Theorem False)"
                except Exception as e:
                    return False, f"Proof Script Error: {e}"

            # Case B: Standard Math Equation Check
            s = Solver()
            var_names = formal_spec.get("variables", ["x", "y", "z"])
            z3_vars = {name: Real(name) for name in var_names}

            # Add Spec Equations
            if spec_type == "math" or spec_type == "system":
                equations = formal_spec.get("equations", [])
                if not equations and formal_spec.get("equation"):
                    equations = [formal_spec.get("equation")]
                
                for eq_str in equations:
                    if not eq_str: continue
                    try:
                        clean_eq = eq_str.replace("=", "==").replace("====", "==").strip()
                        z3_eq = eval(clean_eq, {"__builtins__": None}, z3_vars)
                        s.add(z3_eq)
                    except Exception as e:
                        pass 

            # Check Candidate Assignment
            if candidate_solution and "=" in str(candidate_solution):
                s.push()
                assignments = str(candidate_solution).split(",")
                for a in assignments:
                    if "=" not in a: continue
                    parts = a.split("=")
                    if len(parts) != 2: continue
                    var_name, val_str = parts
                    var_name = var_name.strip()
                    try:
                        val = float(val_str.strip())
                        if var_name in z3_vars:
                            s.add(z3_vars[var_name] == val)
                    except:
                        pass
                
                result = s.check()
                s.pop()
                if result == sat:
                    return True, None
            
            if spec_type == "proof":
                 return False, "Proof candidate was not a valid Z3 script."

            return False, f"Counterexample: {candidate_solution}"

        except Exception as e:
            return False, f"Verification Error: {str(e)}"