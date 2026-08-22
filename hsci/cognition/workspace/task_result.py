"""Task Result Model for HSCI VS-7.

Defines strongly-typed, provenance-preserving intermediate results produced by cognitive tasks.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Dict, Any, List, Optional

from hsci.cognition.interpretation.models import Evidence


class TaskResultType(str, Enum):
    """Enumeration of typed cognitive task results."""
    DEFINITION = "DEFINITION"
    COMPARISON = "COMPARISON"
    RELATIONSHIP_PROOF = "RELATIONSHIP_PROOF"
    REASONING_CONCLUSION = "REASONING_CONCLUSION"
    GROUNDED_ENTITY_SET = "GROUNDED_ENTITY_SET"
    REFUSAL = "REFUSAL"
    DIAGNOSTIC = "DIAGNOSTIC"
    COMPOSITE = "COMPOSITE"


@dataclass
class TaskResult:
    """Strongly typed, provenance-preserving result of a CognitiveTask execution."""
    task_id: str
    result_type: TaskResultType
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    evidence: List[Evidence] = field(default_factory=list)
    provenance: str = "TASK_EXECUTION"  # CANONICAL_KNOWLEDGE, STORED_RELATIONSHIP, DERIVED_CONCLUSION, TASK_EXECUTION
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "result_type": self.result_type.value,
            "payload": self.payload,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "provenance": self.provenance,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "duration_ms": self.duration_ms,
        }
