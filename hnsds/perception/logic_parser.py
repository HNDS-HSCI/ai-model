import re

class LogicParser:
    """
    Parses natural language logic puzzles into structured constraints.
    Focuses on Entity-Attribute relationships and Positional logic.
    """
    def __init__(self):
        self.entities = set()
        self.attributes = {} # type -> [values]
        self.constraints = []

    def parse(self, text):
        """
        Main entry point. Returns a dictionary of parsed problem structure.
        """
        self.entities = set()
        self.attributes = {}
        self.constraints = []
        
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if not sentence: continue
            
            self._extract_entities_and_types(sentence)
            self._extract_constraints(sentence)
            
        return {
            "entities": list(self.entities),
            "attributes": self.attributes,
            "constraints": self.constraints
        }

    def _extract_entities_and_types(self, sentence):
        # Heuristic: "There are 5 houses" -> Type: House, Count: 5
        # "The Brit lives in the red house" -> Entity: Brit, Attr: Red, Type: House
        
        # Simple noun extraction (very basic)
        words = sentence.split()
        
        # Check for numeric definition
        # e.g. "There are 5 houses"
        match = re.search(r'(\d+) ([a-z]+)s', sentence)
        if match:
            count = int(match.group(1))
            type_name = match.group(2)
            self.attributes[type_name] = [f"{type_name}_{i+1}" for i in range(count)]
            return

    def _extract_constraints(self, sentence):
        # 1. Assignment: "The Brit lives in the Red house"
        # 2. Adjacency: "The Green house is next to the White house"
        # 3. Negation: "The Swede does not keep dogs"
        
        # Normalize
        s = sentence.replace("lives in", "is").replace("keeps", "is").replace("eats", "is").replace("drinks", "is")
        
        # KEYWORD MATCHING
        
        # Negation
        is_negation = "not" in s
        
        # Adjacency
        if "next to" in s or "neighbor" in s:
            parts = re.split(r' next to | neighbor ', s)
            if len(parts) == 2:
                # Cleanup "is" from the end of the subject
                # "The Brit is" -> "The Brit"
                left_raw = re.sub(r'\s+is\s*$', '', parts[0].strip())
                
                left = self._extract_noun(left_raw)
                right = self._extract_noun(parts[1])
                self.constraints.append({
                    "type": "adjacency",
                    "entity1": left,
                    "entity2": right,
                    "negation": is_negation
                })
                return

        # Direct Association (is)
        # We need to be careful not to trigger on "is" inside "is next to" (handled above)
        if " is " in s:
            parts = s.split(" is ")
            left = self._extract_noun(parts[0])
            right = self._extract_noun(parts[1])
            self.constraints.append({
                "type": "association",
                "entity1": left,
                "entity2": right,
                "negation": is_negation
            })
            return

    def _extract_noun(self, phrase):
        # Attempt to get the key noun. 
        # "The red house" -> "red" (if it's a known attribute like color)
        # Heuristic: If we have 2 words, and 2nd is "house/man", take 1st.
        # Else take the whole thing cleaned.
        
        clean = phrase.replace("the", "").replace("a ", "").strip()
        words = clean.split()
        
        # Filter generic containers
        generics = {"house", "man", "person", "pet", "drink"}
        
        if len(words) >= 2 and words[-1] in generics:
            return words[-2] # "red house" -> "red"
            
        return clean.split()[-1] # Fallback to last word if single
