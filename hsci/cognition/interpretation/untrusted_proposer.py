"""Untrusted Semantic Proposer Interface for HSCI VS-6.

Allows external statistical models (or LLMs) to propose candidate semantic hypotheses
without granting them authority to invent concepts, define relationships, or assert truth.
Every field is strictly validated and must pass UKM grounding.
"""
import logging
from typing import Dict, Any, List, Optional

from hsci.cognition.interpretation.models import (
    CandidateInterpretation,
    InterpretationAssumption,
    Evidence,
)
from hsci.cognition.interpretation.semantic_model import (
    SemanticRequest,
    CommunicativeGoal,
    EntityMention,
    SemanticRelation,
    SemanticConstraint,
    OutputRequirement,
    ContextReference,
)

logger = logging.getLogger("HSCI.Cognition.Interpretation.UntrustedProposer")


class UntrustedSemanticProposer:
    """Validates and sanitizes untrusted external semantic proposals."""

    @staticmethod
    def parse_proposal(proposal_data: Dict[str, Any]) -> Optional[CandidateInterpretation]:
        """Parses a dictionary proposal into a sanitized CandidateInterpretation."""
        if not isinstance(proposal_data, dict):
            return None

        # 1. Validate Goal
        raw_goal = str(proposal_data.get("goal", "EXPLAIN")).upper()
        try:
            goal_enum = CommunicativeGoal[raw_goal]
        except KeyError:
            goal_enum = CommunicativeGoal.EXPLAIN

        # Map to internal intent string
        intent_map = {
            CommunicativeGoal.EXPLAIN: "ExplainConcept",
            CommunicativeGoal.COMPARE: "CompareConcepts",
            CommunicativeGoal.RELATE: "FindRelationship",
            CommunicativeGoal.IDENTIFY: "ExplainConcept",
            CommunicativeGoal.VERIFY: "FindRelationship",
            CommunicativeGoal.SUMMARIZE: "ExplainConcept",
            CommunicativeGoal.UNKNOWN: "ExplainConcept",
        }
        intent_str = intent_map.get(goal_enum, "ExplainConcept")

        # 2. Extract and sanitize entity mentions (strip fake IDs)
        raw_entities = proposal_data.get("entity_mentions", proposal_data.get("entities", []))
        entity_mentions: List[EntityMention] = []
        clean_mention_strings: List[str] = []

        if isinstance(raw_entities, list):
            for re in raw_entities:
                if isinstance(re, str) and re.strip():
                    clean_str = re.strip()
                    clean_mention_strings.append(clean_str)
                    entity_mentions.append(EntityMention(
                        surface_form=clean_str,
                        normalized_form=clean_str.lower(),
                        candidate_identity=None,  # NEVER trust external concept IDs
                        confidence=0.40,
                        resolution_state="UNRESOLVED"
                    ))
                elif isinstance(re, dict) and "mention" in re:
                    clean_str = str(re["mention"]).strip()
                    if clean_str:
                        clean_mention_strings.append(clean_str)
                        entity_mentions.append(EntityMention(
                            surface_form=clean_str,
                            normalized_form=clean_str.lower(),
                            candidate_identity=None,
                            confidence=0.40,
                            resolution_state="UNRESOLVED"
                        ))

        # 3. Extract relations
        raw_relations = proposal_data.get("relations", proposal_data.get("relationships", []))
        relations: List[SemanticRelation] = []
        if isinstance(raw_relations, list):
            for r in raw_relations:
                if isinstance(r, dict) and "source" in r and "target" in r:
                    relations.append(SemanticRelation(
                        source_mention=str(r["source"]).strip(),
                        relation_type=str(r.get("type", "RELATIONSHIP")).upper(),
                        target_mention=str(r["target"]).strip(),
                        confidence=0.40
                    ))

        # 4. Context References
        raw_context = proposal_data.get("context_references", [])
        context_refs: List[ContextReference] = []
        requires_context = False
        if isinstance(raw_context, list):
            for cr in raw_context:
                if isinstance(cr, str) and cr.strip():
                    context_refs.append(ContextReference(marker=cr.strip(), is_resolved=False))
                    requires_context = True

        # 5. Build SemanticRequest
        raw_conf = float(proposal_data.get("confidence", 0.40))
        semantic_req = SemanticRequest(
            goal=goal_enum,
            entity_mentions=entity_mentions,
            relations=relations,
            constraints=[],
            output_requirements=[OutputRequirement(output_type=goal_enum.value)],
            context_references=context_refs,
            is_negated=bool(proposal_data.get("is_negated", False)),
            modality=str(proposal_data.get("modality", "ASSERTION")),
            confidence=raw_conf,
            source_method="llm_untrusted_proposal",
            assumptions=[InterpretationAssumption(
                statement="Proposed by external untrusted model.",
                rationale="Untrusted semantic proposal requiring full UKM grounding.",
                is_verified=False
            )],
            evidence=[Evidence(
                evidence_type="untrusted_llm_proposal",
                source="UntrustedSemanticProposer",
                description=f"External proposal suggested goal '{goal_enum.value}' with mentions {clean_mention_strings}.",
                confidence=min(0.40, raw_conf)
            )]
        )

        return CandidateInterpretation(
            proposed_intent=intent_str,
            candidate_entity_mentions=clean_mention_strings,
            proposed_relationships=[r.to_dict() for r in relations],
            constraints=[],
            assumptions=semantic_req.assumptions,
            evidence=semantic_req.evidence,
            confidence=raw_conf,
            source_method="llm_untrusted_proposal",
            requires_context=requires_context,
            semantic_request=semantic_req,
        )
