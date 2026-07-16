import logging
import functools
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from hsci.core.data_types import Concept
from hsci.core.storage import HSCIStorageError
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_store import IConceptStore
from hsci.knowledge.knowledge_cache import IKnowledgeCache

logger = logging.getLogger("HSCI.Knowledge.KnowledgeManager")

# ─────────────────────────────────────────────
# CUSTOM EXCEPTION HIERARCHY
# ─────────────────────────────────────────────

class KnowledgeError(Exception):
    """Base exception for all logical Universal Knowledge Model errors."""
    pass

class KnowledgeNotFoundError(KnowledgeError):
    """Raised when a requested concept or entity cannot be resolved."""
    pass

class KnowledgeConflictError(KnowledgeError):
    """Raised when writing a concept conflicts with an existing entry constraint (e.g. duplicate name)."""
    pass

class KnowledgeValidationError(KnowledgeError):
    """Raised when validation constraints (bounds or type matching) fail."""
    pass

class KnowledgeStoreUnavailableError(KnowledgeError):
    """Raised when underlying databases or caches are unreachable or throw errors."""
    pass


def translate_exceptions(func):
    """Decorator translating physical storage exceptions to logical domain exceptions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KnowledgeError:
            raise
        except HSCIStorageError as e:
            msg = str(e)
            if "UNIQUE constraint" in msg or "Duplicate" in msg:
                raise KnowledgeConflictError(f"Duplicate entry conflict: {e}")
            elif "validation" in msg.lower():
                raise KnowledgeValidationError(f"Validation constraints violated: {e}")
            else:
                raise KnowledgeStoreUnavailableError(f"Storage provider execution error: {e}")
        except Exception as e:
            raise KnowledgeStoreUnavailableError(f"Unexpected persistence layer exception: {e}")
    return wrapper


# ─────────────────────────────────────────────
# KNOWLEDGE MANAGER INTERFACE
# ─────────────────────────────────────────────

class IKnowledgeManager(ABC):
    """
    Façade boundary presenting the single gate between cognitive loops and UKM storage.
    Defines logical store coordinate interfaces.
    """
    @abstractmethod
    def get_concept(self, concept_id: str) -> Optional[Concept]: pass
    @abstractmethod
    def get_concept_by_name(self, name: str) -> Optional[Concept]: pass
    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[Concept]: pass
    @abstractmethod
    def search_by_namespace(self, namespace: str) -> List[Concept]: pass
    @abstractmethod
    def create_concept(self, concept: Concept, provenance: Optional[Dict[str, Any]] = None) -> str: pass
    @abstractmethod
    def update_concept(self, concept: Concept) -> None: pass
    @abstractmethod
    def archive_concept(self, concept_id: str) -> None: pass
    @abstractmethod
    def merge_concepts(self, id_1: str, id_2: str, merged_concept: Concept) -> str: pass
    @abstractmethod
    def split_concept(self, parent_id: str, split_1: Concept, split_2: Concept) -> Tuple[str, str]: pass
    @abstractmethod
    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None: pass
    @abstractmethod
    def detach_metadata(self, concept_id: str, key: str) -> None: pass
    @abstractmethod
    def exists(self, concept_id: str) -> bool: pass
    @abstractmethod
    def preload(self, concepts: List[Concept]) -> None: pass
    @abstractmethod
    def warm_cache(self, concept_ids: List[str]) -> None: pass
    @abstractmethod
    def invalidate_cache(self, concept_id: Optional[str] = None) -> None: pass


class KnowledgeManager(IKnowledgeManager):
    """
    Façade coordinator implementation protecting domain callers from underlying storage engines.
    Manages lookups, transactions, and event-based cache invalidations.
    """
    def __init__(self, concept_store: IConceptStore, cache: IKnowledgeCache, event_bus: Optional[EventBus] = None):
        self.concept_store: IConceptStore = concept_store
        self.cache: IKnowledgeCache = cache
        self.event_bus: Optional[EventBus] = event_bus

        # Placeholder fields for future stores
        self.ontology_store = None
        self.fact_store = None
        self.rule_store = None
        self.skill_store = None
        self.episode_store = None
        self.reflection_store = None
        self.verification_store = None

        if self.event_bus:
            self._register_event_listeners()

    def _register_event_listeners(self) -> None:
        """Subscribes cache invalidation hooks to UKM mutation events."""
        def on_concept_mutated(context: CognitiveContext) -> None:
            concept = getattr(context.working_memory, "concept", None)
            if concept:
                self.invalidate_cache(concept.id)

        for event in ["ConceptCreated", "ConceptUpdated", "ConceptMerged", "ConceptSplit", "ConceptArchived", "ConceptDeprecated"]:
            self.event_bus.subscribe(event, on_concept_mutated)

    @translate_exceptions
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Fetches a concept, yielding cache hits where possible."""
        cached = self.cache.get_concept(concept_id)
        if cached:
            return cached
        concept = self.concept_store.get_concept(concept_id)
        if concept:
            self.cache.set_concept(concept_id, concept)
            self.cache.set_concept_by_name(concept.name, concept)
        return concept

    @translate_exceptions
    def get_concept_by_name(self, name: str) -> Optional[Concept]:
        cached = self.cache.get_concept_by_name(name)
        if cached:
            return cached
        # Try finding name from versions list or search
        versions = self.concept_store.list_versions(name)
        active = next((c for c in versions if c.status == "ACTIVE"), None)
        if active:
            self.cache.set_concept(active.id, active)
            self.cache.set_concept_by_name(name, active)
            return active
        return None

    @translate_exceptions
    def search(self, query: str, limit: int = 50) -> List[Concept]:
        cached = self.cache.get_search(query)
        if cached is not None:
            return cached[:limit]
        results = self.concept_store.search(query, limit)
        self.cache.set_search(query, results)
        return results

    @translate_exceptions
    def search_by_namespace(self, namespace: str) -> List[Concept]:
        cached = self.cache.get_namespace(namespace)
        if cached is not None:
            return cached
        results = self.concept_store.get_concepts_by_namespace(namespace)
        self.cache.set_namespace(namespace, results)
        return results

    @translate_exceptions
    def create_concept(self, concept: Concept, provenance: Optional[Dict[str, Any]] = None) -> str:
        # Business validations belong here or delegate to store
        if not concept.name:
            raise KnowledgeValidationError("Concept name cannot be empty.")
        # If active exists, raise conflict
        existing = self.get_concept_by_name(concept.name)
        if existing and existing.id != concept.id and existing.status == "ACTIVE":
            raise KnowledgeConflictError(f"Concept with name '{concept.name}' already active.")
            
        res_id = self.concept_store.create_concept(concept, provenance)
        self.invalidate_cache(concept.id)
        return res_id

    @translate_exceptions
    def update_concept(self, concept: Concept) -> None:
        self.concept_store.update_concept(concept)
        self.invalidate_cache(concept.id)

    @translate_exceptions
    def archive_concept(self, concept_id: str) -> None:
        self.concept_store.archive_concept(concept_id)
        self.invalidate_cache(concept_id)

    @translate_exceptions
    def merge_concepts(self, id_1: str, id_2: str, merged_concept: Concept) -> str:
        res_id = self.concept_store.merge_concepts(id_1, id_2, merged_concept)
        self.invalidate_cache(id_1)
        self.invalidate_cache(id_2)
        self.invalidate_cache(merged_concept.id)
        return res_id

    @translate_exceptions
    def split_concept(self, parent_id: str, split_1: Concept, split_2: Concept) -> Tuple[str, str]:
        s1, s2 = self.concept_store.split_concept(parent_id, split_1, split_2)
        self.invalidate_cache(parent_id)
        self.invalidate_cache(split_1.id)
        self.invalidate_cache(split_2.id)
        return s1, s2

    @translate_exceptions
    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None:
        self.concept_store.attach_metadata(concept_id, key, value)
        self.invalidate_cache(concept_id)

    @translate_exceptions
    def detach_metadata(self, concept_id: str, key: str) -> None:
        self.concept_store.detach_metadata(concept_id, key)
        self.invalidate_cache(concept_id)

    @translate_exceptions
    def exists(self, concept_id: str) -> bool:
        cached = self.cache.get_concept(concept_id)
        if cached:
            return True
        return self.concept_store.exists(concept_id)

    @translate_exceptions
    def preload(self, concepts: List[Concept]) -> None:
        """Bulk inserts concepts into persistence layers."""
        for concept in concepts:
            self.create_concept(concept)

    @translate_exceptions
    def warm_cache(self, concept_ids: List[str]) -> None:
        """Pre-populates looking registers into memory caches."""
        for cid in concept_ids:
            concept = self.get_concept(cid)
            if concept:
                self.cache.set_concept(cid, concept)

    def invalidate_cache(self, concept_id: Optional[str] = None) -> None:
        """Clears memory buffers."""
        if concept_id:
            self.cache.invalidate_concept(concept_id)
        else:
            self.cache.clear()
            logger.info("Universal KnowledgeManager cache flushed.")
