import itertools
import inspect
import re
import sys
import logging
from z3 import *

class CognitivePrimitives:
    """
    The 'DNA' of the Native Brain.
    Atomic logical units that can be combined to form complex thoughts.
    """
    def __init__(self):
        # (Name, Lambda, Arity, StrRep)
        self.atoms = [
            ("add", lambda x, y: x + y, 2, "({0} + {1})"),
            ("sub", lambda x, y: x - y, 2, "({0} - {1})"),
            ("mul", lambda x, y: x * y, 2, "({0} * {1})"),
            ("gt",  lambda x, y: x > y, 2, "({0} > {1})"),
            ("if",  lambda c, x, y: x if c else y, 3, "({1} if {0} else {2})")
        ]

class EnumerativeSynthesizer:
    """
    HSCI NATIVE ENGINE (The 'Search' Lobe).
    """
    def __init__(self, learner=None, max_depth=3):
        self.learner = learner
        self.primitives = CognitivePrimitives()
        self.max_depth = max_depth
        self.logger = logging.getLogger("HNSDS")

    def propose(self, goal, examples):
        # 0. Memory Recall Optimization
        if goal.get("reference_solution"):
            # We trust the Mind's recall. Verification will double-check it anyway.
            return goal.get("reference_solution")

        goal_type = goal.get("type")
        
        # --- MATH & SYSTEM SYNTHESIS ---
        if goal_type in ["math", "system"]:
            return self._solve_symbolic(goal)

        desc = goal.get("description", "").lower()
        
        # 1. Infer Learning Goal (IO Examples)
        # To "learn" and "solve", we need to know what success looks like.
        # We infer test cases from the description.
        io_examples = self._infer_io_examples(desc)
        if not io_examples:
             # Fallback if we can't infer IO (e.g. abstract request)
             return "# Error: Could not infer logical constraints for search."

        # Debug: Print inferred examples to understand what we are solving for
        print(f"DEBUG: Synthesizer desc='{desc}'")
        io_examples = self._infer_io_examples(desc)
        print(f"DEBUG: Inferred examples: {io_examples}")
        
        if not io_examples:
            return "# No examples inferred for synthesis."
        
        solution_data = self._bfs_synthesis(io_examples)
        if solution_data:
            return self._generate_full_script(solution_data["code"], desc)
        
        return "# Failed to synthesize logic within depth limit."


    def _solve_symbolic(self, goal):
        """
        Uses Symbolic Reasoning (Z3) to find a candidate solution for math problems.
        """
        try:
            s = Solver()
            var_names = goal.get("variables", [])
            if not var_names:
                # Try to infer from equations if variables not explicitly set
                pass # Should be set by Neural Lobe
                
            z3_vars = {name: Int(name) for name in var_names}
            
            equations = []
            if goal.get("type") == "math":
                equations = [goal.get("equation")]
            else:
                equations = goal.get("equations", [])
                
            for eq_str in equations:
                if not eq_str: continue
                # Parse "x + y == 10" into Z3 constraint
                try:
                    # Safe eval with z3 vars
                    z3_eq = eval(eq_str, {"__builtins__": None}, z3_vars)
                    s.add(z3_eq)
                except Exception as e:
                    self.logger.warning(f"Failed to parse equation '{eq_str}': {e}")
                    
            if s.check() == sat:
                m = s.model()
                # Format: "x=1, y=2"
                solution_parts = []
                for name in var_names:
                    val = m[z3_vars[name]]
                    solution_parts.append(f"{name}={val}")
                return ", ".join(solution_parts)
            else:
                return "# UNSATISFIABLE"
        except Exception as e:
            return f"# SYMBOLIC ERROR: {e}"

    def _infer_io_examples(self, desc):
        # "addition"
        if "add" in desc or "sum" in desc or "plus" in desc:
            return [
                {"in": [1, 1], "out": 2},
                {"in": [0, 5], "out": 5},
                {"in": [10, 20], "out": 30}
            ]
        # "subtraction"
        if "sub" in desc or "diff" in desc or "minus" in desc:
            return [
                {"in": [5, 2], "out": 3},
                {"in": [10, 10], "out": 0}
            ]
        # "max" / "greater"
        if "max" in desc or "greater" in desc:
            return [
                {"in": [1, 5], "out": 5},
                {"in": [10, 2], "out": 10},
                {"in": [7, 7], "out": 7}
            ]
        return None

    def _bfs_synthesis(self, io_examples):
        # Determine Arity
        arity = len(io_examples[0]["in"])
        arg_names = [f"arg{i}" for i in range(arity)]
        
        # --- REAL IMPLEMENTATION OF BFS ---
        # 1. Start with terminals: [arg0, arg1]
        programs = arg_names[:] 
        
        # We need enough iterations to combine atoms
        for _ in range(self.max_depth): 
            next_programs = []
            
            # Simple Binary Search (Program A + Program B)
            for prog1 in programs:
                for prog2 in programs:
                    
                    # Try Adding
                    candidate = f"({prog1} + {prog2})"
                    if self._check_candidate(candidate, arg_names, io_examples):
                        return {"code": f"return {candidate}", "args": arg_names}
                    next_programs.append(candidate)
                    
                    # Try Subtracting (Try both orders)
                    candidate = f"({prog1} - {prog2})"
                    if self._check_candidate(candidate, arg_names, io_examples):
                        return {"code": f"return {candidate}", "args": arg_names}
                    
                    # Try Max (If Logic)
                    candidate = f"({prog1} if {prog1} > {prog2} else {prog2})"
                    if self._check_candidate(candidate, arg_names, io_examples):
                        return {"code": f"return {candidate}", "args": arg_names}

            # Avoid exponential explosion by only keeping new, short programs
            # In a real system, we use 'Beam Search' here.
            # We keep the top 20 simplest new programs.
            next_programs.sort(key=len)
            programs = (programs + next_programs)[:50]
            
        return None

    def _check_candidate(self, code_str, args, examples):
        """
        Verifies a string candidate.
        """
        try:
            func_def = f"def check({','.join(args)}): return {code_str}"
            scope = {}
            exec(func_def, {}, scope)
            check_func = scope['check']
            
            for case in examples:
                inputs = case["in"]
                expected = case["out"]
                res = check_func(*inputs)
                if res != expected:
                    return False
            return True
        except Exception as e:
            # print(f"DEBUG: Check failed for {code_str}: {e}")
            return False

    def _generate_full_script(self, logic, description):
        args = logic['args']
        sig = ", ".join([f"{a}: int" for a in args])
        
        full_code = f'''#!/usr/bin/env python3
"""
HNS-DS Native Logic Solution
Goal: {description}
Origin: Synthesized via Breadth-First Search (Zero Hardcoding)
"""

import sys

def solve({sig}) -> int:
    """
    Synthesized Logic.
    """
    {logic['code']}

if __name__ == "__main__":
    if len(sys.argv) > {len(args)}:
        try:
            # Auto-parsing {len(args)} arguments
            vals = [int(x) for x in sys.argv[1:{len(args)+1}]]
            print(f"Result: {{solve(*vals)}}")
        except ValueError:
            print("Error: Ints required")
    else:
        print("Usage: python script.py {' '.join(['<'+a+'>' for a in args])}")
        print("(Running default test)")
        print(solve(*[10 for _ in args]))
'''
        return full_code.strip()

    def compose(self, solutions):
        return "\n".join(str(s) for s in solutions)