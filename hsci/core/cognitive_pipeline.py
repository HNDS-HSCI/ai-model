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

from hsci.core.kernel import CognitiveContext, EventBus, ValidationError
from hsci.knowledge.understanding_engine import UnderstandingEngine
from hsci.knowledge.concept_activation import ConceptActivationEngine
from hsci.knowledge.knowledge_manager import IKnowledgeManager
from hsci.reasoning.reasoning_engine import CognitiveReasoningEngine, ReasoningContext
from hsci.response.answer_generation_engine import AnswerGenerationEngine, Answer
from hsci.response.explanatory_synthesizer import ExplanatoryAnswerSynthesizer

logger = logging.getLogger("HSCI.Core.CognitivePipeline")


class CognitivePipeline:
    """Callable facade assembling the four V4 conceptual engines.

    Args:
        manager: An initialized `KnowledgeManager` (façade over the UKM).
        event_bus: The shared `EventBus` used by the underlying engines.

    The four engines are constructed once and reused across calls (they are
    stateless request-wise; all request-scoped state lives in the per-call
    `CognitiveContext.working_memory`).
    """

    def __init__(self, manager: IKnowledgeManager, event_bus: EventBus):
        self.manager: IKnowledgeManager = manager
        self.event_bus: EventBus = event_bus

        # Reuse existing engines — no logic is duplicated here.
        self.understanding_engine = UnderstandingEngine(manager)
        self.activation_engine = ConceptActivationEngine(manager, event_bus)
        self.reasoning_engine = CognitiveReasoningEngine(manager, event_bus)
        self.answer_engine = AnswerGenerationEngine(event_bus)
        # VS-2: definition-first explanatory synthesis, applied after answer generation.
        self.synthesizer = ExplanatoryAnswerSynthesizer(manager, event_bus)

    def answer(self, question: str, style: str = "Standard") -> Answer:
        """Runs the full conceptual slice and returns a structured `Answer`.

        Raises:
            ValidationError: If the question is empty or whitespace-only. This
                reuses the existing `hsci.core.kernel.ValidationError` — no new
                exception hierarchy is introduced.
        """
        if question is None or not str(question).strip():
            raise ValidationError("Question must be a non-empty string.")

        request_id = str(uuid.uuid4())
        # One ephemeral, request-scoped context flows through every stage so the
        # activation field written by the CAE is visible to the AGE metadata.
        with CognitiveContext(
            request_id=request_id,
            session_id="vs1-cognitive-pipeline",
            stimulus=question,
        ) as context:
            # Stage 1 — Understanding.
            understanding = self.understanding_engine.understand(question, context)
            logger.info(
                "[%s] Understanding intent=%s seeds=%s",
                request_id, understanding.intent, understanding.seed_concepts,
            )

            # Stage 3 — Concept Activation over the UKM (stage 2 knowledge
            # resolution happens inside understanding + activation via the manager).
            activated = self.activation_engine.activate_concepts(
                understanding.seed_concepts, context
            )

            # Stage 4 — Cognitive workspace: the resolved activated concepts.
            # VS-1 deliberately keeps this as a plain, type-safe List[Concept];
            # a dedicated workspace subsystem is out of scope.
            workspace_concepts = []
            activation_scores = {}
            for activated_concept in activated.concepts:
                resolved = self.manager.get_concept(activated_concept.concept.id)
                if resolved is not None:
                    workspace_concepts.append(resolved)
                    activation_scores[resolved.id] = activated_concept.score

            # Stage 5 — Cognitive reasoning over the workspace.
            reasoning_context = ReasoningContext(goal=f"Explain: {question}")
            reasoning_result = self.reasoning_engine.reason(
                workspace_concepts, context, reasoning_context
            )
            logger.info(
                "[%s] Reasoning produced %d conclusion(s)",
                request_id, len(reasoning_result.conclusions),
            )

            # Stage 6 — Answer generation from the REAL reasoning result.
            base_answer = self.answer_engine.generate(
                reasoning_result, context, style=style
            )

            # Stage 7 (VS-2) — Explanatory synthesis. For explanation intents this
            # composes a definition-first, traceable answer from the activated concept
            # knowledge + the real reasoning result. Non-explanation intents and
            # empty-knowledge cases return the base answer unchanged.
            answer = self.synthesizer.synthesize(
                understanding=understanding,
                workspace_concepts=workspace_concepts,
                activation_scores=activation_scores,
                reasoning_result=reasoning_result,
                base_answer=base_answer,
                context=context,
            )
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

    pipeline = CognitivePipeline(manager, event_bus)
    # Expose the provider for lifecycle management (close on shutdown).
    pipeline.provider = provider  # type: ignore[attr-defined]
    return pipeline
