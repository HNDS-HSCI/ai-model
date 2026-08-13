import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from hsci.core.data_types import MethodSource

logger = logging.getLogger(__name__)


@dataclass
class SkillUtilityStats:
    """
    SCG3-05: Declarative, typed telemetry statistics for a specific skill.
    Stores primitive numeric counters only—zero executable callbacks.
    """
    skill_id: str
    verified_successes: int = 0
    verified_failures: int = 0
    planning_failures: int = 0
    total_attempts: int = 0
    cumulative_cost: float = 0.0
    last_used_sequence: int = 0

    def compute_utility_score(self, alpha: float = 1.0, beta: float = 1.0) -> float:
        """
        SCG3-07: Numerically stable, deterministic utility evaluator.
        Formula:
            reliability = (successes + alpha) / (successes + failures + alpha + beta)
            penalty = 0.1 * planning_failures + 0.05 * cumulative_cost
            utility = reliability - penalty
        """
        attempts = self.verified_successes + self.verified_failures
        reliability = (self.verified_successes + alpha) / (attempts + alpha + beta)
        penalty = (0.1 * self.planning_failures) + (0.05 * self.cumulative_cost)
        return round(reliability - penalty, 4)


@dataclass
class GraphCandidateScore:
    """
    SCG3-08: Typed, explainable score evaluation artifact for a candidate graph chain.
    """
    candidate_id: str
    utility_score: float
    authority_rank: int               # 0 for CANONICAL, 1 for LEARNED
    estimated_cost: float
    chain_depth: int
    success_evidence: float
    failure_penalty: float
    explanation: List[str] = field(default_factory=list)


class SkillUtilityStore:
    """
    SCG3-14: Declarative local durable storage for utility telemetry (knowledge/skill_utility.json).
    Atomic writes using tmp files and deterministic schema versioning.
    """

    def __init__(self, storage_dir: Optional[Path] = None, filename: str = "skill_utility.json"):
        if storage_dir is None:
            storage_dir = Path(__file__).resolve().parent.parent.parent / "knowledge"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = self.storage_dir / filename
        
        self.stats: Dict[str, SkillUtilityStats] = {}
        self.sequence_counter: int = 0
        self.load_utility()

    def get_stats(self, skill_id: str) -> SkillUtilityStats:
        if skill_id not in self.stats:
            self.stats[skill_id] = SkillUtilityStats(skill_id=skill_id)
        return self.stats[skill_id]

    def record_outcome(
        self,
        skill_id: str,
        outcome: str,  # "VERIFIED_SUCCESS", "VERIFICATION_FAILURE", "PLANNING_FAILURE"
        cost: float = 1.0
    ) -> None:
        self.sequence_counter += 1
        st = self.get_stats(skill_id)
        st.total_attempts += 1
        st.cumulative_cost += cost
        st.last_used_sequence = self.sequence_counter

        if outcome == "VERIFIED_SUCCESS":
            st.verified_successes += 1
        elif outcome == "VERIFICATION_FAILURE":
            st.verified_failures += 1
        elif outcome == "PLANNING_FAILURE":
            st.planning_failures += 1

        self.save_utility()

    def save_utility(self) -> None:
        data = {
            "schema_version": 1,
            "sequence_counter": self.sequence_counter,
            "stats": {
                sid: {
                    "skill_id": st.skill_id,
                    "verified_successes": st.verified_successes,
                    "verified_failures": st.verified_failures,
                    "planning_failures": st.planning_failures,
                    "total_attempts": st.total_attempts,
                    "cumulative_cost": st.cumulative_cost,
                    "last_used_sequence": st.last_used_sequence
                }
                for sid, st in self.stats.items()
            }
        }

        tmp_file = self.storage_path.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            tmp_file.replace(self.storage_path)
        except Exception as e:
            logger.error(f"SkillUtilityStore: Failed to save utility telemetry: {e}")
            if tmp_file.exists():
                tmp_file.unlink()

    def load_utility(self) -> None:
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("schema_version") != 1:
                logger.warning(f"SkillUtilityStore: Incompatible schema version {data.get('schema_version')}")
                return

            self.sequence_counter = data.get("sequence_counter", 0)
            stats_raw = data.get("stats", {})
            for sid, sdata in stats_raw.items():
                self.stats[sid] = SkillUtilityStats(
                    skill_id=sdata.get("skill_id", sid),
                    verified_successes=sdata.get("verified_successes", 0),
                    verified_failures=sdata.get("verified_failures", 0),
                    planning_failures=sdata.get("planning_failures", 0),
                    total_attempts=sdata.get("total_attempts", 0),
                    cumulative_cost=sdata.get("cumulative_cost", 0.0),
                    last_used_sequence=sdata.get("last_used_sequence", 0)
                )
        except Exception as e:
            logger.error(f"SkillUtilityStore: Failed to load utility storage: {e}")


class GraphPlanEvaluator:
    """
    SCG3-08 / SCG3-09: Utility-Guided Evaluator and Deterministic Ranker for candidate graph chains.
    Enforces Strict Authority Order: CANONICAL > LEARNED > UTILITY SCORE.
    """

    def __init__(self, utility_store: Optional[SkillUtilityStore] = None, lifecycle_manager: Optional[Any] = None):
        self.utility_store = utility_store or SkillUtilityStore()
        self.lifecycle_manager = lifecycle_manager

    def evaluate_chain(self, chain: List[Any], candidate_id: str = "cand") -> GraphCandidateScore:
        if not chain:
            return GraphCandidateScore(
                candidate_id=candidate_id,
                utility_score=0.0,
                authority_rank=1,
                estimated_cost=0.0,
                chain_depth=0,
                success_evidence=0.0,
                failure_penalty=0.0,
                explanation=["Empty chain"]
            )

        from hsci.memory.skill_lifecycle import SkillLifecycleManager, SkillLifecycleStatus
        lifecycle_mgr = self.lifecycle_manager or SkillLifecycleManager()

        # Check Authority Rank: If any node in chain is LEARNED, authority_rank = 1 else 0
        has_learned = any(getattr(node, "source", None) == MethodSource.LEARNED for node in chain)
        authority_rank = 1 if has_learned else 0

        total_cost = sum(getattr(node, "cost", 1.0) for node in chain)
        chain_depth = len(chain)

        # Evaluate aggregate utility stats & lifecycle status
        scores = []
        explanations = [f"Authority Rank: {'CANONICAL' if authority_rank == 0 else 'LEARNED'}"]
        decay_penalty = 0.0

        for node in chain:
            method_id = getattr(node, "method_id", getattr(node, "id", node.skill_id if hasattr(node, "skill_id") else str(node)))
            source = getattr(node, "source", MethodSource.LEARNED)

            # SCG4-07: Check Lifecycle Eligibility (DEPRECATED skills excluded from candidate search)
            if not lifecycle_mgr.is_eligible_for_retrieval(method_id, source):
                explanations.append(f"Node '{method_id}': DEPRECATED (Excluded)")
                return GraphCandidateScore(
                    candidate_id=candidate_id,
                    utility_score=-999.0,
                    authority_rank=99,  # Ineligible
                    estimated_cost=total_cost,
                    chain_depth=chain_depth,
                    success_evidence=0.0,
                    failure_penalty=999.0,
                    explanation=explanations
                )

            l_state = lifecycle_mgr.get_state(method_id)
            if l_state.status == SkillLifecycleStatus.DECAYING:
                decay_penalty += 0.25  # Apply ranking penalty for decaying skills
                explanations.append(f"Node '{method_id}': DECAYING (Penalty -0.25)")

            stats = self.utility_store.get_stats(method_id)
            node_score = stats.compute_utility_score()
            scores.append(node_score)
            explanations.append(f"Node '{method_id}': utility={node_score} (status={l_state.status.value})")

        aggregate_utility = round((sum(scores) / len(scores)) - decay_penalty, 4)

        return GraphCandidateScore(
            candidate_id=candidate_id,
            utility_score=aggregate_utility,
            authority_rank=authority_rank,
            estimated_cost=round(total_cost, 2),
            chain_depth=chain_depth,
            success_evidence=round(aggregate_utility, 4),
            failure_penalty=round(decay_penalty, 4),
            explanation=explanations
        )

    def rank_candidate_chains(self, chains: List[List[Any]]) -> List[List[Any]]:
        """
        SCG3-09: Ranks candidate chains deterministically using:
        1. Authority Rank ascending (CANONICAL=0 before LEARNED=1)
        2. Utility Score descending
        3. Estimated Cost ascending
        4. Chain Depth ascending
        5. Deterministic chain repr string comparison
        """
        scored_chains = []
        for idx, chain in enumerate(chains):
            score = self.evaluate_chain(chain, candidate_id=f"cand-{idx}")
            scored_chains.append((score, chain))

        scored_chains.sort(
            key=lambda item: (
                item[0].authority_rank,
                -item[0].utility_score,
                item[0].estimated_cost,
                item[0].chain_depth,
                [getattr(n, "method_id", str(n)) for n in item[1]]
            )
        )

        return [item[1] for item in scored_chains]
