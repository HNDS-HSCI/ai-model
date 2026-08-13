from pathlib import Path
from typing import List, Dict, Any
from hsci.benchmarks.collector import ResultsCollector


class PlotsGenerator:
    """
    RBF-2 Performance Dashboards & Plots Exporter Module.
    Generates text/Markdown visual dashboards for metrics comparison.
    """

    @staticmethod
    def generate_dashboard(collectors: List[ResultsCollector], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# RBF-2 Visual Performance Dashboard",
            "",
            "## Planning Success Rate (PSR) Dashboard",
            "```text"
        ]
        for c in collectors:
            m = c.aggregate_metrics
            if not m:
                continue
            bar_len = int(m.planning_success_rate * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            lines.append(f"{c.suite_name:<25} |{bar}| {m.planning_success_rate * 100:.1f}%")
        lines.append("```")

        lines.extend([
            "",
            "## Mean Planning Latency (ms) Dashboard",
            "```text"
        ])
        for c in collectors:
            m = c.aggregate_metrics
            if not m:
                continue
            bar_len = min(30, int(m.mean_planning_time_ms / 10))
            bar = "█" * bar_len
            lines.append(f"{c.suite_name:<25} |{bar} ({m.mean_planning_time_ms:.2f} ms)")
        lines.append("```")
        lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
