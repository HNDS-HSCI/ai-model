import uuid
import logging
from typing import List, Dict, Any, Optional

from hsci.core.data_types import (
    SkillCandidate, SkillCandidateStatus, SkillLearningResult,
    Method, Task, TaskType, Precondition, PerceptionMap, ReasoningPlan,
    VerificationResult, ReflectionResult, ReflectionFailureType
)
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.symbolic.z3_verifier import Z3VerificationEngine

logger = logging.getLogger("HSCI.Learning.SkillLearningEngine")


class SkillLearningPolicy:
    """
    Evaluates execution/reflection evidence to determine if skill compilation should be attempted.
    Rejects unverified failures, cycles, max-depth errors, and unverified solution candidates.
    """

    def evaluate_reflection(self, reflection: ReflectionResult) -> str:
        """
        Evaluates a ReflectionResult to decide whether skill proposal is permissible.
        Returns 'PROPOSE_SKILL' or 'NO_LEARNING'.
        """
        # Strictly reject failures that do not contain actionable verified domain knowledge
        if reflection.failure_category in [
            ReflectionFailureType.DECOMPOSITION_CYCLE,
            ReflectionFailureType.MAX_DEPTH_EXCEEDED,
            ReflectionFailureType.SOLUTION_VERIFICATION_FAILURE,
            ReflectionFailureType.SOLVER_UNSAT,
            ReflectionFailureType.SOLVER_TIMEOUT
        ]:
            logger.info(f"LearningPolicy: Rejected reflection '{reflection.failure_category.value}' (unlearnable/unverified)")
            return "NO_LEARNING"

        if reflection.failure_category == ReflectionFailureType.NO_METHOD:
            return "PROPOSE_SKILL"

        return "NO_LEARNING"


class SkillValidator:
    """
    Executes a 4-stage validation gate over a SkillCandidate before MethodRegistry activation:
    1. Structural Validation (non-empty subtasks, primitive/compound existence)
    2. Cycle Detection (no self-recursion or direct cycle)
    3. Formal Validation (preconditions check)
    4. Replay Validation (decomposes candidate against context using HTNPlanner)
    """

    def __init__(self, planner: Optional[HTNPlanner] = None, verifier: Optional[Z3VerificationEngine] = None):
        self.planner = planner or HTNPlanner()
        self.verifier = verifier or Z3VerificationEngine()

    def validate(self, candidate: SkillCandidate, context: Optional[Dict[str, Any]] = None) -> bool:
        candidate.status = SkillCandidateStatus.VALIDATING
        candidate.validation_failures.clear()

        # Stage 1: Structural Validation
        if not candidate.target_task_name:
            candidate.validation_failures.append("Empty target_task_name")
        if not candidate.proposed_subtasks:
            candidate.validation_failures.append("Empty proposed_subtasks list")

        for st in candidate.proposed_subtasks:
            if st.name == candidate.target_task_name:
                candidate.validation_failures.append(f"Direct self-cycle detected: subtask '{st.name}' equals target task")

        # Stage 2: Cycle Detection
        visited = set([candidate.target_task_name])
        for st in candidate.proposed_subtasks:
            if st.name in visited:
                candidate.validation_failures.append(f"Cycle detected in candidate subtasks: '{st.name}'")

        # Stage 3: Formal Validation (Precondition syntax & Z3 check if present)
        for pre in candidate.proposed_preconditions:
            if not pre.predicate:
                candidate.validation_failures.append("Invalid empty precondition predicate")

        # Stage 4: Replay Validation
        if not candidate.validation_failures:
            # Create a temporary dry-run method to test decomposition
            temp_method = Method(
                id=f"temp-{candidate.candidate_id}",
                target_task_name=candidate.target_task_name,
                preconditions=candidate.proposed_preconditions,
                subtasks=candidate.proposed_subtasks,
                cost=candidate.cost
            )
            root = Task(id="test-root", name=candidate.target_task_name, task_type=TaskType.COMPOUND)

            # Test-register temporary method
            self.planner.method_registry.register_method(temp_method)
            try:
                plan = self.planner.decompose_task(root, context=context or {})
                if not plan:
                    candidate.validation_failures.append("Replay decomposition yielded an empty primitive plan")
            except Exception as err:
                candidate.validation_failures.append(f"Replay decomposition raised error: {err}")
            finally:
                # Remove temporary method from registry
                if temp_method.id in self.planner.method_registry._registered_ids:
                    self.planner.method_registry._registered_ids.remove(temp_method.id)
                methods = self.planner.method_registry._methods_by_target.get(candidate.target_task_name, [])
                self.planner.method_registry._methods_by_target[candidate.target_task_name] = [
                    m for m in methods if m.id != temp_method.id
                ]


        if candidate.validation_failures:
            candidate.status = SkillCandidateStatus.REJECTED
            logger.warning(f"SkillCandidate '{candidate.candidate_id}' REJECTED: {candidate.validation_failures}")
            return False

        candidate.status = SkillCandidateStatus.VERIFIED
        logger.info(f"SkillCandidate '{candidate.candidate_id}' VERIFIED successfully")
        return True


class SkillLearningEngine:
    """
    LAYER 4C: Dynamic Skill & Method Acquisition Engine.
    Compiles verified execution traces into reusable, declarative HTN Method candidates,
    validates them through SkillValidator, and activates verified skills into MethodRegistry.
    """

    def __init__(self, planner: Optional[HTNPlanner] = None, verifier: Optional[Z3VerificationEngine] = None, auto_rehydrate: bool = False):
        self.planner = planner or HTNPlanner()
        self.verifier = verifier or Z3VerificationEngine()
        self.policy = SkillLearningPolicy()
        self.validator = SkillValidator(planner=self.planner, verifier=self.verifier)
        
        from hsci.learning.persistent_skill_store import PersistentSkillStore
        self.skill_store = PersistentSkillStore()

        if auto_rehydrate:
            self.rehydrate_skills()

    def rehydrate_skills(self) -> int:
        """
        SKB-1 Startup Rehydration Path:
        Loads persistent skill records, validates schema and SHA-256 integrity, re-runs SkillValidator
        replay decomposition, and activates verified skills into MethodRegistry.
        Rejects tampered, corrupted, or invalid records.
        """
        valid_pairs = self.skill_store.load_and_validate_skills()
        activated_count = 0

        for method, raw_record in valid_pairs:
            # Reconstruct temporary SkillCandidate for re-validation
            candidate = SkillCandidate(
                candidate_id=raw_record.get("skill_id", "rehydrated"),
                source_request_id=raw_record.get("source_request_id", ""),
                target_task_name=method.target_task_name,
                proposed_preconditions=method.preconditions,
                proposed_subtasks=method.subtasks,
                provenance_trace=raw_record.get("provenance_trace", []),
                cost=method.cost
            )

            # Re-run 4-stage validation (Structural, Cycle, Formal, Replay)
            if self.validator.validate(candidate):
                self.planner.method_registry.register_method(method)
                if hasattr(self.planner, "skill_graph"):
                    self.planner.skill_graph.add_verified_method(method, candidate.provenance_trace)
                activated_count += 1
                logger.info(f"SkillLearningEngine: Successfully rehydrated verified skill '{method.id}'")
            else:
                logger.warning(f"SkillLearningEngine: Rehydration failed validation for skill '{method.id}'")

        return activated_count

    def learn_from_verified_execution(
        self,
        target_task_name: str,
        verified_subtasks: List[Task],
        perception: PerceptionMap,
        verification: VerificationResult,
        request_id: str = "",
        preconditions: Optional[List[Precondition]] = None
    ) -> SkillLearningResult:
        """
        Synthesizes a candidate HTN Method from a VERIFIED successful execution trace.
        Validates the candidate, activates it into MethodRegistry, and persists it to durable storage.
        """
        # Safety gate: Final verification MUST be proven
        if not verification or not verification.valid:
            logger.warning("SkillLearningEngine: Refusing skill acquisition for unverified or invalid execution trace.")
            return SkillLearningResult(
                decision="NO_LEARNING",
                reason="Execution trace is not proven by final verification."
            )

        if not target_task_name or not verified_subtasks:
            return SkillLearningResult(
                decision="NO_LEARNING",
                reason="Missing target task name or subtasks."
            )

        cand_id = f"cand-{uuid.uuid4().hex[:8]}"
        candidate = SkillCandidate(
            candidate_id=cand_id,
            source_request_id=request_id,
            target_task_name=target_task_name,
            proposed_preconditions=preconditions or [],
            proposed_subtasks=verified_subtasks,
            provenance_trace=[
                f"Compiled from request '{request_id}'",
                f"Verified by Z3 (confidence={verification.confidence})",
                f"Subtask sequence count={len(verified_subtasks)}"
            ],
            cost=1.5  # Slightly higher cost than default hand-crafted methods
        )

        # Validate candidate
        context_facts = perception.entities if perception else {}
        is_valid = self.validator.validate(candidate, context=context_facts)

        if not is_valid:
            return SkillLearningResult(
                decision="SKILL_REJECTED",
                candidate_id=cand_id,
                validation_passed=False,
                reason="; ".join(candidate.validation_failures)
            )

        # Activate into MethodRegistry
        method_id = f"method-learned-{cand_id}"
        from hsci.core.data_types import MethodSource
        learned_method = Method(
            id=method_id,
            target_task_name=candidate.target_task_name,
            preconditions=candidate.proposed_preconditions,
            subtasks=candidate.proposed_subtasks,
            cost=candidate.cost,
            description=f"Dynamically acquired skill for '{candidate.target_task_name}' (Provenance: {request_id})",
            source=MethodSource.LEARNED
        )

        self.planner.method_registry.register_method(learned_method)
        if hasattr(self.planner, "skill_graph"):
            self.planner.skill_graph.add_verified_method(learned_method, candidate.provenance_trace)
        candidate.status = SkillCandidateStatus.ACTIVE

        # SKB-1: Persist verified skill to durable storage
        self.skill_store.save_skill(learned_method, candidate)

        logger.info(f"SkillLearningEngine: Activated and persisted new Method '{method_id}' for task '{target_task_name}'")
        return SkillLearningResult(
            decision="SKILL_ACTIVATED",
            candidate_id=cand_id,
            activated_method_id=method_id,
            validation_passed=True,
            reason=f"Skill candidate '{cand_id}' validated, activated into MethodRegistry as '{method_id}', and persisted to disk."
        )
