"""Task Deriver for HSCI VS-4.

Deterministically derives structured CognitiveTasks from grounded CognitiveSituations.
Does NOT answer queries; specifies WHAT cognitive execution operations need to be performed.
"""
import logging
from typing import Optional

from hsci.cognition.interpretation.models import (
    CognitiveSituation,
    SituationStatus,
    CognitiveTask,
    TaskAction,
    GroundingStatus,
)

logger = logging.getLogger("HSCI.Cognition.Interpretation.TaskDeriver")


class TaskDeriver:
    """Deterministic task constructor mapping CognitiveSituation to CognitiveTask."""

    def derive(self, situation: CognitiveSituation) -> CognitiveTask:
        """Derives an executable CognitiveTask from the grounded situation."""
        # 1. Handle explicit non-grounded / failure states first
        if situation.status == SituationStatus.INSUFFICIENT_CONTEXT:
            return CognitiveTask(
                action=TaskAction.REPORT_INSUFFICIENT_CONTEXT,
                parameters={
                    "reason": "Input requires conversational antecedent context that is unavailable.",
                    "assumptions": [a.statement for a in situation.assumptions],
                },
                situation_id=situation.id,
            )

        if situation.status == SituationStatus.AMBIGUOUS:
            return CognitiveTask(
                action=TaskAction.REPORT_AMBIGUITY,
                parameters={
                    "ambiguities": situation.ambiguities,
                    "grounded_entities": [ge.to_dict() for ge in situation.grounded_entities if ge.status == GroundingStatus.AMBIGUOUS],
                },
                situation_id=situation.id,
            )

        if situation.status == SituationStatus.UNRESOLVED_ENTITIES:
            return CognitiveTask(
                action=TaskAction.REPORT_UNKNOWN,
                parameters={
                    "unresolved_entities": situation.unresolved_entities,
                    "required_knowledge": situation.required_knowledge,
                },
                situation_id=situation.id,
            )

        # 2. Derive task for fully grounded situations
        resolved_entities = [ge for ge in situation.grounded_entities if ge.status == GroundingStatus.RESOLVED]
        if not resolved_entities:
            return CognitiveTask(
                action=TaskAction.REPORT_UNKNOWN,
                parameters={"reason": "No grounded concepts available for task execution."},
                situation_id=situation.id,
            )

        primary_target = resolved_entities[0].canonical_name
        secondary_targets = [re.canonical_name for re in resolved_entities[1:]]

        # Check semantic goal or legacy intent string
        from hsci.cognition.interpretation.semantic_model import CommunicativeGoal
        goal = getattr(getattr(situation, "semantic_request", None), "goal", None)

        # Mathematical Solving Task
        if goal == CommunicativeGoal.SOLVE_MATH or situation.intent == "SolveMathematics":
            return CognitiveTask(
                action=TaskAction.SOLVE_MATHEMATICS,
                primary_target="Mathematics",
                parameters={"raw_text": situation.raw_input.original_text},
                situation_id=situation.id,
            )

        # General System Overview Task
        if goal == CommunicativeGoal.GENERAL or situation.intent == "AnswerGeneral":
            return CognitiveTask(
                action=TaskAction.ANSWER_GENERAL,
                primary_target="GeneralOverview",
                parameters={"raw_text": situation.raw_input.original_text},
                situation_id=situation.id,
            )

        is_compare = (goal == CommunicativeGoal.COMPARE) or (situation.intent == "CompareConcepts")
        is_relate = (goal == CommunicativeGoal.RELATE) or (situation.intent == "FindRelationship")

        # Multi-target Comparison Task
        if is_compare and len(resolved_entities) >= 2:
            return CognitiveTask(
                action=TaskAction.COMPARE_CONCEPTS,
                primary_target=primary_target,
                secondary_targets=secondary_targets,
                parameters={
                    "concept_ids": [re.concept_id for re in resolved_entities],
                    "comparison_pairs": [(resolved_entities[0].concept_id, resolved_entities[1].concept_id)],
                },
                situation_id=situation.id,
                subtasks=[
                    CognitiveTask(action=TaskAction.RETRIEVE_KNOWLEDGE, primary_target=re.canonical_name, parameters={"concept_id": re.concept_id})
                    for re in resolved_entities
                ]
            )

        # Multi-target Relationship / Derivation Task
        if is_relate and len(resolved_entities) >= 2:
            return CognitiveTask(
                action=TaskAction.DERIVE_RELATIONSHIP,
                primary_target=primary_target,
                secondary_targets=secondary_targets,
                parameters={
                    "concept_ids": [re.concept_id for re in resolved_entities],
                    "source_concept": resolved_entities[0].canonical_name,
                    "target_concept": resolved_entities[1].canonical_name,
                },
                situation_id=situation.id,
            )

        # Default Single-Concept Explanation Task
        return CognitiveTask(
            action=TaskAction.EXPLAIN_CONCEPT,
            primary_target=primary_target,
            secondary_targets=secondary_targets,
            parameters={
                "concept_id": resolved_entities[0].concept_id,
                "all_concept_ids": [re.concept_id for re in resolved_entities],
            },
            situation_id=situation.id,
        )
