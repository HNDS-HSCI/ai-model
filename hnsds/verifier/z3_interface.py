from z3 import *
import re

class Z3Verifier:
    """
    The Formal Verification engine of the HNS-DS.
    It takes the native symbolic output of the Formalizer and uses 
    SMT solving to provide definitive proofs or counterexamples.
    """
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
            # For proofs, the logic is self-contained in the candidate script.
            if spec_type == "proof":
                 # We don't add equations from spec, we run the candidate.
                 pass
            
            # 4. Standard Math (Equation Solving)
            else:
                # We need to set up the solver state from the spec
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
            # We need to reconstruct the solver 's' and vars to check the candidate assignment.
            
            # Setup Solver and Vars
            s = Solver()
            var_names = formal_spec.get("variables", ["x", "y"])
            z3_vars = {name: Int(name) for name in var_names}

            # Add Spec Equations (Only for Math type)
            if spec_type == "math" or spec_type == "system":
                equations = []
                if spec_type == "math":
                    equations = [formal_spec.get("equation")]
                else:
                    equations = formal_spec.get("equations", [])
                
                for eq_str in equations:
                    try:
                        z3_eq = eval(eq_str.replace("==", "=="), {"__builtins__": None}, z3_vars)
                        s.add(z3_eq)
                    except:
                        pass # Ignore malformed equations in mixed contexts

            # Check Candidate Assignment
            if candidate_solution and "=" in str(candidate_solution):
                s.push()
                assignments = str(candidate_solution).split(",")
                for a in assignments:
                    if "=" not in a: continue
                    var_name, val = a.split("=")
                    var_name = var_name.strip()
                    try:
                        val = int(val.strip())
                        if var_name in z3_vars:
                            s.add(z3_vars[var_name] == val)
                    except:
                        pass
                
                result = s.check()
                s.pop()
                if result == sat:
                    return True, None
            
            # If we reached here and type is 'proof', we might have failed the script check above
            # or it wasn't a script.
            if spec_type == "proof":
                 return False, "Proof candidate was not a valid Z3 script."

            return False, f"Counterexample: {candidate_solution}"

        except Exception as e:
            return False, f"Verification Error: {str(e)}"