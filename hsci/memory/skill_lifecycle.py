import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from hsci.core.data_types import MethodSource

logger = logging.getLogger(__name__)


class SkillLifecycleStatus(Enum):
    """
    SCG4-01: Explicit lifecycle status enum for learned graph skills.
    CANONICAL methods remain immutably ACTIVE.
    """
    ACTIVE = "active"
    DECAYING = "decaying"
    DEPRECATED = "deprecated"


@dataclass
class SkillLifecycleEvent:
    """
    SCG4-02: Declarative, inspectable lifecycle transition provenance event.
    Stores primitive numeric counters and reasons—zero executable callbacks.
    """
    event_id: str
    skill_id: str
    previous_status: str
    new_status: str
    reason: str
    request_id: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillLifecycleState:
    """
    SCG4-03: Stateful lifecycle tracking for a learned skill node.
    """
    skill_id: str
    status: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE
    consecutive_failures: int = 0
    requests_since_verified_use: int = 0
    selection_opportunities: int = 0
    successful_selections: int = 0
    transition_history: List[Dict[str, Any]] = field(default_factory=list)


class SkillLifecyclePolicy:
    """
    SCG4-04: Deterministic policy engine governing lifecycle state transitions.
    Enforces CANONICAL immutability, hysteresis, and deterministic transition thresholds.
    """
    MAX_LIFECYCLE_HISTORY = 20

    # Named deterministic evidence thresholds
    DECAY_FAILURE_THRESHOLD = 3         # ACTIVE -> DECAYING on 3 consecutive failures or 10 stale requests
    DECAY_STALENESS_THRESHOLD = 10
    DEPRECATION_FAILURE_THRESHOLD = 6   # DECAYING -> DEPRECATED on 6 consecutive failures or 20 stale requests
    DEPRECATION_STALENESS_THRESHOLD = 20
    RECOVERY_SUCCESS_THRESHOLD = 1      # DECAYING -> ACTIVE on 1 Z3 verified success

    def evaluate_transition(
        self,
        skill_id: str,
        source: MethodSource,
        current_state: SkillLifecycleState,
        outcome: Optional[str] = None,   # "VERIFIED_SUCCESS", "VERIFICATION_FAILURE", "PLANNING_FAILURE", "OPPORTUNITY"
        request_id: Optional[str] = None
    ) -> SkillLifecycleStatus:
        # Invariant 1: CANONICAL methods MUST NEVER decay or deprecate
        if source == MethodSource.CANONICAL or getattr(source, "value", source) == "canonical":
            current_state.status = SkillLifecycleStatus.ACTIVE
            return SkillLifecycleStatus.ACTIVE

        old_status = current_state.status

        # Update stats based on outcome
        if outcome == "VERIFIED_SUCCESS":
            current_state.successful_selections += 1
            current_state.consecutive_failures = 0
            current_state.requests_since_verified_use = 0
        elif outcome in ("VERIFICATION_FAILURE", "PLANNING_FAILURE"):
            current_state.consecutive_failures += 1
            current_state.requests_since_verified_use += 1
        elif outcome == "OPPORTUNITY":
            current_state.selection_opportunities += 1
            current_state.requests_since_verified_use += 1

        new_status = old_status

        # Transition Rules with Hysteresis
        if old_status == SkillLifecycleStatus.ACTIVE:
            if (current_state.consecutive_failures >= self.DEPRECATION_FAILURE_THRESHOLD or
                    current_state.requests_since_verified_use >= self.DEPRECATION_STALENESS_THRESHOLD):
                new_status = SkillLifecycleStatus.DEPRECATED
            elif (current_state.consecutive_failures >= self.DECAY_FAILURE_THRESHOLD or
                    current_state.requests_since_verified_use >= self.DECAY_STALENESS_THRESHOLD):
                new_status = SkillLifecycleStatus.DECAYING

        elif old_status == SkillLifecycleStatus.DECAYING:
            if outcome == "VERIFIED_SUCCESS" and current_state.consecutive_failures <= self.RECOVERY_SUCCESS_THRESHOLD:
                # Verified Recovery
                new_status = SkillLifecycleStatus.ACTIVE
            elif (current_state.consecutive_failures >= self.DEPRECATION_FAILURE_THRESHOLD or
                  current_state.requests_since_verified_use >= self.DEPRECATION_STALENESS_THRESHOLD):
                new_status = SkillLifecycleStatus.DEPRECATED

        # DEPRECATED skills remain DEPRECATED unless administrative override (no autonomous resurrection)

        if new_status != old_status:
            current_state.status = new_status
            event = SkillLifecycleEvent(
                event_id=f"evt-{len(current_state.transition_history)+1}",
                skill_id=skill_id,
                previous_status=old_status.value,
                new_status=new_status.value,
                reason=f"Transition triggered by outcome '{outcome}' (failures={current_state.consecutive_failures}, stale={current_state.requests_since_verified_use})",
                request_id=request_id,
                evidence={
                    "consecutive_failures": current_state.consecutive_failures,
                    "requests_since_verified_use": current_state.requests_since_verified_use,
                    "successful_selections": current_state.successful_selections
                }
            )
            hist_entry = {
                "event_id": event.event_id,
                "previous_status": event.previous_status,
                "new_status": event.new_status,
                "reason": event.reason,
                "request_id": event.request_id,
                "evidence": event.evidence
            }
            current_state.transition_history.append(hist_entry)
            if len(current_state.transition_history) > self.MAX_LIFECYCLE_HISTORY:
                current_state.transition_history = current_state.transition_history[-self.MAX_LIFECYCLE_HISTORY:]

        return new_status


class SkillLifecycleManager:
    """
    SCG4-05: Centralized lifecycle state manager & atomic persistence handler (knowledge/skill_lifecycle.json).
    """

    def __init__(self, storage_dir: Optional[Path] = None, filename: str = "skill_lifecycle.json"):
        if storage_dir is None:
            storage_dir = Path(__file__).resolve().parent.parent.parent / "knowledge"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = self.storage_dir / filename

        self.states: Dict[str, SkillLifecycleState] = {}
        self.policy = SkillLifecyclePolicy()
        self.load_lifecycle()

    def get_state(self, skill_id: str) -> SkillLifecycleState:
        if skill_id not in self.states:
            self.states[skill_id] = SkillLifecycleState(skill_id=skill_id)
        return self.states[skill_id]

    def record_skill_outcome(
        self,
        skill_id: str,
        source: Any,
        outcome: str,
        request_id: Optional[str] = None
    ) -> SkillLifecycleStatus:
        state = self.get_state(skill_id)
        new_status = self.policy.evaluate_transition(skill_id, source, state, outcome=outcome, request_id=request_id)
        self.save_lifecycle()
        return new_status

    def is_eligible_for_retrieval(self, skill_id: str, source: Any) -> bool:
        """
        Determines search eligibility:
        CANONICAL: Always eligible
        LEARNED ACTIVE / DECAYING: Eligible (DECAYING receives ranking penalty in GraphPlanEvaluator)
        LEARNED DEPRECATED: Excluded from candidate search
        """
        if source == MethodSource.CANONICAL or getattr(source, "value", source) == "canonical":
            return True
        st = self.get_state(skill_id).status
        return st != SkillLifecycleStatus.DEPRECATED

    def save_lifecycle(self) -> None:
        data = {
            "schema_version": 1,
            "states": {
                sid: {
                    "skill_id": st.skill_id,
                    "status": st.status.value,
                    "consecutive_failures": st.consecutive_failures,
                    "requests_since_verified_use": st.requests_since_verified_use,
                    "selection_opportunities": st.selection_opportunities,
                    "successful_selections": st.successful_selections,
                    "transition_history": st.transition_history
                }
                for sid, st in self.states.items()
            }
        }
        tmp_file = self.storage_path.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            tmp_file.replace(self.storage_path)
        except Exception as e:
            logger.error(f"SkillLifecycleManager: Failed to save lifecycle persistence: {e}")
            if tmp_file.exists():
                tmp_file.unlink()

    def load_lifecycle(self) -> None:
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("schema_version") != 1:
                logger.warning(f"SkillLifecycleManager: Incompatible schema version {data.get('schema_version')}")
                return

            states_raw = data.get("states", {})
            for sid, sdata in states_raw.items():
                status_str = sdata.get("status", "active")
                try:
                    status_enum = SkillLifecycleStatus(status_str)
                except ValueError:
                    status_enum = SkillLifecycleStatus.ACTIVE

                self.states[sid] = SkillLifecycleState(
                    skill_id=sdata.get("skill_id", sid),
                    status=status_enum,
                    consecutive_failures=sdata.get("consecutive_failures", 0),
                    requests_since_verified_use=sdata.get("requests_since_verified_use", 0),
                    selection_opportunities=sdata.get("selection_opportunities", 0),
                    successful_selections=sdata.get("successful_selections", 0),
                    transition_history=sdata.get("transition_history", [])
                )
        except Exception as e:
            logger.error(f"SkillLifecycleManager: Failed to load lifecycle storage: {e}")
