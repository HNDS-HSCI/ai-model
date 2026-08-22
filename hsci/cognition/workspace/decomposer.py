"""Task Decomposer for HSCI VS-7.

Deterministically transforms grounded CognitiveSituations and SemanticRequests
into a structured CognitiveTaskGraph with explicit dependency edges.
"""
import re
import logging
from typing import Optional, List, Dict, Any
import uuid

from hsci.cognition.interpretation.models import (
    CognitiveSituation,
    SituationStatus,
    TaskAction,
    GroundingStatus,
    CognitiveTask,
)
from hsci.cognition.interpretation.semantic_model import (
    SemanticRequest,
    CommunicativeGoal,
)
from hsci.cognition.workspace.task_graph import (
    CognitiveTaskGraph,
    GraphTask,
    TaskStatus,
)

logger = logging.getLogger("HSCI.Cognition.Workspace.Decomposer")


class TaskDecomposer:
    """Constructs a deterministic CognitiveTaskGraph from a CognitiveSituation."""

    def decompose(self, situation: CognitiveSituation) -> CognitiveTaskGraph:
        """Constructs an executable task graph for the situation."""
        graph = CognitiveTaskGraph()

        # 1. Handle non-grounded / Refusal situations
        if situation.status == SituationStatus.INSUFFICIENT_CONTEXT:
            task = GraphTask(
                id=f"task_refusal_{uuid.uuid4().hex[:8]}",
                action=TaskAction.REPORT_INSUFFICIENT_CONTEXT,
                parameters={
                    "reason": "Input requires conversational antecedent context that is unavailable.",
                    "assumptions": [a.statement for a in situation.assumptions],
                },
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        if situation.status == SituationStatus.AMBIGUOUS:
            task = GraphTask(
                id=f"task_ambiguity_{uuid.uuid4().hex[:8]}",
                action=TaskAction.REPORT_AMBIGUITY,
                parameters={
                    "ambiguities": situation.ambiguities,
                    "grounded_entities": [ge.to_dict() for ge in situation.grounded_entities if ge.status == GroundingStatus.AMBIGUOUS],
                },
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        if situation.status == SituationStatus.UNRESOLVED_ENTITIES:
            task = GraphTask(
                id=f"task_unknown_{uuid.uuid4().hex[:8]}",
                action=TaskAction.REPORT_UNKNOWN,
                parameters={
                    "unresolved_entities": situation.unresolved_entities,
                    "required_knowledge": situation.required_knowledge,
                },
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        # 2. Fully Grounded Situations
        goal = getattr(getattr(situation, "semantic_request", None), "goal", None)
        if goal == CommunicativeGoal.SOLVE_MATH or situation.intent == "SolveMathematics":
            task = GraphTask(
                id=f"task_math_{uuid.uuid4().hex[:8]}",
                action=TaskAction.SOLVE_MATHEMATICS,
                primary_target="Mathematics",
                parameters={"raw_text": situation.raw_input.original_text},
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        if goal == CommunicativeGoal.GENERAL or situation.intent == "AnswerGeneral":
            task = GraphTask(
                id=f"task_general_{uuid.uuid4().hex[:8]}",
                action=TaskAction.ANSWER_GENERAL,
                primary_target="GeneralOverview",
                parameters={"raw_text": situation.raw_input.original_text},
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        resolved_entities = [ge for ge in situation.grounded_entities if ge.status == GroundingStatus.RESOLVED]
        if not resolved_entities:
            task = GraphTask(
                id=f"task_unknown_{uuid.uuid4().hex[:8]}",
                action=TaskAction.REPORT_UNKNOWN,
                parameters={"reason": "No grounded concepts available for task execution."},
                status=TaskStatus.READY,
            )
            graph.add_task(task)
            return graph

        primary_target = resolved_entities[0].canonical_name
        secondary_targets = [re.canonical_name for re in resolved_entities[1:]]
        raw_text = situation.raw_input.original_text

        # Check for multi-intent compound requests (e.g. "Explain X, compare it with Y, and relate X to Z")
        is_compound = bool(re.search(r"\b(and\s+compare|and\s+relate|compare\s+.+and\s+tell\s+me|compare\s+.+and\s+explain)\b", raw_text, re.IGNORECASE))
        has_rel_clause = bool(re.search(r"\b(?:relat\w*|connection|how\s+it\s+relates)\b", raw_text, re.IGNORECASE))

        if is_compound and len(resolved_entities) >= 2:
            # Multi-Task Decomposition
            t1_id = f"task_explain_{uuid.uuid4().hex[:8]}"
            t1 = GraphTask(
                id=t1_id,
                action=TaskAction.EXPLAIN_CONCEPT,
                primary_target=primary_target,
                parameters={"concept_id": resolved_entities[0].concept_id},
                dependencies=[],
                status=TaskStatus.READY,
            )
            graph.add_task(t1)

            t2_id = f"task_compare_{uuid.uuid4().hex[:8]}"
            t2 = GraphTask(
                id=t2_id,
                action=TaskAction.COMPARE_CONCEPTS,
                primary_target=primary_target,
                secondary_targets=[resolved_entities[1].canonical_name],
                parameters={
                    "concept_ids": [resolved_entities[0].concept_id, resolved_entities[1].concept_id],
                    "comparison_pairs": [(resolved_entities[0].concept_id, resolved_entities[1].concept_id)],
                },
                dependencies=[],  # Independent comparison task
                status=TaskStatus.READY,
            )
            graph.add_task(t2)

            if has_rel_clause and len(resolved_entities) >= 3:
                t3_id = f"task_relate_{uuid.uuid4().hex[:8]}"
                t3 = GraphTask(
                    id=t3_id,
                    action=TaskAction.DERIVE_RELATIONSHIP,
                    primary_target=primary_target,
                    secondary_targets=[resolved_entities[2].canonical_name],
                    parameters={
                        "concept_ids": [resolved_entities[0].concept_id, resolved_entities[2].concept_id],
                        "source_concept": primary_target,
                        "target_concept": resolved_entities[2].canonical_name,
                    },
                    dependencies=[t1_id],  # Dependent on initial concept definition
                    status=TaskStatus.PENDING,
                )
                graph.add_task(t3)

            return graph

        # 3. Single-Goal Graph Construction
        goal = getattr(getattr(situation, "semantic_request", None), "goal", None)
        is_compare = (goal == CommunicativeGoal.COMPARE) or (situation.intent == "CompareConcepts")
        is_relate = (goal == CommunicativeGoal.RELATE) or (situation.intent == "FindRelationship")

        if is_compare and len(resolved_entities) >= 2:
            t = GraphTask(
                id=f"task_compare_{uuid.uuid4().hex[:8]}",
                action=TaskAction.COMPARE_CONCEPTS,
                primary_target=primary_target,
                secondary_targets=secondary_targets,
                parameters={
                    "concept_ids": [re.concept_id for re in resolved_entities],
                    "comparison_pairs": [(resolved_entities[0].concept_id, resolved_entities[1].concept_id)],
                },
                dependencies=[],
                status=TaskStatus.READY,
            )
            graph.add_task(t)
            return graph

        if is_relate and len(resolved_entities) >= 2:
            t = GraphTask(
                id=f"task_relate_{uuid.uuid4().hex[:8]}",
                action=TaskAction.DERIVE_RELATIONSHIP,
                primary_target=primary_target,
                secondary_targets=secondary_targets,
                parameters={
                    "concept_ids": [re.concept_id for re in resolved_entities],
                    "source_concept": primary_target,
                    "target_concept": resolved_entities[1].canonical_name,
                },
                dependencies=[],
                status=TaskStatus.READY,
            )
            graph.add_task(t)
            return graph

        # Default Single-Concept Explanation
        t = GraphTask(
            id=f"task_explain_{uuid.uuid4().hex[:8]}",
            action=TaskAction.EXPLAIN_CONCEPT,
            primary_target=primary_target,
            secondary_targets=secondary_targets,
            parameters={
                "concept_id": resolved_entities[0].concept_id,
                "all_concept_ids": [re.concept_id for re in resolved_entities],
            },
            dependencies=[],
            status=TaskStatus.READY,
        )
        graph.add_task(t)
        return graph
