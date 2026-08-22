"""Execution Result Model for HSCI VS-5 Cognitive Task Execution.

Captures structured operational metadata describing which task executed, which concepts
were retrieved, what conclusions were derived, and what evidence supports the final answer.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import uuid

from hsci.cognition.interpretation.models import TaskAction


@dataclass
class CognitiveExecutionResult:
    """Structured audit trail of a cognitive task execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    task_action: TaskAction = TaskAction.EXPLAIN_CONCEPT
    situation_id: Optional[str] = None
    grounded_concepts: List[str] = field(default_factory=list)
    retrieved_definitions: Dict[str, str] = field(default_factory=dict)
    derived_conclusions: List[Dict[str, Any]] = field(default_factory=list)
    stored_relationships: List[Dict[str, Any]] = field(default_factory=list)
    refusal_reason: Optional[str] = None
    confidence_score: float = 0.0
    confidence_description: str = "Uncalibrated"
    execution_time_ms: float = 0.0
    is_success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_action": self.task_action.value,
            "situation_id": self.situation_id,
            "grounded_concepts": self.grounded_concepts,
            "retrieved_definitions": self.retrieved_definitions,
            "derived_conclusions": self.derived_conclusions,
            "stored_relationships": self.stored_relationships,
            "refusal_reason": self.refusal_reason,
            "confidence_score": self.confidence_score,
            "confidence_description": self.confidence_description,
            "execution_time_ms": self.execution_time_ms,
            "is_success": self.is_success,
        }
