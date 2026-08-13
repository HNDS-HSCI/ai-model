import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class BenchmarkTaskItem:
    id: str
    input_text: str
    ground_truth: str
    expected_verified: bool
    expected_success: bool
    context: Optional[Dict[str, Any]] = None
    task_type: str = "general"


class DatasetLoader:
    """
    RBF-2 Dataset Loader for loading task items from JSON datasets.
    """

    @staticmethod
    def load_dataset(file_path: str) -> List[BenchmarkTaskItem]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = []
        for d in data.get("items", []):
            items.append(BenchmarkTaskItem(
                id=d["id"],
                input_text=d["input_text"],
                ground_truth=d.get("ground_truth", ""),
                expected_verified=d.get("expected_verified", True),
                expected_success=d.get("expected_success", True),
                context=d.get("context"),
                task_type=d.get("task_type", "general")
            ))
        return items
