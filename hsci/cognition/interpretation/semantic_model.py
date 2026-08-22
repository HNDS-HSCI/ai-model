"""Semantic Intermediate Representation for HSCI VS-6.

Decouples linguistic surface forms from cognitive request structures.
Represents communicative goals, entity mentions with spans, semantic relations,
constraints, output requirements, context references, negation, and modality.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid

from hsci.cognition.interpretation.models import (
    InterpretationAssumption,
    Evidence,
)


class CommunicativeGoal(str, Enum):
    """High-level semantic request goal independent of surface syntax."""
    EXPLAIN = "EXPLAIN"
    COMPARE = "COMPARE"
    RELATE = "RELATE"
    SOLVE_MATH = "SOLVE_MATH"
    GENERAL = "GENERAL"
    IDENTIFY = "IDENTIFY"
    VERIFY = "VERIFY"
    SUMMARIZE = "SUMMARIZE"
    ANALYZE = "ANALYZE"
    CLARIFY = "CLARIFY"
    UNKNOWN = "UNKNOWN"


@dataclass
class EntityMention:
    """Semantic mention of a potential domain entity within the input text."""
    surface_form: str
    normalized_form: str
    candidate_identity: Optional[str] = None
    span_start: int = 0
    span_end: int = 0
    confidence: float = 1.0
    resolution_state: str = "UNRESOLVED"  # UNRESOLVED, RESOLVED, AMBIGUOUS, UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticRelation:
    """Semantic relationship proposed between entity mentions prior to UKM validation."""
    source_mention: str
    relation_type: str  # e.g., "COMPARISON", "RELATIONSHIP", "GENERALIZATION", "PURPOSE"
    target_mention: str
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticConstraint:
    """Explicit modifier or scope constraint applied to the cognitive request."""
    constraint_type: str  # e.g., "EXCLUSION", "RESTRICTION", "CONDITION", "SCOPE"
    operator: str  # e.g., "ONLY", "WITHOUT", "USING", "BEFORE", "AFTER", "UNDER", "NOT"
    value: str
    polarity: bool = True  # True = positive, False = negated

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutputRequirement:
    """Desired format, structure, or depth of the synthesized answer."""
    output_type: str = "EXPLANATION"  # DEFINITION, COMPARISON, PROOF_TRACE, EXPLANATION, VERIFICATION
    depth: int = 1  # 0 = brief, 1 = standard, 2 = deep
    style: str = "Standard"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextReference:
    """Deictic, anaphoric, or referential pronoun requiring discourse context."""
    marker: str  # e.g., "it", "this", "that", "the previous concept"
    reference_type: str = "PRONOUN"  # PRONOUN, DEFINITE_NP, ANAPHORA
    antecedent: Optional[str] = None
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticRequest:
    """Grounded semantic intermediate representation of user intent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: CommunicativeGoal = CommunicativeGoal.EXPLAIN
    entity_mentions: List[EntityMention] = field(default_factory=list)
    relations: List[SemanticRelation] = field(default_factory=list)
    constraints: List[SemanticConstraint] = field(default_factory=list)
    output_requirements: List[OutputRequirement] = field(default_factory=list)
    context_references: List[ContextReference] = field(default_factory=list)
    is_negated: bool = False
    modality: str = "ASSERTION"  # ASSERTION, HYPOTHETICAL, DEONTIC, EPISTEMIC
    confidence: float = 0.5
    source_method: str = "semantic_parser"
    assumptions: List[InterpretationAssumption] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal.value,
            "entity_mentions": [em.to_dict() for em in self.entity_mentions],
            "relations": [r.to_dict() for r in self.relations],
            "constraints": [c.to_dict() for c in self.constraints],
            "output_requirements": [o.to_dict() for o in self.output_requirements],
            "context_references": [cr.to_dict() for cr in self.context_references],
            "is_negated": self.is_negated,
            "modality": self.modality,
            "confidence": self.confidence,
            "source_method": self.source_method,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "evidence": [e.to_dict() for e in self.evidence],
        }
