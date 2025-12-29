import re

class Parser:
    """
    The Perception Lobe: Semantic Transduction.
    Converts human language patterns into symbolic logic.
    """
    def parse(self, raw_input):
        clean_input = raw_input.lower().strip()
        
        # Semantic mapping: Identify the intent
        intent = "unknown"
        
        # Robust Keyword Matching
        tokens = set(clean_input.split())
        
        if any(word in clean_input for word in ["analyze", "log", "parse", "extract"]):
            intent = "analysis"
        # Check for code generation (Handles "write the code", "give me code", "generate function")
        elif "code" in clean_input or "function" in clean_input or "script" in clean_input:
            intent = "code_generation"
        elif any(word in clean_input for word in ["implement", "def ", "python", "algorithm"]):
             intent = "code_generation"
        elif any(word in clean_input for word in ["prove", "theorem", "show that"]):
            intent = "proof"
        elif any(word in clean_input for word in ["why", "how", "explain", "tell me", "what is the"]):
            intent = "conversational"
        elif any(word in clean_input for word in ["solve", "find", "calculate", "what is", "add", "sum", "math"]):
            intent = "math_query"

        # Clean up natural language artifacts before extraction
        # This prevents "find x where x..." from becoming "x x..."
        cleaned_for_regex = clean_input
        for keyword in ["solve", "find", "where", "what is", "calculate", "compute"]:
            cleaned_for_regex = cleaned_for_regex.replace(keyword, "")
            
        # Extract variables and constants
        # Look for patterns like "x + 2 = 5" or "sum of x and y is 10"
        equations = []
        
        # Skip equation extraction for non-math intents
        if intent in ["analysis", "code_generation"]:
            pass
        else:
            # 1. Standard equation notation
            found = re.findall(r'[a-z0-9\s\+\-\*\/\^]+=[a-z0-9\s\+\-\*\/\^]+', cleaned_for_regex)
            equations.extend([e.strip() for e in found])
            
            # 2. Semantic extraction: "x plus y is 10" -> "x + y = 10"
            semantic_input = cleaned_for_regex.replace("plus", "+").replace("minus", "-").replace("is", "=").replace("times", "*")
            found_semantic = re.findall(r'[a-z0-9\s\+\-\*\/\^]+=[a-z0-9\s\+\-\*\/\^]+', semantic_input)
            for e in found_semantic:
                if e.strip() not in equations:
                    equations.append(e.strip())
        
        return {
            "raw": raw_input,
            "intent": intent,
            "equations": equations
        }