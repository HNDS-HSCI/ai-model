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


class EntityRole(str, Enum):
    """What kind of thing an EntityMention denotes, independent of surface form.

    Representational only — no stage in this codebase yet populates or reads
    ``role``/``numeric_value``/``is_known`` on EntityMention. It exists so a
    future Interpret/Ground stage has a typed place to record that a mention
    is a quantity or an unknown variable, instead of every stage discovering
    this by re-parsing the raw surface text.
    """
    CONCEPT = "CONCEPT"    # a domain/knowledge concept, resolved via the UKM (default)
    QUANTITY = "QUANTITY"  # a numeric value, known or unknown
    VARIABLE = "VARIABLE"  # a QUANTITY specifically being solved for (is_known=False)


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
    role: EntityRole = EntityRole.CONCEPT
    # numeric_value/is_known are only meaningful when role != CONCEPT. Neither
    # field is parsed, computed, or inferred here or anywhere else yet — they
    # are pure representation for a future Interpret/Ground stage to populate.
    numeric_value: Optional[float] = None
    is_known: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# The sanctioned, closed set of `relation_type` values denoting an arithmetic
# operation or equality between two QUANTITY/VARIABLE-role EntityMentions.
# relation_type itself remains a plain, unvalidated str (unchanged, matching
# every existing concept-relation value such as "COMPARISON"/"RELATIONSHIP")
# so no existing construction site or proposal is affected; this constant is
# documentation of the closed vocabulary, not an enforced allowlist.
OPERATION_RELATION_TYPES = frozenset({
    "OPERATION:ADD",
    "OPERATION:SUBTRACT",
    "OPERATION:MULTIPLY",
    "OPERATION:DIVIDE",
    "EQUALS",
})


@dataclass
class SemanticRelation:
    """Semantic relationship proposed between entity mentions prior to UKM validation.

    For an operation relation (relation_type in OPERATION_RELATION_TYPES),
    source_mention/target_mention remain positional, exactly as for every
    other relation_type: source_mention is the left/first operand and
    target_mention is the right/second operand, so e.g. "x - 10" and
    "10 - x" remain distinguishable by which mention is source vs. target.
    No arithmetic is performed or implied by this class.
    """
    source_mention: str
    # e.g. "COMPARISON", "RELATIONSHIP", "GENERALIZATION", "PURPOSE", or one
    # of OPERATION_RELATION_TYPES above ("OPERATION:ADD", ..., "EQUALS").
    relation_type: str
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
