import z3
from datetime import datetime
from typing import Any, List, Optional, Union
from hsci.core.data_types import (
    FinalOutput, Concept, StructuredInput, AxiomType, VerificationStatus
)
from hsci.core.config import PerceiverConfig
from hsci.language.bridge import LanguageBridge
from hsci.neural.perceiver import NeuralPerceiver
from hsci.knowledge.knowledge_base import KnowledgeBase
from hsci.reasoning.reasoning_engine import ReasoningEngine
from hsci.symbolic.z3_verifier import Z3VerificationEngine
from hsci.learning.learning_engine import LearningEngine
from hsci.response.response_bridge import ResponseBridge
from hsci.self_play.engine import SelfPlayEngine

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
        self.knowledge_base = KnowledgeBase()

        # Layer 3: Reasoning Engine
        self.reasoning_engine = ReasoningEngine()

        # Layer 4: Verification Engine
        self.verifier = Z3VerificationEngine()

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

        print(f"HSCI initialized. Concepts loaded: {len(self.knowledge_base.concept_library.concepts)}")

    def process_internal(self, raw_input: str) -> FinalOutput:
        """
        Complete pipeline: raw human input → FinalOutput object.
        Internal use for metrics and showcase.
        """
        # print(f"RIRLoop: Processing input: '{raw_input}'")
        # Create transactional context
        ctx = z3.Context()

        # LAYER 0: Language Bridge
        structured = self.language_bridge.parse(raw_input)

        # Handle follow-up context
        structured_dict = self.response_bridge.conversation_manager.resolve_followup(
            raw_input, structured.__dict__.copy()
        )
        
        if structured_dict.get('is_followup'):
             structured = StructuredInput(**structured_dict)

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

            if verification.valid:
                break

            # Repair using counterexample
            if verification.counterexample:
                plan = self.reasoning_engine.repair(
                    plan,
                    verification.counterexample,
                    verification.correction_hint,
                    ctx=ctx
                )

        # LAYER 5: Learn regardless of outcome
        learning_result = self.learning_engine.learn(
            perception, plan, verification
        )

        # Build FinalOutput
        answer = self._extract_answer(verification, plan)
        
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
        if result.valid:
            if result.z3_model:
                return str(result.z3_model)
            elif plan and plan.candidate_solution:
                return plan.candidate_solution.value
        return "Unverified or Error"
