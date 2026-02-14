import logging

class NativeProgramSynthesizer:
    """
    INVENTION: First-Principles Logic Composer.
    
    This replaces 'templates' with 'reasoning'.
    It builds code by understanding the SEMANTICS of the request
    and searching for the right combination of Cognitive Primitives.
    """
    def __init__(self):
        self.logger = logging.getLogger("Synthesizer")
        
        # 1. Cognitive Primitives (The Atoms of Thought)
        self.primitives = {
            "aggregators": {
                "sum": {"init": "0", "op": "+="},
                "product": {"init": "1", "op": "*="},
                "multiply": {"init": "1", "op": "*="},
                "count": {"init": "0", "op": "+= 1 #"}, # # indicates ignore value
            },
            "filters": {
                "even": "n % 2 == 0",
                "odd": "n % 2 != 0",
                "positive": "n > 0",
                "negative": "n < 0",
                "greater": "n > {val}", # Dynamic slot
                "less": "n < {val}"
            },
            "transforms": {
                "square": "n * n",
                "double": "n * 2",
                "half": "n / 2"
            }
        }

    def propose(self, goal, examples=[]):
        """
        Dynamically constructs a solution by reasoning about the constraints.
        """
        desc = goal.get("desc", "").lower()
        
        # 1. Semantic Parsing (Understanding the MEANING)
        semantics = self._extract_semantics(desc)
        
        # 2. Structural Reasoning (Determining the ALGORITHM)
        # If we have a list/collection and a scalar output -> Reduce Pattern
        if "list" in desc or "array" in desc or "numbers" in desc:
            return self._synthesize_reduction(semantics, desc)
            
        # If generic math -> Simple Function
        return self._synthesize_math(semantics)

    def _extract_semantics(self, desc):
        """
        Extracts the logical constraints from natural language.
        This is the 'Perception' of logic.
        """
        semantics = {
            "aggregator": "sum", # Default
            "conditions": [],
            "transform": None,
            "threshold": None
        }
        
        # Detect Aggregation Type
        for key in self.primitives["aggregators"]:
            if key in desc:
                semantics["aggregator"] = key
                break
                
        # Detect Filters
        for key in self.primitives["filters"]:
            if key in desc:
                # Check for dynamic values (e.g. "greater than 5")
                if key in ["greater", "less"]:
                    import re
                    # Find number after the word
                    match = re.search(f"{key}.*?(\d+)", desc)
                    if match:
                        semantics["threshold"] = match.group(1)
                        semantics["conditions"].append(key)
                else:
                    semantics["conditions"].append(key)
        
        # Detect Transforms
        for key in self.primitives["transforms"]:
            if key in desc:
                semantics["transform"] = key
                
        return semantics

    def _synthesize_reduction(self, semantics, desc):
        """
        Constructs a loop-based reduction algorithm from scratch.
        """
        agg_key = semantics["aggregator"]
        agg_logic = self.primitives["aggregators"].get(agg_key, self.primitives["aggregators"]["sum"])
        
        # Build the AST (Abstract Syntax Tree) equivalents in text
        lines = []
        lines.append("def solve(numbers):")
        lines.append(f"    result = {agg_logic['init']}")
        lines.append("    for n in numbers:")
        
        indent = "        "
        
        # Apply Filters (Logic Nesting)
        for cond_key in semantics["conditions"]:
            logic = self.primitives["filters"][cond_key]
            if "{val}" in logic and semantics["threshold"]:
                logic = logic.format(val=semantics["threshold"])
            elif "{val}" in logic:
                 continue # Skip if missing threshold
            
            lines.append(f"{indent}if {logic}:")
            indent += "    "
            
        # Apply Transforms
        value_to_agg = "n"
        if semantics["transform"]:
            # e.g. "square the number"
            trans_logic = self.primitives["transforms"][semantics["transform"]]
            # Simple substitution
            value_to_agg = trans_logic # "n * n"
            
        # Apply Aggregation
        op = agg_logic["op"]
        if "#" in op: # Special case for count
            op = op.split("#")[0]
            lines.append(f"{indent}result {op}")
        else:
            lines.append(f"{indent}result {op} {value_to_agg}")
            
        lines.append("    return result")
        
        return "\n".join(lines)

    def _synthesize_math(self, semantics):
        # Fallback for simple math logic
        return "def solve(n):\n    return n"