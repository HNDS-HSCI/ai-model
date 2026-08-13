import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from hsci.benchmarks.metrics import BenchmarkRunResult, SuiteAggregateMetrics


class ResultsCollector:
    """
    RBF-2 Results Collector Module.
    Accumulates raw test execution results and aggregate suite metrics.
    """

    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.raw_results: List[BenchmarkRunResult] = []
        self.aggregate_metrics: Optional[SuiteAggregateMetrics] = None

    def add_result(self, result: BenchmarkRunResult) -> None:
        self.raw_results.append(result)

    def set_aggregate(self, metrics: SuiteAggregateMetrics) -> None:
        self.aggregate_metrics = metrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "aggregate": self.aggregate_metrics.__dict__ if self.aggregate_metrics else {},
            "results": [r.__dict__ for r in self.raw_results]
        }
