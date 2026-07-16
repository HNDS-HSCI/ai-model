import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import IStorageProvider, HSCIStorageError
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.concept_repository import ConceptRepository

logger = logging.getLogger("HSCI.Knowledge.ConceptStore")

class IConceptStore(ABC):
    """
    Abstract interface defining the complete lifecycle operations for concepts
    in the Universal Knowledge Model.
    """
    @abstractmethod
    def create_concept(self, concept: Concept, provenance: Optional[Dict[str, Any]] = None) -> str: pass
    @abstractmethod
    def get_concept(self, concept_id: str) -> Optional[Concept]: pass
    @abstractmethod
    def update_concept(self, concept: Concept) -> None: pass
    @abstractmethod
    def exists(self, concept_id: str) -> bool: pass
    @abstractmethod
    def list_versions(self, name: str) -> List[Concept]: pass
    @abstractmethod
    def restore_version(self, concept_id: str, version: int) -> Concept: pass
    @abstractmethod
    def get_history(self, concept_id: str) -> List[Dict[str, Any]]: pass
    @abstractmethod
    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None: pass
    @abstractmethod
    def detach_metadata(self, concept_id: str, key: str) -> None: pass
    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[Concept]: pass
    @abstractmethod
    def get_concepts_by_namespace(self, namespace: str) -> List[Concept]: pass
    @abstractmethod
    def search_by_metadata(self, key: str, value: Any) -> List[Concept]: pass
    @abstractmethod
    def deprecate_concept(self, concept_id: str, superseded_by_id: str) -> None: pass
    @abstractmethod
    def archive_concept(self, concept_id: str) -> None: pass
    @abstractmethod
    def merge_concepts(self, id_1: str, id_2: str, merged_concept: Concept) -> str: pass
    @abstractmethod
    def split_concept(self, parent_id: str, split_1: Concept, split_2: Concept) -> Tuple[str, str]: pass
    @abstractmethod
    def validate_concept(self, concept: Concept) -> bool: pass


class ConceptStore(IConceptStore):
    """
    Logical business layer coordinating concept lifecycle workflows, versioning,
    nested savepoint transactions, and dynamic event bus publishers.
    """
    def __init__(self, repository: ConceptRepository, event_bus: Optional[EventBus] = None):
        self.repository: ConceptRepository = repository
        self.event_bus: Optional[EventBus] = event_bus

    def _emit(self, event_name: str, concept: Concept) -> None:
        """Helper to dynamically emit store events on the event bus."""
        if self.event_bus:
            try:
                ctx = CognitiveContext(
                    request_id=f"evt-{int(time.time())}-{uuid.uuid4().hex[:6]}",
                    session_id="system",
                    stimulus=f"event:{event_name}"
                )
                ctx.working_memory.concept = concept
                self.event_bus.emit(event_name, ctx)
            except Exception as e:
                logger.error(f"Failed to emit event '{event_name}': {e}")

    def validate_concept(self, concept: Concept) -> bool:
        """Validates basic concept fields, formatting, and schema correctness."""
        if not concept.id or not concept.name:
            logger.warning(f"Validation failed: Concept name or ID is empty.")
            return False
        if concept.strength < 0.0 or concept.strength > 1.0:
            logger.warning(f"Validation failed: Concept strength '{concept.strength}' is out of bounds [0, 1].")
            return False
        return True

    def create_concept(self, concept: Concept, provenance: Optional[Dict[str, Any]] = None) -> str:
        """Coordinates structural validation, repository insertion, provenance logging, and events."""
        if not self.validate_concept(concept):
            raise HSCIStorageError("Concept validation failure.")
            
        # Write concept via repository
        self.repository.create_concept(concept)
        
        # Provenance logging
        prov_id = str(uuid.uuid4())
        source_type = provenance.get("source_type", "UNKNOWN") if provenance else "UNKNOWN"
        source_id = provenance.get("source_id", "UNKNOWN") if provenance else "UNKNOWN"
        acq_method = provenance.get("acquisition_method", "MANUAL") if provenance else "MANUAL"
        confidence = provenance.get("confidence", 1.0) if provenance else 1.0
        notes = provenance.get("notes", "") if provenance else ""
        
        self.repository.add_provenance(
            prov_id,
            concept.id,
            source_type,
            source_id,
            time.time(),
            acq_method,
            confidence,
            notes
        )
        
        self._emit("ConceptCreated", concept)
        return concept.id

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        return self.repository.get_concept(concept_id)

    def update_concept(self, concept: Concept) -> None:
        if not self.validate_concept(concept):
            raise HSCIStorageError("Concept validation failure.")
        self.repository.update_concept(concept)
        self._emit("ConceptUpdated", concept)

    def exists(self, concept_id: str) -> bool:
        return self.repository.exists(concept_id)

    def list_versions(self, name: str) -> List[Concept]:
        return self.repository.list_versions(name)

    def restore_version(self, concept_id: str, version: int) -> Concept:
        """Restores an inactive concept back to a specific target version status."""
        concept = self.repository.get_concept(concept_id)
        if not concept:
            raise HSCIStorageError(f"Concept '{concept_id}' not found.")
            
        # Find matches for target version
        versions = self.repository.list_versions(concept.name)
        target = next((c for c in versions if c.version == version), None)
        if not target:
            raise HSCIStorageError(f"Concept version {version} not found.")
            
        # Promote version
        concept.status = "ACTIVE"
        concept.version = max(c.version for c in versions) + 1
        concept.abstract_rule = target.abstract_rule
        concept.z3_template = target.z3_template
        concept.strength = target.strength
        
        self.repository.update_concept(concept)
        self._emit("ConceptUpdated", concept)
        return concept

    def get_history(self, concept_id: str) -> List[Dict[str, Any]]:
        return self.repository.get_provenance(concept_id)

    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None:
        if not self.exists(concept_id):
            raise HSCIStorageError(f"Concept '{concept_id}' not found.")
        self.repository.attach_metadata(concept_id, key, value)

    def detach_metadata(self, concept_id: str, key: str) -> None:
        if not self.exists(concept_id):
            raise HSCIStorageError(f"Concept '{concept_id}' not found.")
        self.repository.detach_metadata(concept_id, key)

    def search(self, query: str, limit: int = 50) -> List[Concept]:
        return self.repository.search(query, limit)

    def get_concepts_by_namespace(self, namespace: str) -> List[Concept]:
        return self.repository.get_concepts_by_namespace(namespace)

    def search_by_metadata(self, key: str, value: Any) -> List[Concept]:
        return self.repository.search_by_metadata(key, value)

    def archive_concept(self, concept_id: str) -> None:
        concept = self.repository.get_concept(concept_id)
        if not concept:
            raise HSCIStorageError(f"Concept '{concept_id}' not found.")
        concept.status = "ARCHIVED"
        self.repository.update_concept(concept)
        self._emit("ConceptArchived", concept)

    def deprecate_concept(self, concept_id: str, superseded_by_id: str) -> None:
        concept = self.repository.get_concept(concept_id)
        if not concept:
            raise HSCIStorageError(f"Concept '{concept_id}' not found.")
        concept.status = "DEPRECATED"
        if superseded_by_id not in concept.generalizes_to:
            concept.generalizes_to.append(superseded_by_id)
        self.repository.update_concept(concept)
        self._emit("ConceptDeprecated", concept)

    def merge_concepts(self, id_1: str, id_2: str, merged_concept: Concept) -> str:
        """Executes nested transactional merge operations under SAVEPOINT scopes."""
        c1 = self.repository.get_concept(id_1)
        c2 = self.repository.get_concept(id_2)
        if not c1 or not c2:
            raise HSCIStorageError("Merge sources not found.")

        sp_name = f"merge_{id_1[:6]}_{id_2[:6]}"
        self.repository.provider.create_savepoint(sp_name)
        try:
            # Deprecate original concepts
            self.deprecate_concept(id_1, merged_concept.id)
            self.deprecate_concept(id_2, merged_concept.id)
            
            # Create merged concept
            merged_concept.status = "ACTIVE"
            self.create_concept(merged_concept, {
                "source_type": "CONCEPT_MERGE",
                "source_id": f"{id_1},{id_2}",
                "acquisition_method": "REFLECTION",
                "notes": f"Merged from {id_1} and {id_2}"
            })
            
            self.repository.provider.release_savepoint(sp_name)
            self._emit("ConceptMerged", merged_concept)
            return merged_concept.id
        except Exception as e:
            self.repository.provider.rollback_savepoint(sp_name)
            self.repository.provider.release_savepoint(sp_name)
            logger.error(f"Merge transaction failed, state rolled back: {e}")
            raise HSCIStorageError(f"Merge transaction failure: {e}")

    def split_concept(self, parent_id: str, split_1: Concept, split_2: Concept) -> Tuple[str, str]:
        """Executes nested transactional split operations under SAVEPOINT scopes."""
        parent = self.repository.get_concept(parent_id)
        if not parent:
            raise HSCIStorageError("Split parent concept not found.")

        sp_name = f"split_{parent_id[:8]}"
        self.repository.provider.create_savepoint(sp_name)
        try:
            # Deprecate/Weaken parent
            parent.status = "DEPRECATED"
            self.repository.update_concept(parent)
            
            # Create splits
            self.create_concept(split_1, {
                "source_type": "CONCEPT_SPLIT",
                "source_id": parent_id,
                "acquisition_method": "REFLECTION",
                "notes": f"Split 1 from parent {parent_id}"
            })
            self.create_concept(split_2, {
                "source_type": "CONCEPT_SPLIT",
                "source_id": parent_id,
                "acquisition_method": "REFLECTION",
                "notes": f"Split 2 from parent {parent_id}"
            })
            
            self.repository.provider.release_savepoint(sp_name)
            self._emit("ConceptSplit", parent)
            return split_1.id, split_2.id
        except Exception as e:
            self.repository.provider.rollback_savepoint(sp_name)
            self.repository.provider.release_savepoint(sp_name)
            logger.error(f"Split transaction failed, parent state restored: {e}")
            raise HSCIStorageError(f"Split transaction failure: {e}")
