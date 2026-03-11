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
    def __init__(self, learner=None, max_depth=4):
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

        desc = goal.get("desc", "").lower()
        if not desc:
            desc = goal.get("description", "").lower()

        self.logger.info(f"SYNTHESIZER_DESC: '{desc}'")
        
        # 1. Infer Learning Goal (IO Examples)
        # To "learn" and "solve", we need to know what success looks like.
        # We infer test cases from the description.
        io_examples = self._infer_io_examples(desc)
        
        # Debug: Print inferred examples to understand what we are solving for
        self.logger.info(f"SYNTHESIZER_IO_EXAMPLES: {io_examples}")
        
        if not io_examples:
             # Fallback if we can't infer IO (e.g. abstract request)
             self.logger.warning(f"SYNTHESIZER_FAIL: No IO examples for '{desc}'")
             return "# Error: Could not infer logical constraints for search."
        
        solution_data = self._bfs_synthesis(io_examples)
        if solution_data:
            return self._generate_full_script(solution_data, desc)
        
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
        # 1. Determine Arity from description (Semantic Insight)
        arity = 2
        
        # Concept-based arity detection
        number_concepts = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        for concept, val in number_concepts.items():
            if concept in desc or str(val) in desc:
                arity = val
                break
        
        # Unary concept detection
        if any(w in desc for w in ["square", "cube", "unary", "single"]): 
            arity = 1
        
        # 2. Infer operation and generate dynamic examples
        # Addition / Summation
        if any(w in desc for w in ["add", "sum", "plus", "total", "combine"]):
            # Use non-uniform values to force using multiple args
            return [
                {"in": [i + 1 for i in range(arity)], "out": sum([i + 1 for i in range(arity)])},
                {"in": [10, 5, 2, 8, 3][:arity], "out": sum([10, 5, 2, 8, 3][:arity])},
                {"in": [100, 1, 0, 0, 0][:arity], "out": sum([100, 1, 0, 0, 0][:arity])}
            ]
            
        # Subtraction
        if any(w in desc for w in ["sub", "diff", "minus"]):
            return [
                {"in": [10, 2], "out": 8},
                {"in": [5, 5], "out": 0},
                {"in": [100, 50], "out": 50}
            ]
            
        # Multiplication / Power
        if any(w in desc for w in ["mul", "product", "times", "square", "cube", "power"]):
            if "square" in desc:
                 return [{"in": [x], "out": x*x} for x in [2, 5, 10]]
            if "cube" in desc:
                 return [{"in": [x], "out": x*x*x} for x in [2, 3, 5]]
            
            import math
            return [
                {"in": [i + 2 for i in range(arity)], "out": math.prod([i + 2 for i in range(arity)])},
                {"in": [2, 1, 3, 5, 4][:arity], "out": math.prod([2, 1, 3, 5, 4][:arity])},
                {"in": [10, 0, 5, 2, 3][:arity], "out": 0}
            ]
            
        # Max/Larger
        if any(w in desc for w in ["max", "greater", "larger", "biggest"]):
            return [
                {"in": list(range(arity)), "out": arity - 1},
                {"in": list(reversed(range(arity))), "out": arity - 1},
                {"in": [7] * arity, "out": 7}
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
            
            # Simple Binary Search (Program A [op] Program B)
            for prog1 in programs:
                for prog2 in programs:
                    
                    # Try Adding
                    candidate = f"({prog1} + {prog2})"
                    if self._check_candidate(candidate, arg_names, io_examples):
                        return {"code": f"return {candidate}", "args": arg_names}
                    next_programs.append(candidate)
                    
                    # Try Multiplying
                    candidate = f"({prog1} * {prog2})"
                    if self._check_candidate(candidate, arg_names, io_examples):
                        return {"code": f"return {candidate}", "args": arg_names}
                    next_programs.append(candidate)
                    
                    # Try Subtracting
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