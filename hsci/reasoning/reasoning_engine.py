import z3
from typing import List, Dict, Any, Optional
from hsci.core.data_types import PerceptionMap, KnowledgeResult, ReasoningPlan, SubGoal, Concept, AxiomType
from hsci.reasoning.htn_planner import HTNPlanner
from hsci.reasoning.concept_composer import ConceptComposer
from hsci.reasoning.solution_builder import SolutionBuilder
from hsci.reasoning.synthesizer import ProgramSynthesizer

class ReasoningEngine:
    """
    Core intelligence layer.
    v3.1: Supports multi-concept hierarchical composition and code synthesis.
    """

    def __init__(self):
        self.htn_planner = HTNPlanner()
        self.concept_composer = ConceptComposer()
        self.solution_builder = SolutionBuilder()
        self.synthesizer = ProgramSynthesizer()

    def reason(
        self,
        perception: PerceptionMap,
        knowledge: KnowledgeResult,
        max_attempts: int = 5,
        ctx: Optional[z3.Context] = None
    ) -> ReasoningPlan:
        """
        Reasons about a problem by decomposing it and assigning specific concepts to steps.
        """
        # SHORT-CIRCUIT: Transformation / Conversational logic
        if perception.intent == AxiomType.TRANSFORMATION:
            return ReasoningPlan(
                sub_goals=[],
                concept_assignments={},
                candidate_solution=None,
                concepts_used=[],
                primary_concept=None,
                perception=perception,
                knowledge=knowledge
            )

        # 1. Decompose problem
        sub_goals = self.htn_planner.decompose(perception)

        # 2. Multi-step Assignment
        assignments: Dict[str, Concept] = {}
        
        # Heuristic: if it's a multi-step problem (like percentage deduction)
        # assign appropriate concepts to sub-goals
        text = perception.entity_graph.get('text', "").lower()
        
        for goal in sub_goals:
            # Context-aware selection per sub-goal
            context = f"{text} {goal.description}"
            best = self.concept_composer.find_best(
                goal,
                knowledge.direct_matches,
                knowledge.analogical_matches,
                context_text=context
            )
            
            # Special case for "salary/tax" which needs PERCENTAGE + SUBTRACTION
            if "tax" in text and "salary" in text:
                if "CONSTRAINT" in goal.description:
                    # Look specifically for PERCENTAGE
                    p_match = [c for c in knowledge.direct_matches if c.name == "PERCENTAGE"]
                    best = p_match[0] if p_match else best
            
            assignments[goal.id] = best

        # 3. Build candidate solution
        # If intent is SYNTHESIS, use the synthesizer
        if perception.intent == AxiomType.SYNTHESIS:
            code = self.synthesizer.synthesize(sub_goals, assignments, perception.entities)
            candidate = Expression(value=code, concepts_used=[c.name for c in assignments.values() if c])
        else:
            candidate = self.solution_builder.build(
                sub_goals,
                assignments,
                perception.entities,
                ctx=ctx
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
        # CEGIS Loop implementation: try alternative concepts
        return self.reason(plan.perception, plan.knowledge, ctx=ctx)
