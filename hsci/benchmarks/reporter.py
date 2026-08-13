import json
import csv
from pathlib import Path
from typing import Dict, Any, List
from hsci.benchmarks.collector import ResultsCollector


class BenchmarkReporter:
    """
    RBF-2 Results Exporter & Reporter Module.
    Exports JSON, CSV, and Markdown summaries of benchmark runs.
    """

    @staticmethod
    def export_json(collector: ResultsCollector, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(collector.to_dict(), f, indent=2)

    @staticmethod
    def export_csv(collector: ResultsCollector, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not collector.raw_results:
            return
        fieldnames = list(collector.raw_results[0].__dict__.keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in collector.raw_results:
                writer.writerow(r.__dict__)

    @staticmethod
    def export_markdown_summary(collectors: List[ResultsCollector], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# HSCI RBF-2 Benchmark Execution Summary",
            "",
            "| Benchmark Suite | Total Runs | PSR | VP | FAR | Mean PT (ms) | 95% CI PT (ms) | Mean ESN | Reachability | LRR | TAP |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        ]
        for c in collectors:
            m = c.aggregate_metrics
            if not m:
                continue
            ci_str = f"[{m.ci95_planning_time_ms[0]:.2f}, {m.ci95_planning_time_ms[1]:.2f}]"
            lines.append(
                f"| **{c.suite_name}** | {m.total_runs} | {m.planning_success_rate:.2f} | {m.verification_precision:.2f} | "
                f"{m.false_acceptance_rate:.2f} | {m.mean_planning_time_ms:.2f} | {ci_str} | "
                f"{m.mean_expanded_search_nodes:.1f} | {m.graph_reachability:.2f} | {m.lifecycle_recovery_rate:.2f} | "
                f"{m.telemetry_attribution_parity:.2f} |"
            )

        lines.append("")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
