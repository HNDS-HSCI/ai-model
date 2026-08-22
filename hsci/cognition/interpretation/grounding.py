"""Grounding Engine for HSCI VS-4.

Validates candidate linguistic hypotheses against the Universal Knowledge Model (UKM)
via the IKnowledgeManager facade without accessing SQLite directly.
Distinguishes RESOLVED, AMBIGUOUS, and UNKNOWN entities without silently picking first matches.
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from hsci.cognition.interpretation.models import (
    RawInput,
    InterpretationSet,
    CandidateInterpretation,
    GroundedEntity,
    GroundingStatus,
    CognitiveSituation,
    SituationStatus,
    Evidence,
    InterpretationAssumption,
)
from hsci.knowledge.knowledge_manager import IKnowledgeManager
from hsci.core.data_types import Concept

logger = logging.getLogger("HSCI.Cognition.Interpretation.Grounding")


class GroundingEngine:
    """Evaluates candidate interpretations against authoritative UKM concepts."""

    def __init__(self, manager: IKnowledgeManager):
        self.manager: IKnowledgeManager = manager

    def ground(self, interpretation_set: InterpretationSet) -> CognitiveSituation:
        """Grounds an InterpretationSet against the UKM and produces an accepted CognitiveSituation."""
        raw_input = interpretation_set.raw_input
        candidates = interpretation_set.candidates

        if not candidates:
            return CognitiveSituation(
                raw_input=raw_input,
                status=SituationStatus.UNRESOLVED_ENTITIES,
                interpretation_confidence=0.0,
                grounding_confidence=0.0,
                unresolved_entities=["<no_interpretation_candidates>"],
            )

        # Evaluate candidate interpretations in order of interpretation confidence
        best_candidate: Optional[CandidateInterpretation] = None
        best_grounded_entities: List[GroundedEntity] = []
        best_status = SituationStatus.UNRESOLVED_ENTITIES
        best_grounding_score = 0.0

        for candidate in candidates:
            grounded_ents, status, g_score = self._ground_candidate(candidate, raw_input)
            if g_score > best_grounding_score or best_candidate is None:
                best_candidate = candidate
                best_grounded_entities = grounded_ents
                best_status = status
                best_grounding_score = g_score
                if status == SituationStatus.GROUNDED:
                    break  # Found a fully grounded candidate

        # Collect ambiguities and unresolved entities
        ambiguities = []
        unresolved = []
        required_knowledge = []

        for ge in best_grounded_entities:
            if ge.status == GroundingStatus.AMBIGUOUS:
                ambiguities.append(
                    f"Mention '{ge.mention}' is ambiguous between candidate concepts: {ge.candidate_concept_names}"
                )
            elif ge.status == GroundingStatus.UNKNOWN:
                unresolved.append(ge.mention)
                required_knowledge.append(f"Concept definition for '{ge.mention}'")

        # Validate relationships if proposed
        validated_relationships = []
        if best_candidate and best_candidate.proposed_relationships:
            for rel in best_candidate.proposed_relationships:
                val_rel = self._validate_relationship(rel, best_grounded_entities)
                validated_relationships.append(val_rel)

        # Evidence aggregation
        evidence = list(best_candidate.evidence) if best_candidate else []
        for ge in best_grounded_entities:
            if ge.status == GroundingStatus.RESOLVED:
                evidence.append(Evidence(
                    evidence_type="ukm_grounding",
                    source="KnowledgeManager",
                    description=f"Resolved mention '{ge.mention}' to canonical UKM concept '{ge.canonical_name}' ({ge.concept_id}).",
                    confidence=1.0
                ))
            elif ge.status == GroundingStatus.AMBIGUOUS:
                evidence.append(Evidence(
                    evidence_type="ukm_ambiguity_alert",
                    source="KnowledgeManager",
                    description=f"Mention '{ge.mention}' matched {len(ge.candidate_concept_names)} competing UKM concepts.",
                    confidence=1.0
                ))
            elif ge.status == GroundingStatus.UNKNOWN:
                evidence.append(Evidence(
                    evidence_type="ukm_unknown_alert",
                    source="KnowledgeManager",
                    description=f"Mention '{ge.mention}' has no matching concepts or aliases in UKM.",
                    confidence=1.0
                ))

        # Check for context requirements
        if best_candidate and best_candidate.requires_context:
            best_status = SituationStatus.INSUFFICIENT_CONTEXT

        return CognitiveSituation(
            raw_input=raw_input,
            accepted_interpretation=best_candidate,
            grounded_entities=best_grounded_entities,
            intent=best_candidate.proposed_intent if best_candidate else "ExplainConcept",
            relationships=validated_relationships,
            assumptions=best_candidate.assumptions if best_candidate else [],
            evidence=evidence,
            interpretation_confidence=best_candidate.confidence if best_candidate else 0.0,
            grounding_confidence=best_grounding_score,
            ambiguities=ambiguities,
            unresolved_entities=unresolved,
            required_knowledge=required_knowledge,
            status=best_status,
            semantic_request=best_candidate.semantic_request if best_candidate else None,
        )

    def _ground_candidate(
        self, candidate: CandidateInterpretation, raw_input: RawInput
    ) -> Tuple[List[GroundedEntity], SituationStatus, float]:
        """Validates all entity mentions in a candidate against the UKM."""
        if candidate.proposed_intent == "SolveMathematics":
            math_mention = candidate.candidate_entity_mentions[0] if candidate.candidate_entity_mentions else "mathematics"
            ge = GroundedEntity(
                mention=math_mention,
                status=GroundingStatus.RESOLVED,
                concept_id="c_mathematics",
                canonical_name="Mathematics",
                provenance={"match_type": "formal_computation", "engine": "UniversalMathEngine"}
            )
            return [ge], SituationStatus.GROUNDED, 1.0

        if candidate.proposed_intent == "AnswerGeneral":
            ge = GroundedEntity(
                mention="general_overview",
                status=GroundingStatus.RESOLVED,
                concept_id="c_general",
                canonical_name="GeneralOverview",
                provenance={"match_type": "system_overview", "engine": "CognitivePipeline"}
            )
            return [ge], SituationStatus.GROUNDED, 1.0

        grounded_entities: List[GroundedEntity] = []
        has_ambiguity = False
        has_unknown = False
        resolved_count = 0

        # Ground each candidate entity mention
        for mention in candidate.candidate_entity_mentions:
            ge = self._resolve_mention(mention)
            grounded_entities.append(ge)
            if ge.status == GroundingStatus.RESOLVED:
                resolved_count += 1
            elif ge.status == GroundingStatus.AMBIGUOUS:
                has_ambiguity = True
            elif ge.status == GroundingStatus.UNKNOWN:
                has_unknown = True

        total = len(grounded_entities)
        if total == 0:
            return grounded_entities, SituationStatus.UNRESOLVED_ENTITIES, 0.0

        grounding_score = resolved_count / total

        if has_ambiguity:
            status = SituationStatus.AMBIGUOUS
        elif has_unknown or resolved_count == 0:
            status = SituationStatus.UNRESOLVED_ENTITIES
        else:
            status = SituationStatus.GROUNDED

        return grounded_entities, status, grounding_score

    def _resolve_mention(self, mention: str) -> GroundedEntity:
        """Resolves a raw entity mention against UKM names and aliases."""
        clean = mention.strip()
        if not clean:
            return GroundedEntity(mention=mention, status=GroundingStatus.UNKNOWN)

        # 1. Direct name lookup
        direct_concept = self.manager.get_concept_by_name(clean)
        if direct_concept:
            return GroundedEntity(
                mention=mention,
                status=GroundingStatus.RESOLVED,
                concept_id=direct_concept.id,
                canonical_name=direct_concept.name,
                provenance={"match_type": "direct_name", "concept_id": direct_concept.id}
            )

        # 2. Case-insensitive alias resolution via ConceptRepository
        aliases: List[Concept] = []
        if hasattr(self.manager, "concept_store") and hasattr(self.manager.concept_store, "repository"):
            aliases = self.manager.concept_store.repository.resolve_alias(clean.lower())

        if len(aliases) == 1:
            return GroundedEntity(
                mention=mention,
                status=GroundingStatus.RESOLVED,
                concept_id=aliases[0].id,
                canonical_name=aliases[0].name,
                provenance={"match_type": "alias", "concept_id": aliases[0].id}
            )
        elif len(aliases) > 1:
            # Preserve all candidates — DO NOT silently select aliases[0]
            return GroundedEntity(
                mention=mention,
                status=GroundingStatus.AMBIGUOUS,
                candidate_concept_names=[c.name for c in aliases],
                candidate_concept_ids=[c.id for c in aliases],
                provenance={"match_type": "ambiguous_alias", "count": len(aliases)}
            )

        # 3. Singularization candidates (e.g. "interfaces" -> "interface", "classes" -> "class")
        singular_candidates = self._generate_singular_forms(clean)
        for cand in singular_candidates:
            c = self.manager.get_concept_by_name(cand)
            if c:
                return GroundedEntity(
                    mention=mention,
                    status=GroundingStatus.RESOLVED,
                    concept_id=c.id,
                    canonical_name=c.name,
                    provenance={"match_type": "singularization", "concept_id": c.id}
                )
            if hasattr(self.manager, "concept_store") and hasattr(self.manager.concept_store, "repository"):
                cand_aliases = self.manager.concept_store.repository.resolve_alias(cand.lower())
                if len(cand_aliases) == 1:
                    return GroundedEntity(
                        mention=mention,
                        status=GroundingStatus.RESOLVED,
                        concept_id=cand_aliases[0].id,
                        canonical_name=cand_aliases[0].name,
                        provenance={"match_type": "singular_alias", "concept_id": cand_aliases[0].id}
                    )
                elif len(cand_aliases) > 1:
                    return GroundedEntity(
                        mention=mention,
                        status=GroundingStatus.AMBIGUOUS,
                        candidate_concept_names=[ac.name for ac in cand_aliases],
                        candidate_concept_ids=[ac.id for ac in cand_aliases],
                        provenance={"match_type": "ambiguous_singular_alias", "count": len(cand_aliases)}
                    )

        # 4. Unknown entity
        return GroundedEntity(
            mention=mention,
            status=GroundingStatus.UNKNOWN,
            provenance={"match_type": "none"}
        )

    def _generate_singular_forms(self, word: str) -> List[str]:
        """Generates singular grammatical and modifier-stripped candidates."""
        candidates = []
        w = word.strip()
        if w.endswith("es") and len(w) > 3:
            candidates.append(w[:-1])  # interfaces -> interface
            candidates.append(w[:-2])  # classes -> class
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 2:
            candidates.append(w[:-1])

        # Check stripping language/modifier prefix (e.g. "Java classes" -> "classes" -> "class")
        prefix_m = re.match(r"^(?:java|python|c\+\+|rust|golang|oop)\s+(.+)$", w, re.IGNORECASE)
        if prefix_m:
            base_w = prefix_m.group(1).strip()
            candidates.append(base_w)
            if base_w.endswith("es") and len(base_w) > 3:
                candidates.append(base_w[:-1])
                candidates.append(base_w[:-2])
            elif base_w.endswith("s") and not base_w.endswith("ss") and len(base_w) > 2:
                candidates.append(base_w[:-1])

        return candidates

    def _validate_relationship(
        self, rel: Dict[str, Any], grounded_entities: List[GroundedEntity]
    ) -> Dict[str, Any]:
        """Validates whether a proposed relationship connects grounded concepts."""
        rel_type = rel.get("type", "unknown")
        target_a = rel.get("target_a") or rel.get("source")
        target_b = rel.get("target_b") or rel.get("target")

        # Check if targets are grounded
        ent_a = next((ge for ge in grounded_entities if ge.mention == target_a), None)
        ent_b = next((ge for ge in grounded_entities if ge.mention == target_b), None)

        is_grounded = bool(
            ent_a and ent_a.status == GroundingStatus.RESOLVED and
            ent_b and ent_b.status == GroundingStatus.RESOLVED
        )

        return {
            "type": rel_type,
            "target_a": target_a,
            "target_b": target_b,
            "is_grounded": is_grounded,
            "concept_id_a": ent_a.concept_id if ent_a else None,
            "concept_id_b": ent_b.concept_id if ent_b else None,
        }
