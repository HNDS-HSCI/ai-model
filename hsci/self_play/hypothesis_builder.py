import random
import re
from datetime import datetime
from typing import List, Optional
from hsci.core.data_types import PerceptionMap, Concept, AxiomType, Graph

class HypothesisBuilder:
    """
    Generates novel problems (hypotheses) for the SelfPlayEngine.
    Ensures generated problems have sufficient operands for the selected concepts.
    """

    def build_from_concepts(self, concepts: List[Concept]) -> PerceptionMap:
        """
        Generates a novel problem by combining existing concepts.
        """
        if not concepts:
            return self._generate_random_arithmetic()

        entities = {}
        for concept in concepts:
            # Extract variable names from the abstract rule (e.g., result == a + b)
            # This ensures we provide values for all variables the concept needs.
            vars = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', concept.abstract_rule)
            vars = [v for v in vars if v not in ['result', 'Int', 'Real', 'And', '==', '+', '-', '*', '/']]
            
            for v_name in vars:
                if v_name not in entities:
                    entities[v_name] = random.randint(1, 100)
            
            # Ensure 'result' placeholder is present
            if 'result' not in entities:
                entities['result'] = None

        # Ensure at least one unknown
        unknown_key = 'result' if entities.get('result') is None else random.choice(list(entities.keys()))
        entities[unknown_key] = None

        return PerceptionMap(
            entities=entities,
            unknown_entities=[unknown_key],
            relationships=[],
            intent=concepts[0].axiom_type,
            confidence=0.5,
            entity_graph={"text": f"Generated hypothesis from concepts: {[c.name for c in concepts]}"}
        )

    def build_for_concept(self, concept: Concept, difficulty: float) -> PerceptionMap:
        """
        Generates a problem specifically designed to strengthen a weak concept.
        """
        entities = {}
        vars = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', concept.abstract_rule)
        vars = [v for v in vars if v not in ['result', 'Int', 'Real', 'And', '==', '+', '-', '*', '/']]

        for v_name in vars:
             entities[v_name] = random.randint(1, int(100 * (1 + difficulty)))
        
        entities['result'] = None

        return PerceptionMap(
            entities=entities,
            unknown_entities=['result'],
            relationships=[],
            intent=concept.axiom_type,
            confidence=0.5,
            entity_graph={"text": f"Targeted practice for concept: {concept.name}"}
        )

    def _generate_random_arithmetic(self) -> PerceptionMap:
        """Fallback for when no concepts are available."""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        return PerceptionMap(
            entities={"a": a, "b": b, "result": None},
            unknown_entities=["result"],
            relationships=[],
            intent=AxiomType.REDUCTION,
            confidence=0.5,
            entity_graph={"text": f"Random arithmetic hypothesis: {a} and {b}"}
        )
