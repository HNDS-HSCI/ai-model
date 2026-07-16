from typing import Dict, List, Optional
from hsci.core.data_types import Concept, AxiomType
from hsci.symbolic.z3_templates import Z3_TEMPLATES, Z3_METADATA
from datetime import datetime
import random
import uuid

class ConceptLibrary:
    """
    Manages the storage and retrieval of learned Concepts.
    For now, uses an in-memory dictionary.
    """

    def __init__(self, seed: bool = False):
        self._concepts: Dict[str, Concept] = {}
        if seed:
            self._seed_basic_concepts()

    def _seed_basic_concepts(self):
        """Pre-seeds the library with basic arithmetic concepts from Z3_METADATA."""
        for name, data in Z3_METADATA.items():
            concept_id = name.lower() # Use lowercased name as ID for predictability
            concept = Concept(
                id=concept_id,
                name=name,
                axiom_type=AxiomType.REDUCTION,
                abstract_rule=data["template"],
                z3_template=data["template"], # Simplified for now
                domain=data["domain"],
                learned_from_domains=[data["domain"]],
                strength=1.0, # Pre-seeded concepts are strong
                proof_count=100,
                created_at=datetime.now(),
                last_used=datetime.now(),
                generalizes_to=[],
                required_entities=data.get("entities", []),
                optional_entities=[],
                z3_verified=True
            )
            self._concepts[concept_id] = concept

    def _extract_entities_from_template(self, template: str) -> List[str]:
        """Extracts entity names from a template string (e.g., 'result == a + b')."""
        import re
        # Find all alphanumeric sequences that are not operators or '=='
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', template)
        return [w for w in words if w not in ['result', 'base', 'rate', 'a', 'b', 'c', 'x', 'Int', 'Real', 'And', 'ForAll', 'Implies', 'inv']] + ['result']
        # This is a very rough heuristic, needs improvement

    @property
    def concepts(self) -> List[Concept]:
        return list(self._concepts.values())

    def add(self, concept: Concept):
        """Adds a new concept to the library."""
        if concept.id in self._concepts:
            print(f"Warning: Concept with ID '{concept.id}' already exists. Updating.")
        self._concepts[concept.id] = concept

    def find_by_intent(self, intent: AxiomType, entity_types: List[str]) -> List[Concept]:
        """
        Retrieves concepts matching a given intent.
        Ranks by entity overlap for better concept selection.
        """
        matched_concepts = [
            concept for concept in self._concepts.values()
            if concept.axiom_type == intent
        ]
        
        # Sort by entity overlap: concepts whose required entities 
        # match the query entities should rank higher
        if entity_types and matched_concepts:
            entity_set = set(e.lower() for e in entity_types)
            matched_concepts.sort(
                key=lambda c: (
                    len(set(e.lower() for e in c.required_entities) & entity_set),
                    c.strength
                ),
                reverse=True
            )
        
        return matched_concepts

    def update_strength(self, concept_id: str, strength: float):
        """Updates the strength of a concept."""
        if concept_id in self._concepts:
            self._concepts[concept_id].strength = strength
        else:
            print(f"Warning: Concept with ID '{concept_id}' not found for strength update.")

    def contains(self, concept_id: str) -> bool:
        """Checks if a concept with the given ID exists in the library."""
        return concept_id in self._concepts

    def sample(self, n: int) -> List[Concept]:
        """Samples n random concepts from the library."""
        if not self._concepts:
            return []
        all_concepts = list(self._concepts.values())
        return random.sample(all_concepts, min(n, len(all_concepts)))

    def get_weakest(self, n: int) -> List[Concept]:
        """Returns the n weakest concepts (lowest strength)."""
        if not self._concepts:
            return []
        sorted_concepts = sorted(self._concepts.values(), key=lambda c: c.strength)
        return sorted_concepts[:min(n, len(sorted_concepts))]
