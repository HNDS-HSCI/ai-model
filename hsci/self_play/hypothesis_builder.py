import random
import re
from datetime import datetime
from typing import List, Optional
from hsci.core.data_types import PerceptionMap, Concept, AxiomType, Graph, EntityValue

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
                    val = random.randint(1, 100)
                    entities[v_name] = EntityValue(value=val, unit=None, known=True, raw_text=str(val))
            
            # Ensure 'result' placeholder is present
            if 'result' not in entities:
                entities['result'] = EntityValue(value=None, unit=None, known=False, raw_text="result")

        # Ensure at least one unknown
        unknown_key = 'result' if not entities['result'].known else random.choice(list(entities.keys()))
        entities[unknown_key].value = None
        entities[unknown_key].known = False

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
             val = random.randint(1, int(100 * (1 + difficulty)))
             entities[v_name] = EntityValue(value=val, unit=None, known=True, raw_text=str(val))
        
        entities['result'] = EntityValue(value=None, unit=None, known=False, raw_text="result")

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
            entities={
                "a": EntityValue(value=a, unit=None, known=True, raw_text=str(a)), 
                "b": EntityValue(value=b, unit=None, known=True, raw_text=str(b)), 
                "result": EntityValue(value=None, unit=None, known=False, raw_text="result")
            },
            unknown_entities=["result"],
            relationships=[],
            intent=AxiomType.REDUCTION,
            confidence=0.5,
            entity_graph={"text": f"Random arithmetic hypothesis: {a} and {b}"}
        )
