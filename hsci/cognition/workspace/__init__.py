"""HSCI Cognition Workspace Package (Sprint VS-7)."""
from hsci.cognition.workspace.task_result import TaskResult, TaskResultType
from hsci.cognition.workspace.task_graph import (
    CognitiveTaskGraph,
    GraphTask,
    TaskStatus,
    CycleDetectedError,
    DuplicateTaskError,
    InvalidDependencyError,
)
from hsci.cognition.workspace.decomposer import TaskDecomposer
from hsci.cognition.workspace.workspace import (
    CognitiveWorkspace,
    WorkspaceStatus,
    WorkspaceMetadata,
)

__all__ = [
    "TaskResult",
    "TaskResultType",
    "CognitiveTaskGraph",
    "GraphTask",
    "TaskStatus",
    "CycleDetectedError",
    "DuplicateTaskError",
    "InvalidDependencyError",
    "TaskDecomposer",
    "CognitiveWorkspace",
    "WorkspaceStatus",
    "WorkspaceMetadata",
]
