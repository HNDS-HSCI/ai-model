"""Cognitive Workspace for HSCI VS-7.

Request-scoped ephemeral workspace that manages cognitive work lifecycle,
task graph execution, intermediate typed results, and context reference resolution.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
import logging
from typing import Dict, List, Optional, Any
import uuid

from hsci.core.kernel import CognitiveContext, EventBus
from hsci.response.answer_generation_engine import (
    Answer,
    AnswerSection,
    ConfidenceSummary,
    AnswerMetadata,
    Explanation,
)
from hsci.response.explanatory_synthesizer import (
    ExplanatoryAnswer,
    KnowledgeSource,
)
from hsci.cognition.interpretation.models import (
    CognitiveSituation,
    SituationStatus,
    GroundedEntity,
    GroundingStatus,
    TaskAction,
    Evidence,
)
from hsci.cognition.interpretation.semantic_model import (
    SemanticRequest,
    SemanticConstraint,
    ContextReference,
)
from hsci.cognition.workspace.task_result import TaskResult, TaskResultType
from hsci.cognition.workspace.task_graph import (
    CognitiveTaskGraph,
    GraphTask,
    TaskStatus,
)
from hsci.cognition.workspace.decomposer import TaskDecomposer
from hsci.cognition.execution.task_executor import CognitiveTaskExecutor

logger = logging.getLogger("HSCI.Cognition.Workspace")


class WorkspaceStatus(str, Enum):
    """Lifecycle states of the CognitiveWorkspace."""
    CREATED = "CREATED"
    GROUNDED = "GROUNDED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    COMPLETED = "COMPLETED"
    REFUSED = "REFUSED"
    FAILED = "FAILED"


@dataclass
class WorkspaceMetadata:
    """Metadata tracking workspace creation, request identity, and status."""
    workspace_id: str
    request_id: str
    created_at: float = field(default_factory=time.time)
    status: WorkspaceStatus = WorkspaceStatus.CREATED
    session_id: Optional[str] = None


class CognitiveWorkspace:
    """Request-scoped ephemeral cognitive workspace."""

    def __init__(self, request_id: Optional[str] = None, session_id: Optional[str] = None):
        self.metadata = WorkspaceMetadata(
            workspace_id=str(uuid.uuid4()),
            request_id=request_id or str(uuid.uuid4()),
            session_id=session_id,
        )
        self.semantic_request: Optional[SemanticRequest] = None
        self.grounded_entities: Dict[str, GroundedEntity] = {}
        self.constraints: List[SemanticConstraint] = []
        self.context_references: List[ContextReference] = []
        self.task_graph: CognitiveTaskGraph = CognitiveTaskGraph()
        self.results: Dict[str, TaskResult] = {}
        self.session_context: Dict[str, Any] = {}
        self.decomposer: TaskDecomposer = TaskDecomposer()

    @property
    def status(self) -> WorkspaceStatus:
        return self.metadata.status

    @status.setter
    def status(self, val: WorkspaceStatus) -> None:
        self.metadata.status = val

    def attach_semantic_request(self, req: SemanticRequest) -> None:
        """Attaches validated semantic request to workspace."""
        self.semantic_request = req
        self.constraints = list(req.constraints)
        self.context_references = list(req.context_references)

    def attach_grounded_entities(self, entities: List[GroundedEntity]) -> None:
        """Stores grounded entities by mention key without duplicating UKM data."""
        for ge in entities:
            self.grounded_entities[ge.mention.lower()] = ge
        self.status = WorkspaceStatus.GROUNDED

    def resolve_context_reference(self, marker: str, antecedent: str) -> bool:
        """Resolves anaphoric/deictic pronoun reference with explicit antecedent evidence."""
        for cr in self.context_references:
            if cr.marker.lower() == marker.lower():
                cr.antecedent = antecedent
                cr.is_resolved = True
                self.session_context[marker.lower()] = antecedent
                return True
        return False

    def initialize_from_situation(self, situation: CognitiveSituation) -> None:
        """Initializes workspace state and constructs the task graph from a grounded situation."""
        if situation.semantic_request:
            self.attach_semantic_request(situation.semantic_request)
        self.attach_grounded_entities(situation.grounded_entities)

        # Build task graph
        self.task_graph = self.decomposer.decompose(situation)
        self.task_graph.validate()
        self.status = WorkspaceStatus.READY

    def execute(
        self,
        executor: CognitiveTaskExecutor,
        situation: CognitiveSituation,
        context: CognitiveContext,
        style: str = "Standard",
        activation_engine: Optional[Any] = None,
        reasoning_engine: Optional[Any] = None,
        answer_engine: Optional[Any] = None,
        synthesizer: Optional[Any] = None,
    ) -> Answer:
        """Executes the task graph deterministically and returns the aggregated Answer."""
        self.status = WorkspaceStatus.EXECUTING
        latest_answer: Optional[Answer] = None
        executed_answers: List[Answer] = []

        while not self.task_graph.is_terminal():
            ready_tasks = self.task_graph.get_ready_tasks()
            if not ready_tasks:
                # Deadlock / unmet dependencies
                self.status = WorkspaceStatus.PARTIALLY_COMPLETE
                break

            for g_task in ready_tasks:
                self.task_graph.mark_running(g_task.id)
                t_start = time.time()

                # Thread upstream task results into task parameters for genuine data flow
                upstream_results = {dep_id: self.results[dep_id].to_dict() for dep_id in g_task.dependencies if dep_id in self.results}
                g_task.parameters["upstream_results"] = upstream_results

                try:
                    c_task = g_task.to_cognitive_task()
                    c_task.parameters["upstream_results"] = upstream_results
                    ans = executor.execute(
                        task=c_task,
                        situation=situation,
                        context=context,
                        style=style,
                        activation_engine=activation_engine,
                        reasoning_engine=reasoning_engine,
                        answer_engine=answer_engine,
                        synthesizer=synthesizer,
                    )
                    duration_ms = (time.time() - t_start) * 1000
                    latest_answer = ans
                    executed_answers.append(ans)

                    # Inspect Answer to construct typed TaskResult
                    is_refusal = (
                        g_task.action in (
                            TaskAction.REPORT_INSUFFICIENT_CONTEXT,
                            TaskAction.REPORT_AMBIGUITY,
                            TaskAction.REPORT_UNKNOWN,
                        )
                        or (ans.confidence and ans.confidence.score == 0.0)
                    )
                    logger.info("Executed task '%s' (action=%s), is_refusal=%s, conf=%s", g_task.id, g_task.action.value, is_refusal, ans.confidence.score if ans.confidence else None)

                    result_type = (
                        TaskResultType.REFUSAL if is_refusal
                        else (
                            TaskResultType.COMPARISON if g_task.action == TaskAction.COMPARE_CONCEPTS
                            else (
                                TaskResultType.RELATIONSHIP_PROOF if g_task.action == TaskAction.DERIVE_RELATIONSHIP
                                else TaskResultType.DEFINITION
                            )
                        )
                    )

                    t_res = TaskResult(
                        task_id=g_task.id,
                        result_type=result_type,
                        payload={
                            "direct_answer": ans.direct_answer,
                            "primary_target": g_task.primary_target,
                            "sections": [asdict(s) if hasattr(s, "__dataclass_fields__") else (s if isinstance(s, dict) else str(s)) for s in ans.sections],
                        },
                        confidence=ans.confidence.score if ans.confidence else 1.0,
                        provenance="TASK_EXECUTION",
                        dependencies=list(g_task.dependencies),
                        duration_ms=duration_ms,
                    )

                    if is_refusal:
                        self.task_graph.mark_refused(g_task.id, t_res)
                        self.results[g_task.id] = t_res
                        self.status = WorkspaceStatus.REFUSED
                    else:
                        self.task_graph.mark_completed(g_task.id, t_res)
                        self.results[g_task.id] = t_res

                except Exception as exc:
                    logger.error("Task '%s' execution failed: %s", g_task.id, exc)
                    self.task_graph.mark_failed(g_task.id, str(exc))
                    self.status = WorkspaceStatus.FAILED

        # Final status check
        if self.task_graph.is_terminal():
            if all(t.status == TaskStatus.COMPLETED for t in self.task_graph.tasks.values()):
                self.status = WorkspaceStatus.COMPLETED
            elif any(t.status == TaskStatus.REFUSED for t in self.task_graph.tasks.values()):
                self.status = WorkspaceStatus.REFUSED
            elif any(t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED) for t in self.task_graph.tasks.values()):
                self.status = WorkspaceStatus.PARTIALLY_COMPLETE

        # If multiple tasks executed successfully, synthesize a composite answer
        if len(executed_answers) > 1 and all(t.status == TaskStatus.COMPLETED for t in self.task_graph.tasks.values()):
            composite_answer = self._synthesize_composite_answer(executed_answers, situation, context)
            return composite_answer

        return latest_answer or self._create_empty_answer(context)

    def _synthesize_composite_answer(
        self, answers: List[Answer], situation: CognitiveSituation, context: CognitiveContext
    ) -> ExplanatoryAnswer:
        """Combines multiple executed task answers into a single composite ExplanatoryAnswer."""
        combined_direct = "\n\n".join(ans.direct_answer for ans in answers if ans.direct_answer)
        combined_sections: List[AnswerSection] = []
        combined_sources: List[KnowledgeSource] = []
        min_conf = 1.0

        for ans in answers:
            if ans.confidence and ans.confidence.score < min_conf:
                min_conf = ans.confidence.score
            for sec in ans.sections:
                combined_sections.append(sec)
            if hasattr(ans, "sources") and isinstance(ans.sources, list):
                for src in ans.sources:
                    if src not in combined_sources:
                        combined_sources.append(src)

        composite = ExplanatoryAnswer(
            base=answers[0],
            direct_answer=combined_direct,
            sections=combined_sections,
            definition=getattr(answers[0], "definition", None),
            primary_concept_id=getattr(answers[0], "primary_concept_id", None),
            primary_concept_name=getattr(answers[0], "primary_concept_name", None),
            knowledge_sources=combined_sources,
            confidence=ConfidenceSummary(
                score=min_conf,
                description=f"Composite task execution across {len(self.task_graph.tasks)} subtasks",
            ),
        )
        setattr(composite, "cognitive_situation", situation)
        setattr(composite, "cognitive_task", list(self.task_graph.tasks.values())[0].to_cognitive_task())
        setattr(composite, "workspace", self)
        return composite

    def _create_empty_answer(self, context: CognitiveContext) -> Answer:
        """Fallback empty answer if no tasks executed."""
        return Answer(
            direct_answer="No cognitive tasks were executed.",
            sections=[],
            confidence=ConfidenceSummary(score=0.0, is_confident=False),
            metadata=AnswerMetadata(request_id=context.request_id, session_id=context.session_id, strategy_used="EmptyExecution"),
            explanation=Explanation(summary="Empty task graph execution.", reasoning_path="None"),
        )

    def dispose(self) -> None:
        """Cleans up internal collections for garbage collection."""
        self.grounded_entities.clear()
        self.constraints.clear()
        self.context_references.clear()
        self.results.clear()
        self.session_context.clear()
        self.task_graph.tasks.clear()
        self.task_graph.adjacency.clear()
        self.task_graph.reverse_adjacency.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": asdict(self.metadata),
            "semantic_request": self.semantic_request.to_dict() if self.semantic_request else None,
            "grounded_entities": {k: ge.to_dict() for k, ge in self.grounded_entities.items()},
            "constraints": [c.to_dict() for c in self.constraints],
            "context_references": [cr.to_dict() for cr in self.context_references],
            "task_graph": self.task_graph.to_dict(),
            "results": {k: r.to_dict() for k, r in self.results.items()},
        }
