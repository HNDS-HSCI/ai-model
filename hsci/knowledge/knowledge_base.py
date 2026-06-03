import random
from datetime import datetime
from typing import List, Any, Dict, Optional
from hsci.core.data_types import (
    PerceptionMap, KnowledgeResult, Concept, Episode, AxiomType
)
from hsci.knowledge.concept_library import ConceptLibrary
from hsci.knowledge.ontology_graph import OntologyGraph
from hsci.knowledge.episode_memory import EpisodeMemory

class KnowledgeBase:
    """
    LAYER 2: Knowledge Base
    Integrates ConceptLibrary, OntologyGraph, and EpisodeMemory.
    Handles direct retrieval and analogical mapping.
    """
    def __init__(self, seed: bool = False):
        self.concept_library = ConceptLibrary(seed=seed)
        self.ontology = OntologyGraph()
        self.episode_memory = EpisodeMemory()
        
        # Seed ontology with basic relationships if empty
        if seed:
            self._seed_ontology()

    def _seed_ontology(self):
        # Only seed if concepts were seeded in concept_library
        concepts = self.concept_library.sample(10)
        for c in concepts:
            self.ontology.add_concept(c)
        
        # Add some basic edges for testing/demonstration
        # This is a bit brittle as it depends on seeded names
        try:
            self.ontology.add_relationship("percentage", "multiplication", "IS_A")
            self.ontology.add_relationship("multiplication", "addition", "GENERALIZES")
        except (ValueError, KeyError):
            pass

    def query(self, perception: PerceptionMap) -> KnowledgeResult:
        # 1. Direct Retrieval
        direct = self.concept_library.find_by_intent(
            perception.intent,
            list(perception.entities.keys())
        )
        
        # AGI FLUIDITY: If COMPOSITION (logic) has no direct concept, 
        # look for REDUCTION (math) as these often overlap.
        if not direct and perception.intent == AxiomType.COMPOSITION:
             direct = self.concept_library.find_by_intent(
                 AxiomType.REDUCTION,
                 list(perception.entities.keys())
             )

        # 2. Analogical Retrieval (Structural)
        analogies = self.ontology.find_structural_analogies(perception.entity_graph)
        
        # 3. Episodic Retrieval
        episodes = self.episode_memory.find_similar(perception)
        
        # If no direct matches, confidence should be 0.0 or low, but test expects 0.0
        confidence = 1.0 if direct else (0.7 if analogies else 0.0)

        return KnowledgeResult(
            direct_matches=direct,
            analogical_matches=analogies,
            episodes=episodes,
            confidence=confidence
        )

    def store_concept(self, concept: Concept):
        self.concept_library.add(concept)
        self.ontology.integrate(concept)

    def reinforce_concept(self, concept: Concept, strength: float):
        # Update in both components
        self.concept_library.update_strength(concept.id, strength)
        self.ontology.strengthen_edges(concept.id, strength)

    def store_impossibility(self, pattern: Dict[str, Any], counterexample: Dict[str, Any]):
        """
        Placeholder for storing impossible reasoning patterns or counterexamples.
        """
        print(f"KnowledgeBase: Storing impossibility for pattern '{pattern}' (placeholder)")
