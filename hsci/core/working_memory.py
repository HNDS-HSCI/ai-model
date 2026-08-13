import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import z3

from hsci.core.data_types import (
    PerceptionMap, SubGoal, Expression, VerificationStatus, ProofTrace, Concept, PlanningContext
)

# ─────────────────────────────────────────────
# WORKING MEMORY INTERFACE
# ─────────────────────────────────────────────

class IWorkingMemory(ABC):
    """
    Interface for the request-scoped ephemeral scratchpad.
    """
    @abstractmethod
    def get_stage_duration(self, stage_name: str) -> float:
        pass

    @abstractmethod
    def record_duration(self, stage_name: str, duration_ms: float) -> None:
        pass

# ─────────────────────────────────────────────
# ADDITIONAL DATA TYPES DEFINED FOR V4
# ─────────────────────────────────────────────

@dataclass
class SemanticFrame:
    """
    Stage 0.5: Extracted semantic variables, entities, and constraints.
    """
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    raw_tokens: List[str] = field(default_factory=list)

# ─────────────────────────────────────────────
# TYPED SUB-CONTEXT DATACLASSES
# ─────────────────────────────────────────────

@dataclass
class SessionMetadata:
    """
    Metadata describing the current Thinking Session constraints.
    """
    request_id: str
    session_id: str
    timestamp_start: float
    domain: str = "general"
    timeout_ms: int = 5000


@dataclass
class AttentionBuffer:
    """
    A short-term focus window retaining the top N salient entities.
    """
    salient_entities: List[str] = field(default_factory=list)
    salience_scores: Dict[str, float] = field(default_factory=dict)
    max_capacity: int = 7

    def add_salience(self, entity: str, score: float) -> None:
        self.salience_scores[entity] = score
        if entity not in self.salient_entities:
            self.salient_entities.append(entity)
        # Keep within max capacity sorted by score descending
        self.salient_entities.sort(key=lambda e: self.salience_scores.get(e, 0.0), reverse=True)
        if len(self.salient_entities) > self.max_capacity:
            discarded = self.salient_entities.pop()
            self.salience_scores.pop(discarded, None)

    def clear(self) -> None:
        self.salient_entities.clear()
        self.salience_scores.clear()


@dataclass
class ActivationField:
    """
    Stores concept activations resulting from spreading activation.
    """
    activated_concept_ids: List[str] = field(default_factory=list)
    activation_strengths: Dict[str, float] = field(default_factory=dict)
    decay_rate: float = 0.6

    def set_activation(self, concept_id: str, strength: float) -> None:
        if strength >= 0.1:
            self.activation_strengths[concept_id] = strength
            if concept_id not in self.activated_concept_ids:
                self.activated_concept_ids.append(concept_id)
        else:
            self.activation_strengths.pop(concept_id, None)
            if concept_id in self.activated_concept_ids:
                self.activated_concept_ids.remove(concept_id)

    def clear(self) -> None:
        self.activated_concept_ids.clear()
        self.activation_strengths.clear()


@dataclass
class GoalContext:
    """
    Tracks the active objective and planning sub-goals.
    """
    primary_goal: str
    active_subgoals: List[SubGoal] = field(default_factory=list)
    completed_subgoals: List[str] = field(default_factory=list)
    backlog_goals: List[str] = field(default_factory=list)

    def clear(self) -> None:
        self.active_subgoals.clear()
        self.completed_subgoals.clear()
        self.backlog_goals.clear()


@dataclass
class PlannerContext:
    """
    Maintains the state of the HTN Planner during decomposition.
    """
    rule_bindings: Dict[str, Any] = field(default_factory=dict)
    planning_depth: int = 0
    max_depth: int = 5
    cycle_detected: bool = False

    def clear(self) -> None:
        self.rule_bindings.clear()
        self.planning_depth = 0
        self.cycle_detected = False


@dataclass
class ReasoningContext:
    """
    Stores intermediate solver candidate expressions.
    """
    candidate_expressions: List[Expression] = field(default_factory=list)
    selected_expression: Optional[Expression] = None
    concepts_applied: List[str] = field(default_factory=list)

    def clear(self) -> None:
        self.candidate_expressions.clear()
        self.selected_expression = None
        self.concepts_applied.clear()


@dataclass
class VerificationContext:
    """
    Tracks the Z3 verification and CEGIS iteration state.
    """
    status: VerificationStatus = VerificationStatus.UNKNOWN
    cegis_iteration: int = 0
    max_cegis_iterations: int = 5
    counterexample: Optional[Dict[str, Any]] = None
    z3_proof_trace: Optional[ProofTrace] = None
    verification_passed: bool = False

    def clear(self) -> None:
        self.status = VerificationStatus.UNKNOWN
        self.cegis_iteration = 0
        self.counterexample = None
        self.z3_proof_trace = None
        self.verification_passed = False


@dataclass
class ExecutionContext:
    """
    Stores stdout, logs, and variables during code synthesis runs.
    """
    local_variables: Dict[str, Any] = field(default_factory=dict)
    console_output: List[str] = field(default_factory=list)
    execution_success: bool = True
    error_message: Optional[str] = None

    def clear(self) -> None:
        self.local_variables.clear()
        self.console_output.clear()
        self.execution_success = True
        self.error_message = None


@dataclass
class ReflectionContext:
    """
    Stores failure classifications and evolution proposal parameters.
    """
    failure_category: Optional[str] = None
    diagnosed_root_cause: Optional[str] = None
    proposed_concept_evolutions: List[str] = field(default_factory=list)
    last_reflection: Optional[Any] = None

    def clear(self) -> None:
        self.failure_category = None
        self.diagnosed_root_cause = None
        self.proposed_concept_evolutions.clear()
        self.last_reflection = None


# ─────────────────────────────────────────────
# THE WORKING MEMORY IMPLEMENTATION
# ─────────────────────────────────────────────

class WorkingMemory(IWorkingMemory):
    """
    The main request-scoped active thinking state workspace.
    Implements full deallocation cleanup and complex object snapshot serialization.
    """
    def __init__(self, request_id: str, session_id: str, stimulus: str):
        self.metadata: SessionMetadata = SessionMetadata(
            request_id=request_id,
            session_id=session_id,
            timestamp_start=time.time()
        )
        self.stimulus: str = stimulus
        self.attention_buffer: AttentionBuffer = AttentionBuffer()
        self.activation_field: ActivationField = ActivationField()
        self.goal_context: Optional[GoalContext] = None
        self.planner_context: PlannerContext = PlannerContext()
        self.reasoning_context: ReasoningContext = ReasoningContext()
        self.verification_context: VerificationContext = VerificationContext()
        self.execution_context: ExecutionContext = ExecutionContext()
        self.reflection_context: ReflectionContext = ReflectionContext()
        
        self.stage_durations: Dict[str, float] = {}
        self.active_skills: List[str] = []
        self.semantic_frame: Optional[SemanticFrame] = None
        self.perception_map: Optional[PerceptionMap] = None
        self.verification_passed: bool = False
        self.proof_trace: Optional[ProofTrace] = None
        self.counterexample: Optional[Dict[str, Any]] = None
        self.attempts: int = 1

    def initialize(self, stimulus: str) -> None:
        self.stimulus = stimulus
        self.clear()

    def activate_concepts(self, concept_ids: List[str], strengths: Dict[str, float]) -> None:
        for cid in concept_ids:
            self.activation_field.set_activation(cid, strengths.get(cid, 0.5))

    def store_expression(self, expression: Expression) -> None:
        self.reasoning_context.candidate_expressions.append(expression)

    def store_goal(self, goal: str, subgoals: List[SubGoal]) -> None:
        self.goal_context = GoalContext(primary_goal=goal, active_subgoals=subgoals)

    def get_active_concepts(self) -> List[str]:
        return [
            cid for cid in self.activation_field.activated_concept_ids
            if self.activation_field.activation_strengths.get(cid, 0.0) >= 0.1
        ]

    def get_stage_duration(self, stage_name: str) -> float:
        return self.stage_durations.get(stage_name, 0.0)

    def record_duration(self, stage_name: str, duration_ms: float) -> None:
        self.stage_durations[stage_name] = duration_ms

    def clear(self) -> None:
        """Resets all variable states, preserving session metadata keys."""
        self.attention_buffer.clear()
        self.activation_field.clear()
        if self.goal_context is not None:
            self.goal_context.clear()
            self.goal_context = None
        self.planner_context.clear()
        self.reasoning_context.clear()
        self.verification_context.clear()
        self.execution_context.clear()
        self.reflection_context.clear()
        
        self.stage_durations.clear()
        self.active_skills.clear()
        self.semantic_frame = None
        self.perception_map = None
        self.verification_passed = False
        self.proof_trace = None
        self.counterexample = None
        self.attempts = 1

    def dispose(self) -> None:
        """
        Performs explicit cleanup of nested collection structures to break circular loops
        and guarantee immediate Python garbage collection releases.
        """
        self.clear()
        # Nullify sub-context instances
        del self.attention_buffer
        del self.activation_field
        del self.planner_context
        del self.reasoning_context
        del self.verification_context
        del self.execution_context
        del self.reflection_context

    def snapshot(self) -> Dict[str, Any]:
        """
        Serializes current memory state into a dictionary.
        Enforces conversion of Z3 solver expressions and PyTorch vectors into serializable primitives.
        """
        serialized_expressions = []
        for expr in self.reasoning_context.candidate_expressions:
            val = expr.value
            # Check Z3 expression wrapper reference
            if isinstance(val, z3.ExprRef):
                val = val.sexpr()  # Convert to S-Expression string
            elif hasattr(val, "tolist"):  # PyTorch tensor check
                val = val.tolist()  # Convert PyTorch/numpy to standard list

            serialized_expressions.append({
                "value": val,
                "concepts_used": expr.concepts_used
            })

        return {
            "metadata": {
                "request_id": self.metadata.request_id,
                "session_id": self.metadata.session_id,
                "timestamp_start": self.metadata.timestamp_start,
                "domain": self.metadata.domain,
                "timeout_ms": self.metadata.timeout_ms
            },
            "stimulus": self.stimulus,
            "active_concepts": self.get_active_concepts(),
            "active_skills": list(self.active_skills),
            "stage_durations": dict(self.stage_durations),
            "candidate_expressions": serialized_expressions,
            "verification_passed": self.verification_passed,
            "attempts": self.attempts
        }

    def restore(self, data: Dict[str, Any]) -> None:
        """Restores memory states from a snapshot dictionary."""
        self.clear()
        meta = data.get("metadata", {})
        self.metadata = SessionMetadata(
            request_id=meta.get("request_id", ""),
            session_id=meta.get("session_id", ""),
            timestamp_start=meta.get("timestamp_start", time.time()),
            domain=meta.get("domain", "general"),
            timeout_ms=meta.get("timeout_ms", 5000)
        )
        self.stimulus = data.get("stimulus", "")
        self.verification_passed = data.get("verification_passed", False)
        self.attempts = data.get("attempts", 1)
        self.active_skills = list(data.get("active_skills", []))
        self.stage_durations = dict(data.get("stage_durations", {}))
        
        # Restore active concepts
        for cid in data.get("active_concepts", []):
            self.activation_field.set_activation(cid, 1.0)
            
        # Restore candidate expressions
        for expr in data.get("candidate_expressions", []):
            self.reasoning_context.candidate_expressions.append(
                Expression(value=expr.get("value"), concepts_used=expr.get("concepts_used", []))
            )

    def build_planning_context(self) -> PlanningContext:
        """
        Creates an immutable, request-scoped snapshot of planning-relevant state from WorkingMemory.
        Extracts facts from semantic frame, perception map entities, active concepts, and session metadata.
        """
        facts: Dict[str, Any] = {}
        entities_dict: Dict[str, Any] = {}

        # 1. Semantic Frame facts/constraints
        if self.semantic_frame:
            for k, v in self.semantic_frame.entities.items():
                facts[k] = v
            for c in self.semantic_frame.constraints:
                if isinstance(c, dict):
                    facts.update(c)

        # 2. Perception Map entities & SemanticIR facts
        intent_val = None
        if self.perception_map:
            intent_val = self.perception_map.intent.value if hasattr(self.perception_map.intent, "value") else str(self.perception_map.intent)
            for k, ev in self.perception_map.entities.items():
                entities_dict[k] = ev
                if hasattr(ev, "known") and ev.known and hasattr(ev, "value") and ev.value is not None:
                    facts[k] = ev.value

            # NSG-3: Incorporate SemanticIR declarative relations and facts directly
            sem_ir = getattr(self.perception_map, "semantic_ir", None)
            if sem_ir and hasattr(sem_ir, "entities"):
                for k, v in sem_ir.entities.items():
                    if k not in facts:
                        facts[k] = v
            if sem_ir and hasattr(sem_ir, "relations"):
                for r in sem_ir.relations:
                    facts[f"RELATION_{r.subject}_{r.relation}"] = r.object

        # 3. Rule bindings from planner_context scratchpad
        for k, v in self.planner_context.rule_bindings.items():
            facts[k] = v

        return PlanningContext(
            facts=dict(facts),
            entities=dict(entities_dict),
            active_concepts=list(self.get_active_concepts()),
            intent=intent_val,
            request_id=self.metadata.request_id,
            session_id=self.metadata.session_id
        )

