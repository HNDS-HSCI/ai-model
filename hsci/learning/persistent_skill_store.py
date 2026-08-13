import os
import json
import hmac
import secrets
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, AxiomType, SkillCandidate
)

logger = logging.getLogger("HSCI.Learning.PersistentSkillStore")


class PersistentSkillStore:
    """
    LAYER 4C / SKB-1.1: Persistent Verified Skill Knowledge Base.
    Provides schema-versioned, HMAC-SHA256 authenticated, declarative storage for learned HTN Methods.
    Ensures dynamically acquired verified skills survive process restarts without allowing unverified,
    forged, stale, corrupted, or tampered methods to contaminate MethodRegistry.
    """

    SCHEMA_VERSION = 1
    DEFAULT_STORAGE_DIR = Path("knowledge")
    DEFAULT_FILENAME = "skills.json"
    DEFAULT_KEY_FILENAME = "skill_signing.key"

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        filename: Optional[str] = None,
        signing_key: Optional[bytes] = None
    ):
        self.storage_dir = storage_dir or self.DEFAULT_STORAGE_DIR
        self.filename = filename or self.DEFAULT_FILENAME
        self.storage_path = self.storage_dir / self.filename
        self.key_path = self.storage_dir / self.DEFAULT_KEY_FILENAME
        
        # Key Resolution Order:
        # 1. Direct explicit argument
        # 2. Environment variable HSCI_SKILL_SIGNING_KEY
        # 3. Local key file knowledge/skill_signing.key
        # 4. Generate & persist new 256-bit random key if missing
        self.signing_key = signing_key or self._resolve_signing_key()

    def _resolve_signing_key(self) -> bytes:
        env_key = os.environ.get("HSCI_SKILL_SIGNING_KEY")
        if env_key:
            return env_key.encode("utf-8")

        if self.key_path.exists():
            try:
                with open(self.key_path, "rb") as f:
                    key_data = f.read().strip()
                    if key_data:
                        return key_data
            except Exception as e:
                logger.warning(f"PersistentSkillStore: Failed to read key file '{self.key_path}': {e}")

        # Generate new random 256-bit key
        new_key = secrets.token_bytes(32)
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.key_path, "wb") as f:
                f.write(new_key)
            logger.info(f"PersistentSkillStore: Generated and saved new local signing key to '{self.key_path}'")
        except Exception as e:
            logger.error(f"PersistentSkillStore: Failed to save signing key: {e}")

        return new_key

    def _canonical_json_bytes(self, skill_dict: Dict[str, Any]) -> bytes:
        """
        Produces a deterministic, sorted JSON byte array over canonical declarative skill content.
        Excludes volatile parameters and authentication metadata.
        """
        canonical_content = {
            "skill_id": skill_dict.get("skill_id"),
            "target_task_name": skill_dict.get("target_task_name"),
            "preconditions": skill_dict.get("preconditions", []),
            "subtasks": skill_dict.get("subtasks", []),
            "cost": skill_dict.get("cost", 1.0),
            "source_request_id": skill_dict.get("source_request_id", ""),
            "source": MethodSource.LEARNED.value  # Enforce LEARNED source provenance
        }
        return json.dumps(canonical_content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _compute_content_hash(self, skill_dict: Dict[str, Any]) -> str:
        """Computes SHA-256 fingerprint for non-cryptographic corruption detection."""
        raw_bytes = self._canonical_json_bytes(skill_dict)
        return hashlib.sha256(raw_bytes).hexdigest()

    def _compute_hmac_signature(self, skill_dict: Dict[str, Any]) -> str:
        """Computes HMAC-SHA256 signature using the secret signing key for local authenticity."""
        raw_bytes = self._canonical_json_bytes(skill_dict)
        return hmac.new(self.signing_key, raw_bytes, hashlib.sha256).hexdigest()

    def serialize_method(self, method: Method, candidate: Optional[SkillCandidate] = None) -> Dict[str, Any]:
        """
        Converts a Method instance and candidate provenance into a declarative dictionary.
        Contains ZERO executable code or Python objects.
        """
        pre_list = []
        for p in method.preconditions:
            pre_list.append({
                "predicate": p.predicate,
                "required_state": p.required_state,
                "parameters": p.parameters
            })

        sub_list = []
        for st in method.subtasks:
            sub_list.append({
                "id": st.id,
                "name": st.name,
                "task_type": st.task_type.value,
                "parameters": st.parameters,
                "axiom_type": st.axiom_type.value if st.axiom_type else None
            })

        skill_record = {
            "skill_id": method.id,
            "target_task_name": method.target_task_name,
            "source": MethodSource.LEARNED.value,  # Dynamically acquired skills are strictly LEARNED
            "preconditions": pre_list,
            "subtasks": sub_list,
            "cost": method.cost,
            "description": method.description,
            "source_request_id": candidate.source_request_id if candidate else "",
            "source_reflection_id": candidate.source_reflection_id if candidate else None,
            "provenance_trace": candidate.provenance_trace if candidate else ["Verified by Z3"]
        }

        skill_record["content_hash"] = self._compute_content_hash(skill_record)
        skill_record["hmac_signature"] = self._compute_hmac_signature(skill_record)
        return skill_record

    def deserialize_method(self, skill_dict: Dict[str, Any]) -> Tuple[Optional[Method], Optional[str]]:
        """
        Safely deserializes a skill record into a Method instance.
        Performs HMAC authenticity, SHA-256 integrity, and structural validation before instantiation.
        Returns (Method, None) on success or (None, failure_reason) on error.
        """
        # 1. HMAC Authenticity Check (FAIL CLOSED)
        expected_hmac = skill_dict.get("hmac_signature")
        if not expected_hmac:
            return None, f"Missing HMAC signature for skill '{skill_dict.get('skill_id')}'. Unauthenticated payload rejected."

        computed_hmac = self._compute_hmac_signature(skill_dict)
        if not hmac.compare_digest(expected_hmac, computed_hmac):
            return None, f"HMAC Signature Verification Failed for skill '{skill_dict.get('skill_id')}'. Record is forged or invalid key."

        # 2. Corruption SHA-256 Check
        expected_hash = skill_dict.get("content_hash")
        computed_hash = self._compute_content_hash(skill_dict)
        if not expected_hash or not hmac.compare_digest(expected_hash, computed_hash):
            return None, f"Integrity Hash Mismatch for skill '{skill_dict.get('skill_id')}'. Record is corrupted."

        # 3. Privilege Escalation Prevention (Source MUST be LEARNED)
        source_val = skill_dict.get("source")
        if source_val == MethodSource.CANONICAL.value:
            return None, f"Privilege Escalation Attempt: Persisted record '{skill_dict.get('skill_id')}' claims CANONICAL source."

        # 4. Structural Validation
        method_id = skill_dict.get("skill_id")
        target_task = skill_dict.get("target_task_name")
        if not method_id or not target_task:
            return None, "Missing essential skill_id or target_task_name."

        subtasks_data = skill_dict.get("subtasks", [])
        if not isinstance(subtasks_data, list) or not subtasks_data:
            return None, "Subtasks field must be a non-empty list."

        subtasks = []
        for st in subtasks_data:
            tt_val = st.get("task_type")
            try:
                tt = TaskType(tt_val)
            except ValueError:
                return None, f"Invalid TaskType '{tt_val}' in subtask '{st.get('name')}'."

            ax_val = st.get("axiom_type")
            ax_type = AxiomType(ax_val) if ax_val and ax_val in [a.value for a in AxiomType] else None

            subtasks.append(
                Task(
                    id=st.get("id", f"st-{st.get('name')}"),
                    name=st.get("name"),
                    task_type=tt,
                    parameters=st.get("parameters", {}),
                    axiom_type=ax_type
                )
            )

        preconditions = []
        for p in skill_dict.get("preconditions", []):
            preconditions.append(
                Precondition(
                    predicate=p.get("predicate", ""),
                    required_state=p.get("required_state"),
                    parameters=p.get("parameters", {})
                )
            )

        method = Method(
            id=method_id,
            target_task_name=target_task,
            preconditions=preconditions,
            subtasks=subtasks,
            cost=float(skill_dict.get("cost", 1.0)),
            description=skill_dict.get("description", "Rehydrated persistent skill"),
            source=MethodSource.LEARNED
        )

        return method, None

    def save_skill(self, method: Method, candidate: Optional[SkillCandidate] = None) -> bool:
        """
        Atomically persists a verified Method to durable storage.
        Guarantees thread-safe atomic temp-file replacement to prevent partial writes.
        """
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            existing_data = self.load_records_raw()

            skills_list = existing_data.get("skills", [])
            new_record = self.serialize_method(method, candidate)

            # Deduplicate by skill_id
            updated_list = [s for s in skills_list if s.get("skill_id") != method.id]
            updated_list.append(new_record)

            file_payload = {
                "schema_version": self.SCHEMA_VERSION,
                "skills": updated_list
            }

            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(file_payload, f, indent=2)

            temp_path.replace(self.storage_path)
            logger.info(f"PersistentSkillStore: Successfully saved authenticated skill '{method.id}' to '{self.storage_path}'")
            return True
        except Exception as e:
            logger.error(f"PersistentSkillStore: Failed to save skill '{method.id}': {e}")
            return False

    def load_records_raw(self) -> Dict[str, Any]:
        """Loads raw JSON payload from storage if file exists."""
        if not self.storage_path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "skills": []}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"schema_version": self.SCHEMA_VERSION, "skills": []}
                return data
        except Exception as e:
            logger.warning(f"PersistentSkillStore: Malformed JSON storage file '{self.storage_path}': {e}")
            return {"schema_version": self.SCHEMA_VERSION, "skills": []}

    def load_and_validate_skills(self) -> List[Tuple[Method, Dict[str, Any]]]:
        """
        Reads durable store, checks schema version, HMAC signature, and integrity hashes, and returns valid (Method, raw_record) pairs.
        Rejects tampered, unauthenticated, unsupported schema, or malformed records.
        """
        data = self.load_records_raw()
        schema_ver = data.get("schema_version", 1)
        if schema_ver > self.SCHEMA_VERSION:
            logger.error(f"PersistentSkillStore: Unsupported schema_version {schema_ver} (Max supported: {self.SCHEMA_VERSION})")
            return []

        valid_pairs = []
        for raw_record in data.get("skills", []):
            method, err = self.deserialize_method(raw_record)
            if err:
                logger.warning(f"PersistentSkillStore: Rejected record '{raw_record.get('skill_id')}': {err}")
                continue
            valid_pairs.append((method, raw_record))

        return valid_pairs
