import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from hsci.core.data_types import Concept, AxiomType
from hsci.core.storage import IStorageProvider, HSCIStorageError

logger = logging.getLogger("HSCI.Knowledge.ConceptRepository")

class ConceptRepository:
    """
    Persistence layer mapping Concept dataclass instances to transactional SQL updates.
    Acts as the boundary between logical objects and ukm physical relational tables.
    """
    def __init__(self, provider: IStorageProvider):
        self.provider: IStorageProvider = provider

    def _row_to_concept(self, row: Dict[str, Any]) -> Concept:
        """Helper to map a DB row dictionary to a type-hinted Concept dataclass."""
        concept_id = row["id"]
        
        # Load related list properties
        aliases = [
            r["alias"] for r in self.provider.execute_read(
                "SELECT alias FROM ukm_concept_aliases WHERE concept_id = ?;", (concept_id,)
            )
        ]
        learned_domains = [
            r["domain"] for r in self.provider.execute_read(
                "SELECT domain FROM ukm_concept_learned_domains WHERE concept_id = ?;", (concept_id,)
            )
        ]
        generalizes_to = [
            r["target_id"] for r in self.provider.execute_read(
                "SELECT target_id FROM ukm_concept_generalizes_to WHERE concept_id = ?;", (concept_id,)
            )
        ]
        required_entities = [
            r["entity"] for r in self.provider.execute_read(
                "SELECT entity FROM ukm_concept_required_entities WHERE concept_id = ?;", (concept_id,)
            )
        ]
        optional_entities = [
            r["entity"] for r in self.provider.execute_read(
                "SELECT entity FROM ukm_concept_optional_entities WHERE concept_id = ?;", (concept_id,)
            )
        ]

        return Concept(
            id=concept_id,
            name=row["name"],
            namespace=row["namespace"],
            version=row["version"],
            status=row["status"],
            aliases=aliases,
            axiom_type=AxiomType(row["axiom_type"]),
            abstract_rule=row["abstract_rule"] or "",
            z3_template=row["z3_template"] or "",
            domain=row["domain"],
            learned_from_domains=learned_domains,
            strength=row["strength"],
            proof_count=row["proof_count"],
            created_at=datetime.fromtimestamp(row["created_at"]),
            last_used=datetime.fromtimestamp(row["last_used"]),
            generalizes_to=generalizes_to,
            required_entities=required_entities,
            optional_entities=optional_entities,
            z3_verified=bool(row["z3_verified"])
        )

    def create_concept(self, concept: Concept) -> str:
        """Inserts a new concept record and related list attributes."""
        try:
            self.provider.execute_write(
                """
                INSERT INTO ukm_concepts (
                    id, name, namespace, version, axiom_type, abstract_rule,
                    z3_template, domain, status, created_at, last_used, strength, proof_count, z3_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    concept.id,
                    concept.name,
                    concept.namespace,
                    concept.version,
                    concept.axiom_type.value,
                    concept.abstract_rule,
                    concept.z3_template,
                    concept.domain,
                    concept.status,
                    concept.created_at.timestamp(),
                    concept.last_used.timestamp(),
                    concept.strength,
                    concept.proof_count,
                    1 if concept.z3_verified else 0
                )
            )
            # Insert related lists
            for alias in concept.aliases:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
                    (concept.id, alias)
                )
            for domain in concept.learned_from_domains:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_learned_domains (concept_id, domain) VALUES (?, ?);",
                    (concept.id, domain)
                )
            for target_id in concept.generalizes_to:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_generalizes_to (concept_id, target_id) VALUES (?, ?);",
                    (concept.id, target_id)
                )
            for entity in concept.required_entities:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_required_entities (concept_id, entity) VALUES (?, ?);",
                    (concept.id, entity)
                )
            for entity in concept.optional_entities:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_optional_entities (concept_id, entity) VALUES (?, ?);",
                    (concept.id, entity)
                )
            return concept.id
        except Exception as e:
            logger.error(f"Failed to create concept '{concept.name}': {e}")
            raise HSCIStorageError(f"Create concept failure: {e}")

    def update_concept(self, concept: Concept) -> None:
        """Updates concept metadata and refreshes related attribute lists."""
        try:
            self.provider.execute_write(
                """
                UPDATE ukm_concepts SET
                    name = ?, namespace = ?, version = ?, axiom_type = ?, abstract_rule = ?,
                    z3_template = ?, domain = ?, status = ?, created_at = ?, last_used = ?,
                    strength = ?, proof_count = ?, z3_verified = ?
                WHERE id = ?;
                """,
                (
                    concept.name,
                    concept.namespace,
                    concept.version,
                    concept.axiom_type.value,
                    concept.abstract_rule,
                    concept.z3_template,
                    concept.domain,
                    concept.status,
                    concept.created_at.timestamp(),
                    concept.last_used.timestamp(),
                    concept.strength,
                    concept.proof_count,
                    1 if concept.z3_verified else 0,
                    concept.id
                )
            )
            # Sync aliases
            self.provider.execute_write("DELETE FROM ukm_concept_aliases WHERE concept_id = ?;", (concept.id,))
            for alias in concept.aliases:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_aliases (concept_id, alias) VALUES (?, ?);",
                    (concept.id, alias)
                )
            # Sync learned domains
            self.provider.execute_write("DELETE FROM ukm_concept_learned_domains WHERE concept_id = ?;", (concept.id,))
            for domain in concept.learned_from_domains:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_learned_domains (concept_id, domain) VALUES (?, ?);",
                    (concept.id, domain)
                )
            # Sync generalizes_to
            self.provider.execute_write("DELETE FROM ukm_concept_generalizes_to WHERE concept_id = ?;", (concept.id,))
            for target_id in concept.generalizes_to:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_generalizes_to (concept_id, target_id) VALUES (?, ?);",
                    (concept.id, target_id)
                )
            # Sync required entities
            self.provider.execute_write("DELETE FROM ukm_concept_required_entities WHERE concept_id = ?;", (concept.id,))
            for entity in concept.required_entities:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_required_entities (concept_id, entity) VALUES (?, ?);",
                    (concept.id, entity)
                )
            # Sync optional entities
            self.provider.execute_write("DELETE FROM ukm_concept_optional_entities WHERE concept_id = ?;", (concept.id,))
            for entity in concept.optional_entities:
                self.provider.execute_write(
                    "INSERT INTO ukm_concept_optional_entities (concept_id, entity) VALUES (?, ?);",
                    (concept.id, entity)
                )
        except Exception as e:
            logger.error(f"Failed to update concept '{concept.name}': {e}")
            raise HSCIStorageError(f"Update concept failure: {e}")

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Loads a concept by its unique ID."""
        rows = self.provider.execute_read("SELECT * FROM ukm_concepts WHERE id = ?;", (concept_id,))
        if not rows:
            return None
        return self._row_to_concept(rows[0])

    def get_concept_by_name(self, name: str) -> Optional[Concept]:
        """Loads a concept by its unique name."""
        rows = self.provider.execute_read("SELECT * FROM ukm_concepts WHERE name = ? COLLATE NOCASE;", (name,))
        if not rows:
            return None
        return self._row_to_concept(rows[0])

    def resolve_alias(self, alias: str) -> List[Concept]:
        """Resolves concepts matching a given alias string."""
        rows = self.provider.execute_read(
            """
            SELECT DISTINCT c.* FROM ukm_concepts c
            JOIN ukm_concept_aliases a ON c.id = a.concept_id
            WHERE a.alias = ? COLLATE NOCASE;
            """,
            (alias,)
        )
        return [self._row_to_concept(r) for r in rows]

    def get_concepts_by_namespace(self, namespace: str) -> List[Concept]:
        """Loads concepts under a hierarchical namespace prefix."""
        # Namespace search using a LIKE prefix match
        rows = self.provider.execute_read(
            "SELECT * FROM ukm_concepts WHERE namespace = ? OR namespace LIKE ? ORDER BY version DESC;",
            (namespace, f"{namespace}.%")
        )
        return [self._row_to_concept(r) for r in rows]

    def exists(self, concept_id: str) -> bool:
        """Quick check verifying concept presence by ID."""
        rows = self.provider.execute_read("SELECT 1 FROM ukm_concepts WHERE id = ? LIMIT 1;", (concept_id,))
        return len(rows) > 0

    def search(self, query: str, limit: int = 50) -> List[Concept]:
        """Searches concepts matching names or rules via SQL LIKE."""
        rows = self.provider.execute_read(
            """
            SELECT DISTINCT c.* FROM ukm_concepts c
            LEFT JOIN ukm_concept_aliases a ON c.id = a.concept_id
            WHERE c.name LIKE ? OR c.abstract_rule LIKE ? OR a.alias LIKE ?
            LIMIT ?;
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )
        return [self._row_to_concept(r) for r in rows]

    def search_by_metadata(self, key: str, value: Any) -> List[Concept]:
        """Finds concepts with specific dynamic metadata pairs."""
        rows = self.provider.execute_read(
            """
            SELECT c.* FROM ukm_concepts c
            JOIN ukm_concept_metadata m ON c.id = m.concept_id
            WHERE m.key = ? AND m.value = ?;
            """,
            (key, str(value))
        )
        return [self._row_to_concept(r) for r in rows]

    def attach_metadata(self, concept_id: str, key: str, value: Any) -> None:
        """Saves a dynamic metadata attribute linked to a concept."""
        self.provider.execute_write(
            """
            INSERT OR REPLACE INTO ukm_concept_metadata (concept_id, key, value)
            VALUES (?, ?, ?);
            """,
            (concept_id, key, str(value))
        )

    def detach_metadata(self, concept_id: str, key: str) -> None:
        """Removes a metadata key for a concept."""
        self.provider.execute_write(
            "DELETE FROM ukm_concept_metadata WHERE concept_id = ? AND key = ?;",
            (concept_id, key)
        )

    def list_versions(self, name: str) -> List[Concept]:
        """Lists all version permutations of a concept name."""
        rows = self.provider.execute_read(
            "SELECT * FROM ukm_concepts WHERE name = ? COLLATE NOCASE ORDER BY version ASC;",
            (name,)
        )
        return [self._row_to_concept(r) for r in rows]

    # Provenance Operations
    def add_provenance(self, provenance_id: str, concept_id: str, source_type: str, source_id: str,
                       timestamp: float, acquisition_method: str, confidence: float, notes: Optional[str]) -> None:
        """Logs ingestion tracking details."""
        self.provider.execute_write(
            """
            INSERT INTO ukm_concept_provenance (
                provenance_id, concept_id, source_type, source_id, timestamp, acquisition_method, confidence, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (provenance_id, concept_id, source_type, source_id, timestamp, acquisition_method, confidence, notes)
        )

    def get_provenance(self, concept_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit provenance markers."""
        rows = self.provider.execute_read(
            "SELECT * FROM ukm_concept_provenance WHERE concept_id = ? ORDER BY timestamp DESC;",
            (concept_id,)
        )
        return [dict(row) for row in rows]
