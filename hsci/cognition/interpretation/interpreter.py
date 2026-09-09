"""Language Interpreter for HSCI VS-6: General Cognitive Language Understanding.

Transforms RawInput into a multi-hypothesis InterpretationSet consisting of
structured SemanticRequests and CandidateInterpretations.
Decouples linguistic surface form from semantic request goals.
"""
import re
import logging
from typing import List, Optional, Tuple, Dict, Any

from hsci.cognition.interpretation.models import (
    RawInput,
    CandidateInterpretation,
    InterpretationSet,
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
from hsci.cognition.interpretation.untrusted_proposer import UntrustedSemanticProposer
from hsci.cognition.interpretation.neural_semantic_model import NeuralSemanticModel
from hsci.cognition.interpretation.math_composition import compose_math_structure, ComposedStructure

logger = logging.getLogger("HSCI.Cognition.Interpretation.Interpreter")


class LanguageInterpreter:
    """Neural & Semantic interpreter with optional untrusted proposal ingestion."""

    def __init__(self, llm_adapter: Optional[Any] = None, enable_llm: bool = False):
        self.llm_adapter = llm_adapter
        self.enable_llm = enable_llm
        self.neural_model = NeuralSemanticModel()
        self.trainable_parser = self._try_load_trainable_parser()

    @staticmethod
    def _try_load_trainable_parser():
        """Trained BiLSTM tagger (hsci/language/semantic_tagger.py) used ONLY as
        an extra vote for routing to SOLVE_MATH when the deterministic regex
        check below can't tell (e.g. physics word problems with no "=" or
        operator symbol: "if velocity is 60 and time is 2, what is the
        distance"). It never bypasses grounding/verification -- it just gets
        such phrasing into the same, already-working SOLVE_MATH path that
        "3x + 7 = 25" already uses, so UniversalMathEngine gets a chance to
        solve it instead of the request falling through to concept lookup."""
        try:
            from hsci.language.semantic_tagger import TrainableSemanticParser

            candidate = TrainableSemanticParser()
            if candidate.load():
                return candidate
        except Exception:
            pass
        return None

    def interpret(self, raw_input: RawInput) -> InterpretationSet:
        """Generates candidate interpretations and semantic requests from raw input."""
        candidates: List[CandidateInterpretation] = []

        # 1. Primary Semantic Request Derivation
        primary_cand = self._analyze_semantic_request(raw_input)
        if primary_cand:
            candidates.append(primary_cand)

        # 2. Multi-Hypothesis Alternative Generation (for compound or multi-clause requests)
        alternatives = self._generate_alternatives(raw_input, primary_cand)
        candidates.extend(alternatives)

        # 3. Optional Untrusted LLM Candidate Proposal (strictly validated)
        if self.enable_llm and self.llm_adapter:
            try:
                llm_cands = self._propose_llm_candidates(raw_input)
                candidates.extend(llm_cands)
            except Exception as exc:
                logger.warning("LLM hypothesis proposal failed or skipped: %s", exc)

        return InterpretationSet(raw_input=raw_input, candidates=candidates)

    def _analyze_semantic_request(self, raw_input: RawInput) -> CandidateInterpretation:
        """Extracts structured SemanticRequest from raw input text."""
        text = raw_input.original_text.strip()
        norm = raw_input.normalized_text

        evidence: List[Evidence] = []
        assumptions: List[InterpretationAssumption] = []
        context_refs: List[ContextReference] = []
        constraints: List[SemanticConstraint] = []
        relations: List[SemanticRelation] = []
        requires_context = False

        # --- Modality & Negation Detection ---
        is_negated = bool(re.search(r"\b(not|never|isn't|aren't|doesn't|don't)\b", norm))
        modality = "ASSERTION"
        if re.search(r"\b(can|could|might|may)\b", norm):
            modality = "HYPOTHETICAL"
        elif re.search(r"\b(should|must|ought)\b", norm):
            modality = "DEONTIC"

        # --- Context / Pronoun Reference Analysis ---
        # Detect bare referents that genuinely require antecedent discourse context
        is_bare_referent = bool(re.search(
            r"^(?:(?:can you\s+)?(?:what|why|how)\s+(?:is|does|about|matter|would)\s+(?:it|this|that)(?:\s+(?:useful|work|different|matter|mean))?|explain\s+(?:it|this|that|the previous one|the thing)|tell me about\s+(?:it|this|that))\s*[.,?!]*$",
            norm,
            re.IGNORECASE
        ))

        # Check for standalone pronoun without an explicit noun in the query
        has_standalone_it = bool(re.search(r"\b(it|they|them)\b", norm)) and not bool(re.search(r"[,;]\s*(?:and|compare|relate|with)", norm))
        # Demonstrative "this <noun>" or "that <noun>" is a determiner, not a bare referent
        is_demonstrative_noun = bool(re.search(r"\b(this|that)\s+[a-zA-Z_]{2,}\b", norm)) and not is_bare_referent

        # Detect if query has NO substantive nouns other than question/stop words
        stopwords_and_verbs = {"what", "is", "are", "does", "do", "how", "why", "can", "you", "explain", "tell", "me", "about", "a", "an", "the", "it", "this", "that", "useful", "work", "different", "matter", "mean", "thing", "one", "previous"}
        words_in_norm = set(re.findall(r"\b[a-zA-Z_]{2,}\b", norm))
        substantive_words = words_in_norm - stopwords_and_verbs

        if is_bare_referent or (has_standalone_it and not substantive_words and not is_demonstrative_noun):
            requires_context = True
            marker_m = re.search(r"\b(it|this|that|the thing|they|them)\b", norm)
            marker = marker_m.group(1) if marker_m else "it"
            context_refs.append(ContextReference(marker=marker, reference_type="PRONOUN", is_resolved=False))
            assumptions.append(InterpretationAssumption(
                statement="Input refers to an antecedent entity via pronoun/deictic reference.",
                rationale=f"Found deictic marker '{marker}' with no antecedent in query.",
                is_verified=False
            ))
            evidence.append(Evidence(
                evidence_type="deictic_analysis",
                source="LanguageInterpreter._analyze_semantic_request",
                description=f"Detected referential pronoun '{marker}' requiring discourse context.",
                confidence=0.90
            ))

        # --- Multi-clause / Focus Sentence Selection ---
        sentences = [s.strip() for s in re.split(r"[\n\r]+|[.!?]\s+", text) if s.strip()]
        focus_text = text
        for s in reversed(sentences):
            s_clean = s.strip()
            if re.search(r"\b(what\s+(?:[a-zA-Z]+\s+)?(?:is|are|does)|how\s+(?:is|are|does)|why\s+(?:do|does|is)|compare|can you explain|tell me about|explain)\b", s_clean, re.IGNORECASE):
                focus_text = s_clean
                break
        else:
            for s in sentences:
                s_clean = s.strip()
                if re.search(r"\b(what|how|why|compare|explain|describe|tell me|can you|difference|relat)\b", s_clean, re.IGNORECASE):
                    focus_text = s_clean
                    break

        # Handle compound instruction with negation (e.g. "Don't explain X; compare X and Y")
        excluded_action = None
        neg_override = re.search(r"\bdon't\s+explain\s+([^;,]+)[;,]\s*(compare\s+.+)", text, re.IGNORECASE)
        if neg_override:
            excluded_action = self._clean_mention(neg_override.group(1).strip())
            focus_text = neg_override.group(2).strip()
            constraints.append(SemanticConstraint(
                constraint_type="EXCLUSION",
                operator="NOT",
                value=f"explain {excluded_action}",
                polarity=False
            ))
            is_negated = False  # The active requested goal (compare) is positive

        # --- Neural Semantic Model Intent Prediction ---
        predicted_goal, neural_conf = self.neural_model.predict_goal(focus_text)
        is_math = bool(re.search(r"[\+\-\*\/=\^0-9]", focus_text)) or bool(re.search(r"\b(?:calc\w*|solv\w*|comput\w*|eval\w*)\b", focus_text, re.IGNORECASE))
        neural_math_vote = predicted_goal == CommunicativeGoal.SOLVE_MATH and is_math

        # 0. Communicative Goal: SOLVE_MATH (Neural)
        if neural_math_vote and not requires_context:
            # Try the deterministic compositional parser first: real typed
            # Quantity/Variable/Operation/Equals structure (Cognitive
            # Substrate Final Review, Interpretation Extension) instead of
            # collapsing the whole expression into one raw-text mention.
            composed = compose_math_structure(focus_text)
            if composed is not None:
                return self._candidate_from_composed_math(
                    composed, constraints, context_refs, is_negated, modality, assumptions, evidence,
                    requires_context,
                )

            # Fallback: composition could not confidently resolve a
            # structure (e.g. bare arithmetic with no unknown, or a
            # quadratic term) -- preserve the existing single-mention
            # behavior exactly rather than guess.
            source = "neural_semantic_model"
            conf = neural_conf
            mentions, relations = self.neural_model.extract_entities_and_relations(focus_text, CommunicativeGoal.SOLVE_MATH)
            math_expr = mentions[0].surface_form if mentions else focus_text
            e = EntityMention(surface_form=math_expr, normalized_form=math_expr.lower(), confidence=conf)
            evidence.append(Evidence(
                evidence_type="neural_intent_prediction",
                source=source,
                description=f"{source} identified communicative goal SOLVE_MATH for '{math_expr}'.",
                confidence=conf,
            ))
            sem_req = SemanticRequest(
                goal=CommunicativeGoal.SOLVE_MATH,
                entity_mentions=[e],
                relations=[],
                constraints=constraints,
                output_requirements=[OutputRequirement(output_type="COMPUTATION", depth=1)],
                context_references=context_refs,
                is_negated=is_negated,
                modality=modality,
                confidence=conf,
                source_method=source,
                assumptions=assumptions,
                evidence=evidence,
            )
            return CandidateInterpretation(
                proposed_intent="SolveMathematics",
                candidate_entity_mentions=[math_expr],
                proposed_relationships=[],
                constraints=[c.value for c in constraints],
                assumptions=assumptions,
                evidence=evidence,
                confidence=conf,
                source_method=source,
                requires_context=requires_context,
                semantic_request=sem_req,
            )

        # 0.5 Communicative Goal: GENERAL / CONVERSATIONAL (Neural)
        if predicted_goal == CommunicativeGoal.GENERAL and not requires_context:
            e = EntityMention(surface_form="general_overview", normalized_form="general_overview", confidence=neural_conf)
            sem_req = SemanticRequest(
                goal=CommunicativeGoal.GENERAL,
                entity_mentions=[e],
                relations=[],
                constraints=constraints,
                output_requirements=[OutputRequirement(output_type="EXPLANATION", depth=1)],
                context_references=context_refs,
                is_negated=False,
                modality="ASSERTION",
                confidence=neural_conf,
                source_method="neural_semantic_model",
                assumptions=[],
                evidence=[],
            )
            return CandidateInterpretation(
                proposed_intent="AnswerGeneral",
                candidate_entity_mentions=["general_overview"],
                proposed_relationships=[],
                constraints=[],
                assumptions=[],
                evidence=[],
                confidence=neural_conf,
                source_method="neural_semantic_model",
                requires_context=False,
                semantic_request=sem_req,
            )

        # 1. Communicative Goal: COMPARE
        comp_m1 = re.search(r"\b(?:compare|distinguish|difference between)\s+([^.,?!]+?)\s+(?:and|with|to)\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m2 = re.search(r"\bhow (?:is|are|does)\s+([^.,?!]+?)\s+(?:different from|differ from)\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m3 = re.search(r"\bwhy would (?:i|someone) (?:choose|use)\s+(?:a |an )?([^.,?!]+?)\s+(?:instead of|over)\s+(?:a |an )?([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m4 = re.search(r"\b([^.,?!]+?)\s+(?:vs\.?|versus)\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m5 = re.search(r"\bare\s+([^.,?!]+?)\s+and\s+([^.,?!]+?)\s+the same thing(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m6 = re.search(r"\b(?:reading about|difference between|difference of|get the difference between|difference in)\s+([^.,?!]+?)\s+and\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        comp_m7 = re.search(r"\b(?:reading about|confused about)\s+([^.,?!]+?)\s+and\s+([^.,?!]+?)\s+and\s+(?:don't|cannot|can't)\s+(?:really\s+)?get the difference(?:\.|\?|$)", text, re.IGNORECASE)

        if comp_m1 or comp_m2 or comp_m3 or comp_m4 or comp_m5 or comp_m6 or comp_m7:
            m = comp_m1 or comp_m2 or comp_m3 or comp_m4 or comp_m5 or comp_m6 or comp_m7
            t1 = self._clean_mention(m.group(1))
            t2 = self._clean_mention(m.group(2))

            # Intra-sentence / cross-clause anaphora resolution
            if t1.lower() in ("it", "this", "that", "the thing", "them"):
                if excluded_action:
                    t1 = excluded_action
                else:
                    prec_m = re.search(r"\b(?:explain|define|describe|what is|tell me about|confused about)\s+(?:a |an |the )?([^,;]+?)(?:\s*[,;]|\s+and\s+)", text, re.IGNORECASE)
                    if prec_m:
                        t1 = self._clean_mention(prec_m.group(1))

            if t1 and t2:
                # Check for tertiary concept in subsequent clause (e.g. "and tell me how it relates to Abstraction")
                extra_mentions = []
                rel_clause_m = re.search(r"\b(?:relat\w*|connect\w*)\s+(?:it\s+)?to\s+(?:a |an |the )?([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
                if rel_clause_m:
                    t3 = self._clean_mention(rel_clause_m.group(1))
                    if t3 and t3.lower() not in (t1.lower(), t2.lower()):
                        extra_mentions.append(t3)

                e1 = EntityMention(surface_form=t1, normalized_form=t1.lower(), confidence=0.95)
                e2 = EntityMention(surface_form=t2, normalized_form=t2.lower(), confidence=0.95)
                entity_mentions = [e1, e2]
                for em_str in extra_mentions:
                    entity_mentions.append(EntityMention(surface_form=em_str, normalized_form=em_str.lower(), confidence=0.90))

                rel = SemanticRelation(source_mention=t1, relation_type="COMPARISON", target_mention=t2, confidence=0.95)
                relations.append(rel)
                evidence.append(Evidence(
                    evidence_type="semantic_goal_analysis",
                    source="LanguageInterpreter",
                    description=f"Identified communicative goal COMPARE across '{t1}' and '{t2}'.",
                    confidence=0.95
                ))
                sem_req = SemanticRequest(
                    goal=CommunicativeGoal.COMPARE,
                    entity_mentions=entity_mentions,
                    relations=relations,
                    constraints=constraints,
                    output_requirements=[OutputRequirement(output_type="COMPARISON", depth=1)],
                    context_references=context_refs,
                    is_negated=is_negated,
                    modality=modality,
                    confidence=0.95,
                    source_method="structural_compare_frame",
                    assumptions=assumptions,
                    evidence=evidence,
                )
                return CandidateInterpretation(
                    proposed_intent="CompareConcepts",
                    candidate_entity_mentions=[t1, t2] + extra_mentions,
                    proposed_relationships=[{"type": "comparison", "target_a": t1, "target_b": t2}],
                    constraints=[c.value for c in constraints],
                    assumptions=assumptions,
                    evidence=evidence,
                    confidence=0.95,
                    source_method="structural_compare_frame",
                    requires_context=requires_context,
                    semantic_request=sem_req,
                )

        # 2. Communicative Goal: RELATE
        rel_m1 = re.search(r"\b(?:what is the )?relationship between\s+([^.,?!]+?)\s+and\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m2 = re.search(r"\bhow (?:are|is)\s+([^.,?!]+?)\s+(?:and\s+([^.,?!]+?)\s+(?:connected|related)|(?:connected|related)\s+to\s+([^.,?!]+?))(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m3 = re.search(r"\bhow does\s+([^.,?!]+?)\s+relate to\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m4 = re.search(r"\bdoes\s+([^.,?!]+?)\s+have anything to do with\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m5 = re.search(r"\b(?:what\s+(?:is|are)\s+|can\s+you\s+explain\s+what\s+|explain\s+)(?:a |an |the )?([^.,?!]+?)\s+(?:is|are)?\s+and\s+how\s+it\s+relates\s+to\s+(?:a |an |the )?([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m6 = re.search(r"\bhow\s+([^.,?!]+?)\s+(?:inherits\s+from|implements|extends|relates\s+to)\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m7 = re.search(r"\b(?:what's|what is) the connection between\s+([^.,?!]+?)\s+and\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        rel_m8 = re.search(r"\bhow (?:is|are)\s+([^.,?!]+?)\s+related to\s+([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)

        if rel_m1 or rel_m2 or rel_m3 or rel_m4 or rel_m5 or rel_m6 or rel_m7 or rel_m8:
            m = rel_m1 or rel_m3 or rel_m4 or rel_m5 or rel_m6 or rel_m7 or rel_m8
            if m:
                raw_t1, raw_t2 = m.group(1), m.group(2)
            else:
                raw_t1 = rel_m2.group(1)
                raw_t2 = rel_m2.group(2) or rel_m2.group(3)

            t1 = self._clean_mention(raw_t1)
            t2 = self._clean_mention(raw_t2)

            # Intra-sentence anaphora resolution
            if t1.lower() in ("it", "this", "that", "the thing", "them"):
                prec_m = re.search(r"\b(?:explain|define|describe|what is|tell me about)\s+(?:a |an |the )?([^,;]+?)(?:\s*[,;]|\s+and\s+)", text, re.IGNORECASE)
                if prec_m:
                    t1 = self._clean_mention(prec_m.group(1))

            if t1 and t2:
                # Check for intervening comparison concept (e.g. "compare it with Class")
                extra_mentions = []
                interv_m = re.search(r"\b(?:compare\s+(?:it\s+)?with|compare\s+(?:it\s+)?and)\s+(?:a |an |the )?([^,;]+?)(?:\s*[,;]|\s+and\s+)", text, re.IGNORECASE)
                if interv_m:
                    im = self._clean_mention(interv_m.group(1))
                    if im and im.lower() not in (t1.lower(), t2.lower()):
                        extra_mentions.append(im)

                e1 = EntityMention(surface_form=t1, normalized_form=t1.lower(), confidence=0.95)
                e2 = EntityMention(surface_form=t2, normalized_form=t2.lower(), confidence=0.95)
                entity_mentions = [e1]
                for em_str in extra_mentions:
                    entity_mentions.append(EntityMention(surface_form=em_str, normalized_form=em_str.lower(), confidence=0.90))
                entity_mentions.append(e2)

                rel = SemanticRelation(source_mention=t1, relation_type="RELATIONSHIP", target_mention=t2, confidence=0.95)
                relations.append(rel)
                evidence.append(Evidence(
                    evidence_type="semantic_goal_analysis",
                    source="LanguageInterpreter",
                    description=f"Identified communicative goal RELATE between '{t1}' and '{t2}'.",
                    confidence=0.95
                ))
                sem_req = SemanticRequest(
                    goal=CommunicativeGoal.RELATE,
                    entity_mentions=entity_mentions,
                    relations=relations,
                    constraints=constraints,
                    output_requirements=[OutputRequirement(output_type="PROOF_TRACE", depth=1)],
                    context_references=context_refs,
                    is_negated=is_negated,
                    modality=modality,
                    confidence=0.95,
                    source_method="structural_relationship_frame",
                    assumptions=assumptions,
                    evidence=evidence,
                )
                return CandidateInterpretation(
                    proposed_intent="FindRelationship",
                    candidate_entity_mentions=[t1] + extra_mentions + [t2],
                    proposed_relationships=[{"type": "relationship", "source": t1, "target": t2}],
                    constraints=[c.value for c in constraints],
                    assumptions=assumptions,
                    evidence=evidence,
                    confidence=0.95,
                    source_method="structural_relationship_frame",
                    requires_context=requires_context,
                    semantic_request=sem_req,
                )

        # 3. Communicative Goal: EXPLAIN
        exp_mean = re.search(r"\b(?:what\s+(?:[a-zA-Z]+\s+)?does\s+([^.,?!]+?)\s+mean)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        exp_m1 = re.search(r"\b(?:what\s+(?:[a-zA-Z]+\s+)?(?:is|are)|explain|describe|define|tell me about|can you explain|give me an explanation of|i don't understand)\s+(?:what )?(?:a |an |the )?([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        exp_m2 = re.search(r"\b(?:confused about|curious about|understand)\s+(?:what )?(?:a |an |the )?([^.,?!]+?)(?:\.|\?|$)", focus_text, re.IGNORECASE)
        exp_m3 = re.search(r"\b(?:why (?:do|does|is)|what purpose does)\s+(?:a |an |the )?([^.,?!]+?)(?:\s+(?:exist|exists|serves?|do|useful))?(?:\s+(?:in|for)\s+([^.,?!]+?))?(?:\.|\?|$)", focus_text, re.IGNORECASE)

        if (exp_mean or exp_m1 or exp_m2 or exp_m3) and not requires_context:
            if exp_mean:
                raw_mention = exp_mean.group(1)
                t = self._clean_mention(raw_mention)
            elif exp_m3:
                base_t = self._clean_mention(exp_m3.group(1))
                scope_t = self._clean_mention(exp_m3.group(2)) if exp_m3.group(2) else ""
                t = f"{scope_t} {base_t}".strip() if scope_t else base_t
                raw_mention = exp_m3.group(1)
            else:
                m = exp_m1 or exp_m2
                raw_mention = m.group(1)
                t = self._clean_mention(raw_mention)

            # Anaphora resolution from preceding context in the same stimulus
            if t and t.lower() in ("they", "they are", "what they are", "what it is", "it", "this", "that", "them"):
                prec_exp_m = re.search(r"\b(?:confused about|reading about|about|understand|what is)\s+(?:a |an |the )?([^.,?!]+?)(?:\.|\?|,|$)", text, re.IGNORECASE)
                if prec_exp_m:
                    t = self._clean_mention(prec_exp_m.group(1))
                    raw_mention = prec_exp_m.group(1)

            if t:
                e = EntityMention(surface_form=str(raw_mention).strip(), normalized_form=t.lower(), confidence=0.92)
                evidence.append(Evidence(
                    evidence_type="semantic_goal_analysis",
                    source="LanguageInterpreter",
                    description=f"Identified communicative goal EXPLAIN for target '{t}'.",
                    confidence=0.92
                ))
                sem_req = SemanticRequest(
                    goal=CommunicativeGoal.EXPLAIN,
                    entity_mentions=[e],
                    relations=[],
                    constraints=constraints,
                    output_requirements=[OutputRequirement(output_type="EXPLANATION", depth=1)],
                    context_references=context_refs,
                    is_negated=is_negated,
                    modality=modality,
                    confidence=0.92,
                    source_method="structural_explanation_frame",
                    assumptions=assumptions,
                    evidence=evidence,
                )
                return CandidateInterpretation(
                    proposed_intent="ExplainConcept",
                    candidate_entity_mentions=[t],
                    proposed_relationships=[],
                    constraints=[c.value for c in constraints],
                    assumptions=assumptions,
                    evidence=evidence,
                    confidence=0.92,
                    source_method="structural_explanation_frame",
                    requires_context=requires_context,
                    semantic_request=sem_req,
                )

        # 3.4 Deterministic compositional math structure (no operator
        # symbols required): tries to compose a typed Quantity/Variable/
        # Operation/Equals structure from natural-language predicates (see
        # math_composition.py) once COMPARE/RELATE/EXPLAIN above have all
        # had their chance and none matched -- same safety ordering and for
        # the same reason as 3.5 below: an equality-copula match ("is",
        # "gives", ...) is common enough in non-math sentences that this
        # must not run before the structural COMPARE/RELATE/EXPLAIN frames.
        # Unlike 3.5, this is deterministic (not a classifier vote) and
        # only ever succeeds when every part of the utterance resolves to a
        # recognized quantity/variable/operation -- see module docstring.
        if not requires_context:
            composed = compose_math_structure(focus_text)
            if composed is not None:
                return self._candidate_from_composed_math(
                    composed, constraints, context_refs, is_negated, modality, assumptions, evidence,
                    requires_context,
                )

        # 3.5 Trained-tagger fallback for SOLVE_MATH: only reached once
        # COMPARE/RELATE/EXPLAIN above have all had a chance and none matched
        # -- it must never run before them, since the tagger was trained on
        # arithmetic/word-problem phrasing only and would otherwise confidently
        # misroute something like "Compare Java interface and class" (it has
        # never seen "compare"/"explain"/"relationship between" phrasing in
        # training). Here it can only catch what nothing else recognized at
        # all, e.g. "if velocity is 60 and time is 2, what is the distance"
        # (no operator symbol or "=" for the deterministic check above).
        if not requires_context and self.trainable_parser is not None:
            try:
                tagger_result = self.trainable_parser.parse(focus_text)
                if tagger_result["intent"] in ("REDUCTION", "COMPOSITION") and tagger_result["confidence"] >= 0.6:
                    conf = tagger_result["confidence"]
                    mentions, relations = self.neural_model.extract_entities_and_relations(focus_text, CommunicativeGoal.SOLVE_MATH)
                    math_expr = mentions[0].surface_form if mentions else focus_text
                    e = EntityMention(surface_form=math_expr, normalized_form=math_expr.lower(), confidence=conf)
                    evidence.append(Evidence(
                        evidence_type="neural_intent_prediction",
                        source="trainable_semantic_tagger",
                        description=f"trainable_semantic_tagger identified communicative goal SOLVE_MATH for '{math_expr}'.",
                        confidence=conf,
                    ))
                    sem_req = SemanticRequest(
                        goal=CommunicativeGoal.SOLVE_MATH,
                        entity_mentions=[e],
                        relations=[],
                        constraints=constraints,
                        output_requirements=[OutputRequirement(output_type="COMPUTATION", depth=1)],
                        context_references=context_refs,
                        is_negated=is_negated,
                        modality=modality,
                        confidence=conf,
                        source_method="trainable_semantic_tagger",
                        assumptions=assumptions,
                        evidence=evidence,
                    )
                    return CandidateInterpretation(
                        proposed_intent="SolveMathematics",
                        candidate_entity_mentions=[math_expr],
                        proposed_relationships=[],
                        constraints=[c.value for c in constraints],
                        assumptions=assumptions,
                        evidence=evidence,
                        confidence=conf,
                        source_method="trainable_semantic_tagger",
                        requires_context=requires_context,
                        semantic_request=sem_req,
                    )
            except Exception:
                pass

        # 4. Fallback: Entity Span Extraction
        spans = self._extract_candidate_spans(text)
        entity_mentions_objs: List[EntityMention] = []
        entity_mentions_strs: List[str] = []

        if spans:
            for sp in spans:
                entity_mentions_objs.append(EntityMention(surface_form=sp, normalized_form=sp, confidence=0.60))
                entity_mentions_strs.append(sp)
            evidence.append(Evidence(
                evidence_type="noun_phrase_extraction",
                source="LanguageInterpreter",
                description=f"Extracted candidate entity spans: {spans}",
                confidence=0.60
            ))
        elif not requires_context:
            tokens = [w for w in norm.split() if w not in {"what", "is", "a", "an", "the", "in", "for", "of", "and", "or", "to", "how", "why"}]
            if tokens:
                sp = " ".join(tokens)
                entity_mentions_objs.append(EntityMention(surface_form=sp, normalized_form=sp, confidence=0.40))
                entity_mentions_strs.append(sp)

        goal = CommunicativeGoal.UNKNOWN if (not entity_mentions_strs and not requires_context) else CommunicativeGoal.EXPLAIN
        sem_req = SemanticRequest(
            goal=goal,
            entity_mentions=entity_mentions_objs,
            relations=[],
            constraints=constraints,
            output_requirements=[OutputRequirement(output_type="EXPLANATION", depth=1)],
            context_references=context_refs,
            is_negated=is_negated,
            modality=modality,
            confidence=0.50 if entity_mentions_strs else 0.20,
            source_method="structural_fallback",
            assumptions=assumptions,
            evidence=evidence,
        )

        return CandidateInterpretation(
            proposed_intent="ExplainConcept",
            candidate_entity_mentions=entity_mentions_strs,
            proposed_relationships=[],
            constraints=[c.value for c in constraints],
            assumptions=assumptions,
            evidence=evidence,
            confidence=0.50 if entity_mentions_strs else 0.20,
            source_method="structural_fallback",
            requires_context=requires_context,
            semantic_request=sem_req,
        )

    def _candidate_from_composed_math(
        self,
        composed: ComposedStructure,
        constraints: List[SemanticConstraint],
        context_refs: List[ContextReference],
        is_negated: bool,
        modality: str,
        assumptions: List[InterpretationAssumption],
        evidence: List[Evidence],
        requires_context: bool,
        source_method: str = "compositional_math_structure",
        confidence: float = 0.95,
    ) -> CandidateInterpretation:
        """Builds a SolveMathematics CandidateInterpretation from a
        successfully composed typed structure (math_composition.py) -- the
        real Quantity/Variable/Operation/Equals representation, used by
        every call site that finds one, instead of collapsing the whole
        expression into a single raw-text mention."""
        evidence = list(evidence)
        evidence.append(Evidence(
            evidence_type="compositional_math_structure",
            source="math_composition",
            description=(
                f"Composed typed mathematical structure: {len(composed.mentions)} mention(s), "
                f"{len(composed.relations)} relation(s)."
            ),
            confidence=confidence,
        ))
        sem_req = SemanticRequest(
            goal=CommunicativeGoal.SOLVE_MATH,
            entity_mentions=composed.mentions,
            relations=composed.relations,
            constraints=constraints,
            output_requirements=[OutputRequirement(output_type="COMPUTATION", depth=1)],
            context_references=context_refs,
            is_negated=is_negated,
            modality=modality,
            confidence=confidence,
            source_method=source_method,
            assumptions=assumptions,
            evidence=evidence,
        )
        return CandidateInterpretation(
            proposed_intent="SolveMathematics",
            candidate_entity_mentions=[m.surface_form for m in composed.mentions],
            proposed_relationships=[],
            constraints=[c.value for c in constraints],
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            source_method=source_method,
            requires_context=requires_context,
            semantic_request=sem_req,
        )

    def _generate_alternatives(self, raw_input: RawInput, primary: Optional[CandidateInterpretation]) -> List[CandidateInterpretation]:
        """Generates plausible secondary interpretations for compound multi-concept requests."""
        alternatives: List[CandidateInterpretation] = []
        if not primary:
            return alternatives

        if len(primary.candidate_entity_mentions) > 1 and primary.proposed_intent != "ExplainConcept":
            first_target = primary.candidate_entity_mentions[0]
            alt_req = SemanticRequest(
                goal=CommunicativeGoal.EXPLAIN,
                entity_mentions=[EntityMention(surface_form=first_target, normalized_form=first_target, confidence=0.50)],
                relations=[],
                constraints=[],
                output_requirements=[OutputRequirement(output_type="EXPLANATION")],
                context_references=[],
                confidence=0.50,
                source_method="query_decomposition"
            )
            alt = CandidateInterpretation(
                proposed_intent="ExplainConcept",
                candidate_entity_mentions=[first_target],
                proposed_relationships=[],
                assumptions=[InterpretationAssumption(
                    statement="User might alternatively seek only primary entity definition.",
                    rationale="Compound query contains distinct focus entity.",
                    is_verified=False
                )],
                evidence=[Evidence(
                    evidence_type="decomposition_alternative",
                    source="LanguageInterpreter",
                    description=f"Decomposed multi-entity query to focus on '{first_target}'.",
                    confidence=0.50
                )],
                confidence=0.50,
                source_method="query_decomposition",
                semantic_request=alt_req,
            )
            alternatives.append(alt)

        return alternatives

    def _propose_llm_candidates(self, raw_input: RawInput) -> List[CandidateInterpretation]:
        """Invokes untrusted LLM adapter via the UntrustedSemanticProposer sanitizer."""
        if not self.llm_adapter or not hasattr(self.llm_adapter, "propose"):
            return []
        
        raw_proposals = self.llm_adapter.propose(raw_input.original_text)
        candidates = []
        for prop in raw_proposals:
            if isinstance(prop, dict):
                cand = UntrustedSemanticProposer.parse_proposal(prop)
                if cand:
                    candidates.append(cand)
        return candidates

    def _clean_mention(self, text: str) -> str:
        """Cleans mention by stripping leading/trailing filler words, articles, and punctuation."""
        if not text:
            return ""
        cleaned = text.strip(" .,;:?!\"'()[]{}")
        cleaned = re.sub(
            r"^(?:what\s+(?:is|are|purpose\s+does|do|does)\s+|why\s+(?:do|does|is|would\s+(?:i|someone)\s+(?:choose|use))\s+|how\s+(?:is|are|does)\s+|can\s+you\s+explain\s+(?:what\s+)?|explain\s+|describe\s+|define\s+|tell\s+me\s+about\s+|give\s+me\s+an\s+explanation\s+of\s+|i\s+don't\s+understand\s+|confused\s+about\s+(?:what\s+)?|curious\s+about\s+(?:what\s+)?|understand\s+|i\s+am\s+|a\s+|an\s+|the\s+)+",
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip()

        # Handle "X in Y" -> "Y X"
        in_match = re.search(r"^(.+?)\s+(?:in|of|for)\s+([a-zA-Z0-9_]+)$", cleaned, re.IGNORECASE)
        if in_match:
            base_part = in_match.group(1).strip()
            lang_part = in_match.group(2).strip()
            base_clean = re.sub(r"^(?:an?\s+|the\s+)", "", base_part, flags=re.IGNORECASE)
            base_clean = re.sub(r"\s+(?:is|are|exists?|serves?)$", "", base_clean, flags=re.IGNORECASE).strip()
            cleaned = f"{lang_part} {base_clean}".strip()

        # Strip subordinate clauses
        cleaned = re.sub(r"\s+(?:are|is)?\s+and\s+(?:why|how)\s+.*$", "", cleaned, flags=re.IGNORECASE).strip()
        # Strip common trailing grammatical suffixes
        cleaned = re.sub(r"\s+(?:is|are|exist|exists|serves?|mean|means|stands\s+for|concept|topic|thing)$", "", cleaned, flags=re.IGNORECASE).strip()

        # Regular morphological stemming for known concept forms
        cleaned = re.sub(r"\binterfaces\b", "interface", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bclasses\b", "class", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bmethods\b", "method", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\babstractions\b", "abstraction", cleaned, flags=re.IGNORECASE)

        return cleaned

    def _extract_candidate_spans(self, text: str) -> List[str]:
        """Identifies candidate entity spans using safe linear sliding windows."""
        spans = []
        if not text:
            return spans

        # 1. Capitalized multi-word spans
        cap_matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
        for m in cap_matches:
            cl = self._clean_mention(m)
            if cl and cl not in spans:
                spans.append(cl)

        # 2. Key phrases from filtered tokens
        words = [w.strip(" .,;:?!\"'()[]{}") for w in text.split() if w.strip(" .,;:?!\"'()[]{}")]
        stopwords = {
            "what", "is", "a", "an", "the", "in", "for", "of", "and", "or", "to", "how",
            "why", "can", "you", "tell", "me", "about", "are", "do", "does", "i", "am",
            "we", "have", "our", "that", "this", "these", "those", "specifically", "it",
            "give", "an", "explanation", "understand", "don't"
        }
        filtered = [w for w in words if w.lower() not in stopwords]
        if filtered:
            for k in [2, 1]:
                for i in range(len(filtered) - k + 1):
                    ph = " ".join(filtered[i:i+k])
                    if ph not in spans and len(ph) > 1:
                        spans.append(ph)

        return spans
