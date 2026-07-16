import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.reasoning.reasoning_engine import ReasoningResult, Conclusion, ReasoningStep

logger = logging.getLogger("HSCI.Response.AGE")

# ─────────────────────────────────────────────
# SUPPORTING MODELS
# ─────────────────────────────────────────────

class AnswerSection:
    """Represents a structured section of the final formatted user response."""
    def __init__(self, title: str, content: str):
        self.title: str = title
        self.content: str = content

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "content": self.content}

class Explanation:
    """Holds structured explanations justifying the generated assertions."""
    def __init__(self, reasoning_summary: str, steps_count: int):
        self.reasoning_summary: str = reasoning_summary
        self.steps_count: int = steps_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning_summary": self.reasoning_summary,
            "steps_count": self.steps_count
        }

class SupportingEvidence:
    """Maps derived conclusions to original proof paths and concept names."""
    def __init__(self, statement: str, sources: List[str]):
        self.statement: str = statement
        self.sources: List[str] = sources

    def to_dict(self) -> Dict[str, Any]:
        return {"statement": self.statement, "sources": self.sources}

class ConfidenceSummary:
    """Evaluates and captures the final aggregated verification score."""
    def __init__(self, score: float, description: str):
        self.score: float = score
        self.description: str = description

    def to_dict(self) -> Dict[str, Any]:
        return {"score": self.score, "description": self.description}

class AnswerMetadata:
    """Metadata tracking latency durations and referenced concept names."""
    def __init__(self, activation_concepts: List[str], execution_time_ms: float):
        self.activation_concepts: List[str] = activation_concepts
        self.execution_time_ms: float = execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activation_concepts": self.activation_concepts,
            "execution_time_ms": self.execution_time_ms
        }

class Answer:
    """The final structured package returned by the AGE."""
    def __init__(self, direct_answer: str, sections: List[AnswerSection],
                 explanation: Explanation, evidence: List[SupportingEvidence],
                 confidence: ConfidenceSummary, metadata: AnswerMetadata,
                 assumptions: List[str], known_limitations: List[str]):
        self.direct_answer: str = direct_answer
        self.sections: List[AnswerSection] = sections
        self.explanation: Explanation = explanation
        self.evidence: List[SupportingEvidence] = evidence
        self.confidence: ConfidenceSummary = confidence
        self.metadata: AnswerMetadata = metadata
        self.assumptions: List[str] = assumptions
        self.known_limitations: List[str] = known_limitations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direct_answer": self.direct_answer,
            "sections": [s.to_dict() for s in self.sections],
            "explanation": self.explanation.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence.to_dict(),
            "metadata": self.metadata.to_dict(),
            "assumptions": self.assumptions,
            "known_limitations": self.known_limitations
        }


# ─────────────────────────────────────────────
# AGE INTERFACE
# ─────────────────────────────────────────────

class IAnswerGenerationEngine(ABC):
    """Abstract interface defining the response generation pipeline."""
    @abstractmethod
    def generate(self, result: ReasoningResult, context: CognitiveContext,
                 style: str = "Standard") -> Answer:
        pass


# ─────────────────────────────────────────────
# AGE IMPLEMENTATION
# ─────────────────────────────────────────────

class AnswerGenerationEngine(IAnswerGenerationEngine):
    """
    Converts verified reasoning result trace trees into structured,
    explainable markdown and textual outputs.
    """
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus: Optional[EventBus] = event_bus

    def generate(self, result: ReasoningResult, context: CognitiveContext,
                 style: str = "Standard") -> Answer:
        """Translates ReasoningResult into formatted Answer payload."""
        if self.event_bus:
            self.event_bus.emit("AnswerGenerationStarted", context)

        # Stage 1 & 2 & 4: Read and collect conclusions/evidence
        conclusions = result.conclusions
        evidence_list = []
        for c in conclusions:
            evidence_list.append(SupportingEvidence(c.statement, c.evidence))

        # Handle Errors & Constraints
        # Empty/Low confidence checks
        if not conclusions:
            err_answer = self._generate_error_response("No verified conclusions could be established.", style)
            if self.event_bus:
                self.event_bus.emit("AnswerGenerationFailed", context)
            return err_answer

        if result.contradictions:
            err_answer = self._generate_error_response(
                f"Contradictory findings detected: {result.contradictions[0]}", style
            )
            if self.event_bus:
                self.event_bus.emit("AnswerGenerationFailed", context)
            return err_answer

        # Stage 3: Order conclusions by importance
        # Priority heuristic: shorter statements first or those with higher confidence
        sorted_conclusions = sorted(conclusions, key=lambda x: (-x.confidence, len(x.statement)))

        # Stage 5 & 6: Generate explanation structure and confidence summary
        sections = []
        direct_answer = ""
        
        # Aggregate active concept list from working memory
        wm = context.working_memory
        active_concept_names = list(wm.activation_field.activation_strengths.keys()) if hasattr(wm, 'activation_field') else []

        if style == "Standard":
            direct_answer = "Based on formal reasoning, we verified the following connections:"
            content = "\n".join([f"- {c.statement}" for c in sorted_conclusions])
            sections.append(AnswerSection("Verified Connections", content))
            
        elif style == "Step-by-Step":
            direct_answer = "The reasoning path resolved through these sequential steps:"
            step_content = []
            for step in result.reasoning_trace.steps:
                step_content.append(f"Step {step.step_number}: {step.action}")
                for c in step.conclusions:
                    step_content.append(f"  -> Concluded: {c}")
            sections.append(AnswerSection("Reasoning Steps", "\n".join(step_content)))
            
        elif style == "Technical":
            direct_answer = "Technical logic trace verification details:"
            tech_content = []
            for c in sorted_conclusions:
                tech_content.append(f"Statement: {c.statement}")
                tech_content.append(f"  Confidence: {c.confidence:.2f}")
                tech_content.append(f"  Evidence: {', '.join(c.evidence)}")
            sections.append(AnswerSection("Formal Logic Log", "\n".join(tech_content)))

        # Confidence Summary
        conf_desc = "High" if result.confidence >= 0.80 else "Medium" if result.confidence >= 0.50 else "Low"
        confidence_summary = ConfidenceSummary(result.confidence, conf_desc)

        # Stage 7: Reasoning summary
        explanation = Explanation(
            reasoning_summary=f"Successfully verified {len(conclusions)} assertions in {len(result.reasoning_trace.steps)} iterations.",
            steps_count=len(result.reasoning_trace.steps)
        )

        metadata = AnswerMetadata(
            activation_concepts=active_concept_names,
            execution_time_ms=5.0 # Mock or pass elapsed time if desired
        )

        # Assumptions & Limitations
        assumptions = [a.statement for a in result.assumptions] if result.assumptions else []
        limitations = []
        if result.confidence < 0.60:
            limitations.append("Calculated confidence is below threshold; findings may be partial.")

        # Stage 8: Final Answer Object
        ans = Answer(
            direct_answer=direct_answer,
            sections=sections,
            explanation=explanation,
            evidence=evidence_list,
            confidence=confidence_summary,
            metadata=metadata,
            assumptions=assumptions,
            known_limitations=limitations
        )

        if self.event_bus:
            self.event_bus.emit("AnswerGenerated", context)
        return ans

    def _generate_error_response(self, error_message: str, style: str) -> Answer:
        """Returns a structured answer for error cases."""
        sections = [AnswerSection("Error Details", error_message)]
        return Answer(
            direct_answer="Reasoning Engine was unable to resolve the query.",
            sections=sections,
            explanation=Explanation("Reasoning failed.", 0),
            evidence=[],
            confidence=ConfidenceSummary(0.0, "None"),
            metadata=AnswerMetadata([], 0.0),
            assumptions=[],
            known_limitations=["Reasoning failed to converge."]
        )
