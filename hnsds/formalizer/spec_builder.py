from sympy import symbols, Eq, parse_expr

class SpecBuilder:
    def formalize(self, parsed_input):
        """
        Converts extracted equations into a formal symbolic representation (Sigma).
        """
        # Handle Code Generation Intent
        if parsed_input.get("intent") == "code_generation":
            return {
                "type": "coding",
                "description": parsed_input.get("raw", ""),
                "variables": [] 
            }

        # Handle Theorem Proving Intent
        if parsed_input.get("intent") == "proof":
            return {
                "type": "proof",
                "description": parsed_input.get("raw", ""),
                "variables": [] 
            }

        # Handle Generic Analysis Intent
        if parsed_input.get("intent") == "analysis":
            return {
                "type": "analysis",
                "description": parsed_input.get("raw", ""),
                "variables": []
            }

        # Handle Conversational Intent
        if parsed_input.get("intent") == "conversational":
            return {
                "type": "conversational",
                "description": parsed_input.get("raw", ""),
                "variables": []
            }

        equations_raw = parsed_input.get("equations", [])
        if not equations_raw:
            return {"type": "unknown"}

        formatted_equations = []
        all_vars = set()

        for eq_str in equations_raw:
            # Strip natural language prefixes
            clean_eq = eq_str.replace("solve", "").replace("find", "").replace("what is", "").replace("where", "").strip()
            
            if "=" not in clean_eq: continue
            
            lhs_str, rhs_str = clean_eq.split("=")
            
            # Find variables (single lowercase letters that are not part of numbers)
            # We look for isolated characters a-z
            vars_found = set(re.findall(r'\b[a-z]\b', clean_eq))
            all_vars.update(vars_found)
            
            formatted_equations.append(f"{lhs_str.strip()} == {rhs_str.strip()}")

        if len(formatted_equations) > 1:
            return {
                "type": "system",
                "equations": formatted_equations,
                "variables": sorted(list(all_vars))
            }
        elif len(formatted_equations) == 1:
            return {
                "type": "math",
                "equation": formatted_equations[0],
                "variables": sorted(list(all_vars))
            }
        return {"type": "unknown"}

import re # Needed for the findall in formalize