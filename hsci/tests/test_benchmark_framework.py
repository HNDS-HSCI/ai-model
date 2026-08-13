import pytest
import math
from pathlib import Path
from hsci.benchmarks.statistics import BenchmarkStatistics
from hsci.benchmarks.metrics import BenchmarkRunResult, MetricsCalculator
from hsci.benchmarks.collector import ResultsCollector
from hsci.benchmarks.reporter import BenchmarkReporter
from hsci.benchmarks.runner import BenchmarkRunner


def test_rbf2_statistics_computation():
    data1 = [10.0, 12.0, 14.0, 16.0, 18.0]
    data2 = [20.0, 22.0, 24.0, 26.0, 28.0]

    assert BenchmarkStatistics.mean(data1) == 14.0
    assert BenchmarkStatistics.median(data1) == 14.0
    assert round(BenchmarkStatistics.std(data1), 2) == 3.16

    ci_low, ci_high = BenchmarkStatistics.confidence_interval_95(data1)
    assert ci_low < 14.0 < ci_high

    t_stat, p_val = BenchmarkStatistics.welch_t_test(data1, data2)
    assert t_stat < 0
    assert 0.0 <= p_val <= 1.0

    d = BenchmarkStatistics.cohens_d(data1, data2)
    assert d < 0


def test_rbf2_metrics_calculator():
    results = [
        BenchmarkRunResult(
            test_id="t1", success=True, is_verified=True, false_acceptance=False,
            planning_time_ms=10.0, verification_latency_ms=4.0, planner_latency_ms=5.0,
            expanded_search_nodes=2, graph_reachable=True, lifecycle_recovered=True, telemetry_attributed=True
        ),
        BenchmarkRunResult(
            test_id="t2", success=False, is_verified=False, false_acceptance=False,
            planning_time_ms=20.0, verification_latency_ms=2.0, planner_latency_ms=18.0,
            expanded_search_nodes=0, graph_reachable=False, lifecycle_recovered=None, telemetry_attributed=True
        )
    ]
    agg = MetricsCalculator.compute(results)

    assert agg.total_runs == 2
    assert agg.planning_success_rate == 0.5
    assert agg.verification_precision == 1.0
    assert agg.false_acceptance_rate == 0.0
    assert agg.mean_planning_time_ms == 15.0
    assert agg.graph_reachability == 0.5
    assert agg.telemetry_attribution_parity == 1.0


def test_rbf2_reporter_exporters(tmp_path):
    collector = ResultsCollector("test_suite")
    res = BenchmarkRunResult(
        test_id="t1", success=True, is_verified=True, false_acceptance=False,
        planning_time_ms=10.0, verification_latency_ms=4.0, planner_latency_ms=5.0,
        expanded_search_nodes=2, graph_reachable=True, lifecycle_recovered=True, telemetry_attributed=True
    )
    collector.add_result(res)
    collector.set_aggregate(MetricsCalculator.compute([res]))

    json_p = tmp_path / "out.json"
    csv_p = tmp_path / "out.csv"
    md_p = tmp_path / "out.md"

    BenchmarkReporter.export_json(collector, json_p)
    BenchmarkReporter.export_csv(collector, csv_p)
    BenchmarkReporter.export_markdown_summary([collector], md_p)

    assert json_p.exists()
    assert csv_p.exists()
    assert md_p.exists()


def test_rbf2_runner_deterministic_execution(tmp_path):
    manifest_path = "hsci/benchmarks/manifests/formal_logic.yaml"
    runner = BenchmarkRunner(manifest_path, output_dir=str(tmp_path))
    collector = runner.run()

    assert collector.suite_name == "formal_logic"
    assert len(collector.raw_results) > 0
    assert collector.aggregate_metrics is not None
    assert (tmp_path / "formal_logic_results.json").exists()
    assert (tmp_path / "formal_logic_results.csv").exists()
    assert (tmp_path / "formal_logic_summary.md").exists()
