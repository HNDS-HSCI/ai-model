"""Application-level cognitive pipeline facade (Sprint VS-1).

`CognitivePipeline` is an ASSEMBLY facade. It wires the already-implemented,
already-tested V4 cognitive engines into one callable path so a real end-to-end
conceptual slice can run:

    User Question
        -> UnderstandingEngine        (intent + seed concepts)
        -> ConceptActivationEngine    (spreading activation over the UKM)
        -> cognitive workspace        (resolved List[Concept]; no new subsystem)
        -> CognitiveReasoningEngine   (rule-based inference over the workspace)
        -> AnswerGenerationEngine     (structured, explainable Answer)

The facade does NOT reimplement any engine logic, does NOT modify the SCG-L5
authority infrastructure, and does NOT introduce a formal Z3 verification step for
the conceptual path (see ``KNOWN LIMITATIONS`` below). It only orchestrates existing
public APIs.

NOTE ON VERIFICATION: The conceptual explanation path currently has NO formal Z3
arbitration. `CognitiveReasoningEngine` performs deterministic rule-based inference
with internal consistency checks (circular-reasoning and contradiction detection)
only. Whether canonical conceptual knowledge should undergo Z3 arbitration is a
deferred architectural decision and is intentionally out of scope for VS-1. This
facade never claims Z3 verification for conceptual answers.
"""
import logging
import os
import uuid
from typing import Optional

import logging
import os
import time
import uuid
from typing import Optional

from hsci.core.kernel import CognitiveContext, EventBus, ValidationError
from hsci.knowledge.understanding_engine import UnderstandingEngine, UnderstandingResult
from hsci.knowledge.concept_activation import ConceptActivationEngine
from hsci.knowledge.knowledge_manager import IKnowledgeManager
from hsci.reasoning.reasoning_engine import CognitiveReasoningEngine, ReasoningContext
from hsci.response.answer_generation_engine import (
    Answer, AnswerSection, ConfidenceSummary, AnswerMetadata, Explanation, AnswerGenerationEngine,
)
from hsci.response.explanatory_synthesizer import ExplanatoryAnswerSynthesizer, ExplanatoryAnswer
from hsci.cognition.interpretation.models import (
    RawInput, GroundingStatus, SituationStatus, TaskAction, CognitiveSituation, CognitiveTask,
)
from hsci.cognition.interpretation.interpreter import LanguageInterpreter
from hsci.cognition.interpretation.interpreter import LanguageInterpreter
from hsci.cognition.interpretation.grounding import GroundingEngine
from hsci.cognition.interpretation.task_deriver import TaskDeriver
from hsci.cognition.execution.task_executor import CognitiveTaskExecutor

from hsci.cognition.workspace import CognitiveWorkspace

logger = logging.getLogger("HSCI.Core.CognitivePipeline")


class CognitivePipeline:
    """Callable facade assembling the V4 cognitive engines with VS-6 interpretation and VS-7 workspace.

    Flow:
        Raw User Input
            -> LanguageInterpreter      (Generates candidate hypotheses & semantic frames)
            -> GroundingEngine          (UKM validation, entity resolution, ambiguity detection)
            -> CognitiveSituation       (Accepted grounded situational state)
            -> TaskDeriver              (Constructs executable CognitiveTask hierarchy)
            -> CognitiveWorkspace       (Initializes task graph, grounded entities, constraints)
            -> TaskGraph Execution      (Executes task DAG, manages dependencies & results)
            -> ExplanatoryAnswer / API
    """

    def __init__(self, manager: IKnowledgeManager, event_bus: EventBus):
        self.manager: IKnowledgeManager = manager
        self.event_bus: EventBus = event_bus

        # Interpretation and Task Derivation Layer (VS-4 / VS-6)
        self.interpreter = LanguageInterpreter(enable_llm=False)
        self.grounding_engine = GroundingEngine(manager)
        self.task_deriver = TaskDeriver()

        # Core Engines
        self.understanding_engine = UnderstandingEngine(manager)
        self.activation_engine = ConceptActivationEngine(manager, event_bus)
        self.reasoning_engine = CognitiveReasoningEngine(manager, event_bus)
        self.answer_engine = AnswerGenerationEngine(event_bus)
        self.synthesizer = ExplanatoryAnswerSynthesizer(manager, event_bus)

        # Task Execution Layer (VS-5 / VS-7)
        self.task_executor = CognitiveTaskExecutor(
            manager=manager,
            activation_engine=self.activation_engine,
            reasoning_engine=self.reasoning_engine,
            answer_engine=self.answer_engine,
            synthesizer=self.synthesizer,
            event_bus=event_bus,
        )

    def answer(self, question: str, style: str = "Standard") -> Answer:
        """Runs the full grounded cognitive interpretation and workspace execution slice."""
        if question is None or not str(question).strip():
            raise ValidationError("Question must be a non-empty string.")

        request_id = str(uuid.uuid4())

        with CognitiveContext(
            request_id=request_id,
            session_id="vs7-cognitive-pipeline",
            stimulus=question,
        ) as context:
            # 1. Understanding & Raw Input Preservation
            understanding = self.understanding_engine.understand(question, context)
            raw_input = RawInput.from_text(question, context={})

            # 2. Language Interpretation
            interpretation_set = self.interpreter.interpret(raw_input)

            # 3. Grounding against authoritative UKM
            situation = self.grounding_engine.ground(interpretation_set)

            # 4. Deterministic Task Derivation
            task = self.task_deriver.derive(situation)
            logger.info(
                "[%s] Situation status=%s, Task action=%s, Primary=%s",
                request_id, situation.status.value, task.action.value, task.primary_target,
            )

            # 5. Cognitive Workspace Initialization & Task Graph Construction (VS-7)
            workspace = CognitiveWorkspace(request_id=request_id, session_id=context.session_id)
            workspace.initialize_from_situation(situation)

            # 6. Execute Task Graph over Cognitive Workspace
            answer = workspace.execute(
                executor=self.task_executor,
                situation=situation,
                context=context,
                style=style,
                activation_engine=self.activation_engine,
                reasoning_engine=self.reasoning_engine,
                answer_engine=self.answer_engine,
                synthesizer=self.synthesizer,
            )

            # Preserve situational provenance and workspace on Answer
            setattr(answer, "cognitive_situation", situation)
            setattr(answer, "cognitive_task", task)
            setattr(answer, "workspace", workspace)
            return answer


def _default_migrations_dir() -> str:
    """Locates the UKM migrations directory bundled under hsci/core/migrations."""
    return os.path.join(os.path.dirname(__file__), "migrations")


def bootstrap_cognitive_pipeline(
    db_path: str = ":memory:",
    seed: bool = True,
) -> CognitivePipeline:
    """Builds a ready-to-use `CognitivePipeline` over a fresh UKM instance.

    Reuses the standard UKM bootstrap pattern (SQLiteProvider + SchemaMigration +
    KnowledgeManager) — the same sequence used by the existing demos — and
    optionally applies the canonical OOP knowledge seed.

    The returned pipeline exposes ``.provider`` so callers can close the storage
    provider when finished (important for file-backed databases).

    Args:
        db_path: SQLite path. Defaults to an in-memory database.
        seed: When True, applies the canonical OOP concept seed.
    """
    # Imported here to keep module import light and avoid a heavy import graph for
    # callers that inject their own manager.
    from hsci.core.storage import SQLiteProvider, SchemaMigration
    from hsci.knowledge.concept_repository import ConceptRepository
    from hsci.knowledge.concept_store import ConceptStore
    from hsci.knowledge.knowledge_cache import InMemoryKnowledgeCache
    from hsci.knowledge.knowledge_manager import KnowledgeManager
    from hsci.knowledge.seeds.oop_concepts import seed_oop_concepts
    from hsci.knowledge.seeds.science_concepts import seed_science_concepts

    provider = SQLiteProvider(db_path=db_path)
    provider.initialize()

    migration = SchemaMigration(provider)
    migration.run_directory_migrations(_default_migrations_dir())

    repository = ConceptRepository(provider)
    event_bus = EventBus()
    store = ConceptStore(repository, event_bus)
    cache = InMemoryKnowledgeCache()
    manager = KnowledgeManager(store, cache, event_bus)

    if seed:
        seed_oop_concepts(manager)
        seed_science_concepts(manager)

    pipeline = CognitivePipeline(manager, event_bus)
    # Expose the provider for lifecycle management (close on shutdown).
    pipeline.provider = provider  # type: ignore[attr-defined]
    return pipeline
