"""HSCI VS-4 Cognitive Interpretation & Task Derivation Data Models.

Defines strongly-typed, immutable or structured representations for:
- Raw human language input with preservation of original text
- Candidate linguistic hypotheses and semantic frames
- UKM Grounding statuses and grounded entities
- Cognitive situations capturing grounded understanding, ambiguity, and evidence
- Executable cognitive tasks derived from grounded situations
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class GroundingStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class SituationStatus(str, Enum):
    GROUNDED = "GROUNDED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED_ENTITIES = "UNRESOLVED_ENTITIES"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    UNSUPPORTED_INTERPRETATION = "UNSUPPORTED_INTERPRETATION"


class TaskAction(str, Enum):
    EXPLAIN_CONCEPT = "EXPLAIN_CONCEPT"
    COMPARE_CONCEPTS = "COMPARE_CONCEPTS"
    DERIVE_RELATIONSHIP = "DERIVE_RELATIONSHIP"
    SOLVE_MATHEMATICS = "SOLVE_MATHEMATICS"
    ANSWER_GENERAL = "ANSWER_GENERAL"
    RETRIEVE_KNOWLEDGE = "RETRIEVE_KNOWLEDGE"
    REPORT_UNKNOWN = "REPORT_UNKNOWN"
    REPORT_AMBIGUITY = "REPORT_AMBIGUITY"
    REPORT_INSUFFICIENT_CONTEXT = "REPORT_INSUFFICIENT_CONTEXT"


@dataclass(frozen=True)
class RawInput:
    """Represents the unmodified user input and its normalized form."""
    original_text: str
    normalized_text: str
    conversation_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(cls, text: str, context: Optional[Dict[str, Any]] = None) -> "RawInput":
        import re
        norm = (text or "").lower().strip()
        norm = re.sub(r"[^\w\s\.]", " ", norm)
        norm = re.sub(r"\s+", " ", norm).strip()
        return cls(
            original_text=text or "",
            normalized_text=norm,
            conversation_context=context or {},
            metadata={},
        )


@dataclass
class Evidence:
    """Provenance recording why a candidate interpretation component was proposed."""
    evidence_type: str  # e.g. "lexical", "syntactic_frame", "alias_match", "llm_proposal"
    source: str
    description: str
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterpretationAssumption:
    """Explicitly records an ungrounded or discourse assumption made by an interpreter."""
    statement: str
    rationale: str
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateInterpretation:
    """A linguistic/semantic hypothesis about the user's intent and targets."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposed_intent: str = "ExplainConcept"  # e.g. "ExplainConcept", "CompareConcepts", "FindRelationship"
    candidate_entity_mentions: List[str] = field(default_factory=list)
    proposed_relationships: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[InterpretationAssumption] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.50
    source_method: str = "structural_analysis"  # e.g. "structural_analysis", "llm_proposal"
    requires_context: bool = False
    semantic_request: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposed_intent": self.proposed_intent,
            "candidate_entity_mentions": self.candidate_entity_mentions,
            "proposed_relationships": self.proposed_relationships,
            "constraints": self.constraints,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "source_method": self.source_method,
            "requires_context": self.requires_context,
            "semantic_request": self.semantic_request.to_dict() if hasattr(self.semantic_request, "to_dict") else self.semantic_request,
        }


@dataclass
class InterpretationSet:
    """Collection of candidate interpretations generated from RawInput."""
    raw_input: RawInput
    candidates: List[CandidateInterpretation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_input": {
                "original_text": self.raw_input.original_text,
                "normalized_text": self.raw_input.normalized_text,
            },
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass
class GroundedEntity:
    """The result of grounding a single candidate entity mention against the UKM."""
    mention: str
    status: GroundingStatus
    concept_id: Optional[str] = None
    canonical_name: Optional[str] = None
    candidate_concept_names: List[str] = field(default_factory=list)
    candidate_concept_ids: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention": self.mention,
            "status": self.status.value,
            "concept_id": self.concept_id,
            "canonical_name": self.canonical_name,
            "candidate_concept_names": self.candidate_concept_names,
            "candidate_concept_ids": self.candidate_concept_ids,
            "provenance": self.provenance,
        }


@dataclass
class CognitiveSituation:
    """The accepted, grounded intermediate representation consumed downstream."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_input: RawInput = field(default_factory=lambda: RawInput("", ""))
    accepted_interpretation: Optional[CandidateInterpretation] = None
    grounded_entities: List[GroundedEntity] = field(default_factory=list)
    intent: str = "ExplainConcept"
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[InterpretationAssumption] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    interpretation_confidence: float = 0.0
    grounding_confidence: float = 0.0
    ambiguities: List[str] = field(default_factory=list)
    unresolved_entities: List[str] = field(default_factory=list)
    required_knowledge: List[str] = field(default_factory=list)
    status: SituationStatus = SituationStatus.GROUNDED
    semantic_request: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw_input": {
                "original_text": self.raw_input.original_text,
                "normalized_text": self.raw_input.normalized_text,
            },
            "intent": self.intent,
            "status": self.status.value,
            "interpretation_confidence": self.interpretation_confidence,
            "grounding_confidence": self.grounding_confidence,
            "grounded_entities": [ge.to_dict() for ge in self.grounded_entities],
            "ambiguities": self.ambiguities,
            "unresolved_entities": self.unresolved_entities,
            "required_knowledge": self.required_knowledge,
            "evidence": [e.to_dict() for e in self.evidence],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "semantic_request": self.semantic_request.to_dict() if hasattr(self.semantic_request, "to_dict") else self.semantic_request,
        }


@dataclass
class CognitiveTask:
    """Structured, executable cognitive task derived from a CognitiveSituation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: TaskAction = TaskAction.EXPLAIN_CONCEPT
    primary_target: Optional[str] = None  # Canonical concept name or mention
    secondary_targets: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    situation_id: Optional[str] = None
    subtasks: List["CognitiveTask"] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: str = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action.value,
            "primary_target": self.primary_target,
            "secondary_targets": self.secondary_targets,
            "parameters": self.parameters,
            "situation_id": self.situation_id,
            "status": self.status,
            "dependencies": self.dependencies,
            "subtasks": [st.to_dict() for st in self.subtasks],
        }
