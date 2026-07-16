import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from hsci.core.data_types import Concept

class IKnowledgeCache(ABC):
    """
    Interface for request-safe, replaceable cache engines storing concepts,
    namespace listings, and search index results.
    """
    @abstractmethod
    def get_concept(self, concept_id: str) -> Optional[Concept]: pass
    @abstractmethod
    def set_concept(self, concept_id: str, concept: Concept) -> None: pass
    @abstractmethod
    def get_concept_by_name(self, name: str) -> Optional[Concept]: pass
    @abstractmethod
    def set_concept_by_name(self, name: str, concept: Concept) -> None: pass
    @abstractmethod
    def get_namespace(self, namespace: str) -> Optional[List[Concept]]: pass
    @abstractmethod
    def set_namespace(self, namespace: str, concepts: List[Concept]) -> None: pass
    @abstractmethod
    def get_search(self, query: str) -> Optional[List[Concept]]: pass
    @abstractmethod
    def set_search(self, query: str, concepts: List[Concept]) -> None: pass
    @abstractmethod
    def invalidate_concept(self, concept_id: str) -> None: pass
    @abstractmethod
    def clear(self) -> None: pass


class InMemoryKnowledgeCache(IKnowledgeCache):
    """
    Concrete, thread-safe implementation of IKnowledgeCache utilizing
    synchronized dictionaries for local memory caching.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._concepts: Dict[str, Concept] = {}
        self._names: Dict[str, Concept] = {}
        self._namespaces: Dict[str, List[Concept]] = {}
        self._searches: Dict[str, List[Concept]] = {}

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        with self._lock:
            return self._concepts.get(concept_id)

    def set_concept(self, concept_id: str, concept: Concept) -> None:
        with self._lock:
            self._concepts[concept_id] = concept

    def get_concept_by_name(self, name: str) -> Optional[Concept]:
        with self._lock:
            return self._names.get(name)

    def set_concept_by_name(self, name: str, concept: Concept) -> None:
        with self._lock:
            self._names[name] = concept

    def get_namespace(self, namespace: str) -> Optional[List[Concept]]:
        with self._lock:
            return self._namespaces.get(namespace)

    def set_namespace(self, namespace: str, concepts: List[Concept]) -> None:
        with self._lock:
            self._namespaces[namespace] = concepts

    def get_search(self, query: str) -> Optional[List[Concept]]:
        with self._lock:
            return self._searches.get(query)

    def set_search(self, query: str, concepts: List[Concept]) -> None:
        with self._lock:
            self._searches[query] = concepts

    def invalidate_concept(self, concept_id: str) -> None:
        """Removes a concept and invalidates any names, namespaces, or searches it intersects with."""
        with self._lock:
            concept = self._concepts.pop(concept_id, None)
            if concept:
                # Remove from name index
                self._names.pop(concept.name, None)
                
                # Invalidate namespace caches containing this concept namespace
                ns_to_remove = [
                    ns for ns in self._namespaces 
                    if ns == concept.namespace or concept.namespace.startswith(f"{ns}.")
                ]
                for ns in ns_to_remove:
                    self._namespaces.pop(ns, None)
                    
            # Searches are invalidated conservatively (clear all searches to prevent stale index returns)
            self._searches.clear()

    def clear(self) -> None:
        with self._lock:
            self._concepts.clear()
            self._names.clear()
            self._namespaces.clear()
            self._searches.clear()
