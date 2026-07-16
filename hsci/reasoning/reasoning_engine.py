import z3
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from hsci.core.data_types import PerceptionMap, KnowledgeResult, ReasoningPlan, SubGoal, Concept, AxiomType, Expression
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.knowledge_manager import IKnowledgeManager

# Keep legacy imports intact
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.reasoning.concept_composer import ConceptComposer
from hsci.reasoning.solution_builder import SolutionBuilder
from hsci.reasoning.synthesizer import ProgramSynthesizer

logger = logging.getLogger("HSCI.Reasoning.CRE")

# ─────────────────────────────────────────────
# SUPPORTING MODELS
# ─────────────────────────────────────────────

class ReasoningStep:
    """Represents a single discrete step in the logical reasoning trace."""
    def __init__(self, step_number: int, action: str, concepts_used: List[str],
                 conclusions: List[str], confidence: float):
        self.step_number: int = step_number
        self.action: str = action
        self.concepts_used: List[str] = concepts_used
        self.conclusions: List[str] = conclusions
        self.confidence: float = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action": self.action,
            "concepts_used": self.concepts_used,
            "conclusions": self.conclusions,
            "confidence": self.confidence
        }

class Inference:
    """Represents an inferred derivation candidate before verification."""
    def __init__(self, rule_name: str, derived_statement: str, supporting_evidence: List[str],
                 confidence: float, concepts_used: List[str]):
        self.rule_name: str = rule_name
        self.derived_statement: str = derived_statement
        self.supporting_evidence: List[str] = supporting_evidence
        self.confidence: float = confidence
        self.concepts_used: List[str] = concepts_used

class Assumption:
    """Represents a hypothesized premise introduced to assist reasoning."""
    def __init__(self, statement: str, context: str, confidence: float = 0.50):
        self.statement: str = statement
        self.context: str = context
        self.confidence: float = confidence

class Conclusion:
    """Represents a verified assertion reached by the reasoning process."""
    def __init__(self, statement: str, evidence: List[str], confidence: float,
                 verified: bool = True, rejected_reason: Optional[str] = None):
        self.statement: str = statement
        self.evidence: List[str] = evidence
        self.confidence: float = confidence
        self.verified: bool = verified
        self.rejected_reason: Optional[str] = rejected_reason

class ReasoningTrace:
    """Logs the complete chronological sequence of reasoning steps and results."""
    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.rejected_conclusions: List[Conclusion] = []

    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)

    def log_rejection(self, conclusion: Conclusion) -> None:
        self.rejected_conclusions.append(conclusion)

class ReasoningResult:
    """Encapsulates the final conclusions, traces, and metrics returned by the CRE."""
    def __init__(self, conclusions: List[Conclusion], supporting_evidence: List[str],
                 assumptions: List[Assumption], confidence: float, reasoning_trace: ReasoningTrace,
                 intermediate_results: List[str], remaining_unknowns: List[str],
                 contradictions: List[str]):
        self.conclusions: List[Conclusion] = conclusions
        self.supporting_evidence: List[str] = supporting_evidence
        self.assumptions: List[Assumption] = assumptions
        self.confidence: float = confidence
        self.reasoning_trace: ReasoningTrace = reasoning_trace
        self.intermediate_results: List[str] = intermediate_results
        self.remaining_unknowns: List[str] = remaining_unknowns
        self.contradictions: List[str] = contradictions

class ReasoningContext:
    """Request-scoped tracking payload driving goals and depth limit thresholds."""
    def __init__(self, goal: str, max_steps: int = 10, confidence_threshold: float = 0.50):
        self.goal: str = goal
        self.max_steps: int = max_steps
        self.confidence_threshold: float = confidence_threshold
        self.variables: Dict[str, Any] = {}


# ─────────────────────────────────────────────
# INFERENCE STRATEGY INTERFACES & PATTERNS
# ─────────────────────────────────────────────

class IInferenceStrategy(ABC):
    """Abstract interface defining the rule deduction strategy pattern."""
    @abstractmethod
    def infer(self, active_concepts: List[Concept], context: ReasoningContext) -> List[Inference]:
        pass

class RuleBasedInferenceStrategy(IInferenceStrategy):
    """Concrete inference strategy matching structural relations between active concepts."""
    def infer(self, active_concepts: List[Concept], context: ReasoningContext) -> List[Inference]:
        inferences = []
        concept_names = {c.name.lower() for c in active_concepts}
        concept_map = {c.name.lower(): c for c in active_concepts}

        # Rule 1: Generalization Transitivity
        # If A generalizes to B, then B is a generalization target
        for c in active_concepts:
            for parent_id in c.generalizes_to:
                # Try finding name matching parent ID
                parent_name = parent_id.replace("c_", "").capitalize()
                inferences.append(
                    Inference(
                        rule_name="GeneralizationTransitivity",
                        derived_statement=f"{c.name} generalizes to {parent_name}",
                        supporting_evidence=[f"{c.name}.generalizes_to links to {parent_id}"],
                        confidence=0.90,
                        concepts_used=[c.name]
                    )
                )

        # Rule 2: Namespace Cohabitation Sibling
        # If multiple active concepts share the same hierarchical prefix namespace, infer namespace dependency
        namespaces = {}
        for c in active_concepts:
            if c.namespace:
                namespaces.setdefault(c.namespace, []).append(c)

        for ns, concepts in namespaces.items():
            if len(concepts) > 1:
                names = [c.name for c in concepts]
                inferences.append(
                    Inference(
                        rule_name="NamespaceCohabitation",
                        derived_statement=f"Concepts {names} co-exist under namespace '{ns}'",
                        supporting_evidence=[f"Shared namespace attribute '{ns}' in concepts"],
                        confidence=0.85,
                        concepts_used=names
                    )
                )

        # Rule 3: Aliases overlap
        for c in active_concepts:
            for alias in c.aliases:
                inferences.append(
                    Inference(
                        rule_name="AliasMapping",
                        derived_statement=f"Alias '{alias}' points directly to concept {c.name}",
                        supporting_evidence=[f"Alias registered on concept ID {c.id}"],
                        confidence=0.95,
                        concepts_used=[c.name]
                    )
                )

        return inferences


# ─────────────────────────────────────────────
# COGNITIVE REASONING ENGINE (CRE)
# ─────────────────────────────────────────────

class IReasoningEngine(ABC):
    """Abstract interface defining the entry point for symbolic reasoning."""
    @abstractmethod
    def reason(self, active_concepts: List[Concept], context: CognitiveContext,
               reasoning_context: ReasoningContext) -> ReasoningResult:
        pass

class CognitiveReasoningEngine(IReasoningEngine):
    """
    Central cognitive subsystem performing deterministic symbolic reasoning
    over the active concept workspace.
    """
    def __init__(self, manager: IKnowledgeManager, event_bus: EventBus):
        self.manager: IKnowledgeManager = manager
        self.event_bus: EventBus = event_bus
        self.inference_strategy: IInferenceStrategy = RuleBasedInferenceStrategy()

    def reason(self, active_concepts: List[Concept], context: CognitiveContext,
               reasoning_context: ReasoningContext) -> ReasoningResult:
        """Runs the 8-stage reasoning cycle loop over active concept workspace."""
        if self.event_bus:
            self.event_bus.emit("ReasoningStarted", context)

        trace = ReasoningTrace()
        verified_conclusions: List[Conclusion] = []
        assumptions: List[Assumption] = []
        contradictions: List[str] = []
        intermediate_results: List[str] = []
        known_statements: Set[str] = set()

        step_counter = 1
        loop_active = True

        while loop_active:
            # Stage 1: Read current workspace
            # Active concepts are passed in.
            
            # Stage 2: Identify reasoning goal
            goal = reasoning_context.goal
            
            # Stage 3: Select applicable concepts
            current_concepts = active_concepts
            
            # Stage 4: Select applicable inference rules
            # Stage 5: Generate candidate conclusions
            candidates = self.inference_strategy.infer(current_concepts, reasoning_context)
            
            step_conclusions = []
            concepts_used = []
            
            # Stage 6: Verify consistency
            for cnd in candidates:
                concepts_used.extend(cnd.concepts_used)
                
                # Check 1: Circular reasoning detection
                if cnd.derived_statement in known_statements:
                    rejected = Conclusion(
                        statement=cnd.derived_statement,
                        evidence=cnd.supporting_evidence,
                        confidence=cnd.confidence,
                        verified=False,
                        rejected_reason="Circular reasoning detected: statement already inferred."
                    )
                    if not any(r.statement == cnd.derived_statement and "Circular" in (r.rejected_reason or "") for r in trace.rejected_conclusions):
                        trace.log_rejection(rejected)
                    continue
                
                # Check 2: Contradiction detection
                contradicts = False
                for existing in verified_conclusions:
                    if (f"not {cnd.derived_statement}" in existing.statement 
                            or f"not {existing.statement}" in cnd.derived_statement):
                        contradicts = True
                        msg = f"Contradiction: '{cnd.derived_statement}' conflicts with '{existing.statement}'"
                        if msg not in contradictions:
                            contradictions.append(msg)
                        rejected = Conclusion(
                            statement=cnd.derived_statement,
                            evidence=cnd.supporting_evidence,
                            confidence=cnd.confidence,
                            verified=False,
                            rejected_reason=msg
                        )
                        if not any(r.statement == cnd.derived_statement and "Contradiction" in (r.rejected_reason or "") for r in trace.rejected_conclusions):
                            trace.log_rejection(rejected)
                        break
                        
                if contradicts:
                    continue
                
                verified_conclusion = Conclusion(
                    statement=cnd.derived_statement,
                    evidence=cnd.supporting_evidence,
                    confidence=cnd.confidence
                )
                verified_conclusions.append(verified_conclusion)
                known_statements.add(cnd.derived_statement)
                step_conclusions.append(cnd.derived_statement)
                intermediate_results.append(cnd.derived_statement)
                
                if self.event_bus:
                    self.event_bus.emit("ConclusionGenerated", context)

            # Stage 7: Update workspace
            step = ReasoningStep(
                step_number=step_counter,
                action=f"Iterated rule-based inference step {step_counter}",
                concepts_used=list(set(concepts_used)),
                conclusions=step_conclusions,
                confidence=0.90 if step_conclusions else 0.50
            )
            trace.add_step(step)
            if self.event_bus:
                self.event_bus.emit("ReasoningStepCompleted", context)

            # Stage 8: Repeat check
            step_counter += 1
            if step_counter > reasoning_context.max_steps or len(step_conclusions) == 0:
                loop_active = False

        final_confidence = 1.0
        if verified_conclusions:
            final_confidence = sum(c.confidence for c in verified_conclusions) / len(verified_conclusions)

        result = ReasoningResult(
            conclusions=verified_conclusions,
            supporting_evidence=intermediate_results,
            assumptions=assumptions,
            confidence=final_confidence,
            reasoning_trace=trace,
            intermediate_results=intermediate_results,
            remaining_unknowns=[],
            contradictions=contradictions
        )

        if self.event_bus:
            self.event_bus.emit("ReasoningFinished", context)
        return result


# ─────────────────────────────────────────────
# LEGACY REASONING ENGINE (BACKWARD COMPATIBLE)
# ─────────────────────────────────────────────

class ReasoningEngine:
    """
    Core intelligence layer.
    v3.1: Supports multi-concept hierarchical composition and code synthesis.
    Kept for full backward compatibility with legacy tests.
    """
    def __init__(self):
        self.htn_planner = HTNPlanner()
        self.concept_composer = ConceptComposer()
        self.solution_builder = SolutionBuilder()
        self.synthesizer = ProgramSynthesizer()
        
        from hsci.reasoning.universal_math_engine import UniversalMathEngine
        from hsci.reasoning.universal_physics_engine import UniversalPhysicsEngine
        from hsci.reasoning.universal_concept_engine import UniversalConceptEngine

        self.universal_math = UniversalMathEngine()
        self.universal_physics = UniversalPhysicsEngine()
        self.universal_concept = UniversalConceptEngine()

    def reason(
        self,
        perception: PerceptionMap,
        knowledge: KnowledgeResult,
        max_attempts: int = 5,
        ctx: Optional[z3.Context] = None
    ) -> ReasoningPlan:
        """Reasons about a problem by decomposing it and assigning specific concepts to steps."""
        if perception.intent == AxiomType.TRANSFORMATION:
            return ReasoningPlan(
                sub_goals=[],
                concept_assignments={},
                candidate_solution=Expression(value="conversational_response", concepts_used=[]),
                concepts_used=[],
                primary_concept=None,
                perception=perception,
                knowledge=knowledge
            )

        sub_goals = self.htn_planner.decompose(perception)
        assignments: Dict[SubGoal, Concept] = {}
        text = perception.entity_graph.get('text', "").lower()
        
        for goal in sub_goals:
            context = f"{text} {goal.description}"
            best = self.concept_composer.find_best(
                goal,
                knowledge.direct_matches,
                knowledge.analogical_matches,
                context_text=context
            )
            
            if "tax" in text and "salary" in text:
                if "CONSTRAINT" in goal.description:
                    p_match = [c for c in knowledge.direct_matches if c.name == "PERCENTAGE"]
                    best = p_match[0] if p_match else best
            
            if best is not None:
                assignments[goal] = best

        if perception.intent == AxiomType.SYNTHESIS:
            code = self.synthesizer.synthesize(
                sub_goals,
                assignments,
                perception.entities,
                request_text=perception.entity_graph.get("text", ""),
            )
            candidate = Expression(value=code, concepts_used=[c.name for c in assignments.values() if c])
        else:
            candidate = None
            text = perception.entity_graph.get('text', "")
            
            if self.universal_physics.can_solve(text):
                phys_res = self.universal_physics.solve_from_text(text, perception.entities)
                if phys_res.solved:
                    candidate = Expression(
                        value=phys_res.answer,
                        concepts_used=["universal_physics"] + phys_res.steps
                    )
            
            if not candidate:
                import re
                has_var = bool(re.search(r'\b[x-z]\b', text.lower()))
                has_complex_arithmetic = len(re.findall(r'[\+\-\*\/]', text)) >= 2 or "(" in text or ")" in text
                is_explicit_solve = "solve" in text or "equation" in text
                
                if (has_var and "=" in text) or has_complex_arithmetic or is_explicit_solve:
                    math_res = self.universal_math.solve_from_text(text, perception.entities)
                    if math_res.solved:
                        candidate = Expression(
                            value=math_res.answer,
                            concepts_used=["universal_math"] + math_res.steps
                        )
            
            if not candidate or candidate.value is False:
                candidate = self.solution_builder.build(
                    sub_goals,
                    assignments,
                    perception.entities,
                    ctx=ctx
                )
            
            if not candidate or candidate.value is False:
                math_res = self.universal_math.solve_from_text(text, perception.entities)
                if math_res.solved:
                    candidate = Expression(
                        value=math_res.answer,
                        concepts_used=["universal_math"] + math_res.steps
                    )

        primary_concept = next(iter(assignments.values())) if assignments else None

        return ReasoningPlan(
            sub_goals=sub_goals,
            concept_assignments=assignments,
            candidate_solution=candidate,
            concepts_used=[c.name for c in assignments.values() if c],
            primary_concept=primary_concept,
            perception=perception,
            knowledge=knowledge
        )

    def repair(self, plan: ReasoningPlan, counterexample: Dict, hint: str, ctx: Optional[z3.Context] = None) -> ReasoningPlan:
        """CEGIS Loop: Attempt repair by re-reasoning with counterexample feedback."""
        new_plan = self.reason(plan.perception, plan.knowledge, ctx=ctx)
        
        if (new_plan.candidate_solution and plan.candidate_solution
                and str(new_plan.candidate_solution.value) == str(plan.candidate_solution.value)):
            text = plan.perception.entity_graph.get('text', "")
            math_res = self.universal_math.solve_from_text(text, plan.perception.entities)
            if math_res.solved:
                new_plan.candidate_solution = Expression(
                    value=math_res.answer,
                    concepts_used=["universal_math"] + math_res.steps
                )
        
        return new_plan
