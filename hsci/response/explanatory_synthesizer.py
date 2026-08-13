"""Explanatory Answer Synthesis (Sprint VS-2).

The VS-2 pre-flight found that the VS-1 pipeline retrieves and activates the correct
concept but drops the concept's stored definitional knowledge (`Concept.abstract_rule`)
before answer generation — so the answer lists graph edges instead of explaining the
concept.

This module closes that gap with a **thin, additive** synthesis step that runs AFTER
the existing `AnswerGenerationEngine`. It:

* takes the already-activated `Concept` objects, the real `ReasoningResult`, and the
  base `Answer` produced by `AnswerGenerationEngine`;
* for explanation/definition intents, composes a **definition-first** answer whose
  `direct_answer` is the primary concept's stored `abstract_rule` (retrieved verbatim),
  supported by the reasoner's relationship conclusions;
* records **traceability** distinguishing retrieved knowledge (the definition) from
  reasoned knowledge (the relationships).

Constraints honoured (VS-2):

* READ-ONLY — no writes to the UKM.
* DETERMINISTIC — no randomness, no LLM.
* TRACEABLE — every emitted statement records its source.
* SCG-L5-NEUTRAL — no change to reasoning, verification, HTN, lifecycle, or storage.
* No new storage engine, no direct SQLite, no per-question hardcoding, no Z3.

Honesty notes:

* The definition is presented as **retrieved** knowledge (`knowledge_type="definition"`),
  never as newly reasoned knowledge.
* The reasoning engine does not propagate its rule name onto `Conclusion`, so the
  supporting rule is inferred deterministically from the conclusion's fixed statement
  format (`_infer_reasoning_rule`). Evidence strings from the reasoner are preserved
  verbatim.
* Answer confidence is NOT inflated: when reasoning conclusions exist, the base answer's
  reasoning-derived confidence is preserved unchanged.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from hsci.core.data_types import Concept
from hsci.core.kernel import CognitiveContext, EventBus
from hsci.knowledge.knowledge_manager import IKnowledgeManager
from hsci.knowledge.understanding_engine import UnderstandingResult
from hsci.reasoning.reasoning_engine import ReasoningResult
from hsci.response.answer_generation_engine import (
    Answer, AnswerSection, ConfidenceSummary,
)

logger = logging.getLogger("HSCI.Response.ExplanatorySynthesis")

# Intents for which a definition-first explanation is appropriate. The Understanding
# Engine maps "what is / explain / describe / define" to this single intent.
EXPLANATION_INTENTS = frozenset({"ExplainConcept"})


@dataclass
class KnowledgeSource:
    """A single traceable provenance record backing part of the answer.

    ``knowledge_type`` is either ``"definition"`` (retrieved concept knowledge) or
    ``"reasoned_relationship"`` (produced by the ReasoningEngine).
    """
    knowledge_type: str
    # Retrieved-definition fields
    source_concept_id: Optional[str] = None
    source_concept_name: Optional[str] = None
    source_provenance: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    # Reasoned-relationship fields
    reasoning_conclusion: Optional[str] = None
    reasoning_rule: Optional[str] = None
    reasoning_confidence: Optional[float] = None
    reasoning_evidence: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExplanatoryAnswer(Answer):
    """An `Answer` enriched with a retrieved definition and traceability records.

    Subclasses `Answer` so it remains fully compatible with every existing consumer of
    the answer contract; it only adds fields.
    """

    def __init__(self, base: Answer, direct_answer: str, sections: List[AnswerSection],
                 definition: Optional[str], primary_concept_id: Optional[str],
                 primary_concept_name: Optional[str],
                 knowledge_sources: List[KnowledgeSource],
                 confidence: ConfidenceSummary):
        super().__init__(
            direct_answer=direct_answer,
            sections=sections,
            explanation=base.explanation,
            evidence=base.evidence,
            confidence=confidence,
            metadata=base.metadata,
            assumptions=base.assumptions,
            known_limitations=base.known_limitations,
        )
        self.definition: Optional[str] = definition
        self.primary_concept_id: Optional[str] = primary_concept_id
        self.primary_concept_name: Optional[str] = primary_concept_name
        self.knowledge_sources: List[KnowledgeSource] = knowledge_sources

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "definition": self.definition,
            "primary_concept_id": self.primary_concept_id,
            "primary_concept_name": self.primary_concept_name,
            "knowledge_sources": [ks.to_dict() for ks in self.knowledge_sources],
        })
        return data


class ExplanatoryAnswerSynthesizer:
    """Composes a definition-first, traceable answer from activated concept knowledge.

    Generic across any concept that carries an ``abstract_rule``. Contains no
    question-specific logic.
    """

    def __init__(self, manager: IKnowledgeManager, event_bus: Optional[EventBus] = None):
        self.manager: IKnowledgeManager = manager
        self.event_bus: Optional[EventBus] = event_bus

    def synthesize(self, understanding: UnderstandingResult,
                   workspace_concepts: List[Concept],
                   activation_scores: Dict[str, float],
                   reasoning_result: ReasoningResult,
                   base_answer: Answer,
                   context: CognitiveContext) -> Answer:
        """Returns an `ExplanatoryAnswer` for explanation intents, else the base answer.

        Falls back to the base answer (no fabrication) when the intent is not an
        explanation request or when no primary concept can be resolved.
        """
        if understanding.intent not in EXPLANATION_INTENTS:
            return base_answer

        primary = self._select_primary(workspace_concepts, activation_scores)
        if primary is None:
            # Empty / unknown knowledge: never fabricate a definition.
            return base_answer

        # Resolve the freshest concept state so answers track knowledge updates.
        latest = self.manager.get_concept(primary.id) or primary
        definition = (latest.abstract_rule or "").strip()

        knowledge_sources: List[KnowledgeSource] = []
        sections: List[AnswerSection] = []

        if definition:
            provenance = self._provenance(latest.id)
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="definition",
                source_concept_id=latest.id,
                source_concept_name=latest.name,
                source_provenance=provenance,
                content=definition,
            ))
            sections.append(AnswerSection("Definition", definition))
            direct_answer = definition
        else:
            # Known concept with no stored definition: do not invent one.
            direct_answer = base_answer.direct_answer

        rel_sources, rel_lines = self._relationship_sources(reasoning_result, latest)
        knowledge_sources.extend(rel_sources)
        if rel_lines:
            sections.append(AnswerSection("Supporting Relationships", "\n".join(rel_lines)))

        # If neither a definition nor any reasoned relationship is available, defer to
        # the existing graceful-degradation answer.
        if not definition and not rel_sources:
            return base_answer

        confidence = self._confidence(reasoning_result, base_answer,
                                      knowledge_sources, has_definition=bool(definition))

        if self.event_bus:
            self.event_bus.emit("ExplanatoryAnswerSynthesized", context)

        return ExplanatoryAnswer(
            base=base_answer,
            direct_answer=direct_answer,
            sections=sections,
            definition=definition or None,
            primary_concept_id=latest.id,
            primary_concept_name=latest.name,
            knowledge_sources=knowledge_sources,
            confidence=confidence,
        )

    # ── helpers ─────────────────────────────────────────────────────

    def _select_primary(self, workspace_concepts: List[Concept],
                        activation_scores: Dict[str, float]) -> Optional[Concept]:
        """Primary concept = highest-activation concept (the one the user asked about)."""
        if not workspace_concepts:
            return None
        return max(
            workspace_concepts,
            key=lambda c: activation_scores.get(c.id, 0.0),
        )

    def _relationship_sources(self, reasoning_result: ReasoningResult,
                              primary: Concept):
        """Builds traceable reasoned-relationship sources, primary-related first."""
        prim = primary.name.lower()
        ordered = sorted(
            reasoning_result.conclusions,
            key=lambda c: 0 if prim in c.statement.lower() else 1,
        )
        sources: List[KnowledgeSource] = []
        lines: List[str] = []
        for c in ordered:
            rule = self._infer_reasoning_rule(c.statement)
            sources.append(KnowledgeSource(
                knowledge_type="reasoned_relationship",
                reasoning_conclusion=c.statement,
                reasoning_rule=rule,
                reasoning_confidence=c.confidence,
                reasoning_evidence=list(c.evidence),
            ))
            lines.append(f"- {c.statement} (rule: {rule}, confidence: {c.confidence:.2f})")
        return sources, lines

    @staticmethod
    def _infer_reasoning_rule(statement: str) -> str:
        """Deterministically maps a conclusion's fixed statement format to its rule.

        The ReasoningEngine does not propagate the originating rule name onto
        `Conclusion`; the statement format is deterministic, so the rule is recovered
        from it. Evidence is preserved separately and verbatim.
        """
        lowered = statement.lower()
        if "generalizes to" in lowered:
            return "GeneralizationTransitivity"
        if "co-exist under namespace" in lowered:
            return "NamespaceCohabitation"
        if lowered.startswith("alias "):
            return "AliasMapping"
        return "RuleBasedInference"

    def _provenance(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the most recent provenance record via the ConceptStore (no SQLite)."""
        try:
            history = self.manager.concept_store.get_history(concept_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Provenance lookup failed for %s: %s", concept_id, exc)
            return None
        return history[0] if history else None

    def _confidence(self, reasoning_result: ReasoningResult, base_answer: Answer,
                    knowledge_sources: List[KnowledgeSource],
                    has_definition: bool) -> ConfidenceSummary:
        """Confidence policy: preserve reasoning confidence; never inflate.

        * When reasoning produced conclusions, the base answer's reasoning-derived
          confidence is preserved unchanged.
        * For a definition-only answer (no reasoning conclusions), the definition's own
          retrieval provenance confidence is used and is clearly a *retrieval*
          confidence, not a reasoning confidence.
        """
        if reasoning_result.conclusions:
            return base_answer.confidence

        prov_conf = 0.0
        if has_definition and knowledge_sources:
            prov = knowledge_sources[0].source_provenance or {}
            prov_conf = float(prov.get("confidence", 0.5))
        band = "High" if prov_conf >= 0.80 else "Medium" if prov_conf >= 0.50 else "Low"
        return ConfidenceSummary(prov_conf, band)
