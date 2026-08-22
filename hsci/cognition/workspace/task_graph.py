"""Cognitive Task Graph for HSCI VS-7.

Defines a strict Directed Acyclic Graph (DAG) for cognitive task dependencies,
topological scheduling, cycle detection, and cascading failure/blocked states.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Set, Optional, Any
import logging

from hsci.cognition.interpretation.models import TaskAction, CognitiveTask
from hsci.cognition.workspace.task_result import TaskResult

logger = logging.getLogger("HSCI.Cognition.Workspace.TaskGraph")


class TaskStatus(str, Enum):
    """Lifecycle status of an individual task node in the graph."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    REFUSED = "REFUSED"


class CycleDetectedError(Exception):
    """Raised when a dependency cycle is detected in the CognitiveTaskGraph."""
    pass


class DuplicateTaskError(Exception):
    """Raised when attempting to add a task with an existing ID."""
    pass


class InvalidDependencyError(Exception):
    """Raised when a task depends on a non-existent task ID."""
    pass


@dataclass
class GraphTask:
    """A single executable node in the CognitiveTaskGraph."""
    id: str
    action: TaskAction
    primary_target: Optional[str] = None
    secondary_targets: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action.value,
            "primary_target": self.primary_target,
            "secondary_targets": self.secondary_targets,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "error_message": self.error_message,
        }

    def to_cognitive_task(self) -> CognitiveTask:
        """Converts GraphTask to standard CognitiveTask."""
        return CognitiveTask(
            id=self.id,
            action=self.action,
            primary_target=self.primary_target,
            secondary_targets=self.secondary_targets,
            parameters=self.parameters,
            dependencies=self.dependencies,
            status=self.status.value,
        )

    @classmethod
    def from_cognitive_task(cls, ct: CognitiveTask) -> "GraphTask":
        """Constructs GraphTask from a CognitiveTask instance."""
        return cls(
            id=ct.id,
            action=ct.action,
            primary_target=ct.primary_target,
            secondary_targets=ct.secondary_targets,
            parameters=ct.parameters,
            dependencies=getattr(ct, "dependencies", []),
            status=TaskStatus.PENDING if getattr(ct, "dependencies", []) else TaskStatus.READY,
        )


class CognitiveTaskGraph:
    """Manages task dependencies, cycle detection, and deterministic scheduling."""

    def __init__(self):
        self.tasks: Dict[str, GraphTask] = {}
        self.adjacency: Dict[str, List[str]] = {}  # upstream -> list of downstream tasks
        self.reverse_adjacency: Dict[str, List[str]] = {}  # downstream -> list of upstream tasks

    def add_task(self, task: GraphTask) -> None:
        """Adds a task to the graph with duplicate ID protection."""
        if task.id in self.tasks:
            raise DuplicateTaskError(f"Task with ID '{task.id}' already exists in graph.")
        self.tasks[task.id] = task
        self.adjacency.setdefault(task.id, [])
        self.reverse_adjacency.setdefault(task.id, [])

        for dep in task.dependencies:
            self.adjacency.setdefault(dep, []).append(task.id)
            self.reverse_adjacency[task.id].append(dep)

        # If task has no dependencies, mark as READY immediately
        if not task.dependencies and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.READY

    def validate(self) -> bool:
        """Validates graph consistency and verifies that graph is a strict DAG (no cycles)."""
        # 1. Check all dependencies exist
        for task_id, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    raise InvalidDependencyError(f"Task '{task_id}' depends on non-existent task '{dep}'.")

        # 2. Cycle detection via DFS (3-color tracking: 0=unvisited, 1=visiting, 2=visited)
        visited: Dict[str, int] = {tid: 0 for tid in self.tasks}

        def _dfs(node: str, path: List[str]) -> None:
            visited[node] = 1
            path.append(node)
            for neighbor in self.adjacency.get(node, []):
                if visited[neighbor] == 1:
                    cycle = " -> ".join(path + [neighbor])
                    raise CycleDetectedError(f"Dependency cycle detected in task graph: {cycle}")
                elif visited[neighbor] == 0:
                    _dfs(neighbor, path)
            visited[node] = 2
            path.pop()

        for tid in self.tasks:
            if visited[tid] == 0:
                _dfs(tid, [])

        return True

    def get_ready_tasks(self) -> List[GraphTask]:
        """Returns all tasks that are READY for execution in deterministic order."""
        ready: List[GraphTask] = []
        for task in self.tasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.READY):
                # Check if all upstream dependencies are COMPLETED
                deps_met = all(
                    self.tasks[dep].status == TaskStatus.COMPLETED
                    for dep in task.dependencies
                )
                if deps_met:
                    task.status = TaskStatus.READY
                    ready.append(task)
                else:
                    # If any dependency failed or was refused, block this task
                    any_dep_broken = any(
                        self.tasks[dep].status in (TaskStatus.FAILED, TaskStatus.REFUSED, TaskStatus.BLOCKED)
                        for dep in task.dependencies
                    )
                    if any_dep_broken:
                        task.status = TaskStatus.BLOCKED
        return ready

    def mark_running(self, task_id: str) -> None:
        """Marks a task as actively RUNNING."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.RUNNING

    def mark_completed(self, task_id: str, result: TaskResult) -> None:
        """Marks a task as COMPLETED and evaluates downstream dependents."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.result = result

            # Update status of downstream tasks
            for child_id in self.adjacency.get(task_id, []):
                child = self.tasks[child_id]
                if child.status == TaskStatus.PENDING:
                    if all(self.tasks[d].status == TaskStatus.COMPLETED for d in child.dependencies):
                        child.status = TaskStatus.READY

    def mark_failed(self, task_id: str, error_message: str) -> None:
        """Marks a task as FAILED and cascades BLOCKED to all downstream tasks."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            self._cascade_blocked(task_id)

    def mark_refused(self, task_id: str, refusal_result: TaskResult) -> None:
        """Marks a task as REFUSED and cascades BLOCKED to downstream tasks."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.REFUSED
            task.result = refusal_result
            self._cascade_blocked(task_id)

    def _cascade_blocked(self, upstream_id: str) -> None:
        """Recursively marks all downstream dependent tasks as BLOCKED."""
        for child_id in self.adjacency.get(upstream_id, []):
            child = self.tasks[child_id]
            if child.status in (TaskStatus.PENDING, TaskStatus.READY):
                child.status = TaskStatus.BLOCKED
                child.error_message = f"Blocked by dependency '{upstream_id}'."
                self._cascade_blocked(child_id)

    def is_terminal(self) -> bool:
        """Returns True if all tasks in the graph have reached a terminal state."""
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.FAILED, TaskStatus.REFUSED}
        return all(t.status in terminal_states for t in self.tasks.values())

    def topological_sort(self) -> List[GraphTask]:
        """Returns tasks in deterministic topological order."""
        self.validate()
        in_degree = {tid: len(task.dependencies) for tid, task in self.tasks.items()}
        zero_in_degree = [tid for tid, deg in in_degree.items() if deg == 0]
        zero_in_degree.sort()  # Deterministic tie-breaking

        result: List[GraphTask] = []
        while zero_in_degree:
            curr = zero_in_degree.pop(0)
            result.append(self.tasks[curr])
            for neighbor in sorted(self.adjacency.get(curr, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    zero_in_degree.append(neighbor)
                    zero_in_degree.sort()

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "is_terminal": self.is_terminal(),
        }
