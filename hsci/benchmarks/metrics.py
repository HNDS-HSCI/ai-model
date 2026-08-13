from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from hsci.benchmarks.statistics import BenchmarkStatistics


@dataclass
class BenchmarkRunResult:
    test_id: str
    success: bool
    is_verified: bool
    false_acceptance: bool
    planning_time_ms: float
    verification_latency_ms: float
    planner_latency_ms: float
    expanded_search_nodes: int
    graph_reachable: bool
    lifecycle_recovered: Optional[bool] = None
    telemetry_attributed: Optional[bool] = None
    plan_depth: int = 0
    graph_depth: int = 0
    candidate_count: int = 0


@dataclass
class SuiteAggregateMetrics:
    total_runs: int = 0
    planning_success_rate: float = 0.0
    verification_precision: float = 0.0
    false_acceptance_rate: float = 0.0
    mean_planning_time_ms: float = 0.0
    ci95_planning_time_ms: tuple = (0.0, 0.0)
    mean_verification_latency_ms: float = 0.0
    mean_planner_latency_ms: float = 0.0
    mean_expanded_search_nodes: float = 0.0
    graph_reachability: float = 0.0
    lifecycle_recovery_rate: float = 0.0
    telemetry_attribution_parity: float = 0.0
    mean_plan_depth: float = 0.0
    mean_graph_depth: float = 0.0
    mean_candidate_count: float = 0.0


class MetricsCalculator:
    """
    RBF-2 Quantitative Metrics Module.
    Calculates PSR, VP, FAR, PT, ESN, GR, LRR, TAP, Plan/Graph Depth, and Latency metrics.
    """

    @staticmethod
    def compute(results: List[BenchmarkRunResult]) -> SuiteAggregateMetrics:
        if not results:
            return SuiteAggregateMetrics()

        total = len(results)
        successes = sum(1 for r in results if r.success)
        verified_count = sum(1 for r in results if r.is_verified)
        false_acceptances = sum(1 for r in results if r.false_acceptance)

        tp = sum(1 for r in results if r.is_verified and r.success)
        fp = false_acceptances
        vp = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        far = false_acceptances / total

        pt_list = [r.planning_time_ms for r in results]
        ver_lat_list = [r.verification_latency_ms for r in results]
        plan_lat_list = [r.planner_latency_ms for r in results]
        esn_list = [float(r.expanded_search_nodes) for r in results]
        reach_count = sum(1 for r in results if r.graph_reachable)

        l_recovered_list = [r.lifecycle_recovered for r in results if r.lifecycle_recovered is not None]
        lrr = sum(1 for r in l_recovered_list if r) / len(l_recovered_list) if l_recovered_list else 1.0

        t_attr_list = [r.telemetry_attributed for r in results if r.telemetry_attributed is not None]
        tap = sum(1 for r in t_attr_list if r) / len(t_attr_list) if t_attr_list else 1.0

        p_depth_list = [float(r.plan_depth) for r in results]
        g_depth_list = [float(r.graph_depth) for r in results]
        cand_list = [float(r.candidate_count) for r in results]

        return SuiteAggregateMetrics(
            total_runs=total,
            planning_success_rate=successes / total,
            verification_precision=vp,
            false_acceptance_rate=far,
            mean_planning_time_ms=BenchmarkStatistics.mean(pt_list),
            ci95_planning_time_ms=BenchmarkStatistics.confidence_interval_95(pt_list),
            mean_verification_latency_ms=BenchmarkStatistics.mean(ver_lat_list),
            mean_planner_latency_ms=BenchmarkStatistics.mean(plan_lat_list),
            mean_expanded_search_nodes=BenchmarkStatistics.mean(esn_list),
            graph_reachability=reach_count / total,
            lifecycle_recovery_rate=lrr,
            telemetry_attribution_parity=tap,
            mean_plan_depth=BenchmarkStatistics.mean(p_depth_list),
            mean_graph_depth=BenchmarkStatistics.mean(g_depth_list),
            mean_candidate_count=BenchmarkStatistics.mean(cand_list)
        )
