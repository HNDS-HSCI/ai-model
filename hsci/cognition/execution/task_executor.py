"""Cognitive Task Executor for HSCI VS-5.

Executes structured CognitiveTasks over the HSCI cognitive engine stack:
    KnowledgeManager
    ConceptActivationEngine
    CognitiveReasoningEngine
    AnswerGenerationEngine
    ExplanatoryAnswerSynthesizer

Dispatches task-specific cognitive workflows for EXPLAIN_CONCEPT, COMPARE_CONCEPTS,
DERIVE_RELATIONSHIP, and explicit refusal/diagnostic reporting.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

from hsci.core.data_types import Concept
from hsci.core.kernel import CognitiveContext, EventBus
from hsci.knowledge.knowledge_manager import IKnowledgeManager
from hsci.knowledge.concept_activation import ConceptActivationEngine
from hsci.reasoning.reasoning_engine import (
    CognitiveReasoningEngine,
    ReasoningContext,
    ReasoningResult,
    Conclusion,
)
from hsci.response.answer_generation_engine import (
    Answer,
    AnswerSection,
    ConfidenceSummary,
    AnswerMetadata,
    Explanation,
    AnswerGenerationEngine,
)
from hsci.response.explanatory_synthesizer import (
    ExplanatoryAnswerSynthesizer,
    ExplanatoryAnswer,
    KnowledgeSource,
)
from hsci.cognition.interpretation.models import (
    CognitiveTask,
    TaskAction,
    CognitiveSituation,
    SituationStatus,
    GroundingStatus,
)
from hsci.cognition.execution.execution_result import CognitiveExecutionResult

logger = logging.getLogger("HSCI.Cognition.Execution.TaskExecutor")


class CognitiveTaskExecutor:
    """Orchestrates deterministic cognitive operations for a given CognitiveTask."""

    def __init__(
        self,
        manager: IKnowledgeManager,
        activation_engine: ConceptActivationEngine,
        reasoning_engine: CognitiveReasoningEngine,
        answer_engine: AnswerGenerationEngine,
        synthesizer: ExplanatoryAnswerSynthesizer,
        event_bus: Optional[EventBus] = None,
    ):
        self.manager: IKnowledgeManager = manager
        self.activation_engine: ConceptActivationEngine = activation_engine
        self.reasoning_engine: CognitiveReasoningEngine = reasoning_engine
        self.answer_engine: AnswerGenerationEngine = answer_engine
        self.synthesizer: ExplanatoryAnswerSynthesizer = synthesizer
        self.event_bus: Optional[EventBus] = event_bus

    def execute(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        style: str = "Standard",
        activation_engine: Optional[ConceptActivationEngine] = None,
        reasoning_engine: Optional[CognitiveReasoningEngine] = None,
        answer_engine: Optional[AnswerGenerationEngine] = None,
        synthesizer: Optional[ExplanatoryAnswerSynthesizer] = None,
    ) -> Answer:
        """Executes the given CognitiveTask and returns a verified, explainable Answer."""
        start_time = time.time()
        act_engine = activation_engine or self.activation_engine
        reas_engine = reasoning_engine or self.reasoning_engine
        ans_engine = answer_engine or self.answer_engine
        synth = synthesizer or self.synthesizer

        # 1. Dispatch explicit refusal / diagnostic actions
        if task.action in (
            TaskAction.REPORT_INSUFFICIENT_CONTEXT,
            TaskAction.REPORT_AMBIGUITY,
            TaskAction.REPORT_UNKNOWN,
        ):
            return self._execute_refusal(task, situation, context, start_time)

        # 2. Dispatch mathematical solving
        if task.action == TaskAction.SOLVE_MATHEMATICS:
            return self._execute_solve_mathematics(task, situation, context, start_time)

        # 3. Dispatch general / conversational response
        if task.action == TaskAction.ANSWER_GENERAL:
            return self._execute_answer_general(task, situation, context, start_time)

        # 4. Dispatch multi-concept comparison
        if task.action == TaskAction.COMPARE_CONCEPTS:
            return self._execute_compare_concepts(task, situation, context, start_time, style, act_engine, reas_engine, ans_engine, synth)

        # 5. Dispatch relationship derivation
        if task.action == TaskAction.DERIVE_RELATIONSHIP:
            return self._execute_derive_relationship(task, situation, context, start_time, style, act_engine, reas_engine, ans_engine, synth)

        # 6. Default: single-concept explanation
        return self._execute_explain_concept(task, situation, context, start_time, style, act_engine, reas_engine, ans_engine, synth)

    # ─────────────────────────────────────────────────────────────
    # HANDLER 1: REFUSALS & DIAGNOSTIC REPORTING
    # ─────────────────────────────────────────────────────────────

    def _execute_refusal(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
    ) -> Answer:
        exec_time = (time.time() - start_time) * 1000

        if task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT:
            reason = "The input contains referential terms requiring preceding discourse context that is currently unavailable."
            assumptions_text = "\n".join(f"- {a.statement}" for a in situation.assumptions) if situation.assumptions else "None"
            ans = Answer(
                direct_answer="I cannot answer because the question refers to an antecedent or context that is not provided.",
                sections=[
                    AnswerSection("Refusal Reason", reason),
                    AnswerSection("Assumptions", assumptions_text),
                ],
                explanation=Explanation("Refusal due to missing conversation context.", 0),
                evidence=[e.description for e in situation.evidence],
                confidence=ConfidenceSummary(0.0, "Refusal: Insufficient context"),
                metadata=AnswerMetadata([], exec_time),
                assumptions=[a.statement for a in situation.assumptions],
                known_limitations=["Discourse context is not currently persistent across turns."],
            )
            exec_res = CognitiveExecutionResult(
                task_id=task.id,
                task_action=task.action,
                situation_id=situation.id,
                refusal_reason="Insufficient Context",
                confidence_score=0.0,
                confidence_description="Refusal: Insufficient context",
                execution_time_ms=exec_time,
                is_success=False,
            )
            setattr(ans, "cognitive_execution_result", exec_res)
            setattr(ans, "cognitive_situation", situation)
            setattr(ans, "cognitive_task", task)
            return ans

        if task.action == TaskAction.REPORT_AMBIGUITY:
            ambiguity_details = "\n".join(f"- {a}" for a in situation.ambiguities)
            ans = Answer(
                direct_answer=f"Your request is ambiguous because the term matches multiple concepts in the knowledge base. Please specify which concept you mean.\n\n{ambiguity_details}",
                sections=[
                    AnswerSection("Ambiguity Alert", ambiguity_details),
                ],
                explanation=Explanation("Refusal due to ambiguous concept mention.", 0),
                evidence=list(situation.ambiguities),
                confidence=ConfidenceSummary(0.0, "Refusal: Ambiguous concept reference"),
                metadata=AnswerMetadata([], exec_time),
                assumptions=[],
                known_limitations=["Ambiguous terms are not guessed silently."],
            )
            exec_res = CognitiveExecutionResult(
                task_id=task.id,
                task_action=task.action,
                situation_id=situation.id,
                refusal_reason="Ambiguous concept reference",
                confidence_score=0.0,
                confidence_description="Refusal: Ambiguous concept reference",
                execution_time_ms=exec_time,
                is_success=False,
            )
            setattr(ans, "cognitive_execution_result", exec_res)
            setattr(ans, "cognitive_situation", situation)
            setattr(ans, "cognitive_task", task)
            return ans

        # REPORT_UNKNOWN
        missing = ", ".join(situation.unresolved_entities) if situation.unresolved_entities else "requested topic"
        ans = Answer(
            direct_answer=f"Unable to resolve concept '{missing}' in the Universal Knowledge Model. No verified conclusions available.",
            sections=[
                AnswerSection("Missing Knowledge", f"Concept definition for '{missing}' is not stored in the knowledge base. No verified conclusions can be derived."),
            ],
            explanation=Explanation(f"Concept '{missing}' is absent from UKM.", 0),
            evidence=[f"Unresolved entities: {situation.unresolved_entities}"],
            confidence=ConfidenceSummary(0.0, "Refusal: Knowledge unavailable"),
            metadata=AnswerMetadata([], exec_time),
            assumptions=[],
            known_limitations=["The system does not fabricate ungrounded domain knowledge."],
        )
        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            refusal_reason=f"Unknown concept: {missing}",
            confidence_score=0.0,
            confidence_description="Refusal: Knowledge unavailable",
            execution_time_ms=exec_time,
            is_success=False,
        )
        setattr(ans, "cognitive_execution_result", exec_res)
        setattr(ans, "cognitive_situation", situation)
        setattr(ans, "cognitive_task", task)
        return ans

    # ─────────────────────────────────────────────────────────────
    # HANDLER 1.5: MATHEMATICAL & GENERAL DISPATCH
    # ─────────────────────────────────────────────────────────────

    def _execute_solve_mathematics(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
    ) -> Answer:
        exec_time = (time.time() - start_time) * 1000
        raw_text = situation.raw_input.original_text
        from hsci.reasoning.universal_math_engine import UniversalMathEngine
        from hsci.neural.entity_extractor import EntityExtractor
        math_engine = UniversalMathEngine()

        # Extract named quantities ("velocity is 60", "time is 2") so
        # UniversalMathEngine's formula-inference strategy (distance = rate *
        # time, tax = base * rate, etc.) has something to substitute into --
        # without this it only ever sees an empty dict and that strategy can
        # never fire, even for problems it would otherwise solve correctly.
        entities = EntityExtractor().extract(raw_text)

        res = math_engine.solve_from_text(raw_text, entities=entities)
        if not res.solved:
            res = math_engine.solve_expression(raw_text)

        if res.solved:
            direct_ans = f"The computed mathematical solution is **{res.answer_display}**."
            steps_text = "\n".join(f"- {s}" for s in res.steps) if res.steps else f"- Computed via {res.method}"
            sections = [
                AnswerSection("Mathematical Derivation", steps_text),
                AnswerSection("Method & System", f"- Formal Solver: `UniversalMathEngine` (SymPy Computer Algebra System)\n- Execution Mode: `{res.method}`")
            ]
            ans = Answer(
                direct_answer=direct_ans,
                sections=sections,
                explanation=Explanation(f"Mathematical problem solved via {res.method}: {res.answer_display}", 1),
                evidence=[f"SymPy evaluation: {res.method}", f"Variables: {res.variables}"],
                confidence=ConfidenceSummary(1.0, f"Verified: Computed via {res.method}"),
                metadata=AnswerMetadata(["mathematics", res.method], exec_time),
                assumptions=[],
                known_limitations=[],
            )
        else:
            ans = Answer(
                direct_answer=f"Could not compute a verified solution for expression: '{raw_text}'.",
                sections=[
                    AnswerSection("Mathematical Solver Status", f"The mathematical expression could not be reduced by the Computer Algebra System: {res.error or 'Invalid mathematical syntax'}."),
                ],
                explanation=Explanation("Mathematical parsing or solving failed.", 0),
                evidence=[f"Error: {res.error}"],
                confidence=ConfidenceSummary(0.0, "Refusal: Unsolvable mathematical input"),
                metadata=AnswerMetadata(["mathematics"], exec_time),
                assumptions=[],
                known_limitations=["Requires standard mathematical syntax (e.g. 3*x + 12 = 0, 25 * 4, solve x^2 - 4 = 0)."],
            )

        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            confidence_score=ans.confidence.score,
            confidence_description=ans.confidence.description,
            execution_time_ms=exec_time,
            is_success=ans.confidence.score > 0.0,
        )
        setattr(ans, "cognitive_execution_result", exec_res)
        setattr(ans, "cognitive_situation", situation)
        setattr(ans, "cognitive_task", task)
        return ans

    def _execute_answer_general(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
    ) -> Answer:
        exec_time = (time.time() - start_time) * 1000
        direct_ans = (
            "Hello! I am the **HSCI Neuro-Symbolic Cognitive Brain (v4.0)**. "
            "I combine neural language perception with formal Universal Knowledge Model (UKM) reasoning, "
            "SMT logic verification (Z3), and Computer Algebra (SymPy)."
        )
        sections = [
            AnswerSection(
                "Core Capabilities",
                "- **Concept Explanations**: Ask definitions grounded in UKM (e.g., `What is a Java interface?`)\n"
                "- **Comparative Analysis**: Compare multiple concepts (e.g., `Compare Java interface and class`)\n"
                "- **Multi-Premise Reasoning**: Deduce transitive theorems (e.g., `What is the relationship between Java Interface and Abstraction?`)\n"
                "- **Symbolic Mathematics**: Solve equations & arithmetic via SymPy CAS (e.g., `solve 3*x + 12 = 0`, `calculate 144 / 12`, `what is 25 * 4 + 50`)\n"
                "- **Multi-Task Planning**: Decompose complex compound requests with dependency tracking"
            ),
            AnswerSection(
                "Epistemic Integrity Policy",
                "- **Zero Hallucination**: I answer from formal proofs and verified knowledge; unknown concepts are refused with 0% confidence."
            )
        ]
        ans = Answer(
            direct_answer=direct_ans,
            sections=sections,
            explanation=Explanation("General conversational and system capability overview.", 1),
            evidence=["System manifest: HSCI V4 Neuro-Symbolic Cognitive Pipeline"],
            confidence=ConfidenceSummary(1.0, "Verified: General overview"),
            metadata=AnswerMetadata(["general", "overview"], exec_time),
            assumptions=[],
            known_limitations=[],
        )
        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            confidence_score=1.0,
            confidence_description="Verified: General overview",
            execution_time_ms=exec_time,
            is_success=True,
        )
        setattr(ans, "cognitive_execution_result", exec_res)
        setattr(ans, "cognitive_situation", situation)
        setattr(ans, "cognitive_task", task)
        return ans

    # ─────────────────────────────────────────────────────────────
    # HANDLER 2: EXPLAIN_CONCEPT
    # ─────────────────────────────────────────────────────────────

    def _execute_explain_concept(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
        style: str,
        act_engine: ConceptActivationEngine,
        reas_engine: CognitiveReasoningEngine,
        ans_engine: AnswerGenerationEngine,
        synth: ExplanatoryAnswerSynthesizer,
    ) -> Answer:
        seeds = self._extract_seed_names(task, situation)
        workspace_concepts, activation_scores = self._activate_and_assemble_workspace(seeds, context, act_engine)

        reasoning_context = ReasoningContext(goal=f"Explain: {task.primary_target}")
        reasoning_result = reas_engine.reason(workspace_concepts, context, reasoning_context)
        base_answer = ans_engine.generate(reasoning_result, context, style=style)

        # Build understanding bridge for synthesizer
        from hsci.knowledge.understanding_engine import UnderstandingResult
        understanding_bridge = UnderstandingResult(
            intent="ExplainConcept",
            seed_concepts=seeds,
            entities={ge.mention: "concept" for ge in situation.grounded_entities},
            keywords=[ge.mention for ge in situation.grounded_entities],
            constraints=[],
            confidence=situation.grounding_confidence,
            ambiguities=situation.ambiguities,
            normalized_query=situation.raw_input.normalized_text,
            explanations={},
        )

        answer = synth.synthesize(
            understanding=understanding_bridge,
            workspace_concepts=workspace_concepts,
            activation_scores=activation_scores,
            reasoning_result=reasoning_result,
            base_answer=base_answer,
            context=context,
        )

        exec_time = (time.time() - start_time) * 1000
        retrieved_defs = {
            c.name: (c.abstract_rule or "").strip()
            for c in workspace_concepts
            if (c.abstract_rule or "").strip()
        }
        derived_concls = [
            {"statement": c.statement, "rule": getattr(c, "rule_name", "GeneralizationTransitivity"), "premises": getattr(c, "premises", [])}
            for c in reasoning_result.conclusions
            if getattr(c, "derived", False)
        ]
        stored_rels = [
            {"statement": c.statement, "rule": getattr(c, "rule_name", "StoredGeneralization")}
            for c in reasoning_result.conclusions
            if not getattr(c, "derived", False)
        ]

        conf_score = getattr(getattr(answer, "confidence", None), "score", 1.0)
        conf_desc = getattr(getattr(answer, "confidence", None), "description", "Standard")

        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            grounded_concepts=seeds,
            retrieved_definitions=retrieved_defs,
            derived_conclusions=derived_concls,
            stored_relationships=stored_rels,
            confidence_score=conf_score,
            confidence_description=conf_desc,
            execution_time_ms=exec_time,
            is_success=True,
        )
        setattr(answer, "cognitive_execution_result", exec_res)
        setattr(answer, "cognitive_situation", situation)
        setattr(answer, "cognitive_task", task)
        return answer

    # ─────────────────────────────────────────────────────────────
    # HANDLER 3: DERIVE_RELATIONSHIP
    # ─────────────────────────────────────────────────────────────

    def _execute_derive_relationship(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
        style: str,
        act_engine: ConceptActivationEngine,
        reas_engine: CognitiveReasoningEngine,
        ans_engine: AnswerGenerationEngine,
        synth: ExplanatoryAnswerSynthesizer,
    ) -> Answer:
        seeds = self._extract_seed_names(task, situation)
        workspace_concepts, activation_scores = self._activate_and_assemble_workspace(seeds, context, act_engine)

        source_name = task.primary_target or (seeds[0] if seeds else "")
        target_name = task.secondary_targets[0] if task.secondary_targets else (seeds[1] if len(seeds) > 1 else "")

        reasoning_context = ReasoningContext(goal=f"Derive relationship between {source_name} and {target_name}")
        reasoning_result = reas_engine.reason(workspace_concepts, context, reasoning_context)
        base_answer = ans_engine.generate(reasoning_result, context, style=style)

        # Search for conclusions connecting source and target
        matching_derived: List[Conclusion] = []
        matching_stored: List[Conclusion] = []

        s_lower = source_name.lower()
        t_lower = target_name.lower()

        for c in reasoning_result.conclusions:
            stmt_lower = c.statement.lower()
            if s_lower in stmt_lower and t_lower in stmt_lower and "co-exist under namespace" not in stmt_lower:
                if getattr(c, "derived", False):
                    matching_derived.append(c)
                else:
                    matching_stored.append(c)

        knowledge_sources: List[KnowledgeSource] = []
        sections: List[AnswerSection] = []

        # Retrieve definitions of source and target
        source_concept = self._find_concept_by_name(workspace_concepts, source_name)
        target_concept = self._find_concept_by_name(workspace_concepts, target_name)

        if source_concept and (source_concept.abstract_rule or "").strip():
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="definition",
                source_concept_id=source_concept.id,
                source_concept_name=source_concept.name,
                source_provenance=self._provenance(source_concept.id),
                content=source_concept.abstract_rule.strip(),
            ))
        if target_concept and (target_concept.abstract_rule or "").strip():
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="definition",
                source_concept_id=target_concept.id,
                source_concept_name=target_concept.name,
                source_provenance=self._provenance(target_concept.id),
                content=target_concept.abstract_rule.strip(),
            ))

        if matching_derived:
            top_concl = matching_derived[0]
            rule = getattr(top_concl, "rule_name", "GeneralizationTransitivity")
            premises = getattr(top_concl, "premises", [])
            direct_answer = f"{top_concl.statement} (derived via {rule} from premises: {premises})."
            sections.append(AnswerSection(
                "Derived Relationship",
                f"- [DERIVED] {top_concl.statement}\n  * Inference Rule: `{rule}`\n  * Premises: {premises}\n  * Confidence: {top_concl.confidence:.2f}"
            ))
            prov = {
                "rule": rule,
                "premises": premises,
                "derived": True,
                "depth": getattr(top_concl, "depth", 1),
                "source_type": "derived",
            }
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="derived_relationship",
                reasoning_conclusion=top_concl.statement,
                reasoning_rule=rule,
                reasoning_confidence=top_concl.confidence,
                reasoning_evidence=list(top_concl.evidence),
                source_provenance=prov,
            ))
            confidence = ConfidenceSummary(top_concl.confidence, "High: Genuinely derived from UKM axioms")

        elif matching_stored:
            top_concl = matching_stored[0]
            rule = getattr(top_concl, "rule_name", "StoredGeneralization")
            direct_answer = f"{top_concl.statement} (verified stored relationship)."
            sections.append(AnswerSection(
                "Stored Relationship",
                f"- {top_concl.statement} (rule: {rule}, confidence: {top_concl.confidence:.2f})"
            ))
            prov = {
                "rule": rule,
                "premises": [],
                "derived": False,
                "depth": 0,
                "source_type": "knowledge",
            }
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="reasoned_relationship",
                reasoning_conclusion=top_concl.statement,
                reasoning_rule=rule,
                reasoning_confidence=top_concl.confidence,
                reasoning_evidence=list(top_concl.evidence),
                source_provenance=prov,
            ))
            confidence = ConfidenceSummary(top_concl.confidence, "High: Direct stored relationship in UKM")

        else:
            # No relationship found connecting source and target
            direct_answer = f"No direct or derived relationship could be established between '{source_name}' and '{target_name}' based on verified Universal Knowledge Model axioms."
            sections.append(AnswerSection(
                "Relationship Status",
                f"Neither direct storage links nor transitive generalizations connect '{source_name}' and '{target_name}' in the active knowledge workspace."
            ))
            confidence = ConfidenceSummary(0.0, "Refusal: Unsupported relationship")

        # Also add all other supporting workspace conclusions
        rel_sources, rel_lines = self._format_supporting_relationships(reasoning_result)
        knowledge_sources.extend(rel_sources)
        if rel_lines:
            sections.append(AnswerSection("All Workspace Relationships", "\n".join(rel_lines)))

        exec_time = (time.time() - start_time) * 1000
        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            grounded_concepts=seeds,
            retrieved_definitions={
                c.name: (c.abstract_rule or "").strip()
                for c in workspace_concepts
                if (c.abstract_rule or "").strip()
            },
            derived_conclusions=[
                {"statement": c.statement, "rule": getattr(c, "rule_name", "GeneralizationTransitivity"), "premises": getattr(c, "premises", [])}
                for c in reasoning_result.conclusions
                if getattr(c, "derived", False)
            ],
            stored_relationships=[
                {"statement": c.statement, "rule": getattr(c, "rule_name", "StoredGeneralization")}
                for c in reasoning_result.conclusions
                if not getattr(c, "derived", False)
            ],
            confidence_score=confidence.score,
            confidence_description=confidence.description,
            execution_time_ms=exec_time,
            is_success=confidence.score > 0.0,
        )

        ans = ExplanatoryAnswer(
            base=base_answer,
            direct_answer=direct_answer,
            sections=sections,
            definition=None,
            primary_concept_id=source_concept.id if source_concept else None,
            primary_concept_name=source_name,
            knowledge_sources=knowledge_sources,
            confidence=confidence,
        )
        setattr(ans, "cognitive_execution_result", exec_res)
        setattr(ans, "cognitive_situation", situation)
        setattr(ans, "cognitive_task", task)
        return ans

    # ─────────────────────────────────────────────────────────────
    # HANDLER 4: COMPARE_CONCEPTS
    # ─────────────────────────────────────────────────────────────

    def _execute_compare_concepts(
        self,
        task: CognitiveTask,
        situation: CognitiveSituation,
        context: CognitiveContext,
        start_time: float,
        style: str,
        act_engine: ConceptActivationEngine,
        reas_engine: CognitiveReasoningEngine,
        ans_engine: AnswerGenerationEngine,
        synth: ExplanatoryAnswerSynthesizer,
    ) -> Answer:
        seeds = self._extract_seed_names(task, situation)
        workspace_concepts, activation_scores = self._activate_and_assemble_workspace(seeds, context, act_engine)

        concept_a_name = task.primary_target or (seeds[0] if seeds else "")
        concept_b_name = task.secondary_targets[0] if task.secondary_targets else (seeds[1] if len(seeds) > 1 else "")

        reasoning_context = ReasoningContext(goal=f"Compare {concept_a_name} and {concept_b_name}")
        reasoning_result = reas_engine.reason(workspace_concepts, context, reasoning_context)
        base_answer = ans_engine.generate(reasoning_result, context, style=style)

        concept_a = self._find_concept_by_name(workspace_concepts, concept_a_name)
        concept_b = self._find_concept_by_name(workspace_concepts, concept_b_name)

        knowledge_sources: List[KnowledgeSource] = []
        sections: List[AnswerSection] = []

        def_a = (concept_a.abstract_rule or "").strip() if concept_a else ""
        def_b = (concept_b.abstract_rule or "").strip() if concept_b else ""

        if concept_a and def_a:
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="definition",
                source_concept_id=concept_a.id,
                source_concept_name=concept_a.name,
                source_provenance=self._provenance(concept_a.id),
                content=def_a,
            ))
        if concept_b and def_b:
            knowledge_sources.append(KnowledgeSource(
                knowledge_type="definition",
                source_concept_id=concept_b.id,
                source_concept_name=concept_b.name,
                source_provenance=self._provenance(concept_b.id),
                content=def_b,
            ))

        # Check if UKM contains enough knowledge for comparison
        if not def_a and not def_b:
            direct_answer = f"Insufficient knowledge in Universal Knowledge Model to compare '{concept_a_name}' and '{concept_b_name}'."
            sections.append(AnswerSection("Comparison Status", "Neither concept has stored definitions in the UKM."))
            confidence = ConfidenceSummary(0.0, "Refusal: Insufficient comparison knowledge")
        else:
            # Build structured comparison based ONLY on real knowledge and reasoning conclusions
            def_lines = []
            if def_a:
                def_lines.append(f"- **{concept_a_name}**: {def_a}")
            else:
                def_lines.append(f"- **{concept_a_name}**: (No stored definition in UKM)")
            if def_b:
                def_lines.append(f"- **{concept_b_name}**: {def_b}")
            else:
                def_lines.append(f"- **{concept_b_name}**: (No stored definition in UKM)")

            sections.append(AnswerSection("Definitions", "\n".join(def_lines)))

            # Analyze structural generalizations for Concept A and Concept B
            gen_a = [
                c for c in reasoning_result.conclusions
                if concept_a_name.lower() in c.statement.lower() and "generalizes to" in c.statement.lower()
            ]
            gen_b = [
                c for c in reasoning_result.conclusions
                if concept_b_name.lower() in c.statement.lower() and "generalizes to" in c.statement.lower()
            ]

            # Find shared generalization targets
            targets_a = {self._extract_target(c.statement) for c in gen_a} - {None}
            targets_b = {self._extract_target(c.statement) for c in gen_b} - {None}
            shared_targets = targets_a.intersection(targets_b)

            structural_lines = []
            if shared_targets:
                for st in shared_targets:
                    structural_lines.append(f"- **Shared Generalization**: Both `{concept_a_name}` and `{concept_b_name}` generalize to `{st}`.")
            
            for c in gen_a:
                rule = getattr(c, "rule_name", "Generalization")
                derived_flag = "[DERIVED] " if getattr(c, "derived", False) else ""
                structural_lines.append(f"- `{concept_a_name}`: {derived_flag}{c.statement} (rule: {rule})")
            for c in gen_b:
                rule = getattr(c, "rule_name", "Generalization")
                derived_flag = "[DERIVED] " if getattr(c, "derived", False) else ""
                structural_lines.append(f"- `{concept_b_name}`: {derived_flag}{c.statement} (rule: {rule})")

            if structural_lines:
                sections.append(AnswerSection("Structural Relationships & Generalizations", "\n".join(structural_lines)))

            # Format direct answer
            direct_answer = f"Comparison of {concept_a_name} and {concept_b_name}:\n" + "\n".join(def_lines)
            confidence = ConfidenceSummary(0.90, "High: Verified comparative definitions and generalizations")

        # Attach reasoned relationships to knowledge sources
        rel_sources, _ = self._format_supporting_relationships(reasoning_result)
        knowledge_sources.extend(rel_sources)

        exec_time = (time.time() - start_time) * 1000
        exec_res = CognitiveExecutionResult(
            task_id=task.id,
            task_action=task.action,
            situation_id=situation.id,
            grounded_concepts=seeds,
            retrieved_definitions={
                c.name: (c.abstract_rule or "").strip()
                for c in workspace_concepts
                if (c.abstract_rule or "").strip()
            },
            derived_conclusions=[
                {"statement": c.statement, "rule": getattr(c, "rule_name", "GeneralizationTransitivity"), "premises": getattr(c, "premises", [])}
                for c in reasoning_result.conclusions
                if getattr(c, "derived", False)
            ],
            stored_relationships=[
                {"statement": c.statement, "rule": getattr(c, "rule_name", "StoredGeneralization")}
                for c in reasoning_result.conclusions
                if not getattr(c, "derived", False)
            ],
            confidence_score=confidence.score,
            confidence_description=confidence.description,
            execution_time_ms=exec_time,
            is_success=confidence.score > 0.0,
        )

        ans = ExplanatoryAnswer(
            base=base_answer,
            direct_answer=direct_answer,
            sections=sections,
            definition=def_a or def_b or None,
            primary_concept_id=concept_a.id if concept_a else (concept_b.id if concept_b else None),
            primary_concept_name=f"{concept_a_name} vs {concept_b_name}",
            knowledge_sources=knowledge_sources,
            confidence=confidence,
        )
        setattr(ans, "cognitive_execution_result", exec_res)
        setattr(ans, "cognitive_situation", situation)
        setattr(ans, "cognitive_task", task)
        return ans

    # ─────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────

    def _extract_seed_names(self, task: CognitiveTask, situation: CognitiveSituation) -> List[str]:
        seeds = []
        for ge in situation.grounded_entities:
            if ge.status == GroundingStatus.RESOLVED and ge.canonical_name:
                if ge.canonical_name not in seeds:
                    seeds.append(ge.canonical_name)
        if not seeds and task.primary_target:
            seeds.append(task.primary_target)
        for st in task.secondary_targets:
            if st not in seeds:
                seeds.append(st)
        return seeds

    def _activate_and_assemble_workspace(
        self, seeds: List[str], context: CognitiveContext, activation_engine: Optional[ConceptActivationEngine] = None
    ) -> Tuple[List[Concept], Dict[str, float]]:
        act_engine = activation_engine or self.activation_engine
        activated = act_engine.activate_concepts(seeds, context)
        workspace_concepts: List[Concept] = []
        activation_scores: Dict[str, float] = {}

        for activated_concept in getattr(activated, "concepts", []):
            resolved = self.manager.get_concept(activated_concept.concept.id)
            if resolved is not None:
                workspace_concepts.append(resolved)
                activation_scores[resolved.id] = getattr(activated_concept, "score", 1.0)

        return workspace_concepts, activation_scores

    def _find_concept_by_name(self, concepts: List[Concept], name: str) -> Optional[Concept]:
        if not name:
            return None
        n_lower = name.lower()
        for c in concepts:
            if c.name.lower() == n_lower:
                return self.manager.get_concept(c.id) or c
        # Fallback to direct manager lookup
        c_direct = self.manager.get_concept_by_name(name)
        if c_direct:
            return c_direct
        aliases = self.manager.concept_store.repository.resolve_alias(name)
        if aliases:
            return self.manager.get_concept(aliases[0].id) or aliases[0]
        return None

    def _provenance(self, concept_id: str) -> Optional[Dict[str, Any]]:
        try:
            history = self.manager.concept_store.get_history(concept_id)
            return history[0] if history else None
        except Exception:
            return None

    def _extract_target(self, statement: str) -> Optional[str]:
        if "generalizes to" in statement.lower():
            parts = statement.split("generalizes to")
            if len(parts) == 2:
                return parts[1].strip(" .")
        return None

    def _format_supporting_relationships(
        self, reasoning_result: ReasoningResult
    ) -> Tuple[List[KnowledgeSource], List[str]]:
        sources: List[KnowledgeSource] = []
        lines: List[str] = []

        for c in reasoning_result.conclusions:
            rule = getattr(c, "rule_name", "GeneralizationTransitivity" if getattr(c, "derived", False) else "StoredGeneralization")
            is_derived = getattr(c, "derived", False)
            k_type = "derived_relationship" if is_derived else "reasoned_relationship"
            prov = {
                "rule": rule,
                "premises": getattr(c, "premises", []),
                "derived": is_derived,
                "depth": getattr(c, "depth", 0),
                "source_type": "derived" if is_derived else "knowledge",
            }
            sources.append(KnowledgeSource(
                knowledge_type=k_type,
                reasoning_conclusion=c.statement,
                reasoning_rule=rule,
                reasoning_confidence=c.confidence,
                reasoning_evidence=list(c.evidence),
                source_provenance=prov,
            ))
            if is_derived:
                lines.append(f"- [DERIVED] {c.statement} (rule: {rule}, premises: {getattr(c, 'premises', [])}, confidence: {c.confidence:.2f})")
            else:
                lines.append(f"- {c.statement} (rule: {rule}, confidence: {c.confidence:.2f})")

        return sources, lines
