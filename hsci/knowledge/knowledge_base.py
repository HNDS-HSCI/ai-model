import random
import networkx as nx
from datetime import datetime
from typing import List, Any, Dict, Optional
from hsci.core.data_types import (
    PerceptionMap, KnowledgeResult, Concept, Episode, AxiomType
)
from hsci.symbolic.z3_templates import Z3_METADATA

class ConceptLibrary:
    """Stores and retrieves learned concepts."""

    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self._seed_concepts()

    def _seed_concepts(self):
        for name, meta in Z3_METADATA.items():
            concept = Concept(
                name=name,
                abstract_rule=meta["template"],
                z3_template=meta["template"], # Simplified placeholder
                domain=meta["domain"],
                learned_from_domains=[meta["domain"]],
                strength=1.0,
                z3_verified=True,
                required_entities=meta["entities"]
            )
            self.concepts[name] = concept

    def find_by_intent(self, intent: AxiomType, entity_types: List[str]) -> List[Concept]:
        matches = []
        for concept in self.concepts.values():
            if concept.axiom_type == intent:
                matches.append(concept)
        return sorted(matches, key=lambda c: c.strength, reverse=True)

    def add(self, concept: Concept):
        self.concepts[concept.name] = concept

    def update_strength(self, concept_name: str, delta: float):
        if concept_name in self.concepts:
            c = self.concepts[concept_name]
            c.strength = min(1.0, c.strength + delta)
            c.proof_count += 1
            c.last_used = datetime.now()

    def contains(self, concept_name: str) -> bool:
        return concept_name in self.concepts

    def get_weakest(self, n: int = 3) -> List[Concept]:
        sorted_concepts = sorted(self.concepts.values(), key=lambda c: c.strength)
        return sorted_concepts[:min(n, len(sorted_concepts))]

    def sample(self, n: int = 2) -> List[Concept]:
        all_concepts = list(self.concepts.values())
        return random.sample(all_concepts, min(n, len(all_concepts)))


class OntologyGraph:
    """Graph of concept relationships."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._seed_ontology()

    def _seed_ontology(self):
        edges = [
            ("PERCENTAGE", "MULTIPLICATION", "IS_A"),
            ("MULTIPLICATION", "ADDITION", "GENERALIZES"),
            ("SUBTRACTION", "ADDITION", "ANALOGOUS_TO"),
            ("LINEAR_EQUATION", "SUBTRACTION", "COMPOSES"),
            ("LINEAR_EQUATION", "DIVISION", "COMPOSES"),
            ("DISTANCE_RATE_TIME", "MULTIPLICATION", "ANALOGOUS_TO"),
            ("FORCE_MASS_ACCEL", "MULTIPLICATION", "ANALOGOUS_TO"),
        ]
        for src, tgt, rel in edges:
            self.graph.add_edge(src, tgt, relation=rel)

    def integrate(self, concept: Concept):
        self.graph.add_node(concept.name)

    def find_structural_analogies(self, entity_graph, top_k=5):
        # Placeholders for analogical matches based on common physics/finance terms
        text = str(entity_graph.get('text', "")).lower()
        analogies = []
        if any(w in text for w in ["distance", "velocity", "time"]):
             analogies.append("DISTANCE_RATE_TIME")
        if any(w in text for w in ["force", "mass", "acceleration"]):
             analogies.append("FORCE_MASS_ACCEL")
        
        # In a full implementation, we'd return Concept objects.
        # But rir_loop expects direct_matches to be empty for analogies to trigger.
        return analogies


class EpisodeMemory:
    """Stores past solved problems."""

    def __init__(self, max_episodes=10000):
        self.episodes: List[Episode] = []
        self.max_episodes = max_episodes

    def store(self, episode: Episode):
        self.episodes.append(episode)
        if len(self.episodes) > self.max_episodes:
            self.episodes.sort(key=lambda e: (e.was_verified, e.timestamp), reverse=True)
            self.episodes = self.episodes[:self.max_episodes]

    def find_similar(self, perception: PerceptionMap, top_k=3):
        return [e for e in self.episodes if e.domain == perception.domain][:top_k]


class KnowledgeBase:
    def __init__(self):
        self.concept_library = ConceptLibrary()
        self.ontology = OntologyGraph()
        self.episode_memory = EpisodeMemory()

    def query(self, perception: PerceptionMap) -> KnowledgeResult:
        direct = self.concept_library.find_by_intent(
            perception.intent,
            list(perception.entities.keys())
        )
        
        # If no direct match in domain, look for structural analogies
        analogies_names = self.ontology.find_structural_analogies(perception.entity_graph)
        analogies = [self.concept_library.concepts[name] for name in analogies_names if name in self.concept_library.concepts]
        
        episodes = self.episode_memory.find_similar(perception)
        
        confidence = 1.0 if direct else (0.7 if analogies else 0.3)

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
        self.concept_library.update_strength(concept.name, strength)
