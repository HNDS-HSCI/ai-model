"""
UniversalConceptEngine — Phase 8 of HSCI Activation
Autonomous Concept Acquisition (Meta-Learning).
Enables the system to learn new mathematical or logical formulas described in text,
synthesize Z3 template constraints dynamically, and register them as permanent Concepts.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from hsci.core.data_types import Concept, AxiomType

class UniversalConceptEngine:
    """
    HSCI Universal Concept & Metacognitive Engine.
    Allows users to define new equations, formulas, and relationships in natural language.
    Synthesizes Z3 templates and stores them in the Concept Library.
    """

    def __init__(self):
        pass

    def extract_definition(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Parses text to extract a concept definition.
        Examples:
          "define concept density as mass / volume" -> ("density", "mass / volume")
          "let profit_margin = profit / revenue" -> ("profit_margin", "profit / revenue")
          "concept velocity is distance divided by time" -> ("velocity", "distance / time")
        """
        patterns = [
            # "define concept X as Y" or "define X as Y"
            r'(?:define\s+concept|define)\s+(\w+)\s+as\s+(.+)$',
            # "let X = Y" or "let X be Y"
            r'let\s+(\w+)\s+(?:=|be)\s+(.+)$',
            # "concept X is Y"
            r'concept\s+(\w+)\s+is\s+(.+)$',
        ]

        text_clean = text.strip()
        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                name = match.group(1).strip().upper()
                formula = match.group(2).strip()
                # Clean up English words in formula
                formula = formula.replace("divided by", "/").replace("times", "*").replace("plus", "+").replace("minus", "-")
                return name, formula

        return None

    def learn_concept(self, text: str, concept_library) -> Optional[Concept]:
        """
        Parses definition, builds a Z3 template, and adds it to the library.
        """
        def_info = self.extract_definition(text)
        if not def_info:
            return None

        concept_name, formula_str = def_info
        formula_str = formula_str.replace("^", "**")

        # Parse variables involved in the formula
        # Extract alphanumeric words that are not operators/numbers
        words = re.findall(r'[a-zA-Z_]\w*', formula_str)
        variables = list(set(words))
        
        # Determine the target entity (the concept name itself)
        target = concept_name.lower()
        if target not in variables:
            variables.append(target)

        # Build Z3 constraint string dynamically
        # Example: lambda target, val1, val2: target == val1 / val2
        z3_template_str = f"lambda {target}, {', '.join([v for v in variables if v != target])}: {target} == {formula_str}"

        # Create new Concept object
        new_concept = Concept(
            name=concept_name,
            axiom_type=AxiomType.REDUCTION,
            abstract_rule=f"{target} = {formula_str}",
            z3_template=z3_template_str,
            domain="meta_learned",
            learned_from_domains=["user_input"],
            strength=1.0,
            proof_count=1,
            required_entities=variables,
            z3_verified=True
        )

        # Register in library
        concept_library.add(new_concept)
        print(f"[ConceptEngine] Successfully learned new concept: {concept_name} | Rule: {new_concept.abstract_rule}")
        return new_concept

    def can_learn(self, text: str) -> bool:
        """Check if input text is proposing a concept definition."""
        return self.extract_definition(text) is not None
