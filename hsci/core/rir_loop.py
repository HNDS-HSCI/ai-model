import z3
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from hsci.core.data_types import (
    FinalOutput, Concept, StructuredInput, AxiomType, VerificationStatus, MethodSource
)
from hsci.core.config import PerceiverConfig
from hsci.language.bridge import LanguageBridge
from hsci.neural.perceiver import NeuralPerceiver
from hsci.knowledge.knowledge_base import KnowledgeBase
from hsci.reasoning.reasoning_engine import ReasoningEngine
from hsci.symbolic.z3_verifier import Z3VerificationEngine
from hsci.learning.learning_engine import LearningEngine
from hsci.response.response_bridge import ResponseBridge
from prototype.hsci_perception.self_play_engine import SelfPlayEngine
from hsci.training.weight_persistence import WeightPersistence  # Phase 5

class RIRLoop:
    """
    Main Orchestrator — Reinforced Intuitive Reasoning Loop (v3.0)
    Coordinates all 7 layers + background self-play.
    Single entry point for all interactions.
    """

    def __init__(self, use_llm: bool = False):
        print("Initializing HSCI v3.0...")

        # Layer 0: Language Bridge
        self.language_bridge = LanguageBridge(use_llm=use_llm)

        # Layer 1: Neural Perceiver
        self.perceiver = NeuralPerceiver(PerceiverConfig())

        # Layer 2: Knowledge Base
        self.knowledge_base = KnowledgeBase(seed=True)

        # Layer 3: Reasoning Engine
        self.reasoning_engine = ReasoningEngine()

        # Layer 4: Verification Engine
        self.verifier = Z3VerificationEngine()

        # Layer 4C: Skill Learning Engine
        from hsci.learning.skill_learning_engine import SkillLearningEngine
        self.skill_learning_engine = SkillLearningEngine(
            planner=self.reasoning_engine.htn_planner,
            verifier=self.verifier
        )

        # Layer 5: Learning Engine
        self.learning_engine = LearningEngine(
            self.perceiver,
            self.knowledge_base
        )

        # Layer 6: Response Bridge

        self.response_bridge = ResponseBridge()

        # Background: Self-Play
        self.self_play = SelfPlayEngine(
            self.knowledge_base,
            self.reasoning_engine,
            self.verifier,
            self.learning_engine
        )
        self.self_play.start()

        # Phase 5: Auto-load persisted neural weights
        self._weight_persistence = WeightPersistence()
        self._weight_persistence.load(self.perceiver)

        print(f"HSCI initialized. Concepts loaded: {len(self.knowledge_base.concept_library.concepts)}")
        print(f"  Neural classifier proof count: {self.perceiver.intent_classifier.proof_count}")
        print(f"  Weight version: {self.perceiver.weight_version}")

    def process_internal(self, raw_input: str, context: Optional[Dict[str, Any]] = None) -> FinalOutput:
        """
        Complete pipeline: raw human input → FinalOutput object.
        Internal use for metrics, showcase, and benchmarks.
        """
        # print(f"RIRLoop: Processing input: '{raw_input}'")
        # Create transactional context
        ctx = z3.Context()

        # LAYER 0: Language Bridge
        structured = self.language_bridge.parse(raw_input)
        if context:
            structured.entities.update(context)

        # Handle follow-up context
        structured_dict = self.response_bridge.conversation_manager.resolve_followup(
            raw_input, structured.__dict__.copy()
        )
        
        if structured_dict.get('is_followup'):
             structured = StructuredInput(**structured_dict)

        # Intercept Concept Definition learning
        if self.reasoning_engine.universal_concept.can_learn(raw_input):
            new_concept = self.reasoning_engine.universal_concept.learn_concept(
                raw_input, self.knowledge_base.concept_library
            )
            if new_concept:
                final_out = FinalOutput(
                    answer=f"Successfully learned new concept {new_concept.name}: {new_concept.abstract_rule}",
                    is_verified=True,
                    confidence=1.0,
                    concepts_used=["universal_concept"],
                    reasoning_trace=["Autonomous Concept Acquisition: Extracted definition and registered in Knowledge Base."],
                    proof=None
                )
                return final_out, structured

        # LAYER 1: Neural Perceiver
        perception = self.perceiver.perceive(structured)

        # LAYER 2: Retrieve knowledge
        knowledge = self.knowledge_base.query(perception)

        # LAYER 3: Initial reasoning
        plan = self.reasoning_engine.reason(perception, knowledge, ctx=ctx)

        # LAYERS 3+4: CEGIS repair loop
        verification = None
        attempt = 0
        for attempt in range(5):
            primary_concept = plan.primary_concept
            if not primary_concept and plan.concept_assignments:
                 primary_concept = list(plan.concept_assignments.values())[0]

            verification = self.verifier.verify(
                plan.candidate_solution,
                perception,
                primary_concept,
                ctx=ctx
            )

            if verification.valid or perception.intent in [AxiomType.SYNTHESIS, AxiomType.TRANSFORMATION]:
                break

            # Repair using counterexample
            if verification.counterexample:
                plan = self.reasoning_engine.repair(
                    plan,
                    verification.counterexample,
                    verification.correction_hint,
                    ctx=ctx
                )

        # Reflect on final verification failure if not valid
        if verification and not verification.valid and perception.intent not in [AxiomType.SYNTHESIS, AxiomType.TRANSFORMATION]:
            if hasattr(self.reasoning_engine, "reflection_engine"):
                ref_res = self.reasoning_engine.reflection_engine.reflect_verification_failure(verification)
                # Reflection recorded deterministically without mutating plan or weights

        # LAYER 5: Learn regardless of outcome

        learning_result = self.learning_engine.learn(
            perception, plan, verification
        )

        # Update SkillUtilityStore & SkillLifecycleManager based on final Z3 formal verification outcome (SCG4 exact trace attribution)
        from hsci.memory.skill_utility import SkillUtilityStore
        from hsci.memory.skill_lifecycle import SkillLifecycleManager
        utility_store = SkillUtilityStore()
        lifecycle_mgr = SkillLifecycleManager()
        outcome_key = "VERIFIED_SUCCESS" if (verification and verification.valid) else "VERIFICATION_FAILURE"

        # SCG4.2: Exact attribution & reconciliation across both direct MethodRegistry and SkillGraph execution paths
        if plan and hasattr(plan, "planning_trace") and plan.planning_trace:
            trace = plan.planning_trace
            req_id = getattr(self.reasoning_engine, "last_request_id", None)
            htn_planner = getattr(self.reasoning_engine, "htn_planner", None)
            method_registry = getattr(htn_planner, "method_registry", None) if htn_planner else None
            skill_graph = getattr(htn_planner, "skill_graph", None) if htn_planner else None

            # 1. Update Graph Utility Store for graph nodes
            if trace.executed_graph_node_ids:
                for node_id in trace.executed_graph_node_ids:
                    utility_store.record_outcome(node_id, outcome_key)

            # 2. Reconcile and deduplicate executed LEARNED skill IDs across both direct and graph paths
            executed_learned_skills: Dict[str, MethodSource] = {}

            # Collect from direct executed_method_ids
            for mid in (trace.executed_method_ids or []):
                # Check MethodRegistry first for method object and source
                m_obj = method_registry.get_method(mid) if method_registry else None
                source = getattr(m_obj, "source", None) if m_obj else None
                if source == MethodSource.LEARNED:
                    executed_learned_skills[mid] = MethodSource.LEARNED

            # Collect from executed_graph_node_ids
            for nid in (trace.executed_graph_node_ids or []):
                source = MethodSource.LEARNED
                if skill_graph and nid in skill_graph.nodes:
                    source = skill_graph.nodes[nid].source
                if source == MethodSource.LEARNED:
                    # Strip 'node-' prefix if node_id was formatted as 'node-method_id'
                    clean_id = nid[5:] if nid.startswith("node-") else nid
                    executed_learned_skills[clean_id] = MethodSource.LEARNED

            # 3. Record lifecycle outcome exactly ONCE per executed learned skill
            for skill_id, source in executed_learned_skills.items():
                lifecycle_mgr.record_skill_outcome(skill_id, source, outcome_key, request_id=req_id)

        # Build FinalOutput with Strict Formal Verification Authority (NSG-3.1)
        if (verification and verification.valid) or perception.intent in [AxiomType.SYNTHESIS, AxiomType.TRANSFORMATION]:
            if perception.intent == AxiomType.SYNTHESIS and plan.candidate_solution:
                answer = plan.candidate_solution.value
            else:
                answer = self._extract_answer(verification, plan)
        else:
            answer = None
        
        trace_steps = []
        if verification.proof_trace:
            for step in verification.proof_trace.steps:
                # step is ProofStep
                trace_steps.append(f"{step.operation}: {step.output_value}")
        else:
            trace_steps = ["Reasoning failed to verify."]

        final_out = FinalOutput(
            answer=answer,
            is_verified=verification.valid,
            confidence=verification.confidence,
            concepts_used=plan.concepts_used,
            reasoning_trace=trace_steps,
            proof=verification.proof_trace,
            new_concept_learned=learning_result.new_concept.name if learning_result.new_concept else None,
            counterexample=verification.counterexample,
            correction_hint=verification.correction_hint,
            attempts=attempt + 1
        )
        
        return final_out, structured

    def process(self, raw_input: str) -> str:
        """
        Complete pipeline: raw human input → natural language response.
        """
        final_out, structured = self.process_internal(raw_input)

        # Ensure concepts_used is passed for UI/Response logic
        # ResponseBridge uses final_output properties to generate text
        
        # LAYER 6: Response Bridge
        response = self.response_bridge.generate(final_out, raw_input, structured.domain)
        
        # Update history
        self.response_bridge.conversation_manager.add_turn(structured, final_out, response)

        return response

    def _extract_answer(self, result, plan=None) -> Any:
        """Extract the most meaningful answer from verification result."""
        if result.valid:
            # Priority 1: Check proof trace variable assignments
            if result.proof_trace and result.proof_trace.variable_assignments:
                vars_dict = result.proof_trace.variable_assignments
                for key in ['total_quantity', 'result', 'answer', 'x', 'y']:
                    if key in vars_dict:
                        return vars_dict[key]
                if vars_dict:
                    first_val = next(iter(vars_dict.values()))
                    if first_val and str(first_val) != 'dummy_solution_expression':
                        return first_val
            
            # Priority 2: Z3 model
            if result.z3_model:
                return str(result.z3_model)
            
            # Priority 3: Candidate solution value (but skip dummy/sentinel values)
            if plan and plan.candidate_solution:
                val = plan.candidate_solution.value
                if val is not None and val is not False and str(val) not in ['dummy_solution_expression', 'False']:
                    return val
                    
            # Priority 4: Conversational/transformation response
            if plan and plan.candidate_solution and str(plan.candidate_solution.value) == 'conversational_response':
                return "conversational_response"
        
        return None

    def save_weights(self):
        """Phase 5: Manually trigger weight save."""
        self._weight_persistence.save(self.perceiver)

    def get_neural_stats(self) -> dict:
        """Return current neural classifier training stats."""
        return {
            "weight_version": self.perceiver.weight_version,
            "classifier": self.perceiver.intent_classifier.stats(),
        }
